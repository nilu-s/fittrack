"""Add dishes table for reusable meal presets + photo-grown dish database.

Revision ID: 006
Revises: 005
Create Date: 2026-08-20
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dishes",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Text, nullable=False, server_default="luis"),
        sa.Column("slot", sa.Integer, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("kcal", sa.Numeric(7, 2)),
        sa.Column("protein_g", sa.Numeric(6, 2)),
        sa.Column("carbs_g", sa.Numeric(6, 2)),
        sa.Column("fat_g", sa.Numeric(6, 2)),
        sa.Column("photo_url", sa.Text),
        sa.Column("is_default", sa.Boolean, server_default=sa.text("false")),
        sa.Column("usage_count", sa.Integer, server_default="0"),
        sa.Column("source", sa.Text, server_default="seed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "slot", "name", name="uq_dishes_user_slot_name"),
    )

    # Migrate existing meal_templates into dishes with is_default=true
    op.execute("""
        INSERT INTO dishes (id, user_id, slot, name, kcal, protein_g, carbs_g, fat_g, is_default, usage_count, source)
        SELECT gen_random_uuid(), user_id, slot, name, kcal, protein_g, carbs_g, fat_g, true, 0, 'seed'
        FROM meal_templates
        ON CONFLICT (user_id, slot, name) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_table("dishes")