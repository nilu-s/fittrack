"""Add sleep detail metrics and steps_source column.

Revision ID: 004
Revises: 003
Create Date: 2026-08-20
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Sleep detail metrics (from Google Fit sleep segments)
    op.add_column("day_entries", sa.Column("sleep_deep_hours", sa.Numeric(4, 2)))
    op.add_column("day_entries", sa.Column("sleep_rem_hours", sa.Numeric(4, 2)))
    op.add_column("day_entries", sa.Column("sleep_light_hours", sa.Numeric(4, 2)))
    op.add_column("day_entries", sa.Column("sleep_awake_hours", sa.Numeric(4, 2)))
    op.add_column("day_entries", sa.Column("sleep_efficiency", sa.Numeric(5, 2)))
    op.add_column("day_entries", sa.Column("sleep_quality", sa.Integer))

    # Steps provenance — 'google_fit' when API confirmed, 'manual' when user entered, NULL when nothing
    op.add_column("day_entries", sa.Column("steps_source", sa.Text))

    # steps_confirmed replaces steps_done semantics: only set by API, not manual toggle
    op.add_column("day_entries", sa.Column("steps_confirmed", sa.Boolean, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("day_entries", "steps_confirmed")
    op.drop_column("day_entries", "steps_source")
    op.drop_column("day_entries", "sleep_quality")
    op.drop_column("day_entries", "sleep_efficiency")
    op.drop_column("day_entries", "sleep_awake_hours")
    op.drop_column("day_entries", "sleep_light_hours")
    op.drop_column("day_entries", "sleep_rem_hours")
    op.drop_column("day_entries", "sleep_deep_hours")