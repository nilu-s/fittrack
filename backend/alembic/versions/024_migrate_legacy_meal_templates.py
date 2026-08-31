"""Preserve legacy daily meal templates as an inactive configurable plan.

Revision ID: 024
Revises: 023

The plan is deliberately inactive: enabling it is an explicit account choice
and must not silently create a second representation of historic daily meals.
"""
from alembic import op


revision = "024"
down_revision = "023"


def upgrade() -> None:
    op.execute("""
        INSERT INTO meal_categories (id, account_id, name, sort_order, is_active)
        SELECT gen_random_uuid(), account_id,
               CASE slot WHEN 1 THEN 'Frühstück' WHEN 2 THEN 'Mittag'
                         WHEN 3 THEN 'Snack' WHEN 4 THEN 'Abendessen'
                         ELSE 'Ohne Kategorie' END,
               COALESCE(slot, 99), true
        FROM meal_templates
        GROUP BY account_id, slot
        ON CONFLICT (account_id, name) DO NOTHING
    """)
    # One plan per account with old templates.  The generated name avoids the
    # duplicate-prone user-editable template names and is safely repeatable.
    op.execute("""
        INSERT INTO meal_plans (id, account_id, name, version, is_active)
        SELECT gen_random_uuid(), account_id, 'Migrierter Standardplan', 1, false
        FROM meal_templates
        GROUP BY account_id
        ON CONFLICT DO NOTHING
    """)
    # A legacy template carries nutrient values rather than a reusable food or
    # recipe.  Create an auditable imported recipe + food per slot and attach
    # it to the new plan, preserving its original serving snapshot.
    op.execute("""
        INSERT INTO foods
          (id, account_id, name, source, confidence, kcal_per_100g,
           protein_g_per_100g, carbs_g_per_100g, fat_g_per_100g,
           fiber_g_per_100g, sugar_g_per_100g, free_sugar_g_per_100g)
        SELECT gen_random_uuid(), t.account_id, 'Legacy template: ' || t.name,
               'import', 'estimated', t.kcal, t.protein_g, t.carbs_g, t.fat_g,
               t.fiber_g, t.sugar_g, t.free_sugar_g
        FROM meal_templates t
        ON CONFLICT (account_id, name) DO NOTHING
    """)
    op.execute("""
        INSERT INTO recipes (id, account_id, name, status, servings, notes)
        SELECT gen_random_uuid(), t.account_id, 'Legacy template: ' || t.name,
               'active', 1, 'Aus Legacy-Mahlzeitvorlage migriert.'
        FROM meal_templates t
        ON CONFLICT (account_id, name) DO NOTHING
    """)
    op.execute("""
        INSERT INTO recipe_ingredients
          (id, account_id, recipe_id, food_id, quantity, unit, sort_order)
        SELECT gen_random_uuid(), t.account_id, r.id, f.id, 100, 'g', 0
        FROM meal_templates t
        JOIN recipes r ON r.account_id = t.account_id
          AND r.name = 'Legacy template: ' || t.name
        JOIN foods f ON f.account_id = t.account_id
          AND f.name = 'Legacy template: ' || t.name
        ON CONFLICT (recipe_id, sort_order) DO NOTHING
    """)
    op.execute("""
        INSERT INTO meal_plan_items
          (id, account_id, meal_plan_id, category_id, recipe_id, name, portion, sort_order)
        SELECT gen_random_uuid(), t.account_id, p.id, c.id, r.id, t.name, 1, t.slot
        FROM meal_templates t
        JOIN meal_plans p ON p.account_id = t.account_id
          AND p.name = 'Migrierter Standardplan'
        JOIN meal_categories c ON c.account_id = t.account_id AND c.name =
          CASE t.slot WHEN 1 THEN 'Frühstück' WHEN 2 THEN 'Mittag'
                      WHEN 3 THEN 'Snack' WHEN 4 THEN 'Abendessen'
                      ELSE 'Ohne Kategorie' END
        JOIN recipes r ON r.account_id = t.account_id
          AND r.name = 'Legacy template: ' || t.name
    """)


def downgrade() -> None:
    # Imported foods/recipes can be referenced by user-created data after an
    # upgrade.  A downgrade therefore removes only the generated plan, whose
    # cascading items are the sole migration-owned projection.
    op.execute("DELETE FROM meal_plans WHERE name = 'Migrierter Standardplan'")
