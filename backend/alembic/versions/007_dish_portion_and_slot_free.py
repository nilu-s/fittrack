"""Make dishes slot-independent + add portion fields + meal portion_factor.

Revision ID: 007
Revises: 006
Create Date: 2026-08-21
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Dish: make slot nullable (preferred slot, not mandatory)
    op.alter_column("dishes", "slot", nullable=True)

    # 2. Dish: drop old unique constraint (user_id, slot, name)
    op.drop_constraint("uq_dishes_user_slot_name", "dishes", type_="unique")

    # 3. Dish: add new unique constraint (user_id, name) — dish is unique globally
    op.create_unique_constraint("uq_dishes_user_name", "dishes", ["user_id", "name"])

    # 4. Dish: add portion fields
    op.add_column("dishes", sa.Column("portion_label", sa.Text, nullable=True))
    op.add_column("dishes", sa.Column("portion_grams", sa.Numeric(7, 2), nullable=True))
    op.add_column("dishes", sa.Column("is_scalable", sa.Boolean, server_default=sa.text("false")))

    # 5. Meal: add portion_factor (default 1.0)
    op.add_column("meals", sa.Column("portion_factor", sa.Numeric(5, 2), server_default=sa.text("1.00")))

    # 6. Meal: add dish_id (optional link to dish)
    op.add_column("meals", sa.Column("dish_id", sa.UUID(as_uuid=True), nullable=True))


def downgrade() -> None:
    op.drop_column("meals", "dish_id")
    op.drop_column("meals", "portion_factor")
    op.drop_column("dishes", "is_scalable")
    op.drop_column("dishes", "portion_grams")
    op.drop_column("dishes", "portion_label")
    op.drop_constraint("uq_dishes_user_name", "dishes", type_="unique")
    op.create_unique_constraint("uq_dishes_user_slot_name", "dishes", ["user_id", "slot", "name"])
    op.alter_column("dishes", "slot", nullable=False)