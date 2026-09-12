"""Add a shared, vetted shopping icon catalogue.

Revision ID: d7e8f9a0b123
Revises: c6d7e8f9a012
Create Date: 2026-09-12
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "d7e8f9a0b123"
down_revision = "c6d7e8f9a012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shopping_catalog_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("term_fingerprint", sa.Text(), nullable=False),
        sa.Column("category_key", sa.Text(), nullable=False),
        sa.Column("icon_key", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("term_fingerprint", name="uq_shopping_catalog_entries_term_fingerprint"),
    )
    op.create_index("ix_shopping_catalog_entries_icon_key", "shopping_catalog_entries", ["icon_key"])


def downgrade() -> None:
    op.drop_index("ix_shopping_catalog_entries_icon_key", table_name="shopping_catalog_entries")
    op.drop_table("shopping_catalog_entries")
