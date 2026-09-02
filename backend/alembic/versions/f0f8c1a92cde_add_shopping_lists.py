"""Add account-private shopping lists and meal imports.

Revision ID: f0f8c1a92cde
Revises: 7095ad546555
Create Date: 2026-09-02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "f0f8c1a92cde"
down_revision = "7095ad546555"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shopping_lists",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "name", name="uq_shopping_lists_account_name"),
    )
    op.create_index("ix_shopping_lists_account_id", "shopping_lists", ["account_id"])
    op.create_table(
        "shopping_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("shopping_list_id", sa.UUID(), nullable=False),
        sa.Column("food_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("category_key", sa.Text(), nullable=False),
        sa.Column("icon_key", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["food_id"], ["foods.id"]),
        sa.ForeignKeyConstraint(["shopping_list_id"], ["shopping_lists.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shopping_items_account_id", "shopping_items", ["account_id"])
    op.create_table(
        "shopping_meal_imports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("shopping_list_id", sa.UUID(), nullable=False),
        sa.Column("meal_plan_id", sa.UUID(), nullable=False),
        sa.Column("meal_plan_version", sa.Integer(), nullable=False),
        sa.Column("from_date", sa.Date(), nullable=False),
        sa.Column("to_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["shopping_list_id"], ["shopping_lists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["meal_plan_id"], ["meal_plans.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shopping_list_id", "meal_plan_id", "meal_plan_version", "from_date", "to_date", name="uq_shopping_meal_import_period"),
    )
    op.create_index("ix_shopping_meal_imports_account_id", "shopping_meal_imports", ["account_id"])


def downgrade() -> None:
    op.drop_index("ix_shopping_meal_imports_account_id", table_name="shopping_meal_imports")
    op.drop_table("shopping_meal_imports")
    op.drop_index("ix_shopping_items_account_id", table_name="shopping_items")
    op.drop_table("shopping_items")
    op.drop_index("ix_shopping_lists_account_id", table_name="shopping_lists")
    op.drop_table("shopping_lists")
