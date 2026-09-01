"""Populate standard recipes with ingredients and cooking instructions.

Revision ID: 033
Revises: 032
"""
from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa


revision = "033"
down_revision = "032"


# Values are typical label values per 100 g (or ml where explicitly named).
# Every nutrient is present, including known zero values.
FOODS = {
    "Haferflocken": (372, 13.5, 58.7, 7.0, 10.0, 1.0, 0),
    "Whey-Proteinpulver": (380, 75, 8, 6, 1, 5, 2),
    "Skyr natur": (63, 11, 4, 0.2, 0, 4, 0),
    "Magerquark": (67, 12, 4, 0.2, 0, 4, 0),
    "Banane": (89, 1.1, 20, 0.3, 2.6, 12, 0),
    "Apfel": (52, 0.3, 11.4, 0.2, 2.4, 10.4, 0),
    "Beeren-Mix": (45, 0.8, 6.5, 0.4, 4.5, 5.5, 0),
    "Hähnchenbrust": (110, 23, 0, 1.5, 0, 0, 0),
    "Putenhack": (135, 22, 0, 5, 0, 0, 0),
    "Lachsfilet": (208, 20, 0, 13, 0, 0, 0),
    "Naturtofu": (145, 15, 1.5, 8.5, 1, 0.6, 0),
    "Reis, trocken": (356, 7, 79, 0.8, 1.3, 0.2, 0),
    "Vollkornnudeln, trocken": (348, 13, 65, 2.5, 8, 3, 0),
    "Kartoffeln": (77, 2, 15, 0.1, 2.2, 0.8, 0),
    "Brokkoli": (34, 2.8, 2.7, 0.4, 3, 1.7, 0),
    "Passierte Tomaten": (30, 1.5, 4.8, 0.2, 1.5, 3.8, 0),
    "Kidneybohnen": (95, 6.8, 12, 0.5, 6.4, 0.7, 0),
    "Mais": (86, 3.4, 14, 1.2, 2.4, 5, 0),
    "Olivenöl": (884, 0, 0, 100, 0, 0, 0),
    "Erdnussmus": (590, 25, 12, 49, 8, 5, 3),
    "Mandeln": (579, 21, 6, 50, 12, 4, 0),
    "Parmesan": (431, 38, 4, 29, 0, 0, 0),
    "Käse, gerieben": (356, 25, 2, 27, 0, 0, 0),
    "Teriyaki-Sauce": (110, 3, 22, 0.2, 0.5, 18, 16),
    "Salsa": (35, 1.5, 5, 0.3, 1.5, 3.5, 0),
    "Flohsamenschalen": (190, 2, 2, 1, 85, 0, 0),
    "Zitronensaft": (22, 0.4, 6.9, 0.2, 0.3, 2.5, 0),
    "Zimt": (247, 4, 28, 1.2, 53, 2.2, 0),
}

RECIPES = {
    "Banana-Whey-Cream": ([('Skyr natur', 250), ('Banane', 120), ('Whey-Proteinpulver', 30), ('Haferflocken', 30), ('Erdnussmus', 15)], ['Skyr und Proteinpulver glatt rühren.', 'Banane in Scheiben schneiden und unterheben.', 'Mit Haferflocken und Erdnussmus servieren.']),
    "Cheesecake-Bowl": ([('Magerquark', 300), ('Skyr natur', 150), ('Haferflocken', 50), ('Beeren-Mix', 150), ('Whey-Proteinpulver', 20)], ['Quark, Skyr und Proteinpulver cremig verrühren.', 'Haferflocken kurz trocken anrösten.', 'Mit Beeren und Haferflocken anrichten.']),
    "Chicken-Rice-Bowl": ([('Hähnchenbrust', 220), ('Reis, trocken', 100), ('Brokkoli', 200), ('Olivenöl', 10)], ['Reis nach Packungsangabe garen.', 'Hähnchen würzen und im Öl vollständig durchbraten.', 'Brokkoli dämpfen und alles in einer Bowl anrichten.']),
    "More Fizz Ballaststoff-Limo Mojito": ([('Flohsamenschalen', 10), ('Zitronensaft', 30)], ['Flohsamenschalen mit kaltem Wasser verrühren.', 'Zitronensaft und nach Wunsch Minze zugeben.', 'Sofort trinken und anschließend ein Glas Wasser nachtrinken.']),
    "Pasta Pomodore": ([('Vollkornnudeln, trocken', 120), ('Hähnchenbrust', 150), ('Passierte Tomaten', 300), ('Olivenöl', 10), ('Parmesan', 15)], ['Nudeln al dente kochen.', 'Hähnchen im Öl durchbraten.', 'Tomaten zugeben, kurz köcheln lassen und mit Nudeln sowie Parmesan servieren.']),
    "Protein-Porridge Apfel-Zimt": ([('Haferflocken', 80), ('Whey-Proteinpulver', 30), ('Apfel', 150), ('Skyr natur', 200), ('Zimt', 3)], ['Haferflocken mit Wasser zu Porridge kochen.', 'Vom Herd nehmen und Proteinpulver einrühren.', 'Mit Skyr, Apfelwürfeln und Zimt servieren.']),
    "Protein-Pudding Banane": ([('Skyr natur', 250), ('Whey-Proteinpulver', 25), ('Banane', 120), ('Käse, gerieben', 0)], ['Skyr und Proteinpulver glatt rühren.', 'Banane zerdrücken und unterheben.', 'Für eine festere Konsistenz zehn Minuten kalt stellen.']),
    "Salmon-Potato-Bowl": ([('Lachsfilet', 200), ('Kartoffeln', 350), ('Brokkoli', 200), ('Olivenöl', 10)], ['Kartoffeln garen und halbieren.', 'Lachs würzen und in einer Pfanne gar braten.', 'Brokkoli dämpfen und mit Kartoffeln sowie Öl anrichten.']),
    "Skyr-Beeren-Crunch": ([('Skyr natur', 300), ('Beeren-Mix', 150), ('Haferflocken', 60), ('Mandeln', 25), ('Whey-Proteinpulver', 20)], ['Skyr und Proteinpulver verrühren.', 'Haferflocken und Mandeln kurz anrösten.', 'Mit Beeren und Crunch servieren.']),
    "Skyr-Beeren-Crunch Snack": ([('Skyr natur', 200), ('Beeren-Mix', 100), ('Haferflocken', 30), ('Mandeln', 15)], ['Skyr in eine Schale geben.', 'Beeren darauf verteilen.', 'Haferflocken und Mandeln als Crunch darübergeben.']),
    "Smoky Loaded Potatoes": ([('Kartoffeln', 350), ('Putenhack', 180), ('Kidneybohnen', 150), ('Mais', 100), ('Käse, gerieben', 35), ('Salsa', 100)], ['Kartoffeln garen oder im Ofen backen.', 'Putenhack krümelig und vollständig durchbraten.', 'Bohnen und Mais erhitzen, alles auf den Kartoffeln verteilen und mit Käse sowie Salsa servieren.']),
    "Teriyaki-Tofu-Bowl": ([('Naturtofu', 250), ('Reis, trocken', 100), ('Brokkoli', 200), ('Teriyaki-Sauce', 40), ('Olivenöl', 10)], ['Reis garen.', 'Tofu würfeln und im Öl knusprig braten.', 'Brokkoli dämpfen, Teriyaki-Sauce zugeben und mit Reis servieren.']),
    "Turkey-Chili-Bowl": ([('Putenhack', 200), ('Kidneybohnen', 150), ('Reis, trocken', 80), ('Passierte Tomaten', 300), ('Olivenöl', 10)], ['Reis garen.', 'Putenhack im Öl vollständig durchbraten.', 'Bohnen und Tomaten zugeben, zehn Minuten köcheln und mit Reis servieren.']),
}


def upgrade() -> None:
    bind = op.get_bind()
    accounts = bind.execute(sa.text("SELECT DISTINCT account_id FROM recipes")).scalars().all()
    for account_id in accounts:
        food_ids = {}
        for name, nutrients in FOODS.items():
            bind.execute(sa.text("""
                INSERT INTO foods (id, account_id, name, tags, source, confidence, kcal_per_100g, protein_g_per_100g, carbs_g_per_100g, fat_g_per_100g, fiber_g_per_100g, sugar_g_per_100g, free_sugar_g_per_100g, is_archived)
                VALUES (gen_random_uuid(), :account_id, :name, CAST(:tags AS jsonb), 'manual', 'verified', :kcal, :protein, :carbs, :fat, :fiber, :sugar, :free_sugar, false)
                ON CONFLICT (account_id, name) DO NOTHING
            """), dict(account_id=account_id, name=name, tags=json.dumps(['standard-rezept']), kcal=nutrients[0], protein=nutrients[1], carbs=nutrients[2], fat=nutrients[3], fiber=nutrients[4], sugar=nutrients[5], free_sugar=nutrients[6]))
            food_ids[name] = bind.execute(sa.text("SELECT id FROM foods WHERE account_id=:account_id AND name=:name"), dict(account_id=account_id, name=name)).scalar_one()
        for recipe_name, (ingredients, instructions) in RECIPES.items():
            recipe_id = bind.execute(sa.text("SELECT id FROM recipes WHERE account_id=:account_id AND name=:name"), dict(account_id=account_id, name=recipe_name)).scalar_one_or_none()
            if recipe_id is None:
                continue
            bind.execute(sa.text("""
                UPDATE recipes SET status='active', servings=1, notes='Standardrezept mit berechneten Nährwerten.', instructions=CAST(:instructions AS jsonb), nutrition_per_serving='{}'::jsonb
                WHERE id=:recipe_id
            """), dict(recipe_id=recipe_id, instructions=json.dumps(instructions)))
            bind.execute(sa.text("DELETE FROM recipe_ingredients WHERE recipe_id=:recipe_id"), dict(recipe_id=recipe_id))
            for order, (food_name, quantity) in enumerate(ingredients):
                if quantity:
                    bind.execute(sa.text("""
                        INSERT INTO recipe_ingredients (id, account_id, recipe_id, food_id, quantity, unit, sort_order)
                        VALUES (gen_random_uuid(), :account_id, :recipe_id, :food_id, :quantity, 'g', :sort_order)
                    """), dict(account_id=account_id, recipe_id=recipe_id, food_id=food_ids[food_name], quantity=quantity, sort_order=order))


def downgrade() -> None:
    # Ingredient provenance is intentionally retained; no safe inverse exists.
    pass
