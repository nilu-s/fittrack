from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Shared config
# ---------------------------------------------------------------------------
class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# DayEntry
# ---------------------------------------------------------------------------
class DayEntryBase(_Base):
    date: date
    weight_kg: Optional[Decimal] = None
    weight_source: Optional[str] = None
    bmi: Optional[Decimal] = None
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
    bmi: Optional[Decimal] = None
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


class ScaleSyncV2Request(_Base):
    """Raw device-only payload. Extra fields are rejected deliberately."""

    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(min_length=1, max_length=128)
    device_event_id: str = Field(min_length=1, max_length=128)
    measured_at: datetime
    weight_kg: float = Field(ge=0.5, le=300)
    impedance_ohm: Optional[int] = Field(default=None, ge=1, le=5000)
    protocol: str = Field(min_length=1, max_length=64)
    protocol_version: int = Field(ge=1, le=1000)

    @field_validator("measured_at")
    @classmethod
    def measured_at_must_include_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("measured_at must include a timezone")
        return value


class BodyProfileUpdate(_Base):
    height_cm: Optional[Decimal] = Field(default=None, ge=50, le=300)
    birth_date: Optional[date] = None
    calculation_sex: Optional[Literal["male", "female"]] = None


class BodyProfileResponse(BodyProfileUpdate):
    id: uuid.UUID


# ---------------------------------------------------------------------------
# Meal
# ---------------------------------------------------------------------------
class MealBase(_Base):
    date: date
    meal_slot: int
    name: str
    default_time: Optional[time] = None
    kcal: Optional[Decimal] = None
    protein_g: Optional[Decimal] = None
    carbs_g: Optional[Decimal] = None
    fat_g: Optional[Decimal] = None
    fiber_g: Optional[Decimal] = None
    sugar_g: Optional[Decimal] = None
    free_sugar_g: Optional[Decimal] = None
    is_standard: bool = False
    is_done: bool = False
    replaced_by: Optional[str] = None
    photo_url: Optional[str] = None
    photo_analysis: Optional[dict[str, Any]] = None
    assigned_via_photo: bool = False
    deleted: bool = False
    portion_factor: Optional[Decimal] = Decimal("1.00")
    dish_id: Optional[uuid.UUID] = None


class MealCreate(MealBase):
    pass


class MealUpdate(_Base):
    name: Optional[str] = None
    default_time: Optional[time] = None
    kcal: Optional[Decimal] = None
    protein_g: Optional[Decimal] = None
    carbs_g: Optional[Decimal] = None
    fat_g: Optional[Decimal] = None
    fiber_g: Optional[Decimal] = None
    sugar_g: Optional[Decimal] = None
    free_sugar_g: Optional[Decimal] = None
    is_standard: Optional[bool] = None
    is_done: Optional[bool] = None
    replaced_by: Optional[str] = None
    photo_url: Optional[str] = None
    photo_analysis: Optional[dict[str, Any]] = None
    assigned_via_photo: Optional[bool] = None
    deleted: Optional[bool] = None
    portion_factor: Optional[Decimal] = None
    dish_id: Optional[uuid.UUID] = None


class MealResponse(MealBase):
    id: uuid.UUID
    updated_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# MealTemplate
# ---------------------------------------------------------------------------
class MealTemplateBase(_Base):
    slot: int
    name: str
    kcal: Optional[Decimal] = None
    protein_g: Optional[Decimal] = None
    carbs_g: Optional[Decimal] = None
    fat_g: Optional[Decimal] = None
    fiber_g: Optional[Decimal] = None
    sugar_g: Optional[Decimal] = None
    free_sugar_g: Optional[Decimal] = None


class MealTemplateCreate(MealTemplateBase):
    pass


class MealTemplateUpdate(_Base):
    name: Optional[str] = None
    kcal: Optional[Decimal] = None
    protein_g: Optional[Decimal] = None
    carbs_g: Optional[Decimal] = None
    fat_g: Optional[Decimal] = None
    fiber_g: Optional[Decimal] = None
    sugar_g: Optional[Decimal] = None
    free_sugar_g: Optional[Decimal] = None


class MealTemplateResponse(MealTemplateBase):
    id: uuid.UUID


# ---------------------------------------------------------------------------#
# Dish
# ---------------------------------------------------------------------------#
class DishBase(_Base):
    slot: Optional[int] = None  # preferred slot, not mandatory
    name: str
    kcal: Optional[Decimal] = None
    protein_g: Optional[Decimal] = None
    carbs_g: Optional[Decimal] = None
    fat_g: Optional[Decimal] = None
    fiber_g: Optional[Decimal] = None
    sugar_g: Optional[Decimal] = None
    free_sugar_g: Optional[Decimal] = None
    photo_url: Optional[str] = None
    is_default: bool = False
    usage_count: int = 0
    source: str = "manual"
    portion_label: Optional[str] = None
    portion_grams: Optional[Decimal] = None
    is_scalable: bool = False


class DishCreate(DishBase):
    pass


class DishUpdate(_Base):
    name: Optional[str] = None
    kcal: Optional[Decimal] = None
    protein_g: Optional[Decimal] = None
    carbs_g: Optional[Decimal] = None
    fat_g: Optional[Decimal] = None
    fiber_g: Optional[Decimal] = None
    sugar_g: Optional[Decimal] = None
    free_sugar_g: Optional[Decimal] = None
    photo_url: Optional[str] = None
    is_default: Optional[bool] = None
    slot: Optional[int] = None
    portion_label: Optional[str] = None
    portion_grams: Optional[Decimal] = None
    is_scalable: Optional[bool] = None


class DishResponse(DishBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DishMatchResult(_Base):
    matched: bool
    dish: Optional[DishResponse] = None
    similarity: float = 0.0


class DishRecommendResult(_Base):
    """Result for GET /dishes/recommend — default + alternatives for a slot."""
    default: Optional[DishResponse] = None
    alternatives: list[DishResponse] = []


# ---------------------------------------------------------------------------
# Configurable meal domain (v1)
# ---------------------------------------------------------------------------
NutritionValue = Optional[Decimal]


class Nutrition(_Base):
    kcal: NutritionValue = Field(default=None, ge=0)
    protein_g: NutritionValue = Field(default=None, ge=0)
    carbs_g: NutritionValue = Field(default=None, ge=0)
    fat_g: NutritionValue = Field(default=None, ge=0)
    fiber_g: NutritionValue = Field(default=None, ge=0)
    sugar_g: NutritionValue = Field(default=None, ge=0)
    free_sugar_g: NutritionValue = Field(default=None, ge=0)


class MealCategoryCreate(_Base):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    sort_order: int = Field(default=0, ge=0)
    is_active: bool = True


class MealCategoryUpdate(_Base):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    sort_order: Optional[int] = Field(default=None, ge=0)
    is_active: Optional[bool] = None
    expected_updated_at: Optional[datetime] = None


class MealCategoryResponse(MealCategoryCreate):
    id: uuid.UUID
    updated_at: datetime


class MealCategoryReorder(_Base):
    """An atomic, account-local category order command."""
    model_config = ConfigDict(extra="forbid")
    ids: list[uuid.UUID] = Field(min_length=1)

    @field_validator("ids")
    @classmethod
    def unique_ids(cls, ids):
        if len(ids) != len(set(ids)):
            raise ValueError("ids must be unique")
        return ids


class FoodCreate(Nutrition):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    tags: list[str] = Field(default_factory=list)
    source: Literal["manual", "photo", "import"] = "manual"
    confidence: Literal["verified", "estimated", "unknown"] = "verified"


class FoodUpdate(FoodCreate):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    is_archived: Optional[bool] = None
    expected_updated_at: Optional[datetime] = None


class FoodResponse(FoodCreate):
    id: uuid.UUID
    is_archived: bool
    updated_at: datetime


class RecipeIngredientInput(_Base):
    model_config = ConfigDict(extra="forbid")
    food_id: Optional[uuid.UUID] = None
    nested_recipe_id: Optional[uuid.UUID] = None
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    unit: Literal["g", "ml", "serving"] = "g"
    sort_order: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def one_source(self):
        if (self.food_id is None) == (self.nested_recipe_id is None):
            raise ValueError("exactly one of food_id or nested_recipe_id is required")
        return self


class RecipeCreate(_Base):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    status: Literal["draft", "active", "archived"] = "draft"
    servings: Decimal = Field(default=Decimal("1"), gt=0, max_digits=10, decimal_places=3)
    notes: Optional[str] = Field(default=None, max_length=5000)
    ingredients: list[RecipeIngredientInput] = Field(default_factory=list)


class RecipeUpdate(RecipeCreate):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    ingredients: Optional[list[RecipeIngredientInput]] = None
    expected_updated_at: Optional[datetime] = None


class RecipeIngredientResponse(RecipeIngredientInput):
    id: uuid.UUID


class RecipeResponse(_Base):
    id: uuid.UUID
    name: str
    status: str
    servings: Decimal
    notes: Optional[str]
    ingredients: list[RecipeIngredientResponse]
    nutrition: Nutrition
    updated_at: datetime


class MealPlanItemInput(_Base):
    model_config = ConfigDict(extra="forbid")
    category_id: uuid.UUID
    recipe_id: Optional[uuid.UUID] = None
    name: Optional[str] = Field(default=None, max_length=200)
    planned_time: Optional[time] = None
    weekdays: Optional[list[int]] = None
    portion: Decimal = Field(default=Decimal("1"), gt=0, max_digits=10, decimal_places=3)
    sort_order: int = Field(default=0, ge=0)

    @field_validator("weekdays")
    @classmethod
    def valid_weekdays(cls, value):
        if value is not None and (any(day < 0 or day > 6 for day in value) or len(set(value)) != len(value)):
            raise ValueError("weekdays must be unique values from 0 to 6")
        return value


class MealPlanCreate(_Base):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    is_active: bool = False
    items: list[MealPlanItemInput] = Field(default_factory=list)


class MealPlanUpdate(MealPlanCreate):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    items: Optional[list[MealPlanItemInput]] = None
    expected_updated_at: Optional[datetime] = None


class MealPlanItemResponse(MealPlanItemInput):
    id: uuid.UUID


class MealPlanResponse(_Base):
    id: uuid.UUID
    name: str
    version: int
    is_active: bool
    items: list[MealPlanItemResponse]
    updated_at: datetime


class MealPlanVersionResponse(_Base):
    version: int
    name: str
    items_snapshot: list[dict[str, Any]]
    created_at: datetime


class MealEntryItemInput(_Base):
    model_config = ConfigDict(extra="forbid")
    food_id: Optional[uuid.UUID] = None
    recipe_id: Optional[uuid.UUID] = None
    quantity: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    unit: Literal["g", "ml", "serving"] = "g"

    @model_validator(mode="after")
    def one_entry_source(self):
        if (self.food_id is None) == (self.recipe_id is None):
            raise ValueError("exactly one of food_id or recipe_id is required")
        return self


class MealEntryCreate(_Base):
    model_config = ConfigDict(extra="forbid")
    date: date
    category_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    status: Literal["planned", "consumed", "skipped"] = "planned"
    consumed_at: Optional[datetime] = None
    source: Literal["manual", "plan", "photo"] = "manual"
    items: list[MealEntryItemInput] = Field(default_factory=list)


class MealEntryUpdate(_Base):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    category_id: Optional[uuid.UUID] = None
    status: Optional[Literal["planned", "consumed", "skipped"]] = None
    consumed_at: Optional[datetime] = None
    items: Optional[list[MealEntryItemInput]] = None
    expected_updated_at: Optional[datetime] = None


class MealEntryStatusCommand(_Base):
    """A state transition with optimistic-concurrency protection."""
    model_config = ConfigDict(extra="forbid")
    expected_updated_at: Optional[datetime] = None


class MealEntryItemResponse(_Base):
    id: uuid.UUID
    food_id: Optional[uuid.UUID]
    recipe_id: Optional[uuid.UUID]
    quantity: Decimal
    unit: str
    nutrition_snapshot: dict[str, NutritionValue]
    source_snapshot: dict[str, Any]


class MealEntryResponse(_Base):
    id: uuid.UUID
    date: date
    category_id: uuid.UUID
    name: str
    status: str
    consumed_at: Optional[datetime]
    source: str
    nutrition: Nutrition
    items: list[MealEntryItemResponse]
    updated_at: datetime


class MealPhotoAnalysisResponse(_Base):
    id: uuid.UUID
    meal_entry_id: uuid.UUID
    state: Literal["pending", "accepted", "rejected", "failed"]
    analysis: Optional[dict[str, Any]] = None
    error_code: Optional[str] = None
    created_at: datetime


class MealPhotoAnalysisAccept(_Base):
    """Explicitly applies user-reviewed food/recipe items to an entry."""
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    items: list[MealEntryItemInput] = Field(min_length=1)
    status: Optional[Literal["planned", "consumed"]] = None


# ---------------------------------------------------------------------------#
# Todo
# ---------------------------------------------------------------------------
class TodoBase(_Base):
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
class TrainingUnitBase(_Base):
    name: str
    description: Optional[str] = None
    unit_type: str = "gym"
    cardio_minutes: Optional[int] = None
    is_active: bool = True


class TrainingUnitCreate(TrainingUnitBase):
    pass


class TrainingUnitUpdate(_Base):
    name: Optional[str] = None
    description: Optional[str] = None
    unit_type: Optional[str] = None
    cardio_minutes: Optional[int] = None
    is_active: Optional[bool] = None


class TrainingUnitResponse(TrainingUnitBase):
    id: uuid.UUID


class TrainingRotationBase(_Base):
    slot: int
    training_type: str
    weekday: Optional[int] = None
    frequency_weeks: int = 1
    week_offset: int = 0
    start_date: Optional[date] = None


class TrainingRotationCreate(TrainingRotationBase):
    pass


class TrainingRotationUpdate(_Base):
    training_type: Optional[str] = None
    weekday: Optional[int] = None
    frequency_weeks: Optional[int] = None
    week_offset: Optional[int] = None
    start_date: Optional[date] = None


class TrainingRotationResponse(TrainingRotationBase):
    id: uuid.UUID


# ---------------------------------------------------------------------------
# Exercise
# ---------------------------------------------------------------------------
class ExerciseBase(_Base):
    training_type: str
    exercise_name: str
    target_sets: str = Field(pattern=r"^[1-9][0-9]?$")
    target_reps_low: Optional[int] = Field(default=None, ge=1, le=999)
    target_reps_high: Optional[int] = Field(default=None, ge=1, le=999)
    base_reps_low: Optional[int] = Field(default=None, ge=1, le=999)
    base_reps_high: Optional[int] = Field(default=None, ge=1, le=999)
    target_weight_kg: Optional[Decimal] = Field(default=None, ge=0, le=999.99)
    progression_strategy: Literal["double_progression", "weight_increase", "reps_only"] = "double_progression"
    progression_increment_weight: Decimal = Field(default=Decimal("2.5"), ge=0, le=100)
    is_topset: bool = False
    top_set_count: int = Field(default=0, ge=0, le=1)
    backoff_set_count: int = Field(default=0, ge=0, le=5)
    backoff_reps_low: Optional[int] = Field(default=None, ge=1, le=999)
    backoff_reps_high: Optional[int] = Field(default=None, ge=1, le=999)
    backoff_weight_percent: Optional[Decimal] = Field(default=None, ge=1, le=100)
    target_rir: Optional[int] = Field(default=2, ge=0, le=5)
    sort_order: int = 0


class ExerciseCreate(ExerciseBase):
    pass


class ExerciseUpdate(_Base):
    exercise_name: Optional[str] = None
    target_sets: Optional[str] = Field(default=None, pattern=r"^[1-9][0-9]?$")
    target_reps_low: Optional[int] = Field(default=None, ge=1, le=999)
    target_reps_high: Optional[int] = Field(default=None, ge=1, le=999)
    base_reps_low: Optional[int] = Field(default=None, ge=1, le=999)
    base_reps_high: Optional[int] = Field(default=None, ge=1, le=999)
    target_weight_kg: Optional[Decimal] = Field(default=None, ge=0, le=999.99)
    progression_strategy: Optional[Literal["double_progression", "weight_increase", "reps_only"]] = None
    progression_increment_weight: Optional[Decimal] = Field(default=None, ge=0, le=100)
    is_topset: Optional[bool] = None
    top_set_count: Optional[int] = Field(default=None, ge=0, le=1)
    backoff_set_count: Optional[int] = Field(default=None, ge=0, le=5)
    backoff_reps_low: Optional[int] = Field(default=None, ge=1, le=999)
    backoff_reps_high: Optional[int] = Field(default=None, ge=1, le=999)
    backoff_weight_percent: Optional[Decimal] = Field(default=None, ge=1, le=100)
    target_rir: Optional[int] = Field(default=None, ge=0, le=5)
    sort_order: Optional[int] = None


class ExerciseResponse(ExerciseBase):
    id: uuid.UUID


# ---------------------------------------------------------------------------
# TrainingSet
# ---------------------------------------------------------------------------
class TrainingSetBase(_Base):
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
    exercise_name: str = Field(min_length=1, max_length=200)
    set_number: int = Field(ge=1, le=99)
    set_type: Literal["warmup", "work", "top", "backoff", "drop"] = "work"
    reps: Optional[int] = Field(default=None, ge=0, le=999)
    weight_kg: Optional[Decimal] = Field(default=None, ge=0, le=999.99)
    rir: Optional[int] = Field(default=None, ge=0, le=10)


class TrainingCompleteRequest(_Base):
    date: date
    training_type: str
    sets: list[TrainingCompleteSetItem] = []
    cardio_minutes: Optional[int] = Field(default=None, ge=0, le=1_440)


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
    top_set_count: int = 0
    backoff_set_count: int = 0
    backoff_reps_low: Optional[int] = None
    backoff_reps_high: Optional[int] = None
    backoff_weight_percent: Optional[Decimal] = None
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
    avg_fiber: Optional[Decimal] = None
    avg_sugar: Optional[Decimal] = None
    avg_free_sugar: Optional[Decimal] = None
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
