from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Literal, Optional
import re

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
    saturated_fat_g: NutritionValue = Field(default=None, ge=0)
    sodium_mg: NutritionValue = Field(default=None, ge=0)
    potassium_mg: NutritionValue = Field(default=None, ge=0)
    calcium_mg: NutritionValue = Field(default=None, ge=0)
    magnesium_mg: NutritionValue = Field(default=None, ge=0)
    iron_mg: NutritionValue = Field(default=None, ge=0)
    zinc_mg: NutritionValue = Field(default=None, ge=0)
    vitamin_a_ug: NutritionValue = Field(default=None, ge=0)
    vitamin_c_mg: NutritionValue = Field(default=None, ge=0)
    vitamin_d_ug: NutritionValue = Field(default=None, ge=0)
    vitamin_b12_ug: NutritionValue = Field(default=None, ge=0)
    folate_ug: NutritionValue = Field(default=None, ge=0)


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


class MealCategoryRecipePresetUpdate(_Base):
    """Replace the at-most-two quick recipes for one owned category."""
    model_config = ConfigDict(extra="forbid")
    recipe_ids: list[uuid.UUID] = Field(default_factory=list, max_length=2)

    @field_validator("recipe_ids")
    @classmethod
    def unique_recipe_ids(cls, recipe_ids):
        if len(recipe_ids) != len(set(recipe_ids)):
            raise ValueError("recipe_ids must be unique")
        return recipe_ids


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


class HistoricalNutrientEnrichmentResponse(_Base):
    updated_item_count: int


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
    instructions: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("instructions")
    @classmethod
    def valid_instructions(cls, instructions: list[str] | None) -> list[str] | None:
        if instructions is None:
            return None
        cleaned = [step.strip() for step in instructions]
        if any(not step for step in cleaned):
            raise ValueError("instructions may not contain blank steps")
        if any(len(step) > 2000 for step in cleaned):
            raise ValueError("each instruction must not exceed 2000 characters")
        return cleaned


class RecipeUpdate(RecipeCreate):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    ingredients: Optional[list[RecipeIngredientInput]] = None
    instructions: Optional[list[str]] = None
    expected_updated_at: Optional[datetime] = None


class RecipeIngredientResponse(RecipeIngredientInput):
    id: uuid.UUID


class RecipeResponse(_Base):
    id: uuid.UUID
    name: str
    status: str
    servings: Decimal
    notes: Optional[str]
    instructions: list[str]
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

    @model_validator(mode="after")
    def one_item_per_slot_and_weekday(self):
        """A weekly plan may project at most one meal into a slot each day."""
        if self.items is None:  # MealPlanUpdate may intentionally omit items.
            return self
        occupied: set[tuple[uuid.UUID, int]] = set()
        for item in self.items:
            for weekday in (item.weekdays if item.weekdays is not None else range(7)):
                key = (item.category_id, weekday)
                if key in occupied:
                    raise ValueError("only one meal-plan item is allowed per category and weekday")
                occupied.add(key)
        return self


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
    model_config = ConfigDict(from_attributes=True, extra="forbid")
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
    space_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    assignee_id: Optional[uuid.UUID] = None
    place_id: Optional[str] = Field(default=None, max_length=512)
    place_name: Optional[str] = Field(default=None, max_length=300)
    place_address: Optional[str] = Field(default=None, max_length=500)
    travel_mode: Optional[Literal["drive", "bicycle", "walk", "transit"]] = None
    travel_buffer_minutes: int = Field(default=10, ge=0, le=180)
    travel_monitoring_enabled: bool = False
    deleted: bool = False
    sort_order: int = 0


class TodoCreate(TodoBase):
    pass


class TodoUpdate(_Base):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
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
    space_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    assignee_id: Optional[uuid.UUID] = None
    place_id: Optional[str] = Field(default=None, max_length=512)
    place_name: Optional[str] = Field(default=None, max_length=300)
    place_address: Optional[str] = Field(default=None, max_length=500)
    travel_mode: Optional[Literal["drive", "bicycle", "walk", "transit"]] = None
    travel_buffer_minutes: Optional[int] = Field(default=None, ge=0, le=180)
    travel_monitoring_enabled: Optional[bool] = None
    sort_order: Optional[int] = None
    deleted: Optional[bool] = None


class TodoResponse(TodoBase):
    id: uuid.UUID
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    travel_last_checked_at: Optional[datetime] = None
    travel_duration_seconds: Optional[int] = None
    travel_depart_at: Optional[datetime] = None
    assignee_display_name: Optional[str] = None
    origin_note_id: Optional[uuid.UUID] = None


class NoteCreate(_Base):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=300)
    body: Optional[str] = Field(default=None, max_length=20_000)
    space_id: Optional[uuid.UUID] = None


class NoteUpdate(_Base):
    model_config = ConfigDict(extra="forbid")
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    body: Optional[str] = Field(default=None, max_length=20_000)
    sort_order: Optional[int] = None


class NoteMove(_Base):
    model_config = ConfigDict(extra="forbid")
    space_id: Optional[uuid.UUID] = None
    confirm_share: bool = False
    confirm_private: bool = False


class NotePlan(_Base):
    model_config = ConfigDict(extra="forbid")
    due_date: date
    start_time: Optional[time] = None


class NoteResponse(_Base):
    id: uuid.UUID
    title: str
    body: Optional[str] = None
    space_id: Optional[uuid.UUID] = None
    status: str
    sort_order: int
    scheduled_todo_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------#
# Shared spaces
# ---------------------------------------------------------------------------#
ALIAS_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{2,31}$")


def normalize_alias(value: str) -> str:
    """Return the canonical public handle, rejecting email-like identifiers."""
    alias = value.strip().removeprefix("@").casefold()
    if not ALIAS_PATTERN.fullmatch(alias):
        raise ValueError("alias must be 3-32 characters using letters, numbers, ., _ or -")
    return alias


class AccountAliasUpdate(_Base):
    model_config = ConfigDict(extra="forbid")
    alias: str = Field(min_length=3, max_length=33)

    @field_validator("alias")
    @classmethod
    def canonical_alias(cls, value: str) -> str:
        return normalize_alias(value)


class ContactInviteCreate(_Base):
    model_config = ConfigDict(extra="forbid")
    alias: str = Field(min_length=3, max_length=33)

    @field_validator("alias")
    @classmethod
    def canonical_alias(cls, value: str) -> str:
        return normalize_alias(value)


class ContactResponse(_Base):
    id: uuid.UUID
    display_name: str
    alias: str


class ContactSearchResult(_Base):
    alias: str
    display_name: str


class ContactInvitationResponse(_Base):
    id: uuid.UUID
    invited_by_display_name: str
    invited_by_alias: str


class ContactOutgoingInvitationResponse(_Base):
    id: uuid.UUID
    invited_display_name: str
    invited_alias: str


class SpaceCreate(_Base):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)


class SpaceUpdate(_Base):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)


class SpaceMemberResponse(_Base):
    member_id: uuid.UUID
    display_name: Optional[str] = None
    role: str


class SpaceResponse(_Base):
    id: uuid.UUID
    name: str
    owner_id: uuid.UUID
    role: str
    members: list[SpaceMemberResponse] = Field(default_factory=list)


class SpaceInviteCreate(_Base):
    model_config = ConfigDict(extra="forbid")
    contact_id: uuid.UUID


class SpaceInvitationResponse(_Base):
    id: uuid.UUID
    space_id: uuid.UUID
    space_name: str
    invited_by_display_name: Optional[str] = None
    status: str


class SpaceProjectCreate(_Base):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)


class SpaceProjectUpdate(_Base):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=1000)
    is_archived: Optional[bool] = None


class SpaceProjectResponse(_Base):
    id: uuid.UUID
    space_id: uuid.UUID
    name: str
    description: Optional[str] = None
    is_archived: bool


class TodoDraftRequest(_Base):
    text: str = Field(min_length=1, max_length=2000)
    date: date


class AssistantRequest(_Base):
    text: str = Field(min_length=1, max_length=2000)
    date: date


class AssistantResponse(_Base):
    message: str


class TodoDraftResponse(_Base):
    title: str
    due_date: date
    start_time: Optional[time] = None
    place_query: Optional[str] = None
    travel_mode: Optional[Literal["drive", "bicycle", "walk", "transit"]] = None
    needs_review: list[str] = Field(default_factory=list)


class PlaceSuggestion(_Base):
    place_id: str
    name: str
    address: Optional[str] = None


class TravelEstimateRequest(_Base):
    origin_latitude: float = Field(ge=-90, le=90)
    origin_longitude: float = Field(ge=-180, le=180)


class TravelEstimateResponse(_Base):
    duration_seconds: int = Field(ge=0)
    depart_at: datetime
    arrival_at: datetime
    checked_at: datetime
    traffic_aware: bool


class TodoRoutineBase(_Base):
    title: str = Field(min_length=1, max_length=200)
    weekdays: list[int] = Field(min_length=1, max_length=7)
    due_time: Optional[time] = None
    priority: int = Field(default=2, ge=1, le=3)
    is_active: bool = True

    @field_validator("weekdays")
    @classmethod
    def weekdays_are_unique_calendar_days(cls, value: list[int]) -> list[int]:
        if any(day < 0 or day > 6 for day in value) or len(set(value)) != len(value):
            raise ValueError("weekdays must contain distinct values from 0 to 6")
        return sorted(value)


class TodoRoutineCreate(TodoRoutineBase):
    pass


class TodoRoutineUpdate(_Base):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    weekdays: Optional[list[int]] = Field(default=None, min_length=1, max_length=7)
    due_time: Optional[time] = None
    priority: Optional[int] = Field(default=None, ge=1, le=3)
    is_active: Optional[bool] = None

    @field_validator("weekdays")
    @classmethod
    def updated_weekdays_are_valid(cls, value: Optional[list[int]]) -> Optional[list[int]]:
        if value is not None and (any(day < 0 or day > 6 for day in value) or len(set(value)) != len(value)):
            raise ValueError("weekdays must contain distinct values from 0 to 6")
        return sorted(value) if value is not None else value


class TodoRoutineResponse(TodoRoutineBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


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


class SyncOperationResult(_Base):
    change_index: int
    entity_type: str
    entity_id: uuid.UUID
    status: Literal["applied", "duplicate", "conflict", "validation_error"]
    detail: Optional[str] = None


class SyncResponse(_Base):
    server_changes: list[dict[str, Any]] = []
    conflicts: list[SyncConflictItem] = []
    results: list[SyncOperationResult] = []
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


# ---------------------------------------------------------------------------
# Shopping
# ---------------------------------------------------------------------------
class ShoppingItemCreate(_Base):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    food_id: Optional[uuid.UUID] = None
    category_key: Optional[Literal["produce", "dairy", "bakery", "pantry", "frozen", "beverage", "household", "other"]] = None
    icon_key: Optional[Literal["produce", "dairy", "bakery", "pantry", "frozen", "beverage", "household", "shopping"]] = None
    quantity: Optional[Decimal] = Field(default=None, gt=0, max_digits=12, decimal_places=3)
    unit: Optional[str] = Field(default=None, max_length=24)
    note: Optional[str] = Field(default=None, max_length=500)


class ShoppingItemUpdate(_Base):
    model_config = ConfigDict(extra="forbid")
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    category_key: Optional[Literal["produce", "dairy", "bakery", "pantry", "frozen", "beverage", "household", "other"]] = None
    icon_key: Optional[Literal["produce", "dairy", "bakery", "pantry", "frozen", "beverage", "household", "shopping"]] = None
    quantity: Optional[Decimal] = Field(default=None, gt=0, max_digits=12, decimal_places=3)
    unit: Optional[str] = Field(default=None, max_length=24)
    note: Optional[str] = Field(default=None, max_length=500)
    status: Optional[Literal["open", "done"]] = None


class ShoppingItemResponse(_Base):
    id: uuid.UUID
    title: str
    food_id: Optional[uuid.UUID]
    category_key: str
    icon_key: str
    quantity: Optional[Decimal]
    unit: Optional[str]
    note: Optional[str]
    status: Literal["open", "done"]
    source: Literal["manual", "meal_plan", "mixed"]
    sort_order: int
    completed_at: Optional[datetime]
    updated_at: datetime


class ShoppingListResponse(_Base):
    id: uuid.UUID
    name: str
    space_id: Optional[uuid.UUID] = None
    items: list[ShoppingItemResponse]


class ShoppingMealPreviewItem(_Base):
    food_id: Optional[uuid.UUID]
    title: str
    category_key: str
    icon_key: str
    quantity: Optional[Decimal]
    unit: Optional[str]
    needs_review: bool = False


class ShoppingMealPreviewResponse(_Base):
    from_date: date
    to_date: date
    plan_name: Optional[str]
    items: list[ShoppingMealPreviewItem]


class ShoppingMealImportCommand(_Base):
    model_config = ConfigDict(extra="forbid")
    from_date: date
    to_date: date

    @model_validator(mode="after")
    def valid_period(self):
        if self.to_date < self.from_date:
            raise ValueError("to_date must not precede from_date")
        if (self.to_date - self.from_date).days >= 14:
            raise ValueError("shopping import period must not exceed 14 days")
        return self
