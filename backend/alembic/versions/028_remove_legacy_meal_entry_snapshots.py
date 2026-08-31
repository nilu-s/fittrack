"""Remove legacy meal-entry snapshots after the configurable-meal cutover.

Revision ID: 028
Revises: 027

The legacy rows are copies of the retired Meal domain, not the configurable
meal source of truth. Manual entries and plan projections are preserved.
"""
from alembic import op


revision = "028"
down_revision = "027"


def upgrade() -> None:
    op.execute("""
        DELETE FROM meal_entries
        WHERE source = 'legacy'
    """)


def downgrade() -> None:
    # Removed legacy snapshots cannot be reconstructed safely.
    pass
