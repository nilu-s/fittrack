"""Initial migration — create all FitTrack tables.

Revision ID: 001
Revises:
Create Date: 2026-08-19
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- day_entries ---
    op.create_table(
        "day_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.Text, nullable=False, server_default="luis"),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("weight_kg", sa.Numeric(5, 2)),
        sa.Column("steps", sa.Integer),
        sa.Column("sleep_hours", sa.Numeric(4, 2)),
        sa.Column("cardio_minutes", sa.Integer),
        sa.Column("training_type", sa.Text),
        sa.Column("training_done", sa.Boolean, server_default=sa.false()),
        sa.Column("rotation_slot", sa.Integer),
        sa.Column("steps_done", sa.Boolean, server_default=sa.false()),
        sa.Column("sleep_done", sa.Boolean, server_default=sa.false()),
        sa.Column("creatine_done", sa.Boolean, server_default=sa.false()),
        sa.Column("belly_cm", sa.Numeric(5, 2)),
        sa.Column("notes", sa.Text),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "date", name="uq_day_entries_user_date"),
    )

    # --- meals ---
    op.create_table(
        "meals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.Text, nullable=False, server_default="luis"),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("meal_slot", sa.Integer, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("default_time", sa.Time),
        sa.Column("kcal", sa.Numeric(7, 2)),
        sa.Column("protein_g", sa.Numeric(6, 2)),
        sa.Column("carbs_g", sa.Numeric(6, 2)),
        sa.Column("fat_g", sa.Numeric(6, 2)),
        sa.Column("is_standard", sa.Boolean, server_default=sa.false()),
        sa.Column("is_done", sa.Boolean, server_default=sa.false()),
        sa.Column("replaced_by", sa.Text),
        sa.Column("photo_url", sa.Text),
        sa.Column("photo_analysis", postgresql.JSONB),
        sa.Column("assigned_via_photo", sa.Boolean, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- todos ---
    op.create_table(
        "todos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.Text, nullable=False, server_default="luis"),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("category", sa.Text),
        sa.Column("priority", sa.Integer, server_default="2"),
        sa.Column("status", sa.Text, server_default="open"),
        sa.Column("due_date", sa.Date),
        sa.Column("due_time", sa.Time),
        sa.Column("start_time", sa.Time),
        sa.Column("end_time", sa.Time),
        sa.Column("is_all_day", sa.Boolean, server_default=sa.true()),
        sa.Column("source", sa.Text, server_default="manual"),
        sa.Column("external_id", sa.Text),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("sort_order", sa.Integer, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- meal_templates ---
    op.create_table(
        "meal_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.Text, nullable=False, server_default="luis"),
        sa.Column("slot", sa.Integer, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("kcal", sa.Numeric(7, 2)),
        sa.Column("protein_g", sa.Numeric(6, 2)),
        sa.Column("carbs_g", sa.Numeric(6, 2)),
        sa.Column("fat_g", sa.Numeric(6, 2)),
        sa.UniqueConstraint("user_id", "slot", name="uq_meal_templates_user_slot"),
    )

    # --- training_rotation ---
    op.create_table(
        "training_rotation",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.Text, nullable=False, server_default="luis"),
        sa.Column("slot", sa.Integer, nullable=False),
        sa.Column("training_type", sa.Text, nullable=False),
        sa.Column("cardio_minutes", sa.Integer),
        sa.UniqueConstraint("user_id", "slot", name="uq_training_rotation_user_slot"),
    )

    # --- training_sets ---
    op.create_table(
        "training_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.Text, nullable=False, server_default="luis"),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("training_type", sa.Text, nullable=False),
        sa.Column("exercise_name", sa.Text, nullable=False),
        sa.Column("set_number", sa.Integer, nullable=False),
        sa.Column("set_type", sa.Text, server_default="work"),
        sa.Column("reps", sa.Integer),
        sa.Column("weight_kg", sa.Numeric(5, 2)),
        sa.Column("rir", sa.Integer),
        sa.Column("completed", sa.Boolean, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- exercises ---
    op.create_table(
        "exercises",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.Text, nullable=False, server_default="luis"),
        sa.Column("training_type", sa.Text, nullable=False),
        sa.Column("exercise_name", sa.Text, nullable=False),
        sa.Column("target_sets", sa.Text, nullable=False),
        sa.Column("target_reps_low", sa.Integer),
        sa.Column("target_reps_high", sa.Integer),
        sa.Column("target_weight_kg", sa.Numeric(5, 2)),
        sa.Column("progression_strategy", sa.Text, server_default="double_progression"),
        sa.Column("progression_increment_weight", sa.Numeric(5, 2), server_default="2.5"),
        sa.Column("is_topset", sa.Boolean, server_default=sa.false()),
        sa.Column("target_rir", sa.Integer, server_default="2"),
        sa.Column("sort_order", sa.Integer, server_default="0"),
        sa.UniqueConstraint("user_id", "training_type", "exercise_name", name="uq_exercises_user_type_name"),
    )

    # --- sync_log ---
    op.create_table(
        "sync_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.Text, nullable=False, server_default="luis"),
        sa.Column("entity_type", sa.Text, nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("payload", postgresql.JSONB),
        sa.Column("client_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("server_timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("synced", sa.Boolean, server_default=sa.true()),
    )

    # --- photos ---
    op.create_table(
        "photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.Text, nullable=False, server_default="luis"),
        sa.Column("meal_id", postgresql.UUID(as_uuid=True)),
        sa.Column("file_path", sa.Text, nullable=False),
        sa.Column("original_filename", sa.Text),
        sa.Column("mime_type", sa.Text),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("photos")
    op.drop_table("sync_log")
    op.drop_table("exercises")
    op.drop_table("training_sets")
    op.drop_table("training_rotation")
    op.drop_table("meal_templates")
    op.drop_table("todos")
    op.drop_table("meals")
    op.drop_table("day_entries")