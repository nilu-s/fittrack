from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Shared config
# ---------------------------------------------------------------------------
class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# DayEntry
# ---------------------------------------------------------------------------
class DayEntryBase(_Base):
    user_id: str = "luis"
    date: date
    weight_kg: Optional[Decimal] = None
    steps: Optional[int] = None
    sleep_hours: Optional[Decimal] = None
    cardio_minutes: Optional[int] = None
    training_type: Optional[str] = None
    training_done: bool = False
    rotation_slot: Optional[int] = None
    steps_done: bool = False
    sleep_done: bool = False
    creatine_done: bool = False
    belly_cm: Optional[Decimal] = None
    notes: Optional[str] = None


class DayEntryCreate(DayEntryBase):
    pass


class DayEntryUpdate(_Base):
    weight_kg: Optional[Decimal] = None
    steps: Optional[int] = None
    sleep_hours: Optional[Decimal] = None
    cardio_minutes: Optional[int] = None
    training_type: Optional[str] = None
    training_done: Optional[bool] = None
    rotation_slot: Optional[int] = None
    steps_done: Optional[bool] = None
    sleep_done: Optional[bool] = None
    creatine_done: Optional[bool] = None
    belly_cm: Optional[Decimal] = None
    notes: Optional[str] = None


class DayEntryResponse(DayEntryBase):
    id: uuid.UUID
    updated_at: Optional[datetime] = None


class DayEntryBulkRequest(_Base):
    dates: list[date]


class DayEntryBulkResponse(_Base):
    entries: list[DayEntryResponse]


# ---------------------------------------------------------------------------
# Meal
# ---------------------------------------------------------------------------
class MealBase(_Base):
    user_id: str = "luis"
    date: date
    meal_slot: int
    name: str
    default_time: Optional[time] = None
    kcal: Optional[Decimal] = None
    protein_g: Optional[Decimal] = None
    carbs_g: Optional[Decimal] = None
    fat_g: Optional[Decimal] = None
    is_standard: bool = False
    is_done: bool = False
    replaced_by: Optional[str] = None
    photo_url: Optional[str] = None
    photo_analysis: Optional[dict[str, Any]] = None
    assigned_via_photo: bool = False


class MealCreate(MealBase):
    pass


class MealUpdate(_Base):
    name: Optional[str] = None
    default_time: Optional[time] = None
    kcal: Optional[Decimal] = None
    protein_g: Optional[Decimal] = None
    carbs_g: Optional[Decimal] = None
    fat_g: Optional[Decimal] = None
    is_standard: Optional[bool] = None
    is_done: Optional[bool] = None
    replaced_by: Optional[str] = None
    photo_url: Optional[str] = None
    photo_analysis: Optional[dict[str, Any]] = None
    assigned_via_photo: Optional[bool] = None


class MealResponse(MealBase):
    id: uuid.UUID
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# MealTemplate
# ---------------------------------------------------------------------------
class MealTemplateBase(_Base):
    user_id: str = "luis"
    slot: int
    name: str
    kcal: Optional[Decimal] = None
    protein_g: Optional[Decimal] = None
    carbs_g: Optional[Decimal] = None
    fat_g: Optional[Decimal] = None


class MealTemplateCreate(MealTemplateBase):
    pass


class MealTemplateUpdate(_Base):
    name: Optional[str] = None
    kcal: Optional[Decimal] = None
    protein_g: Optional[Decimal] = None
    carbs_g: Optional[Decimal] = None
    fat_g: Optional[Decimal] = None


class MealTemplateResponse(MealTemplateBase):
    id: uuid.UUID


# ---------------------------------------------------------------------------
# Todo
# ---------------------------------------------------------------------------
class TodoBase(_Base):
    user_id: str = "luis"
    title: str
    category: Optional[str] = None
    priority: int = 2
    status: str = "open"
    due_date: Optional[date] = None
    due_time: Optional[time] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    is_all_day: bool = True
    source: str = "manual"
    external_id: Optional[str] = None
    sort_order: int = 0


class TodoCreate(TodoBase):
    pass


class TodoUpdate(_Base):
    title: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[int] = None
    status: Optional[str] = None
    due_date: Optional[date] = None
    due_time: Optional[time] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    is_all_day: Optional[bool] = None
    source: Optional[str] = None
    external_id: Optional[str] = None
    sort_order: Optional[int] = None


class TodoResponse(TodoBase):
    id: uuid.UUID
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# TrainingRotation
# ---------------------------------------------------------------------------
class TrainingRotationBase(_Base):
    user_id: str = "luis"
    slot: int
    training_type: str
    cardio_minutes: Optional[int] = None


class TrainingRotationCreate(TrainingRotationBase):
    pass


class TrainingRotationUpdate(_Base):
    training_type: Optional[str] = None
    cardio_minutes: Optional[int] = None


class TrainingRotationResponse(TrainingRotationBase):
    id: uuid.UUID


# ---------------------------------------------------------------------------
# Exercise
# ---------------------------------------------------------------------------
class ExerciseBase(_Base):
    user_id: str = "luis"
    training_type: str
    exercise_name: str
    target_sets: str
    target_reps_low: Optional[int] = None
    target_reps_high: Optional[int] = None
    target_weight_kg: Optional[Decimal] = None
    progression_strategy: str = "double_progression"
    progression_increment_weight: Decimal = Decimal("2.5")
    is_topset: bool = False
    target_rir: Optional[int] = 2
    sort_order: int = 0


class ExerciseCreate(ExerciseBase):
    pass


class ExerciseUpdate(_Base):
    target_sets: Optional[str] = None
    target_reps_low: Optional[int] = None
    target_reps_high: Optional[int] = None
    target_weight_kg: Optional[Decimal] = None
    progression_strategy: Optional[str] = None
    progression_increment_weight: Optional[Decimal] = None
    is_topset: Optional[bool] = None
    target_rir: Optional[int] = None
    sort_order: Optional[int] = None


class ExerciseResponse(ExerciseBase):
    id: uuid.UUID


# ---------------------------------------------------------------------------
# TrainingSet
# ---------------------------------------------------------------------------
class TrainingSetBase(_Base):
    user_id: str = "luis"
    date: date
    training_type: str
    exercise_name: str
    set_number: int
    set_type: Optional[str] = "work"
    reps: Optional[int] = None
    weight_kg: Optional[Decimal] = None
    rir: Optional[int] = None
    completed: bool = False


class TrainingSetCreate(TrainingSetBase):
    pass


class TrainingSetResponse(TrainingSetBase):
    id: uuid.UUID
    updated_at: Optional[datetime] = None


class TrainingCompleteSetItem(_Base):
    exercise_name: str
    set_number: int
    set_type: Optional[str] = "work"
    reps: Optional[int] = None
    weight_kg: Optional[Decimal] = None
    rir: Optional[int] = None


class TrainingCompleteRequest(_Base):
    date: date
    training_type: str
    sets: list[TrainingCompleteSetItem]


class TrainingCompleteResponse(_Base):
    saved: int
    progressed_exercises: list[ExerciseResponse]
    next_training: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Training suggestion (GET /api/training)
# ---------------------------------------------------------------------------
class TrainingSuggestionExercise(_Base):
    exercise_name: str
    target_sets: str
    target_reps_low: Optional[int] = None
    target_reps_high: Optional[int] = None
    target_weight_kg: Optional[Decimal] = None
    is_topset: bool = False
    target_rir: Optional[int] = None
    sort_order: int = 0


class TrainingSuggestion(_Base):
    date: date
    training_type: str
    rotation_slot: Optional[int] = None
    cardio_minutes: Optional[int] = None
    exercises: list[TrainingSuggestionExercise] = []


# ---------------------------------------------------------------------------
# Sync
# ---------------------------------------------------------------------------
class SyncChangeItem(_Base):
    entity_type: str
    entity_id: uuid.UUID
    action: str
    payload: dict[str, Any]
    client_timestamp: datetime


class SyncRequest(_Base):
    last_sync: Optional[datetime] = None
    changes: list[SyncChangeItem] = []
    client_id: str = "default"


class SyncConflictItem(_Base):
    entity_type: str
    entity_id: uuid.UUID
    client_payload: dict[str, Any]
    server_payload: dict[str, Any]
    client_timestamp: datetime
    server_timestamp: datetime


class SyncResponse(_Base):
    server_changes: list[dict[str, Any]] = []
    conflicts: list[SyncConflictItem] = []
    sync_token: datetime


# ---------------------------------------------------------------------------
# Photos / Vision
# ---------------------------------------------------------------------------
class PhotoAnalysisResponse(_Base):
    photo_id: uuid.UUID
    file_path: str
    analysis: Optional[dict[str, Any]] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------
class WeekSummary(_Base):
    week_start: date
    week_end: date
    avg_weight: Optional[Decimal] = None
    avg_kcal: Optional[Decimal] = None
    avg_steps: Optional[Decimal] = None
    training_days: int = 0
    training_completion: Decimal = Decimal("0")
    todo_total: int = 0
    todo_done: int = 0
    todo_completion: Decimal = Decimal("0")


class TrendPoint(_Base):
    date: date
    value: Optional[Decimal] = None


class TrendResponse(_Base):
    metric: str
    points: list[TrendPoint]