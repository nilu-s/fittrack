"""Explicit, auditable enrichment of historical meal nutrient snapshots."""
from __future__ import annotations

from decimal import Decimal
import uuid

from sqlalchemy import select

from app.models import Food, MealEntry, MealEntryItem, Recipe, RecipeIngredient


MICRONUTRIENTS = (
    "saturated_fat_g", "sodium_mg", "potassium_mg", "calcium_mg", "magnesium_mg",
    "iron_mg", "zinc_mg", "vitamin_a_ug", "vitamin_c_mg", "vitamin_d_ug",
    "vitamin_b12_ug", "folate_ug",
)


async def _food_nutrients(food: Food, quantity: Decimal) -> dict[str, Decimal | None]:
    return {
        key: getattr(food, f"{key}_per_100g") * quantity / Decimal("100")
        if getattr(food, f"{key}_per_100g") is not None else None
        for key in MICRONUTRIENTS
    }


def _sum(parts: list[dict[str, Decimal | None]]) -> dict[str, Decimal | None]:
    return {key: None if any(part.get(key) is None for part in parts) else sum((part[key] for part in parts), Decimal("0")) for key in MICRONUTRIENTS}


async def _recipe_nutrients(session, recipe: Recipe, account_id: uuid.UUID, multiplier=Decimal("1"), visited=None) -> dict[str, Decimal | None]:
    visited = set() if visited is None else visited
    if recipe.id in visited:
        return {key: None for key in MICRONUTRIENTS}
    ingredients = (await session.execute(select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id, RecipeIngredient.account_id == account_id))).scalars().all()
    values: list[dict[str, Decimal | None]] = []
    for ingredient in ingredients:
        if ingredient.food_id:
            food = await session.scalar(select(Food).where(Food.id == ingredient.food_id, Food.account_id == account_id))
            if food:
                values.append(await _food_nutrients(food, ingredient.quantity))
        elif ingredient.nested_recipe_id:
            nested = await session.scalar(select(Recipe).where(Recipe.id == ingredient.nested_recipe_id, Recipe.account_id == account_id))
            if nested:
                # ``quantity`` is the number of nested-recipe servings.  This
                # helper performs the batch-to-serving conversion itself.
                values.append(await _recipe_nutrients(session, nested, account_id, ingredient.quantity, visited | {recipe.id}))
    total = _sum(values) if values else {key: None for key in MICRONUTRIENTS}
    return {key: value * multiplier / recipe.servings if value is not None else None for key, value in total.items()}


async def enrich_historical_meal_nutrients(session, account_id: uuid.UUID) -> int:
    """Fill only missing micronutrients from current, account-owned food facts.

    The caller opts in deliberately. Original macro values are never changed;
    absent source values remain null instead of being inferred.
    """
    entries = (await session.execute(select(MealEntry).where(MealEntry.account_id == account_id))).scalars().all()
    changed = 0
    for entry in entries:
        items = (await session.execute(select(MealEntryItem).where(MealEntryItem.meal_entry_id == entry.id, MealEntryItem.account_id == account_id))).scalars().all()
        if not items:
            continue
        for item in items:
            values: dict[str, Decimal | None] | None = None
            if item.food_id:
                food = await session.scalar(select(Food).where(Food.id == item.food_id, Food.account_id == account_id))
                if food:
                    values = await _food_nutrients(food, item.quantity)
            elif item.recipe_id:
                recipe = await session.scalar(select(Recipe).where(Recipe.id == item.recipe_id, Recipe.account_id == account_id))
                if recipe:
                    values = await _recipe_nutrients(session, recipe, account_id, item.quantity)
            if values is None:
                continue
            snapshot = dict(item.nutrition_snapshot or {})
            for key, value in values.items():
                snapshot[key] = str(value) if value is not None else None
            item.nutrition_snapshot = snapshot
            changed += 1
        entry_snapshot = dict(entry.nutrition_snapshot or {})
        totals = _sum([{key: Decimal(str((item.nutrition_snapshot or {}).get(key))) if (item.nutrition_snapshot or {}).get(key) is not None else None for key in MICRONUTRIENTS} for item in items])
        for key, value in totals.items():
            entry_snapshot[key] = str(value) if value is not None else None
        entry.nutrition_snapshot = entry_snapshot
    return changed
