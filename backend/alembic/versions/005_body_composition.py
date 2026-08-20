"""Add body composition fields and weight_source to day_entries.

Revision ID: 005
Revises: 004
Create Date: 2026-08-20
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("day_entries", sa.Column("weight_source", sa.Text(), nullable=True))
    op.add_column("day_entries", sa.Column("body_fat_pct", sa.Numeric(5, 2), nullable=True))
    op.add_column("day_entries", sa.Column("muscle_mass_kg", sa.Numeric(5, 2), nullable=True))
    op.add_column("day_entries", sa.Column("water_pct", sa.Numeric(5, 2), nullable=True))
    op.add_column("day_entries", sa.Column("bone_mass_kg", sa.Numeric(5, 2), nullable=True))
    op.add_column("day_entries", sa.Column("bmi", sa.Numeric(4, 1), nullable=True))
    op.add_column("day_entries", sa.Column("basal_metabolism", sa.Integer(), nullable=True))
    op.add_column("day_entries", sa.Column("impedance", sa.Integer(), nullable=True))
    op.add_column("day_entries", sa.Column("visceral_fat", sa.Integer(), nullable=True))
    op.add_column("day_entries", sa.Column("metabolic_age", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("day_entries", "metabolic_age")
    op.drop_column("day_entries", "visceral_fat")
    op.drop_column("day_entries", "impedance")
    op.drop_column("day_entries", "basal_metabolism")
    op.drop_column("day_entries", "bmi")
    op.drop_column("day_entries", "bone_mass_kg")
    op.drop_column("day_entries", "water_pct")
    op.drop_column("day_entries", "muscle_mass_kg")
    op.drop_column("day_entries", "body_fat_pct")
    op.drop_column("day_entries", "weight_source")