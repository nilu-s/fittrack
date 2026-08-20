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


class DayEntry(Base):
    __tablename__ = "day_entries"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_day_entries_user_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(Text, nullable=False, default="luis")
    date: Mapped[date] = mapped_column(Date, nullable=False)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    weight_source: Mapped[str | None] = mapped_column(Text)  # 'scale_esp' | 'manual' | 'google_fit' | None
    # Body composition — from Renpho scale via ESP32 BLE
    body_fat_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    muscle_mass_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    water_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    bone_mass_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    bmi: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    basal_metabolism: Mapped[int | None] = mapped_column(Integer)  # BMR in kcal
    impedance: Mapped[int | None] = mapped_column(Integer)  # ohms
    visceral_fat: Mapped[int | None] = mapped_column(Integer)
    metabolic_age: Mapped[int | None] = mapped_column(Integer)
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


class Meal(Base):
    __tablename__ = "meals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(Text, nullable=False, default="luis")
    date: Mapped[date] = mapped_column(Date, nullable=False)
    meal_slot: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    default_time: Mapped[time | None] = mapped_column(Time)
    kcal: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    protein_g: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    carbs_g: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    fat_g: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    is_standard: Mapped[bool] = mapped_column(Boolean, default=False)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False)
    replaced_by: Mapped[str | None] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(Text)
    photo_analysis: Mapped[dict | None] = mapped_column(JSONB)
    assigned_via_photo: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Todo(Base):
    __tablename__ = "todos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(Text, nullable=False, default="luis")
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
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MealTemplate(Base):
    __tablename__ = "meal_templates"
    __table_args__ = (UniqueConstraint("user_id", "slot", name="uq_meal_templates_user_slot"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(Text, nullable=False, default="luis")
    slot: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    kcal: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    protein_g: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    carbs_g: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    fat_g: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))


class TrainingRotation(Base):
    __tablename__ = "training_rotation"
    __table_args__ = (UniqueConstraint("user_id", "slot", name="uq_training_rotation_user_slot"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(Text, nullable=False, default="luis")
    slot: Mapped[int] = mapped_column(Integer, nullable=False)
    training_type: Mapped[str] = mapped_column(Text, nullable=False)
    cardio_minutes: Mapped[int | None] = mapped_column(Integer)


class TrainingSet(Base):
    __tablename__ = "training_sets"
    __table_args__ = (
        UniqueConstraint("user_id", "date", "exercise_name", "set_number", name="uq_training_set_user_date_ex_set"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(Text, nullable=False, default="luis")
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


class Exercise(Base):
    __tablename__ = "exercises"
    __table_args__ = (
        UniqueConstraint("user_id", "training_type", "exercise_name", name="uq_exercises_user_type_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(Text, nullable=False, default="luis")
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
    target_rir: Mapped[int | None] = mapped_column(Integer, default=2)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class SyncLog(Base):
    __tablename__ = "sync_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(Text, nullable=False, default="luis")
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    client_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    server_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    synced: Mapped[bool] = mapped_column(Boolean, default=True)


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(Text, nullable=False, default="luis")
    meal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str | None] = mapped_column(Text)
    mime_type: Mapped[str | None] = mapped_column(Text)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GoogleToken(Base):
    __tablename__ = "google_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(Text, default="luis")
    email: Mapped[str | None] = mapped_column(Text)
    access_token: Mapped[str | None] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    token_type: Mapped[str] = mapped_column(Text, default="Bearer")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scope: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ExerciseProgress(Base):
    """Tracks actual performance per exercise per session — separate from Exercise definition.

    Exercise.target_reps_low / target_weight_kg are the CURRENT target (mutated by progression).
    ExerciseProgress records what actually happened and the progression decision applied.
    This prevents the old bug where target_reps_low drifts up and gets stuck.
    """
    __tablename__ = "exercise_progress"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(Text, nullable=False, default="luis")
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


class Dish(Base):
    """Reusable dish/preset — grows over time from templates + photo analyses.

    is_default=True marks the dish that auto-creates as the meal for a slot each day.
    Multiple dishes per slot exist; user picks via long-press or photo creates new ones.
    """
    __tablename__ = "dishes"
    __table_args__ = (
        UniqueConstraint("user_id", "slot", "name", name="uq_dishes_user_slot_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(Text, nullable=False, default="luis")
    slot: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    kcal: Mapped[Decimal | None] = mapped_column(Numeric(7, 2))
    protein_g: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    carbs_g: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    fat_g: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    photo_url: Mapped[str | None] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(Text, default="seed")  # 'seed' | 'photo' | 'manual'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Goal(Base):
    """Backend-persisted daily/weekly goals — single source of truth, not frontend-only."""
    __tablename__ = "goals"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_goals_user_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(Text, nullable=False, default="luis")
    key: Mapped[str] = mapped_column(Text, nullable=False)  # kcal | protein | carbs | fat | steps | sleep_hours | training_days_per_week
    value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())