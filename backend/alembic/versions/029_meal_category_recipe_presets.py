"""Add account-scoped quick recipe choices for meal categories.

Revision ID: 029
Revises: 028
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "029"
down_revision = "028"


def upgrade() -> None:
    op.create_table(
        "meal_category_recipe_presets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meal_categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("rank BETWEEN 1 AND 2", name="ck_meal_category_recipe_preset_rank"),
        sa.UniqueConstraint("account_id", "category_id", "rank", name="uq_meal_category_recipe_preset_rank"),
        sa.UniqueConstraint("account_id", "category_id", "recipe_id", name="uq_meal_category_recipe_preset_recipe"),
    )
    op.create_index("ix_meal_category_recipe_presets_account_category", "meal_category_recipe_presets", ["account_id", "category_id"])


def downgrade() -> None:
    op.drop_index("ix_meal_category_recipe_presets_account_category", table_name="meal_category_recipe_presets")
    op.drop_table("meal_category_recipe_presets")
