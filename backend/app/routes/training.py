from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import date as date_type, timedelta
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import async_session
from app.models import DayEntry, Exercise, ExerciseProgress, TrainingRotation, TrainingSet, TrainingUnit
from app.routes.auth import get_current_user
from app.services.ownership import current_account_id
from app.schemas import (
    ExerciseCreate,
    ExerciseProgressResponse,
    ExerciseResponse,
    ExerciseUpdate,
    TrainingCompleteRequest,
    TrainingCompleteResponse,
    TrainingRotationCreate,
    TrainingRotationResponse,
    TrainingRotationUpdate,
    TrainingUnitCreate,
    TrainingUnitResponse,
    TrainingUnitUpdate,
    TrainingSuggestion,
    TrainingSuggestionExercise,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["training"])


def _account_id():
    account_id = current_account_id()
    if account_id is None:
        raise RuntimeError("training access requires an account scope")
    return account_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _get_rotation_slot_for_date(session, target_date: date_type) -> tuple[Optional[int], Optional[TrainingRotation]]:
    """Determine which rotation slot applies to a given date.

    Uses the most recent day_entry with a rotation_slot before or on target_date.
    If that day was completed, advances by 1 (wrapping to 1 after 7); otherwise repeats
    the same slot so a missed session is not skipped. Falls back to slot 1 if no history.
    """
    configured_result = await session.execute(
        select(TrainingRotation)
        .join(
            TrainingUnit,
            (TrainingUnit.account_id == TrainingRotation.account_id) & (TrainingUnit.name == TrainingRotation.training_type),
        )
        .where(TrainingRotation.account_id == _account_id(), TrainingRotation.weekday.isnot(None), TrainingUnit.is_active.is_(True))
        .order_by(TrainingRotation.slot)
    )
    configured = configured_result.scalars().all()
    if configured:
        for rotation in configured:
            if rotation.start_date and target_date < rotation.start_date:
                continue
            anchor = rotation.start_date or date_type(2025, 1, 6)
            week_index = (target_date - anchor).days // 7
            frequency = max(rotation.frequency_weeks or 1, 1)
            active_week = (week_index - (rotation.week_offset or 0)) % frequency == 0
            if rotation.weekday == target_date.weekday() and active_week:
                return rotation.slot, rotation
        return None, None

    result = await session.execute(
        select(DayEntry)
        .where(DayEntry.account_id == _account_id(), DayEntry.date <= target_date, DayEntry.rotation_slot.isnot(None))
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
        select(TrainingRotation).where(TrainingRotation.account_id == _account_id(), TrainingRotation.slot == slot)
    )
    rotation = rot_result.scalars().first()
    return slot, rotation


async def _build_suggestion(session, target_date: date_type, training_type: str, rotation_slot: Optional[int], cardio_minutes: Optional[int]) -> TrainingSuggestion:
    ex_result = await session.execute(
        select(Exercise)
        .where(Exercise.account_id == _account_id(), Exercise.training_type == training_type)
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
                top_set_count=e.top_set_count,
                backoff_set_count=e.backoff_set_count,
                backoff_reps_low=e.backoff_reps_low,
                backoff_reps_high=e.backoff_reps_high,
                backoff_weight_percent=e.backoff_weight_percent,
                target_rir=e.target_rir,
                sort_order=e.sort_order,
            )
            for e in exercises
        ],
    )


@dataclass(frozen=True)
class ProgressionResult:
    action: str
    weight_kg: Decimal | None
    reps_low: int | None
    reps_high: int | None


def calculate_progression(
    *,
    strategy: str,
    actual_reps: int,
    actual_rir: int,
    target_reps_low: int | None,
    target_reps_high: int | None,
    target_rir: int,
    target_weight_kg: Decimal | None,
    increment: Decimal,
    base_reps_low: int | None,
    base_reps_high: int | None,
) -> ProgressionResult:
    """Apply exactly the progression strategy configured for one exercise."""
    result = ProgressionResult("none", target_weight_kg, target_reps_low, target_reps_high)
    if target_reps_low is None or target_reps_high is None or actual_rir > target_rir:
        return result

    reached_high = actual_reps >= target_reps_high
    reached_low = actual_reps >= target_reps_low
    if strategy == "weight_increase":
        return ProgressionResult(
            "weight_increase" if reached_high else "none",
            (target_weight_kg or Decimal("0")) + increment if reached_high else target_weight_kg,
            target_reps_low,
            target_reps_high,
        )
    if strategy == "reps_only":
        return ProgressionResult(
            "rep_increase" if reached_low and not reached_high else "none",
            target_weight_kg,
            min(actual_reps + 1, target_reps_high) if reached_low and not reached_high else target_reps_low,
            target_reps_high,
        )
    if reached_high:
        return ProgressionResult(
            "weight_increase",
            (target_weight_kg or Decimal("0")) + increment,
            base_reps_low if base_reps_low is not None else target_reps_low,
            base_reps_high if base_reps_high is not None else target_reps_high,
        )
    if reached_low:
        return ProgressionResult("rep_increase", target_weight_kg, min(actual_reps + 1, target_reps_high), target_reps_high)
    return result


def _topset_from_sets(sets: list[Any]) -> Any:
    """Prefer a marked top set; otherwise use the heaviest completed set."""
    marked = [set_item for set_item in sets if set_item.set_type == "top"]
    candidates = marked or sets
    return max(candidates, key=lambda set_item: (set_item.weight_kg or Decimal("0"), set_item.reps or 0))


def _validate_exercise_plan(exercise: Exercise) -> None:
    try:
        set_count = int(exercise.target_sets)
    except (TypeError, ValueError) as error:
        raise ValueError("Set count must be a whole number") from error
    if not 1 <= set_count <= 20:
        raise ValueError("Set count must be between 1 and 20")
    if exercise.target_reps_low is None or exercise.target_reps_high is None or exercise.target_reps_low > exercise.target_reps_high:
        raise ValueError("Target reps need a valid range")
    if exercise.target_rir is not None and not 0 <= exercise.target_rir <= 5:
        raise ValueError("Target RIR must be between 0 and 5")
    if not exercise.is_topset:
        return
    if exercise.top_set_count != 1:
        raise ValueError("Top-set plans use exactly one top set")
    if not 0 <= exercise.backoff_set_count <= 5:
        raise ValueError("Top-set plans allow up to five back-off sets")
    if exercise.top_set_count + exercise.backoff_set_count != set_count:
        raise ValueError("Top and back-off set counts must equal the total set count")
    if exercise.backoff_set_count > 0 and (
        exercise.backoff_reps_low is None
        or exercise.backoff_reps_high is None
        or exercise.backoff_reps_low > exercise.backoff_reps_high
        or exercise.backoff_weight_percent is None
        or not 50 <= exercise.backoff_weight_percent <= 99
    ):
        raise ValueError("Back-off sets need a valid rep range and 50–99% weight")


def _validate_topset_plan(exercise: Exercise) -> None:
    try:
        _validate_exercise_plan(exercise)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


async def _require_active_training_unit(session, training_type: str) -> None:
    unit = (await session.execute(
        select(TrainingUnit).where(TrainingUnit.account_id == _account_id(), TrainingUnit.name == training_type, TrainingUnit.is_active.is_(True))
    )).scalars().first()
    if unit is None:
        raise HTTPException(status_code=422, detail="training_type must reference an active training unit")


# ---------------------------------------------------------------------------
# GET /api/training?date=  — training for date (auto-suggest from rotation)
# ---------------------------------------------------------------------------
@router.get("/training", response_model=TrainingSuggestion)
async def get_training_for_date(date: date_type = Query(...), user: str = Depends(get_current_user)):
    async with async_session() as session:
        slot, rotation = await _get_rotation_slot_for_date(session, date)
        training_type = rotation.training_type if rotation else "Ruhetag"
        unit_result = await session.execute(select(TrainingUnit).where(TrainingUnit.account_id == _account_id(), TrainingUnit.name == training_type))
        unit = unit_result.scalars().first()
        cardio = unit.cardio_minutes if unit and unit.unit_type == "cardio" else None
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
        unit = (await session.execute(select(TrainingUnit).where(TrainingUnit.account_id == _account_id(), TrainingUnit.name == training_type))).scalars().first()
        cardio_minutes = unit.cardio_minutes if unit and unit.unit_type == "cardio" else None
        return await _build_suggestion(session, target_date, training_type, None, cardio_minutes)


# ---------------------------------------------------------------------------
# POST /api/training/complete — save sets (upsert), apply progression, record ExerciseProgress
# ---------------------------------------------------------------------------
@router.post("/training/complete", response_model=TrainingCompleteResponse)
async def complete_training(body: TrainingCompleteRequest, user: str = Depends(get_current_user)):
    if body.cardio_minutes is not None and body.cardio_minutes < 0:
        raise HTTPException(status_code=422, detail="cardio_minutes must not be negative")
    async with async_session() as session:
        # 1. Upsert all training_sets (handle unique constraint on user/date/exercise/set_number)
        saved_count = 0
        for set_item in body.sets:
            insert_stmt = pg_insert(TrainingSet).values(
                account_id=_account_id(),
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
                index_elements=["account_id", "date", "exercise_name", "set_number"],
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
            .where(Exercise.account_id == _account_id(), Exercise.training_type == body.training_type)
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
            progression = calculate_progression(
                strategy=ex.progression_strategy or "double_progression",
                actual_reps=actual_reps,
                actual_rir=actual_rir,
                target_reps_low=ex.target_reps_low,
                target_reps_high=ex.target_reps_high,
                target_rir=ex.target_rir if ex.target_rir is not None else 2,
                target_weight_kg=ex.target_weight_kg,
                increment=ex.progression_increment_weight or Decimal("2.5"),
                base_reps_low=ex.base_reps_low,
                base_reps_high=ex.base_reps_high,
            )
            ex.target_weight_kg = progression.weight_kg
            ex.target_reps_low = progression.reps_low
            ex.target_reps_high = progression.reps_high
            progression_action = progression.action

            total_volume_kg = sum((s.weight_kg or Decimal("0")) * (s.reps or 0) for s in actual_sets)

            progress_values = {
                "account_id": _account_id(),
                "exercise_id": ex.id,
                "date": body.date,
                "training_type": body.training_type,
                "exercise_name": ex.exercise_name,
                "topset_reps": topset.reps,
                "topset_weight_kg": topset.weight_kg,
                "topset_rir": topset.rir,
                "all_sets_reps": [
                    {"set_number": s.set_number, "reps": s.reps, "weight_kg": float(s.weight_kg) if s.weight_kg is not None else None, "rir": s.rir, "set_type": s.set_type}
                    for s in sorted(actual_sets, key=lambda x: x.set_number)
                ],
                "total_volume_kg": total_volume_kg,
                "progression_action": progression_action,
                "prev_target_weight_kg": prev_target_weight_kg,
                "prev_target_reps_low": prev_target_reps_low,
                "new_target_weight_kg": ex.target_weight_kg,
                "new_target_reps_low": ex.target_reps_low,
            }
            progress_insert = pg_insert(ExerciseProgress).values(**progress_values)
            await session.execute(
                progress_insert.on_conflict_do_update(
                    index_elements=["account_id", "exercise_id", "date"],
                    set_={key: progress_insert.excluded[key] for key in progress_values if key not in {"account_id", "exercise_id", "date"}},
                )
            )
            progressed.append(ex)

        await session.flush()

        # 3. Mark day_entries.training_done = True
        day_result = await session.execute(
            select(DayEntry).where(DayEntry.account_id == _account_id(), DayEntry.date == body.date)
        )
        day_entry = day_result.scalars().first()
        if day_entry is None:
            day_entry = DayEntry(
                account_id=_account_id(),
                date=body.date,
                training_done=True,
                training_type=body.training_type,
                cardio_minutes=body.cardio_minutes,
                cardio_done=body.cardio_minutes is not None,
            )
            session.add(day_entry)
        else:
            day_entry.training_done = True
            day_entry.training_type = body.training_type
            if body.cardio_minutes is not None:
                day_entry.cardio_minutes = body.cardio_minutes
                day_entry.cardio_done = True

        await session.commit()

        # 4. Build next training suggestion (next rotation slot)
        slot, rotation = await _get_rotation_slot_for_date(session, body.date + timedelta(days=1))
        next_type = rotation.training_type if rotation else body.training_type
        unit_result = await session.execute(select(TrainingUnit).where(TrainingUnit.account_id == _account_id(), TrainingUnit.name == next_type))
        unit = unit_result.scalars().first()
        next_cardio = unit.cardio_minutes if unit and unit.unit_type == "cardio" else None
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
        stmt = select(ExerciseProgress).where(ExerciseProgress.account_id == _account_id())
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
        stmt = select(Exercise).where(Exercise.account_id == _account_id())
        if training_type:
            stmt = stmt.where(Exercise.training_type == training_type)
        stmt = stmt.order_by(Exercise.sort_order)
        result = await session.execute(stmt)
        exercises = result.scalars().all()
        return [ExerciseResponse.model_validate(e) for e in exercises]


@exercises_router.post("", response_model=ExerciseResponse, status_code=201)
async def create_exercise(body: ExerciseCreate, user: str = Depends(get_current_user)):
    async with async_session() as session:
        ex = Exercise(account_id=user, **body.model_dump())
        _validate_topset_plan(ex)
        session.add(ex)
        await session.commit()
        await session.refresh(ex)
        return ExerciseResponse.model_validate(ex)


@exercises_router.put("/{exercise_id}", response_model=ExerciseResponse)
async def update_exercise(exercise_id: uuid.UUID, body: ExerciseUpdate, user: str = Depends(get_current_user)):
    async with async_session() as session:
        result = await session.execute(
            select(Exercise).where(Exercise.id == exercise_id, Exercise.account_id == user)
        )
        ex = result.scalars().first()
        if ex is None:
            raise HTTPException(status_code=404, detail="Exercise not found")
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(ex, field, value)
        _validate_topset_plan(ex)
        await session.commit()
        await session.refresh(ex)
        return ExerciseResponse.model_validate(ex)


@exercises_router.delete("/{exercise_id}", status_code=204)
async def delete_exercise(exercise_id: uuid.UUID, user: str = Depends(get_current_user)):
    async with async_session() as session:
        ex = (await session.execute(select(Exercise).where(Exercise.id == exercise_id, Exercise.account_id == _account_id()))).scalars().first()
        if ex is None:
            raise HTTPException(status_code=404, detail="Exercise not found")
        has_history = await session.scalar(select(func.count()).select_from(ExerciseProgress).where(ExerciseProgress.exercise_id == exercise_id))
        if has_history:
            raise HTTPException(status_code=409, detail="Exercise has training history and cannot be deleted")
        await session.delete(ex)
        await session.commit()


@exercises_router.put("/reorder/all", response_model=list[ExerciseResponse])
async def reorder_exercises(body: list[uuid.UUID], training_type: str = Query(...), user: str = Depends(get_current_user)):
    async with async_session() as session:
        exercises = (await session.execute(select(Exercise).where(Exercise.account_id == _account_id(), Exercise.training_type == training_type))).scalars().all()
        by_id = {exercise.id: exercise for exercise in exercises}
        if set(body) != set(by_id):
            raise HTTPException(status_code=422, detail="Exercise order must contain every exercise exactly once")
        for sort_order, exercise_id in enumerate(body):
            by_id[exercise_id].sort_order = sort_order
        await session.commit()
        return [ExerciseResponse.model_validate(by_id[exercise_id]) for exercise_id in body]


router.include_router(exercises_router)


# ---------------------------------------------------------------------------
# Training unit endpoints: /api/training-units
# ---------------------------------------------------------------------------
units_router = APIRouter(prefix="/training-units", tags=["training-units"])


@units_router.get("", response_model=list[TrainingUnitResponse])
async def list_training_units(user: str = Depends(get_current_user)):
    async with async_session() as session:
        result = await session.execute(
            select(TrainingUnit).where(TrainingUnit.account_id == _account_id()).order_by(TrainingUnit.name)
        )
        return [TrainingUnitResponse.model_validate(unit) for unit in result.scalars().all()]


@units_router.post("", response_model=TrainingUnitResponse, status_code=201)
async def create_training_unit(body: TrainingUnitCreate, user: str = Depends(get_current_user)):
    if body.unit_type not in {"gym", "cardio"}:
        raise HTTPException(status_code=422, detail="unit_type must be gym or cardio")
    if body.cardio_minutes is not None and body.cardio_minutes < 0:
        raise HTTPException(status_code=422, detail="cardio_minutes must not be negative")
    async with async_session() as session:
        unit = TrainingUnit(account_id=_account_id(), name=body.name.strip(), description=body.description, unit_type=body.unit_type, cardio_minutes=body.cardio_minutes, is_active=body.is_active)
        session.add(unit)
        await session.commit()
        await session.refresh(unit)
        return TrainingUnitResponse.model_validate(unit)


@units_router.put("/{unit_id}", response_model=TrainingUnitResponse)
async def update_training_unit(unit_id: uuid.UUID, body: TrainingUnitUpdate, user: str = Depends(get_current_user)):
    if body.unit_type is not None and body.unit_type not in {"gym", "cardio"}:
        raise HTTPException(status_code=422, detail="unit_type must be gym or cardio")
    if body.cardio_minutes is not None and body.cardio_minutes < 0:
        raise HTTPException(status_code=422, detail="cardio_minutes must not be negative")
    async with async_session() as session:
        result = await session.execute(select(TrainingUnit).where(TrainingUnit.id == unit_id, TrainingUnit.account_id == _account_id()))
        unit = result.scalars().first()
        if unit is None:
            raise HTTPException(status_code=404, detail="Training unit not found")
        old_name = unit.name
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(unit, field, value.strip() if field == "name" and isinstance(value, str) else value)
        if unit.name != old_name:
            exercises = (await session.execute(select(Exercise).where(Exercise.account_id == _account_id(), Exercise.training_type == old_name))).scalars().all()
            for exercise in exercises:
                exercise.training_type = unit.name
            rotations = (await session.execute(select(TrainingRotation).where(TrainingRotation.account_id == _account_id(), TrainingRotation.training_type == old_name))).scalars().all()
            for rotation in rotations:
                rotation.training_type = unit.name
        await session.commit()
        await session.refresh(unit)
        return TrainingUnitResponse.model_validate(unit)


@units_router.delete("/{unit_id}", response_model=TrainingUnitResponse)
async def archive_training_unit(unit_id: uuid.UUID, user: str = Depends(get_current_user)):
    async with async_session() as session:
        unit = (await session.execute(select(TrainingUnit).where(TrainingUnit.id == unit_id, TrainingUnit.account_id == _account_id()))).scalars().first()
        if unit is None:
            raise HTTPException(status_code=404, detail="Training unit not found")
        unit.is_active = False
        rotations = (await session.execute(select(TrainingRotation).where(TrainingRotation.account_id == _account_id(), TrainingRotation.training_type == unit.name))).scalars().all()
        for rotation in rotations:
            rotation.weekday = None
        await session.commit()
        await session.refresh(unit)
        return TrainingUnitResponse.model_validate(unit)


router.include_router(units_router)


# ---------------------------------------------------------------------------
# Rotation template endpoints:  /api/templates/rotation
# ---------------------------------------------------------------------------
rotation_router = APIRouter(prefix="/templates/rotation", tags=["rotation"])


@rotation_router.get("", response_model=list[TrainingRotationResponse])
async def list_rotation(user: str = Depends(get_current_user)):
    async with async_session() as session:
        result = await session.execute(
            select(TrainingRotation).where(TrainingRotation.account_id == _account_id()).order_by(TrainingRotation.slot)
        )
        entries = result.scalars().all()
        return [TrainingRotationResponse.model_validate(r) for r in entries]


@rotation_router.post("", response_model=TrainingRotationResponse, status_code=201)
async def create_rotation(body: TrainingRotationCreate, user: str = Depends(get_current_user)):
    if body.weekday is not None and not 0 <= body.weekday <= 6:
        raise HTTPException(status_code=422, detail="weekday must be between 0 and 6")
    if not 1 <= body.frequency_weeks <= 52:
        raise HTTPException(status_code=422, detail="frequency_weeks must be between 1 and 52")
    async with async_session() as session:
        await _require_active_training_unit(session, body.training_type)
        max_slot = await session.scalar(select(func.max(TrainingRotation.slot)).where(TrainingRotation.account_id == user))
        rotation = TrainingRotation(account_id=user, slot=(max_slot or 0) + 1, **body.model_dump(exclude={"slot"}))
        session.add(rotation)
        await session.commit()
        await session.refresh(rotation)
        return TrainingRotationResponse.model_validate(rotation)


@rotation_router.put("/{slot}", response_model=TrainingRotationResponse)
async def update_rotation(slot: int, body: TrainingRotationUpdate, user: str = Depends(get_current_user)):
    if body.weekday is not None and not 0 <= body.weekday <= 6:
        raise HTTPException(status_code=422, detail="weekday must be between 0 and 6")
    if body.frequency_weeks is not None and not 1 <= body.frequency_weeks <= 52:
        raise HTTPException(status_code=422, detail="frequency_weeks must be between 1 and 52")
    if body.week_offset is not None and body.week_offset < 0:
        raise HTTPException(status_code=422, detail="week_offset must not be negative")
    async with async_session() as session:
        result = await session.execute(
            select(TrainingRotation).where(TrainingRotation.account_id == _account_id(), TrainingRotation.slot == slot)
        )
        rot = result.scalars().first()
        if rot is None:
            raise HTTPException(status_code=404, detail="Rotation slot not found")
        values = body.model_dump(exclude_unset=True)
        next_training_type = values.get("training_type", rot.training_type)
        await _require_active_training_unit(session, next_training_type)
        for field, value in values.items():
            setattr(rot, field, value)
        await session.commit()
        await session.refresh(rot)
        return TrainingRotationResponse.model_validate(rot)


@rotation_router.delete("/{slot}", status_code=204)
async def delete_rotation(slot: int, user: str = Depends(get_current_user)):
    async with async_session() as session:
        rotation = (await session.execute(select(TrainingRotation).where(TrainingRotation.account_id == _account_id(), TrainingRotation.slot == slot))).scalars().first()
        if rotation is None:
            raise HTTPException(status_code=404, detail="Rotation slot not found")
        await session.delete(rotation)
        await session.commit()


router.include_router(rotation_router)
