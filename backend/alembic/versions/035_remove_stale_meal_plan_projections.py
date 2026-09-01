"""Remove pending meal projections superseded by the active plan.

Revision ID: 035
Revises: 034
"""
from alembic import op


revision = "035"
down_revision = "034"


def upgrade() -> None:
    # Planned plan entries are disposable projections.  Preserve manual,
    # consumed and skipped entries as historical records.
    op.execute("""
        DELETE FROM meal_entries entry
        WHERE entry.source = 'plan'
          AND entry.status = 'planned'
          AND NOT EXISTS (
              SELECT 1
              FROM meal_plans plan
              WHERE plan.id = entry.meal_plan_id
                AND plan.account_id = entry.account_id
                AND plan.is_active = true
                AND plan.version = entry.meal_plan_version
          )
    """)


def downgrade() -> None:
    # Removed pending projections can be recreated deterministically from the
    # current active plan; old plan versions must not be reconstructed.
    pass
