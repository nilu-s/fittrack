"""Deterministic, account-scoped ingredients required by an active meal plan."""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Food, MealPlan, MealPlanItem, Recipe, RecipeIngredient


_CATEGORY_RULES = {
    "produce": ("apfel", "banan", "beere", "brokk", "gemüse", "gurke", "karott", "kartoff", "paprika", "salat", "tomat", "zwiebel", "zitrone"),
    "dairy": ("butter", "joghurt", "käse", "milch", "quark", "sahne", "skyr"),
    "bakery": ("brot", "bröt", "mehl", "toast"),
    "frozen": ("tiefkühl", "tk-"),
    "beverage": ("kaffee", "saft", "tee", "wasser"),
    "household": ("müll", "papier", "reiniger", "spül", "wasch"),
    "pantry": ("hafer", "nudel", "reis", "öl", "salz", "zucker", "gewürz", "bohne", "lins", "passat"),
}


def classify_article(title: str) -> tuple[str, str]:
    value = title.casefold()
    for category, words in _CATEGORY_RULES.items():
        if any(word in value for word in words):
            return category, category
    return "other", "shopping"


async def _owned(session: AsyncSession, model, resource_id: uuid.UUID, account_id: uuid.UUID):
    row = await session.scalar(select(model).where(model.id == resource_id, model.account_id == account_id))
    if row is None:
        raise HTTPException(404, "Resource not found")
    return row


async def _flatten_recipe(
    session: AsyncSession, recipe: Recipe, requested_servings: Decimal,
    account_id: uuid.UUID, visited: set[uuid.UUID] | None = None,
) -> list[tuple[Food | None, str, Decimal | None, str | None, bool]]:
    """Return direct foods for requested recipe servings; never invent units."""
    visited = set() if visited is None else visited
    if recipe.id in visited:
        raise HTTPException(422, "Recipe nesting may not contain cycles")
    ingredients = (await session.execute(select(RecipeIngredient).where(
        RecipeIngredient.recipe_id == recipe.id,
        RecipeIngredient.account_id == account_id,
    ).order_by(RecipeIngredient.sort_order))).scalars().all()
    if not ingredients:
        return [(None, recipe.name, None, None, True)]
    multiplier = requested_servings / recipe.servings
    result: list[tuple[Food | None, str, Decimal | None, str | None, bool]] = []
    for ingredient in ingredients:
        if ingredient.food_id is not None:
            food = await _owned(session, Food, ingredient.food_id, account_id)
            # Foods currently have meaningful shopping quantities only in grams.
            if ingredient.unit != "g":
                result.append((None, food.name, None, ingredient.unit, True))
            else:
                result.append((food, food.name, ingredient.quantity * multiplier, "g", False))
        else:
            nested = await _owned(session, Recipe, ingredient.nested_recipe_id, account_id)
            result.extend(await _flatten_recipe(session, nested, ingredient.quantity * multiplier, account_id, visited | {recipe.id}))
    return result


async def planned_meal_requirements(
    session: AsyncSession, account_id: uuid.UUID, from_date: date, to_date: date,
) -> tuple[MealPlan | None, list[dict]]:
    plan = await session.scalar(select(MealPlan).where(MealPlan.account_id == account_id, MealPlan.is_active.is_(True)))
    if plan is None:
        return None, []
    items = (await session.execute(select(MealPlanItem).where(
        MealPlanItem.account_id == account_id, MealPlanItem.meal_plan_id == plan.id, MealPlanItem.is_active.is_(True)
    ))).scalars().all()
    aggregate: dict[tuple[uuid.UUID | None, str, str | None, bool], dict] = {}
    day = from_date
    while day <= to_date:
        for item in items:
            if item.weekdays is not None and day.weekday() not in item.weekdays:
                continue
            if item.recipe_id is None:
                continue
            recipe = await _owned(session, Recipe, item.recipe_id, account_id)
            for food, title, quantity, unit, needs_review in await _flatten_recipe(session, recipe, item.portion, account_id):
                key = (food.id if food else None, title.casefold(), unit, needs_review)
                category, icon = classify_article(title)
                row = aggregate.setdefault(key, {"food_id": food.id if food else None, "title": title, "quantity": Decimal("0") if quantity is not None else None, "unit": unit, "needs_review": needs_review, "category_key": category, "icon_key": icon})
                if quantity is not None:
                    row["quantity"] += quantity
        day = date.fromordinal(day.toordinal() + 1)
    return plan, sorted(aggregate.values(), key=lambda item: (item["category_key"], item["title"].casefold()))
