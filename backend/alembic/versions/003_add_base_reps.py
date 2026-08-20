"""Add base_reps_low/base_reps_high to exercises.

Revision ID: 003
Revises: 002
Create Date: 2026-08-20
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE exercises ADD COLUMN IF NOT EXISTS base_reps_low INTEGER")
    op.execute("ALTER TABLE exercises ADD COLUMN IF NOT EXISTS base_reps_high INTEGER")
    op.execute(
        "UPDATE exercises SET base_reps_low = target_reps_low, base_reps_high = target_reps_high WHERE base_reps_low IS NULL"
    )


def downgrade() -> None:
    op.drop_column("exercises", "base_reps_high")
    op.drop_column("exercises", "base_reps_low")
