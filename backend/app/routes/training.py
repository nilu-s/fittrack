from __future__ import annotations

import logging
import uuid
from datetime import date as date_type, timedelta
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import async_session
from app.models import DayEntry, Exercise, ExerciseProgress, TrainingRotation, TrainingSet
from app.routes.auth import get_current_user
from app.schemas import (
    ExerciseCreate,
    ExerciseProgressResponse,
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

    Uses the most recent day_entry with a rotation_slot before or on target_date.
    If that day was completed, advances by 1 (wrapping to 1 after 7); otherwise repeats
    the same slot so a missed session is not skipped. Falls back to slot 1 if no history.
    """
    result = await session.execute(
        select(DayEntry)
        .where(DayEntry.user_id == USER_ID, DayEntry.date <= target_date, DayEntry.rotation_slot.isnot(None))
        .order_by(desc(DayEntry.date))
        .limit(1)
    )
    last_entry = result.scalars().first()

    if last_entry and last_entry.rotation_slot is not None:
        if last_entry.training_done:
            slot = (last_entry.rotation_slot % 7) + 1  # advance
        else:
            slot = last_entry.rotation_slot  # repeat — user missed session
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
                target_reps_low=(e.target_reps_low if e.is_topset else (e.base_reps_low or e.target_reps_low)),
                target_reps_high=(e.target_reps_high if e.is_topset else (e.base_reps_high or e.target_reps_high)),
                target_weight_kg=e.target_weight_kg,
                is_topset=e.is_topset,
                target_rir=e.target_rir,
                sort_order=e.sort_order,
            )
            for e in exercises
        ],
    )


def _topset_from_sets(sets: list[Any]) -> Any:
    """Pick the top set: highest weight, then highest reps."""
    def key(s):
        return (s.weight_kg or Decimal("0"), s.reps or 0)
    return max(sets, key=key)


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
# POST /api/training/complete — save sets (upsert), apply progression, record ExerciseProgress
# ---------------------------------------------------------------------------
@router.post("/training/complete", response_model=TrainingCompleteResponse)
async def complete_training(body: TrainingCompleteRequest, user: str = Depends(get_current_user)):
    async with async_session() as session:
        # 1. Upsert all training_sets (handle unique constraint on user/date/exercise/set_number)
        saved_count = 0
        for set_item in body.sets:
            insert_stmt = pg_insert(TrainingSet).values(
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
            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=["user_id", "date", "exercise_name", "set_number"],
                set_={
                    "set_type": insert_stmt.excluded.set_type,
                    "reps": insert_stmt.excluded.reps,
                    "weight_kg": insert_stmt.excluded.weight_kg,
                    "rir": insert_stmt.excluded.rir,
                    "completed": True,
                },
            )
            await session.execute(upsert_stmt)
            saved_count += 1

        # 2. Apply progression and record ExerciseProgress for each exercise in this training_type
        ex_result = await session.execute(
            select(Exercise)
            .where(Exercise.user_id == USER_ID, Exercise.training_type == body.training_type)
            .order_by(Exercise.sort_order)
        )
        exercises = list(ex_result.scalars().all())
        progressed: list[Exercise] = []

        exercise_actuals: dict[str, list[Any]] = {}
        for s in body.sets:
            exercise_actuals.setdefault(s.exercise_name, []).append(s)

        for ex in exercises:
            actual_sets = exercise_actuals.get(ex.exercise_name, [])
            if not actual_sets:
                # No sets recorded for this exercise — skip progression/record
                progressed.append(ex)
                continue

            topset = _topset_from_sets(actual_sets)
            actual_reps = topset.reps or 0
            actual_rir = topset.rir if topset.rir is not None else 99

            prev_target_weight_kg = ex.target_weight_kg
            prev_target_reps_low = ex.target_reps_low
            progression_action = "none"

            if ex.target_reps_high is not None and ex.target_reps_low is not None:
                target_rir = ex.target_rir if ex.target_rir is not None else 2
                increment = ex.progression_increment_weight or Decimal("2.5")

                if actual_reps >= ex.target_reps_high and actual_rir <= target_rir:
                    # Increase weight; reset rep target back to base range.
                    if ex.target_weight_kg is not None:
                        ex.target_weight_kg = ex.target_weight_kg + increment
                    else:
                        ex.target_weight_kg = increment
                    progression_action = "weight_increase"
                    if ex.base_reps_low is not None and ex.base_reps_high is not None:
                        ex.target_reps_low = ex.base_reps_low
                        ex.target_reps_high = ex.base_reps_high
                elif actual_reps >= ex.target_reps_low and actual_rir <= target_rir:
                    # Increase reps by 1 (capped at high)
                    new_low = min(actual_reps + 1, ex.target_reps_high)
                    ex.target_reps_low = new_low
                    progression_action = "rep_increase"

            total_volume_kg = sum((s.weight_kg or Decimal("0")) * (s.reps or 0) for s in actual_sets)

            progress = ExerciseProgress(
                user_id=USER_ID,
                exercise_id=ex.id,
                date=body.date,
                training_type=body.training_type,
                exercise_name=ex.exercise_name,
                topset_reps=topset.reps,
                topset_weight_kg=topset.weight_kg,
                topset_rir=topset.rir,
                all_sets_reps=[
                    {
                        "set_number": s.set_number,
                        "reps": s.reps,
                        "weight_kg": float(s.weight_kg) if s.weight_kg is not None else None,
                        "rir": s.rir,
                        "set_type": s.set_type,
                    }
                    for s in sorted(actual_sets, key=lambda x: x.set_number)
                ],
                total_volume_kg=total_volume_kg,
                progression_action=progression_action,
                prev_target_weight_kg=prev_target_weight_kg,
                prev_target_reps_low=prev_target_reps_low,
                new_target_weight_kg=ex.target_weight_kg,
                new_target_reps_low=ex.target_reps_low,
            )
            session.add(progress)
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
# Exercise progress history
# ---------------------------------------------------------------------------
progress_router = APIRouter(prefix="/training/progress", tags=["training-progress"])


@progress_router.get("", response_model=list[ExerciseProgressResponse])
async def list_exercise_progress(
    exercise_name: Optional[str] = Query(None),
    from_date: Optional[date_type] = Query(None),
    to_date: Optional[date_type] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    user: str = Depends(get_current_user),
):
    async with async_session() as session:
        stmt = select(ExerciseProgress).where(ExerciseProgress.user_id == USER_ID)
        if exercise_name:
            stmt = stmt.where(ExerciseProgress.exercise_name == exercise_name)
        if from_date:
            stmt = stmt.where(ExerciseProgress.date >= from_date)
        if to_date:
            stmt = stmt.where(ExerciseProgress.date <= to_date)
        stmt = stmt.order_by(desc(ExerciseProgress.date), ExerciseProgress.exercise_name).limit(limit)
        result = await session.execute(stmt)
        return [ExerciseProgressResponse.model_validate(p) for p in result.scalars().all()]


router.include_router(progress_router)


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
