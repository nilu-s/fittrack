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
    weight_source: Optional[str] = None
    body_fat_pct: Optional[Decimal] = None
    muscle_mass_kg: Optional[Decimal] = None
    water_pct: Optional[Decimal] = None
    bone_mass_kg: Optional[Decimal] = None
    bmi: Optional[Decimal] = None
    basal_metabolism: Optional[int] = None
    impedance: Optional[int] = None
    visceral_fat: Optional[int] = None
    metabolic_age: Optional[int] = None
    steps: Optional[int] = None
    sleep_hours: Optional[Decimal] = None
    sleep_deep_hours: Optional[Decimal] = None
    sleep_rem_hours: Optional[Decimal] = None
    sleep_light_hours: Optional[Decimal] = None
    sleep_awake_hours: Optional[Decimal] = None
    sleep_efficiency: Optional[Decimal] = None  # 0-100
    sleep_quality: Optional[int] = None  # 1-5
    cardio_minutes: Optional[int] = None
    training_type: Optional[str] = None
    training_done: bool = False
    rotation_slot: Optional[int] = None
    steps_done: bool = False  # legacy
    steps_confirmed: bool = False  # only set by Google Fit API
    steps_source: Optional[str] = None  # 'google_fit' | 'manual' | None
    sleep_done: bool = False  # legacy
    creatine_done: bool = False
    cardio_done: bool = False
    belly_cm: Optional[Decimal] = None
    notes: Optional[str] = None


class DayEntryCreate(DayEntryBase):
    pass


class DayEntryUpdate(_Base):
    weight_kg: Optional[Decimal] = None
    weight_source: Optional[str] = None
    body_fat_pct: Optional[Decimal] = None
    muscle_mass_kg: Optional[Decimal] = None
    water_pct: Optional[Decimal] = None
    bone_mass_kg: Optional[Decimal] = None
    bmi: Optional[Decimal] = None
    basal_metabolism: Optional[int] = None
    impedance: Optional[int] = None
    visceral_fat: Optional[int] = None
    metabolic_age: Optional[int] = None
    steps: Optional[int] = None
    sleep_hours: Optional[Decimal] = None
    sleep_deep_hours: Optional[Decimal] = None
    sleep_rem_hours: Optional[Decimal] = None
    sleep_light_hours: Optional[Decimal] = None
    sleep_awake_hours: Optional[Decimal] = None
    sleep_efficiency: Optional[Decimal] = None
    sleep_quality: Optional[int] = None
    cardio_minutes: Optional[int] = None
    training_type: Optional[str] = None
    training_done: Optional[bool] = None
    rotation_slot: Optional[int] = None
    steps_done: Optional[bool] = None  # legacy — frontend should not send this for steps
    steps_confirmed: Optional[bool] = None  # only Google Fit sync sets this
    steps_source: Optional[str] = None
    sleep_done: Optional[bool] = None  # legacy — no longer used for sleep
    creatine_done: Optional[bool] = None
    cardio_done: Optional[bool] = None
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
# Scale Sync (ESP32 → API)
# ---------------------------------------------------------------------------
class ScaleSyncRequest(_Base):
    """Payload from ESP32 reading a Renpho BLE scale."""
    date: Optional[str] = None  # YYYY-MM-DD, defaults to today (server time)
    weight_kg: float
    impedance: Optional[int] = None  # ohms — if scale provides it
    # Pre-calculated body composition (if ESP did the math):
    body_fat_pct: Optional[float] = None
    muscle_mass_kg: Optional[float] = None
    water_pct: Optional[float] = None
    bone_mass_kg: Optional[float] = None
    bmi: Optional[float] = None
    basal_metabolism: Optional[int] = None
    visceral_fat: Optional[int] = None
    metabolic_age: Optional[int] = None
    # User profile for server-side body comp calc (if impedance provided but not pre-calc):
    height_cm: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None  # 'male' | 'female'
    device_id: Optional[str] = None  # ESP32 identifier


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
    deleted: bool = False


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
    deleted: Optional[bool] = None


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


# ---------------------------------------------------------------------------#
# Dish
# ---------------------------------------------------------------------------#
class DishBase(_Base):
    user_id: str = "luis"
    slot: int
    name: str
    kcal: Optional[Decimal] = None
    protein_g: Optional[Decimal] = None
    carbs_g: Optional[Decimal] = None
    fat_g: Optional[Decimal] = None
    photo_url: Optional[str] = None
    is_default: bool = False
    usage_count: int = 0
    source: str = "manual"


class DishCreate(DishBase):
    pass


class DishUpdate(_Base):
    name: Optional[str] = None
    kcal: Optional[Decimal] = None
    protein_g: Optional[Decimal] = None
    carbs_g: Optional[Decimal] = None
    fat_g: Optional[Decimal] = None
    photo_url: Optional[str] = None
    is_default: Optional[bool] = None


class DishResponse(DishBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DishMatchResult(_Base):
    matched: bool
    dish: Optional[DishResponse] = None
    similarity: float = 0.0


# ---------------------------------------------------------------------------#
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
    deleted: bool = False
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
    deleted: Optional[bool] = None


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
    base_reps_low: Optional[int] = None
    base_reps_high: Optional[int] = None
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
    base_reps_low: Optional[int] = None
    base_reps_high: Optional[int] = None
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
    dish_match: Optional[DishMatchResult] = None


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------
class WeekSummary(_Base):
    week_start: date
    week_end: date
    avg_weight: Optional[Decimal] = None
    avg_kcal: Optional[Decimal] = None
    avg_protein: Optional[Decimal] = None
    avg_carbs: Optional[Decimal] = None
    avg_fat: Optional[Decimal] = None
    avg_steps: Optional[Decimal] = None
    avg_sleep_hours: Optional[Decimal] = None
    avg_sleep_quality: Optional[Decimal] = None
    total_cardio_minutes: int = 0
    creatine_compliance: Decimal = Decimal("0")
    training_days: int = 0
    training_completion: Decimal = Decimal("0")
    training_streak: int = 0
    step_goal_streak: int = 0
    todo_total: int = 0
    todo_done: int = 0
    todo_completion: Decimal = Decimal("0")
    macro_compliance: Optional[dict[str, Decimal]] = None
    goals: Optional[dict[str, Any]] = None


class TrendPoint(_Base):
    date: date
    value: Optional[Decimal] = None


class TrendResponse(_Base):
    metric: str
    points: list[TrendPoint]


# ---------------------------------------------------------------------------
# ExerciseProgress
# ---------------------------------------------------------------------------
class ExerciseProgressResponse(_Base):
    id: uuid.UUID
    exercise_id: uuid.UUID
    date: date
    training_type: str
    exercise_name: str
    topset_reps: Optional[int] = None
    topset_weight_kg: Optional[Decimal] = None
    topset_rir: Optional[int] = None
    total_volume_kg: Optional[Decimal] = None
    progression_action: str = "none"
    prev_target_weight_kg: Optional[Decimal] = None
    prev_target_reps_low: Optional[int] = None
    new_target_weight_kg: Optional[Decimal] = None
    new_target_reps_low: Optional[int] = None
    consecutive_failures: int = 0
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Goals
# ---------------------------------------------------------------------------
class GoalResponse(_Base):
    id: uuid.UUID
    key: str
    value: Decimal
    effective_from: date
    updated_at: Optional[datetime] = None


class GoalUpdate(_Base):
    value: Decimal
    effective_from: Optional[date] = None


class GoalsBatchUpdate(_Base):
    goals: dict[str, Decimal]