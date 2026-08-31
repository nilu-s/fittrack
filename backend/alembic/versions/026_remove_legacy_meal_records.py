"""Remove obsolete Meal/Dish/MealTemplate records after configurable-meal cutover.

Revision ID: 026
Revises: 025

Revision 022 copied historic daily Meal values into ``meal_entries`` as
immutable snapshots, and revision 024 created an inactive configurable plan
from MealTemplate data.  This cleanup intentionally removes only the old
parallel domain tables.  It does not touch foods, recipes, plans, categories,
or meal entries, which are the active configurable-meal domain.

The cleanup is deliberately irreversible: the source records are user health
data that were explicitly requested to be removed.  Photos tied solely to an
old Meal and legacy sync-log rows are removed as dependent stale records, so
they cannot leave dangling references or be presented as current data.
"""
from alembic import op


revision = "026"
down_revision = "025"


def upgrade() -> None:
    # ``photos.meal_id`` has no foreign key by design.  Limit this deletion to
    # IDs that actually exist in the legacy Meal table and preserve all
    # configurable MealEntry photos (including photos carrying both links).
    op.execute("""
        DELETE FROM photos
        WHERE meal_id IN (SELECT id FROM meals)
          AND meal_entry_id IS NULL
    """)

    # These server-side log entries refer to objects removed below.  Keeping
    # them would make a later sync/audit view advertise stale legacy entities.
    op.execute("DELETE FROM sync_log WHERE entity_type IN ('meal', 'meal_template', 'dish')")

    # The three tables are intentionally retained for the transitional API
    # schema; only their obsolete data is purged.  Configurable records use
    # meal_entries, recipes, foods, meal_plans, and meal_categories instead.
    op.execute("DELETE FROM meals")
    op.execute("DELETE FROM dishes")
    op.execute("DELETE FROM meal_templates")


def downgrade() -> None:
    # Data deletion cannot be reconstructed safely.
    pass
