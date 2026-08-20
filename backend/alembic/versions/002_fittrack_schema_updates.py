"""FitTrack schema updates: soft-delete flags, cardio_done, goals, exercise_progress, google_tokens.

Revision ID: 002
Revises: 001
Create Date: 2026-08-20
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- day_entries: add cardio_done ---
    op.add_column(
        "day_entries",
        sa.Column("cardio_done", sa.Boolean, server_default=sa.false(), default=False),
    )

    # --- meals: add deleted (soft-delete) ---
    op.add_column(
        "meals",
        sa.Column("deleted", sa.Boolean, server_default=sa.false(), default=False),
    )

    # --- todos: add deleted (soft-delete) ---
    op.add_column(
        "todos",
        sa.Column("deleted", sa.Boolean, server_default=sa.false(), default=False),
    )

    # --- training_sets: add unique constraint ---
    op.create_unique_constraint(
        "uq_training_set_user_date_ex_set",
        "training_sets",
        ["user_id", "date", "exercise_name", "set_number"],
    )

    # --- exercise_progress (IF NOT EXISTS — create_all may have already made it) ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS exercise_progress (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id TEXT NOT NULL DEFAULT 'luis',
            exercise_id UUID NOT NULL REFERENCES exercises(id),
            date DATE NOT NULL,
            training_type TEXT NOT NULL,
            exercise_name TEXT NOT NULL,
            topset_reps INTEGER,
            topset_weight_kg NUMERIC(5,2),
            topset_rir INTEGER,
            all_sets_reps JSONB,
            total_volume_kg NUMERIC(10,2),
            progression_action TEXT DEFAULT 'none',
            prev_target_weight_kg NUMERIC(5,2),
            prev_target_reps_low INTEGER,
            new_target_weight_kg NUMERIC(5,2),
            new_target_reps_low INTEGER,
            consecutive_failures INTEGER DEFAULT 0,
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)

    # --- goals (IF NOT EXISTS) ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id TEXT NOT NULL DEFAULT 'luis',
            key TEXT NOT NULL,
            value NUMERIC(10,2) NOT NULL,
            effective_from DATE NOT NULL DEFAULT CURRENT_DATE,
            updated_at TIMESTAMPTZ DEFAULT now(),
            CONSTRAINT uq_goals_user_key UNIQUE (user_id, key)
        )
    """)

    # --- google_tokens (IF NOT EXISTS) ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS google_tokens (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id TEXT DEFAULT 'luis',
            email TEXT,
            access_token TEXT,
            refresh_token TEXT,
            token_type TEXT DEFAULT 'Bearer',
            expires_at TIMESTAMPTZ,
            scope TEXT,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)


def downgrade() -> None:
    op.drop_table("google_tokens")
    op.drop_table("goals")
    op.drop_table("exercise_progress")
    op.drop_constraint("uq_training_set_user_date_ex_set", "training_sets", type_="unique")
    op.drop_column("todos", "deleted")
    op.drop_column("meals", "deleted")
    op.drop_column("day_entries", "cardio_done")
