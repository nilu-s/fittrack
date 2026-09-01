"""Normalize imported dishes into recipes and repair the active weekly plan.

Revision ID: 030
Revises: 029
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "030"
down_revision = "029"


def upgrade() -> None:
    op.add_column("recipes", sa.Column("nutrition_per_serving", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    # Historic one-ingredient imports use a 100 g pseudo-food.  Preserve the
    # complete per-serving values on the recipe before deleting that pseudo-food.
    op.execute("""
        UPDATE recipes r SET nutrition_per_serving = jsonb_build_object(
          'kcal', f.kcal_per_100g::text, 'protein_g', f.protein_g_per_100g::text,
          'carbs_g', f.carbs_g_per_100g::text, 'fat_g', f.fat_g_per_100g::text,
          'fiber_g', f.fiber_g_per_100g::text, 'sugar_g', f.sugar_g_per_100g::text,
          'free_sugar_g', f.free_sugar_g_per_100g::text)
        FROM recipe_ingredients ri JOIN foods f ON f.id = ri.food_id
        WHERE ri.recipe_id = r.id AND r.nutrition_per_serving = '{}'::jsonb
          AND f.account_id = r.account_id AND ri.quantity = 100 AND ri.unit = 'g'
          AND f.source = 'import' AND f.name LIKE 'Legacy%'
    """)
    # Consolidate the duplicate template recipes before removing their inputs.
    op.execute("""
        UPDATE meal_plan_items mpi SET recipe_id = canonical.id, name = canonical.name
        FROM recipes duplicate JOIN recipes canonical ON canonical.account_id = duplicate.account_id
          AND canonical.name = replace(duplicate.name, 'Legacy template: ', '')
        WHERE mpi.recipe_id = duplicate.id AND duplicate.name LIKE 'Legacy template: %'
    """)
    op.execute("""
        UPDATE meal_entry_items mei SET recipe_id = canonical.id,
          source_snapshot = jsonb_set(COALESCE(mei.source_snapshot, '{}'::jsonb), '{name}', to_jsonb(canonical.name), true)
        FROM recipes duplicate JOIN recipes canonical ON canonical.account_id = duplicate.account_id
          AND canonical.name = replace(duplicate.name, 'Legacy template: ', '')
        WHERE mei.recipe_id = duplicate.id AND duplicate.name LIKE 'Legacy template: %'
    """)
    op.execute("DELETE FROM recipe_ingredients ri USING recipes r WHERE ri.recipe_id = r.id AND r.name LIKE 'Legacy template: %'")
    op.execute("DELETE FROM recipes WHERE name LIKE 'Legacy template: %'")
    # The other imported food rows are aggregate dishes, never individual foods.
    op.execute("DELETE FROM recipe_ingredients ri USING foods f WHERE ri.food_id = f.id AND f.source = 'import' AND f.name LIKE 'Legacy%'")
    op.execute("DELETE FROM foods WHERE source = 'import' AND name LIKE 'Legacy%'")
    op.execute("""
        DELETE FROM meal_categories c WHERE c.name = 'Ohne Kategorie'
          AND NOT EXISTS (SELECT 1 FROM meal_entries e WHERE e.category_id = c.id)
          AND NOT EXISTS (SELECT 1 FROM meal_plan_items i WHERE i.category_id = c.id)
    """)
    # Replace imported duplicate slots with one all-week standard entry per category.
    # Historical entries retain their former template item as an inactive
    # audit reference; only active items participate in instantiation.
    op.execute("UPDATE meal_plan_items SET is_active = false WHERE meal_plan_id IN (SELECT id FROM meal_plans WHERE is_active)")
    op.execute("""
        INSERT INTO meal_plan_items (id, account_id, meal_plan_id, category_id, recipe_id, name, portion, sort_order, is_active)
        SELECT gen_random_uuid(), p.account_id, p.id, c.id, r.id, r.name, 1, c.sort_order, true
        FROM meal_plans p JOIN meal_categories c ON c.account_id = p.account_id AND c.is_active
        JOIN recipes r ON r.account_id = p.account_id AND r.name = CASE c.name
          WHEN 'Frühstück' THEN 'Protein-Porridge Apfel-Zimt' WHEN 'Mittag' THEN 'Chicken-Rice-Bowl'
          WHEN 'Snack' THEN 'Protein-Pudding Banane' WHEN 'Abendessen' THEN 'Salmon-Potato-Bowl' END
        WHERE p.is_active
    """)
    op.execute("UPDATE meal_plans SET name = 'Standard-Wochenplan', version = version + 1 WHERE is_active AND name = 'Migrierter Standardplan'")
    # Two active quick choices for every retained standard category.
    op.execute("DELETE FROM meal_category_recipe_presets")
    op.execute("""
        INSERT INTO meal_category_recipe_presets (id, account_id, category_id, recipe_id, rank)
        SELECT gen_random_uuid(), c.account_id, c.id, r.id, choices.rank
        FROM meal_categories c CROSS JOIN LATERAL (VALUES
          (1, CASE c.name WHEN 'Frühstück' THEN 'Protein-Porridge Apfel-Zimt' WHEN 'Mittag' THEN 'Chicken-Rice-Bowl' WHEN 'Snack' THEN 'Protein-Pudding Banane' WHEN 'Abendessen' THEN 'Salmon-Potato-Bowl' END),
          (2, CASE c.name WHEN 'Frühstück' THEN 'Banana-Whey-Cream' WHEN 'Mittag' THEN 'Pasta Pomodore' WHEN 'Snack' THEN 'Skyr-Beeren-Crunch Snack' WHEN 'Abendessen' THEN 'Turkey-Chili-Bowl' END)
        ) AS choices(rank, recipe_name) JOIN recipes r ON r.account_id = c.account_id AND r.name = choices.recipe_name
        WHERE c.is_active AND choices.recipe_name IS NOT NULL
    """)


def downgrade() -> None:
    # The deletion of misleading duplicate input rows is intentionally irreversible.
    op.drop_column("recipes", "nutrition_per_serving")
