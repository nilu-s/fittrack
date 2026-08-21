"""Harden training session persistence.

Revision ID: 016
Revises: 015
"""
from alembic import op

revision = "016"
down_revision = "015"


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_exercise_progress_user_exercise_date",
        "exercise_progress",
        ["user_id", "exercise_id", "date"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_exercise_progress_user_exercise_date", "exercise_progress", type_="unique")
