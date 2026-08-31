"""Finalize the one-way account ownership cutover.

Revision ID: 021
Revises: 020

This revision is intentionally a release gate: applying it to a legacy
database requires the nominated owner to have completed an allowed Google
login after revision 019.  It never guesses an account from a device or from
an arbitrary email address.
"""
from __future__ import annotations

import os

from alembic import op
import sqlalchemy as sa


revision = "021"
down_revision = "020"

OWNED_TABLES = (
    "day_entries", "meals", "todos", "meal_templates", "training_units",
    "training_rotation", "training_sets", "exercises", "sync_log", "photos",
    "google_tokens", "exercise_progress", "dishes", "goals",
)

REMOVED_WEIGHT_ONLY_COLUMNS = (
    "body_fat_pct", "muscle_mass_kg", "water_pct", "bone_mass_kg",
    "basal_metabolism", "impedance", "visceral_fat", "metabolic_age",
)

LEGACY_UNIQUES = (
    ("day_entries", "uq_day_entries_user_date", ("account_id", "date"), "uq_day_entries_account_date"),
    ("meal_templates", "uq_meal_templates_user_slot", ("account_id", "slot"), "uq_meal_templates_account_slot"),
    ("training_units", "uq_training_units_user_name", ("account_id", "name"), "uq_training_units_account_name"),
    ("training_rotation", "uq_training_rotation_user_slot", ("account_id", "slot"), "uq_training_rotation_account_slot"),
    ("training_sets", "uq_training_set_user_date_ex_set", ("account_id", "date", "exercise_name", "set_number"), "uq_training_set_account_date_ex_set"),
    ("exercises", "uq_exercises_user_type_name", ("account_id", "training_type", "exercise_name"), "uq_exercises_account_type_name"),
    ("exercise_progress", "uq_exercise_progress_user_exercise_date", ("account_id", "exercise_id", "date"), "uq_exercise_progress_account_exercise_date"),
    ("dishes", "uq_dishes_user_name", ("account_id", "name"), "uq_dishes_account_name"),
    ("goals", "uq_goals_user_key", ("account_id", "key"), "uq_goals_account_key"),
)


def upgrade() -> None:
    bind = op.get_bind()
    missing = sum(
        bind.execute(sa.text(f"SELECT count(*) FROM {table} WHERE account_id IS NULL")).scalar_one()
        for table in OWNED_TABLES
    )
    if missing:
        legacy_owner_email = os.environ.get("LEGACY_OWNER_EMAIL", "").strip().casefold()
        if not legacy_owner_email:
            raise RuntimeError("LEGACY_OWNER_EMAIL is required while legacy account-owned rows exist")
        accounts = bind.execute(
            sa.text("SELECT id FROM accounts WHERE lower(email) = :email"),
            {"email": legacy_owner_email},
        ).scalars().all()
        if len(accounts) != 1:
            raise RuntimeError("legacy owner must resolve to exactly one authenticated account")
        for table in OWNED_TABLES:
            bind.execute(
                sa.text(
                    f"UPDATE {table} SET account_id = :account_id "
                    "WHERE account_id IS NULL AND user_id = 'luis'"
                ),
                {"account_id": accounts[0]},
            )
    for table in OWNED_TABLES:
        orphan_count = bind.execute(
            sa.text(f"SELECT count(*) FROM {table} WHERE account_id IS NULL")
        ).scalar_one()
        if orphan_count:
            raise RuntimeError(f"{table} contains account-owned rows without a resolved account")
        op.alter_column(table, "account_id", existing_type=sa.UUID(), nullable=False)
    for table, old_name, columns, new_name in LEGACY_UNIQUES:
        op.drop_constraint(old_name, table, type_="unique")
        op.create_unique_constraint(new_name, table, columns)
    for table in OWNED_TABLES:
        op.drop_column(table, "user_id")
    # The current bridge has no genuine impedance. These provisional fields
    # must not survive a weight-only release as dormant medical-looking data.
    for column in REMOVED_WEIGHT_ONLY_COLUMNS:
        op.drop_column("day_entries", column)


def downgrade() -> None:
    op.add_column("day_entries", sa.Column("metabolic_age", sa.Integer(), nullable=True))
    op.add_column("day_entries", sa.Column("visceral_fat", sa.Integer(), nullable=True))
    op.add_column("day_entries", sa.Column("impedance", sa.Integer(), nullable=True))
    op.add_column("day_entries", sa.Column("basal_metabolism", sa.Integer(), nullable=True))
    op.add_column("day_entries", sa.Column("bone_mass_kg", sa.Numeric(5, 2), nullable=True))
    op.add_column("day_entries", sa.Column("water_pct", sa.Numeric(5, 2), nullable=True))
    op.add_column("day_entries", sa.Column("muscle_mass_kg", sa.Numeric(5, 2), nullable=True))
    op.add_column("day_entries", sa.Column("body_fat_pct", sa.Numeric(5, 2), nullable=True))
    for table in OWNED_TABLES:
        op.add_column(table, sa.Column("user_id", sa.Text(), nullable=True))
    for table, old_name, columns, new_name in reversed(LEGACY_UNIQUES):
        op.drop_constraint(new_name, table, type_="unique")
        legacy_columns = tuple("user_id" if column == "account_id" else column for column in columns)
        op.create_unique_constraint(old_name, table, legacy_columns)
    for table in reversed(OWNED_TABLES):
        op.alter_column(table, "account_id", existing_type=sa.UUID(), nullable=True)
