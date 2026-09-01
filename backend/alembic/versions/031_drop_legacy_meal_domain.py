"""Drop the retired Meal, Dish, and MealTemplate persistence domain.

Revision ID: 031
Revises: 030
"""
from alembic import op


revision = "031"
down_revision = "030"


def upgrade() -> None:
    # 026 removed the records; 030 retained all useful nutrient snapshots in
    # the configurable domain.  The old tables and photo link can now vanish.
    op.drop_column("photos", "meal_id")
    op.drop_table("dishes")
    op.drop_table("meals")
    op.drop_table("meal_templates")


def downgrade() -> None:
    raise RuntimeError("The retired meal domain has no safe reconstruction path")
