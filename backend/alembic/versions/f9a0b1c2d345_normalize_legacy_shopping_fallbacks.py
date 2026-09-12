"""Normalize remaining legacy shopping-bag fallbacks to initials.

Revision ID: f9a0b1c2d345
Revises: e8f9a0b1c234
Create Date: 2026-09-12
"""
from alembic import op
import sqlalchemy as sa


revision = "f9a0b1c2d345"
down_revision = "e8f9a0b1c234"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A legacy ``shopping`` key was rendered as a bag by older clients.  It
    # has no article meaning, so the product fallback policy is initials.
    op.execute(sa.text("""
        UPDATE shopping_items
        SET category_key = 'other', icon_key = 'initials'
        WHERE icon_key = 'shopping'
    """))


def downgrade() -> None:
    pass
