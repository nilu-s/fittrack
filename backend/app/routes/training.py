from __future__ import annotations

import logging
import uuid
from datetime import date as date_type, timedelta
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select

from app.database import async_session
from app.models import DayEntry, Exercise, TrainingRotation, TrainingSet
from app.routes.auth import get_current_user
from app.schemas import (
    ExerciseCreate,
    ExerciseResponse,
    ExerciseUpdate,
    TrainingCompleteRequest,
    TrainingCompleteResponse,
    TrainingRotationResponse,
    TrainingRotationUpdate,
    TrainingSuggestion,
    TrainingSuggestionExercise,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["training"])

USER_ID = "luis"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _get_rotation_slot_for_date(session, target_date: date_type) -> tuple[Optional[int], Optional[TrainingRotation]]:
    """Determine which rotation slot applies to a given date.

    Uses the most recent day_entry with a rotation_slot before or on target_date,
    and increments by 1 (wrapping to 1 after 7). Falls back to slot 1 if no history.
    """
    result = await session.execute(
        select(DayEntry)
        .where(DayEntry.user_id == USER_ID, DayEntry.date <= target_date, DayEntry.rotation_slot.isnot(None))
        .order_by(desc(DayEntry.date))
        .limit(1)
    )
    last_entry = result.scalars().first()

    if last_entry and last_entry.rotation_slot is not None:
        slot = (last_entry.rotation_slot % 7) + 1
    else:
        slot = 1

    rot_result = await session.execute(
        select(TrainingRotation).where(TrainingRotation.user_id == USER_ID, TrainingRotation.slot == slot)
    )
    rotation = rot_result.scalars().first()
    return slot, rotation


async def _build_suggestion(session, target_date: date_type, training_type: str, rotation_slot: Optional[int], cardio_minutes: Optional[int]) -> TrainingSuggestion:
    ex_result = await session.execute(
        select(Exercise)
        .where(Exercise.user_id == USER_ID, Exercise.training_type == training_type)
        .order_by(Exercise.sort_order)
    )
    exercises = ex_result.scalars().all()
    return TrainingSuggestion(
        date=target_date,
        training_type=training_type,
        rotation_slot=rotation_slot,
        cardio_minutes=cardio_minutes,
        exercises=[
            TrainingSuggestionExercise(
                exercise_name=e.exercise_name,
                target_sets=e.target_sets,
                target_reps_low=e.target_reps_low,
                target_reps_high=e.target_reps_high,
                target_weight_kg=e.target_weight_kg,
                is_topset=e.is_topset,
                target_rir=e.target_rir,
                sort_order=e.sort_order,
            )
            for e in exercises
        ],
    )


# ---------------------------------------------------------------------------
# GET /api/training?date=  — training for date (auto-suggest from rotation)
# ---------------------------------------------------------------------------
@router.get("/training", response_model=TrainingSuggestion)
async def get_training_for_date(date: date_type = Query(...), user: str = Depends(get_current_user)):
    async with async_session() as session:
        slot, rotation = await _get_rotation_slot_for_date(session, date)
        training_type = rotation.training_type if rotation else "Oberkörper A"
        cardio = rotation.cardio_minutes if rotation else None
        return await _build_suggestion(session, date, training_type, slot, cardio)


# ---------------------------------------------------------------------------
# GET /api/training/next?training_type=  — next training with auto-progressed values
# ---------------------------------------------------------------------------
@router.get("/training/next", response_model=TrainingSuggestion)
async def get_next_training(
    training_type: str = Query(...),
    date: Optional[date_type] = Query(None),
    user: str = Depends(get_current_user),
):
    target_date = date or date_type.today()
    async with async_session() as session:
        suggestion = await _build_suggestion(session, target_date, training_type, None, None)
        # Enrich each exercise with last-actual values from training_sets
        for ex in suggestion.exercises:
            ts_result = await session.execute(
                select(TrainingSet)
                .where(
                    TrainingSet.user_id == USER_ID,
                    TrainingSet.training_type == training_type,
                    TrainingSet.exercise_name == ex.exercise_name,
                    TrainingSet.date < target_date,
                )
                .order_by(desc(TrainingSet.date), desc(TrainingSet.set_number))
                .limit(1)
            )
            last_set = ts_result.scalars().first()
            if last_set and last_set.weight_kg is not None:
                ex.target_weight_kg = last_set.weight_kg
        return suggestion


# ---------------------------------------------------------------------------
# POST /api/training/complete — save sets, apply progression, update exercises
# ---------------------------------------------------------------------------
@router.post("/training/complete", response_model=TrainingCompleteResponse)
async def complete_training(body: TrainingCompleteRequest, user: str = Depends(get_current_user)):
    async with async_session() as session:
        # 1. Save all training_sets
        saved_count = 0
        exercise_actuals: dict[str, list[TrainingSet]] = {}

        for set_item in body.sets:
            ts = TrainingSet(
                user_id=USER_ID,
                date=body.date,
                training_type=body.training_type,
                exercise_name=set_item.exercise_name,
                set_number=set_item.set_number,
                set_type=set_item.set_type or "work",
                reps=set_item.reps,
                weight_kg=set_item.weight_kg,
                rir=set_item.rir,
                completed=True,
            )
            session.add(ts)
            saved_count += 1
            exercise_actuals.setdefault(set_item.exercise_name, []).append(ts)

        await session.flush()

        # 2. Apply progression for each exercise in this training_type
        ex_result = await session.execute(
            select(Exercise)
            .where(Exercise.user_id == USER_ID, Exercise.training_type == body.training_type)
            .order_by(Exercise.sort_order)
        )
        exercises = list(ex_result.scalars().all())
        progressed: list[Exercise] = []

        for ex in exercises:
            actual_sets = exercise_actuals.get(ex.exercise_name, [])
            if not actual_sets:
                # No sets recorded for this exercise — skip progression
                progressed.append(ex)
                continue

            # Use the first set (topset) for progression decisions
            topset = actual_sets[0]
            actual_reps = topset.reps or 0
            actual_rir = topset.rir if topset.rir is not None else 99

            if ex.target_reps_high is None or ex.target_reps_low is None:
                progressed.append(ex)
                continue

            target_rir = ex.target_rir if ex.target_rir is not None else 2
            increment = ex.progression_increment_weight or Decimal("2.5")

            if actual_reps >= ex.target_reps_high and actual_rir <= target_rir:
                # Increase weight, reset reps to low
                if ex.target_weight_kg is not None:
                    ex.target_weight_kg = ex.target_weight_kg + increment
                else:
                    ex.target_weight_kg = increment
                # Reps target stays at target_reps_low (the low end)
            elif actual_reps >= ex.target_reps_low and actual_rir <= target_rir:
                # Increase reps by 1 (capped at high)
                # For progression tracking we bump the effective low target
                new_low = min(actual_reps + 1, ex.target_reps_high)
                ex.target_reps_low = new_low
            # else: no progression

            progressed.append(ex)

        await session.flush()

        # 3. Mark day_entries.training_done = True
        day_result = await session.execute(
            select(DayEntry).where(DayEntry.user_id == USER_ID, DayEntry.date == body.date)
        )
        day_entry = day_result.scalars().first()
        if day_entry is None:
            day_entry = DayEntry(user_id=USER_ID, date=body.date, training_done=True, training_type=body.training_type)
            session.add(day_entry)
        else:
            day_entry.training_done = True
            day_entry.training_type = body.training_type

        await session.commit()

        # 4. Build next training suggestion (next rotation slot)
        slot, rotation = await _get_rotation_slot_for_date(session, body.date + timedelta(days=1))
        next_type = rotation.training_type if rotation else body.training_type
        next_cardio = rotation.cardio_minutes if rotation else None
        next_suggestion = await _build_suggestion(session, body.date + timedelta(days=1), next_type, slot, next_cardio)

        return TrainingCompleteResponse(
            saved=saved_count,
            progressed_exercises=[ExerciseResponse.model_validate(e) for e in progressed],
            next_training=next_suggestion.model_dump(mode="json"),
        )


# ---------------------------------------------------------------------------
# Exercise endpoints:  /api/exercises
# ---------------------------------------------------------------------------
exercises_router = APIRouter(prefix="/exercises", tags=["exercises"])


@exercises_router.get("", response_model=list[ExerciseResponse])
async def list_exercises(training_type: Optional[str] = Query(None), user: str = Depends(get_current_user)):
    async with async_session() as session:
        stmt = select(Exercise).where(Exercise.user_id == USER_ID)
        if training_type:
            stmt = stmt.where(Exercise.training_type == training_type)
        stmt = stmt.order_by(Exercise.sort_order)
        result = await session.execute(stmt)
        exercises = result.scalars().all()
        return [ExerciseResponse.model_validate(e) for e in exercises]


@exercises_router.post("", response_model=ExerciseResponse, status_code=201)
async def create_exercise(body: ExerciseCreate, user: str = Depends(get_current_user)):
    async with async_session() as session:
        ex = Exercise(**body.model_dump())
        session.add(ex)
        await session.commit()
        await session.refresh(ex)
        return ExerciseResponse.model_validate(ex)


@exercises_router.put("/{exercise_id}", response_model=ExerciseResponse)
async def update_exercise(exercise_id: uuid.UUID, body: ExerciseUpdate, user: str = Depends(get_current_user)):
    async with async_session() as session:
        result = await session.execute(select(Exercise).where(Exercise.id == exercise_id))
        ex = result.scalars().first()
        if ex is None:
            raise HTTPException(status_code=404, detail="Exercise not found")
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(ex, field, value)
        await session.commit()
        await session.refresh(ex)
        return ExerciseResponse.model_validate(ex)


router.include_router(exercises_router)


# ---------------------------------------------------------------------------
# Rotation template endpoints:  /api/templates/rotation
# ---------------------------------------------------------------------------
rotation_router = APIRouter(prefix="/templates/rotation", tags=["rotation"])


@rotation_router.get("", response_model=list[TrainingRotationResponse])
async def list_rotation(user: str = Depends(get_current_user)):
    async with async_session() as session:
        result = await session.execute(
            select(TrainingRotation).where(TrainingRotation.user_id == USER_ID).order_by(TrainingRotation.slot)
        )
        entries = result.scalars().all()
        return [TrainingRotationResponse.model_validate(r) for r in entries]


@rotation_router.put("/{slot}", response_model=TrainingRotationResponse)
async def update_rotation(slot: int, body: TrainingRotationUpdate, user: str = Depends(get_current_user)):
    async with async_session() as session:
        result = await session.execute(
            select(TrainingRotation).where(TrainingRotation.user_id == USER_ID, TrainingRotation.slot == slot)
        )
        rot = result.scalars().first()
        if rot is None:
            raise HTTPException(status_code=404, detail="Rotation slot not found")
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(rot, field, value)
        await session.commit()
        await session.refresh(rot)
        return TrainingRotationResponse.model_validate(rot)


router.include_router(rotation_router)