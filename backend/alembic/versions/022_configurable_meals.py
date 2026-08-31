"""Add the account-private configurable meal domain.

Revision ID: 022
Revises: 021
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "022"
down_revision = "021"

UUID = postgresql.UUID(as_uuid=True)
JSON = postgresql.JSONB(astext_type=sa.Text())
NUT = sa.Numeric(10, 4)


def owned(table, columns, uniques=()):
    op.create_table(table,
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("account_id", UUID, sa.ForeignKey("accounts.id"), nullable=False),
        *columns,
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        *[sa.UniqueConstraint(*cols, name=name) for name, cols in uniques],
    )
    op.create_index(f"ix_{table}_account_id", table, ["account_id"])


def upgrade() -> None:
    owned("meal_categories", [sa.Column("name", sa.Text(), nullable=False), sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true())], [("uq_meal_categories_account_name", ("account_id", "name"))])
    owned("foods", [sa.Column("name", sa.Text(), nullable=False), sa.Column("tags", JSON), sa.Column("source", sa.Text(), nullable=False, server_default="manual"), sa.Column("confidence", sa.Text(), nullable=False, server_default="verified"), *[sa.Column(f"{n}_per_100g", NUT) for n in ("kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g", "free_sugar_g")], sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false())], [("uq_foods_account_name", ("account_id", "name"))])
    owned("recipes", [sa.Column("name", sa.Text(), nullable=False), sa.Column("status", sa.Text(), nullable=False, server_default="draft"), sa.Column("servings", sa.Numeric(10, 3), nullable=False, server_default="1"), sa.Column("notes", sa.Text())], [("uq_recipes_account_name", ("account_id", "name"))])
    owned("recipe_ingredients", [sa.Column("recipe_id", UUID, sa.ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False), sa.Column("food_id", UUID, sa.ForeignKey("foods.id")), sa.Column("nested_recipe_id", UUID, sa.ForeignKey("recipes.id")), sa.Column("quantity", sa.Numeric(12, 3), nullable=False), sa.Column("unit", sa.Text(), nullable=False, server_default="g"), sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"), sa.CheckConstraint("(food_id IS NULL) <> (nested_recipe_id IS NULL)", name="ck_recipe_ingredients_one_source")], [("uq_recipe_ingredients_order", ("recipe_id", "sort_order"))])
    owned("meal_plans", [sa.Column("name", sa.Text(), nullable=False), sa.Column("version", sa.Integer(), nullable=False, server_default="1"), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false())])
    owned("meal_plan_items", [sa.Column("meal_plan_id", UUID, sa.ForeignKey("meal_plans.id", ondelete="CASCADE"), nullable=False), sa.Column("category_id", UUID, sa.ForeignKey("meal_categories.id"), nullable=False), sa.Column("recipe_id", UUID, sa.ForeignKey("recipes.id")), sa.Column("name", sa.Text()), sa.Column("planned_time", sa.Time()), sa.Column("weekdays", JSON), sa.Column("portion", sa.Numeric(10, 3), nullable=False, server_default="1"), sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0")])
    owned("meal_entries", [sa.Column("date", sa.Date(), nullable=False), sa.Column("category_id", UUID, sa.ForeignKey("meal_categories.id"), nullable=False), sa.Column("name", sa.Text(), nullable=False), sa.Column("status", sa.Text(), nullable=False, server_default="planned"), sa.Column("consumed_at", sa.DateTime(timezone=True)), sa.Column("source", sa.Text(), nullable=False, server_default="manual"), sa.Column("meal_plan_id", UUID, sa.ForeignKey("meal_plans.id")), sa.Column("meal_plan_item_id", UUID, sa.ForeignKey("meal_plan_items.id")), sa.Column("nutrition_snapshot", JSON, nullable=False, server_default=sa.text("'{}'::jsonb")), sa.CheckConstraint("status IN ('planned', 'consumed', 'skipped')", name="ck_meal_entries_status")], [("uq_meal_entries_plan_instance", ("account_id", "date", "meal_plan_id", "meal_plan_item_id"))])
    op.create_index("ix_meal_entries_account_date", "meal_entries", ["account_id", "date"])
    owned("meal_entry_items", [sa.Column("meal_entry_id", UUID, sa.ForeignKey("meal_entries.id", ondelete="CASCADE"), nullable=False), sa.Column("food_id", UUID, sa.ForeignKey("foods.id")), sa.Column("recipe_id", UUID, sa.ForeignKey("recipes.id")), sa.Column("quantity", sa.Numeric(12, 3), nullable=False), sa.Column("unit", sa.Text(), nullable=False, server_default="g"), sa.Column("nutrition_snapshot", JSON, nullable=False, server_default=sa.text("'{}'::jsonb")), sa.Column("source_snapshot", JSON, nullable=False, server_default=sa.text("'{}'::jsonb")), sa.CheckConstraint("(food_id IS NULL) <> (recipe_id IS NULL)", name="ck_meal_entry_items_one_source")])

    # Preserve today's tracker data as snapshots.  This migration never trusts
    # legacy UUID links (Meal.dish_id had no FK); it copies nutrition as the
    # historical fact and leaves an auditable legacy source marker instead.
    op.execute("""
        INSERT INTO meal_categories (id, account_id, name, sort_order, is_active)
        SELECT gen_random_uuid(), account_id,
               CASE meal_slot WHEN 1 THEN 'Frühstück' WHEN 2 THEN 'Mittag'
                              WHEN 3 THEN 'Snack' WHEN 4 THEN 'Abendessen'
                              ELSE 'Ohne Kategorie' END,
               COALESCE(meal_slot, 99), true
        FROM meals
        GROUP BY account_id, meal_slot
        ON CONFLICT (account_id, name) DO NOTHING
    """)
    op.execute("""
        INSERT INTO meal_categories (id, account_id, name, sort_order, is_active)
        SELECT gen_random_uuid(), account_id,
               CASE slot WHEN 1 THEN 'Frühstück' WHEN 2 THEN 'Mittag'
                         WHEN 3 THEN 'Snack' WHEN 4 THEN 'Abendessen'
                         ELSE 'Ohne Kategorie' END,
               COALESCE(slot, 99), true
        FROM dishes
        GROUP BY account_id, slot
        ON CONFLICT (account_id, name) DO NOTHING
    """)
    op.execute("""
        INSERT INTO foods
          (id, account_id, name, source, confidence, kcal_per_100g, protein_g_per_100g,
           carbs_g_per_100g, fat_g_per_100g, fiber_g_per_100g, sugar_g_per_100g, free_sugar_g_per_100g)
        SELECT gen_random_uuid(), account_id, 'Legacy: ' || name, 'import', 'estimated',
               kcal, protein_g, carbs_g, fat_g, fiber_g, sugar_g, free_sugar_g
        FROM dishes
        ON CONFLICT (account_id, name) DO NOTHING
    """)
    op.execute("""
        INSERT INTO recipes (id, account_id, name, status, servings, notes)
        SELECT gen_random_uuid(), account_id, name, 'active', 1,
               'Aus Legacy-Gericht migriert; Nährwert-Snapshot siehe historische Mahlzeiten.'
        FROM dishes
        ON CONFLICT (account_id, name) DO NOTHING
    """)
    op.execute("""
        INSERT INTO recipe_ingredients
          (id, account_id, recipe_id, food_id, quantity, unit, sort_order)
        SELECT gen_random_uuid(), r.account_id, r.id, f.id, 100, 'g', 0
        FROM dishes d
        JOIN recipes r ON r.account_id = d.account_id AND r.name = d.name
        JOIN foods f ON f.account_id = d.account_id AND f.name = 'Legacy: ' || d.name
        ON CONFLICT (recipe_id, sort_order) DO NOTHING
    """)
    op.execute("""
        INSERT INTO meal_entries
          (id, account_id, date, category_id, name, status, consumed_at, source, nutrition_snapshot, created_at, updated_at)
        SELECT gen_random_uuid(), m.account_id, m.date, c.id, m.name,
               CASE WHEN m.is_done THEN 'consumed' ELSE 'planned' END,
               NULL, 'legacy',
               jsonb_build_object(
                 'kcal', m.kcal, 'protein_g', m.protein_g, 'carbs_g', m.carbs_g,
                 'fat_g', m.fat_g, 'fiber_g', m.fiber_g, 'sugar_g', m.sugar_g,
                 'free_sugar_g', m.free_sugar_g),
               COALESCE(m.updated_at, now()), COALESCE(m.updated_at, now())
        FROM meals m
        JOIN meal_categories c ON c.account_id = m.account_id AND c.name =
          CASE m.meal_slot WHEN 1 THEN 'Frühstück' WHEN 2 THEN 'Mittag'
                           WHEN 3 THEN 'Snack' WHEN 4 THEN 'Abendessen'
                           ELSE 'Ohne Kategorie' END
        WHERE m.deleted = false
    """)


def downgrade() -> None:
    for table in ("meal_entry_items", "meal_entries", "meal_plan_items", "meal_plans", "recipe_ingredients", "recipes", "foods", "meal_categories"):
        op.drop_table(table)
