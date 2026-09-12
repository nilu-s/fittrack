"""Add account-private learned shopping icon choices.

Revision ID: c6d7e8f9a012
Revises: b60908c002
Create Date: 2026-09-12
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "c6d7e8f9a012"
down_revision = "b60908c002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shopping_icon_preferences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("normalized_title", sa.Text(), nullable=False),
        sa.Column("category_key", sa.Text(), nullable=False),
        sa.Column("icon_key", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "normalized_title", name="uq_shopping_icon_preferences_account_title"),
    )
    op.create_index("ix_shopping_icon_preferences_account_id", "shopping_icon_preferences", ["account_id"])


def downgrade() -> None:
    op.drop_index("ix_shopping_icon_preferences_account_id", table_name="shopping_icon_preferences")
    op.drop_table("shopping_icon_preferences")
