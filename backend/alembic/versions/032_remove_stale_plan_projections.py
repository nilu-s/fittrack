"""Remove stale planned projections from retired plan items.

Revision ID: 032
Revises: 031
"""
from alembic import op


revision = "032"
down_revision = "031"


def upgrade() -> None:
    # These are not consumption records: they were only pending projections of
    # the retired plan.  Removing them lets the active standard plan create
    # exactly one current item per category/date.  Consumed entries remain
    # immutable historical nutrition snapshots.
    op.execute("""
        DELETE FROM meal_entries e
        USING meal_plan_items i
        WHERE e.meal_plan_item_id = i.id
          AND e.source = 'plan'
          AND e.status = 'planned'
          AND i.is_active = false
    """)


def downgrade() -> None:
    # Pending projections can be regenerated only by the current plan, never
    # reconstructed faithfully from a retired plan item.
    pass
