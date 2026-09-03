from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.services.ownership import AccountOwned


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_subject: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Space(Base):
    """An explicit shared workspace; private account data never belongs here."""
    __tablename__ = "spaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    owner_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SpaceMembership(Base):
    __tablename__ = "space_memberships"
    __table_args__ = (UniqueConstraint("space_id", "account_id", name="uq_space_memberships_space_account"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    space_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False, default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SpaceInvitation(Base):
    __tablename__ = "space_invitations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    space_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False)
    invited_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    invited_by_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SpaceProject(Base):
    __tablename__ = "space_projects"
    __table_args__ = (UniqueConstraint("space_id", "name", name="uq_space_projects_space_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    space_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class AccountWeightRange(Base):
    __tablename__ = "account_weight_ranges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, unique=True)
    baseline_kg: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    lower_offset_kg: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    upper_offset_kg: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    baseline_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class RegisteredDevice(Base):
    __tablename__ = "registered_devices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    credential_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BodyProfile(AccountOwned, Base):
    __tablename__ = "body_profiles"
    __table_args__ = (UniqueConstraint("account_id", name="uq_body_profiles_account"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    birth_date: Mapped[date | None] = mapped_column(Date)
    calculation_sex: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ScaleMeasurement(AccountOwned, Base):
    __tablename__ = "scale_measurements"
    __table_args__ = (UniqueConstraint("device_id", "device_event_id", name="uq_scale_measurements_device_event"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_id: Mapped[str] = mapped_column(Text, nullable=False)
    device_event_id: Mapped[str] = mapped_column(Text, nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    impedance_ohm: Mapped[int | None] = mapped_column(Integer)
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="assigned")
    assignment_method: Mapped[str] = mapped_column(Text, nullable=False, default="weight_range")
    assignment_confidence: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False, default=Decimal("1.0"))
    assignment_reason: Mapped[str | None] = mapped_column(Text)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    bmi: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    profile_snapshot: Mapped[dict | None] = mapped_column(JSONB)


class DayEntry(AccountOwned, Base):
    __tablename__ = "day_entries"
    __table_args__ = (UniqueConstraint("account_id", "date", name="uq_day_entries_account_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    weight_source: Mapped[str | None] = mapped_column(Text)  # 'scale_esp' | 'manual' | 'google_fit' | None
    bmi: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    steps: Mapped[int | None] = mapped_column(Integer)
    sleep_hours: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    # Sleep detail metrics — from Google Fit sleep segments (never manually "done")
    sleep_deep_hours: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    sleep_rem_hours: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    sleep_light_hours: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    sleep_awake_hours: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    sleep_efficiency: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))  # 0-100
    sleep_quality: Mapped[int | None] = mapped_column(Integer)  # 1-5 derived score
    cardio_minutes: Mapped[int | None] = mapped_column(Integer)
    training_type: Mapped[str | None] = mapped_column(Text)
    training_done: Mapped[bool] = mapped_column(Boolean, default=False)
    rotation_slot: Mapped[int | None] = mapped_column(Integer)
    steps_done: Mapped[bool] = mapped_column(Boolean, default=False)  # legacy, kept for compat
    steps_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)  # only set by API
    steps_source: Mapped[str | None] = mapped_column(Text)  # 'google_fit' | 'manual' | None
    sleep_done: Mapped[bool] = mapped_column(Boolean, default=False)  # legacy, kept for compat
    creatine_done: Mapped[bool] = mapped_column(Boolean, default=False)
    cardio_done: Mapped[bool] = mapped_column(Boolean, default=False)
    belly_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Todo(AccountOwned, Base):
    __tablename__ = "todos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=2)
    status: Mapped[str] = mapped_column(Text, default="open")
    due_date: Mapped[date | None] = mapped_column(Date)
    due_time: Mapped[time | None] = mapped_column(Time)
    start_time: Mapped[time | None] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time)
    is_all_day: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(Text, default="manual")
    external_id: Mapped[str | None] = mapped_column(Text)
    space_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("spaces.id", ondelete="SET NULL"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("space_projects.id", ondelete="SET NULL"))
    assignee_account_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL"))
    # A Google Place ID is the durable, unique destination reference. Display
    # strings are snapshots and never substitute for the identifier.
    place_id: Mapped[str | None] = mapped_column(Text)
    place_name: Mapped[str | None] = mapped_column(Text)
    place_address: Mapped[str | None] = mapped_column(Text)
    travel_mode: Mapped[str | None] = mapped_column(Text)
    travel_buffer_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    travel_monitoring_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    travel_last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    travel_duration_seconds: Mapped[int | None] = mapped_column(Integer)
    travel_depart_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TodoRoutine(AccountOwned, Base):
    """An account-private rule that creates one todo on matching calendar days."""

    __tablename__ = "todo_routines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    weekdays: Mapped[list[int]] = mapped_column(JSONB, nullable=False, default=list)
    due_time: Mapped[time | None] = mapped_column(Time)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


# Configurable meal records are immutable at use: nutritional values copied to
# MealEntry/MealEntryItem remain historical facts.
class MealCategory(AccountOwned, Base):
    __tablename__ = "meal_categories"
    __table_args__ = (UniqueConstraint("account_id", "name", name="uq_meal_categories_account_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Food(AccountOwned, Base):
    __tablename__ = "foods"
    __table_args__ = (UniqueConstraint("account_id", "name", name="uq_foods_account_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list | None] = mapped_column(JSONB)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    confidence: Mapped[str] = mapped_column(Text, nullable=False, default="verified")
    kcal_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    protein_g_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    carbs_g_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    fat_g_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    fiber_g_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    sugar_g_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    free_sugar_g_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    saturated_fat_g_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    sodium_mg_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    potassium_mg_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    calcium_mg_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    magnesium_mg_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    iron_mg_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    zinc_mg_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    vitamin_a_ug_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    vitamin_c_mg_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    vitamin_d_ug_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    vitamin_b12_ug_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    folate_ug_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Recipe(AccountOwned, Base):
    __tablename__ = "recipes"
    __table_args__ = (UniqueConstraint("account_id", "name", name="uq_recipes_account_name"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    servings: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, default=Decimal("1"))
    notes: Mapped[str | None] = mapped_column(Text)
    # Ordered, human-authored cooking directions.  Ingredients remain the
    # nutritional source of truth; directions must never contain nutrition
    # values that the API would be unable to validate.
    instructions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # Complete per-serving nutrition for imported or manually specified
    # recipes whose ingredient list is unavailable. This prevents a complete
    # dish from masquerading as a Food merely to carry its nutrient values.
    nutrition_per_serving: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class MealCategoryRecipePreset(AccountOwned, Base):
    """A person's two quick recipe choices for one meal category.

    Recipes are deliberately not given a global ``is_default`` flag: the same
    recipe can be a useful breakfast and an occasional dinner.  The category
    owns the shortcut and its stable display rank instead.
    """
    __tablename__ = "meal_category_recipe_presets"
    __table_args__ = (
        UniqueConstraint("account_id", "category_id", "rank", name="uq_meal_category_recipe_preset_rank"),
        UniqueConstraint("account_id", "category_id", "recipe_id", name="uq_meal_category_recipe_preset_recipe"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meal_categories.id", ondelete="CASCADE"), nullable=False)
    recipe_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RecipeIngredient(AccountOwned, Base):
    __tablename__ = "recipe_ingredients"
    __table_args__ = (UniqueConstraint("recipe_id", "sort_order", name="uq_recipe_ingredients_order"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    food_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("foods.id"))
    nested_recipe_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(Text, nullable=False, default="g")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class MealPlan(AccountOwned, Base):
    __tablename__ = "meal_plans"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class MealPlanItem(AccountOwned, Base):
    __tablename__ = "meal_plan_items"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meal_plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meal_plans.id", ondelete="CASCADE"), nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meal_categories.id"), nullable=False)
    recipe_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id"))
    name: Mapped[str | None] = mapped_column(Text)
    planned_time: Mapped[time | None] = mapped_column(Time)
    weekdays: Mapped[list | None] = mapped_column(JSONB)  # ISO weekday values 0..6, null = every day
    portion: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, default=Decimal("1"))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Removed items are retained while historic entries still reference them.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class MealPlanVersion(AccountOwned, Base):
    """Immutable audit snapshot of a plan revision."""
    __tablename__ = "meal_plan_versions"
    __table_args__ = (UniqueConstraint("meal_plan_id", "version", name="uq_meal_plan_versions_plan_version"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meal_plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meal_plans.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    items_snapshot: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MealEntry(AccountOwned, Base):
    __tablename__ = "meal_entries"
    __table_args__ = (UniqueConstraint("account_id", "date", "meal_plan_id", "meal_plan_item_id", name="uq_meal_entries_plan_instance"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meal_categories.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="planned")
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    meal_plan_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("meal_plans.id"))
    meal_plan_item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("meal_plan_items.id"))
    meal_plan_version: Mapped[int | None] = mapped_column(Integer)
    nutrition_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class MealEntryItem(AccountOwned, Base):
    __tablename__ = "meal_entry_items"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meal_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meal_entries.id", ondelete="CASCADE"), nullable=False)
    food_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("foods.id"))
    recipe_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("recipes.id"))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(Text, nullable=False, default="g")
    nutrition_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    source_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class ShoppingList(AccountOwned, Base):
    """A private or explicitly shared manual shopping workspace."""
    __tablename__ = "shopping_lists"
    __table_args__ = (UniqueConstraint("account_id", "name", name="uq_shopping_lists_account_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False, default="Einkauf")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    space_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("spaces.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ShoppingItem(AccountOwned, Base):
    __tablename__ = "shopping_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shopping_list_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shopping_lists.id", ondelete="CASCADE"), nullable=False)
    food_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("foods.id"))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    category_key: Mapped[str] = mapped_column(Text, nullable=False, default="other")
    icon_key: Mapped[str] = mapped_column(Text, nullable=False, default="shopping")
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    unit: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="open")
    source: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ShoppingMealImport(AccountOwned, Base):
    """Records a confirmed plan period so repeated imports remain idempotent."""
    __tablename__ = "shopping_meal_imports"
    __table_args__ = (UniqueConstraint("shopping_list_id", "meal_plan_id", "meal_plan_version", "from_date", "to_date", name="uq_shopping_meal_import_period"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shopping_list_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shopping_lists.id", ondelete="CASCADE"), nullable=False)
    meal_plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meal_plans.id"), nullable=False)
    meal_plan_version: Mapped[int] = mapped_column(Integer, nullable=False)
    from_date: Mapped[date] = mapped_column(Date, nullable=False)
    to_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TrainingUnit(AccountOwned, Base):
    __tablename__ = "training_units"
    __table_args__ = (UniqueConstraint("account_id", "name", name="uq_training_units_account_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    unit_type: Mapped[str] = mapped_column(Text, nullable=False, default="gym")
    cardio_minutes: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class TrainingRotation(AccountOwned, Base):
    __tablename__ = "training_rotation"
    __table_args__ = (UniqueConstraint("account_id", "slot", name="uq_training_rotation_account_slot"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slot: Mapped[int] = mapped_column(Integer, nullable=False)
    training_type: Mapped[str] = mapped_column(Text, nullable=False)
    weekday: Mapped[int | None] = mapped_column(Integer)
    frequency_weeks: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    week_offset: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_date: Mapped[date | None] = mapped_column(Date)


class TrainingSet(AccountOwned, Base):
    __tablename__ = "training_sets"
    __table_args__ = (
        UniqueConstraint("account_id", "date", "exercise_name", "set_number", name="uq_training_set_account_date_ex_set"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    training_type: Mapped[str] = mapped_column(Text, nullable=False)
    exercise_name: Mapped[str] = mapped_column(Text, nullable=False)
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    set_type: Mapped[str | None] = mapped_column(Text, default="work")
    reps: Mapped[int | None] = mapped_column(Integer)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    rir: Mapped[int | None] = mapped_column(Integer)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Exercise(AccountOwned, Base):
    __tablename__ = "exercises"
    __table_args__ = (
        UniqueConstraint("account_id", "training_type", "exercise_name", name="uq_exercises_account_type_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    training_type: Mapped[str] = mapped_column(Text, nullable=False)
    exercise_name: Mapped[str] = mapped_column(Text, nullable=False)
    target_sets: Mapped[str] = mapped_column(Text, nullable=False)
    target_reps_low: Mapped[int | None] = mapped_column(Integer)
    target_reps_high: Mapped[int | None] = mapped_column(Integer)
    base_reps_low: Mapped[int | None] = mapped_column(Integer)
    base_reps_high: Mapped[int | None] = mapped_column(Integer)
    target_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    progression_strategy: Mapped[str] = mapped_column(Text, default="double_progression")
    progression_increment_weight: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=Decimal("2.5"))
    is_topset: Mapped[bool] = mapped_column(Boolean, default=False)
    top_set_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    backoff_set_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    backoff_reps_low: Mapped[int | None] = mapped_column(Integer)
    backoff_reps_high: Mapped[int | None] = mapped_column(Integer)
    backoff_weight_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    target_rir: Mapped[int | None] = mapped_column(Integer, default=2)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class SyncLog(AccountOwned, Base):
    __tablename__ = "sync_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    client_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    server_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    synced: Mapped[bool] = mapped_column(Boolean, default=True)


class Photo(AccountOwned, Base):
    __tablename__ = "photos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meal_entry_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("meal_entries.id", ondelete="SET NULL"))
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str | None] = mapped_column(Text)
    mime_type: Mapped[str | None] = mapped_column(Text)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MealPhotoAnalysis(AccountOwned, Base):
    __tablename__ = "meal_photo_analyses"
    __table_args__ = (UniqueConstraint("photo_id", name="uq_meal_photo_analyses_photo"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    photo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("photos.id", ondelete="CASCADE"), nullable=False)
    meal_entry_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meal_entries.id", ondelete="CASCADE"), nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False, default="pending")
    analysis: Mapped[dict | None] = mapped_column(JSONB)
    provider: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    schema_version: Mapped[str | None] = mapped_column(Text)
    error_code: Mapped[str | None] = mapped_column(Text)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class GoogleToken(AccountOwned, Base):
    __tablename__ = "google_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str | None] = mapped_column(Text)
    access_token: Mapped[str | None] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    token_type: Mapped[str] = mapped_column(Text, default="Bearer")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scope: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ExerciseProgress(AccountOwned, Base):
    """Tracks actual performance per exercise per completed session."""
    __tablename__ = "exercise_progress"
    __table_args__ = (UniqueConstraint("account_id", "exercise_id", "date", name="uq_exercise_progress_account_exercise_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    exercise_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("exercises.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    training_type: Mapped[str] = mapped_column(Text, nullable=False)
    exercise_name: Mapped[str] = mapped_column(Text, nullable=False)
    topset_reps: Mapped[int | None] = mapped_column(Integer)
    topset_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    topset_rir: Mapped[int | None] = mapped_column(Integer)
    all_sets_reps: Mapped[list | None] = mapped_column(JSONB)  # [{reps, weight, rir, set_type}, ...]
    total_volume_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    progression_action: Mapped[str] = mapped_column(Text, default="none")  # weight_increase | rep_increase | none | deload
    prev_target_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    prev_target_reps_low: Mapped[int | None] = mapped_column(Integer)
    new_target_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    new_target_reps_low: Mapped[int | None] = mapped_column(Integer)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Goal(AccountOwned, Base):
    """Backend-persisted daily/weekly goals — single source of truth, not frontend-only."""
    __tablename__ = "goals"
    __table_args__ = (UniqueConstraint("account_id", "key", name="uq_goals_account_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(Text, nullable=False)  # kcal | protein | carbs | fat | steps | sleep_hours | training_days_per_week
    value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
