"""Account-scoped configurable meals API.

All cross-resource references are resolved with account_id in the query.  A
missing or foreign resource is deliberately indistinguishable (404).
"""
from __future__ import annotations

import base64
import logging
import os
import uuid
from datetime import date as date_type, datetime, timezone
from decimal import Decimal

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import async_session
from app.models import Food, MealCategory, MealEntry, MealEntryItem, MealPhotoAnalysis, MealPlan, MealPlanItem, MealPlanVersion, Photo, Recipe, RecipeIngredient
from app.routes.auth import get_current_user
from app.schemas import (
    FoodCreate, FoodResponse, FoodUpdate, MealCategoryCreate, MealCategoryResponse, MealCategoryReorder, MealCategoryUpdate,
    MealEntryCreate, MealEntryItemInput, MealEntryItemResponse, MealEntryResponse, MealEntryUpdate,
    MealPlanCreate, MealPlanItemInput, MealPlanItemResponse, MealPlanResponse, MealPlanUpdate,
    Nutrition, RecipeCreate, RecipeIngredientInput, RecipeIngredientResponse, RecipeResponse, RecipeUpdate, MealPhotoAnalysisAccept, MealPhotoAnalysisResponse, MealEntryStatusCommand, MealPlanVersionResponse,
)

router = APIRouter(tags=["configurable-meals"])
_NUTRIENTS = ("kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g", "free_sugar_g")
logger = logging.getLogger(__name__)

_MAX_PHOTO_BYTES = 10 * 1024 * 1024
_IMAGE_SIGNATURES = (
    ("image/jpeg", ".jpg", lambda data: data.startswith(b"\xff\xd8\xff")),
    ("image/png", ".png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
    ("image/webp", ".webp", lambda data: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"),
)


def _not_found(detail="Resource not found"):
    raise HTTPException(status_code=404, detail=detail)


def _image_metadata(contents: bytes, declared_mime: str | None) -> tuple[str, str]:
    """Return an allow-listed MIME type and extension based on file bytes.

    The upload header is only a consistency check; it never determines the
    stored format.  This keeps executable content with an image extension out
    of the photo directory without adding a platform-specific libmagic
    dependency.
    """
    if not contents:
        raise HTTPException(400, "Empty photo")
    if len(contents) > _MAX_PHOTO_BYTES:
        raise HTTPException(413, "Photo must not exceed 10 MiB")
    for mime_type, extension, matches in _IMAGE_SIGNATURES:
        if matches(contents):
            if declared_mime and declared_mime.lower() != mime_type:
                raise HTTPException(422, "Photo MIME type does not match its content")
            return mime_type, extension
    raise HTTPException(422, "Only JPEG, PNG, and WebP photos are supported")


async def _vision_proposal(contents: bytes) -> tuple[str, dict | None, str | None]:
    """Ask the vision service for a proposal, never for a MealEntry mutation."""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{settings.VISION_PROXY_URL}/analyze",
                json={"image_base64": base64.b64encode(contents).decode("ascii")},
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        logger.warning("Meal photo vision request failed: %s", type(exc).__name__)
        return "failed", None, "vision_unavailable"
    except (TypeError, ValueError) as exc:
        logger.warning("Meal photo vision response was invalid: %s", type(exc).__name__)
        return "failed", None, "vision_response_invalid"
    except Exception as exc:  # Do not expose provider details or uploaded data.
        logger.exception("Meal photo vision processing failed: %s", type(exc).__name__)
        return "failed", None, "vision_failed"

    if not isinstance(payload, dict):
        return "failed", None, "vision_response_invalid"
    if payload.get("not_food"):
        return "failed", None, "not_food"
    analysis = payload.get("analysis")
    if not isinstance(analysis, dict):
        return "failed", None, "vision_response_invalid"
    return "pending", analysis, None


def _snapshot(values: dict[str, Decimal | None]) -> dict[str, str | None]:
    return {key: str(value) if value is not None else None for key, value in values.items()}


def _nutrition_from_snapshot(snapshot: dict) -> Nutrition:
    return Nutrition(**{key: snapshot.get(key) for key in _NUTRIENTS})


def _sum(parts: list[dict[str, Decimal | None]]) -> dict[str, Decimal | None]:
    # Unknown is contagious: a total never falsely claims a known zero.
    return {key: None if any(p[key] is None for p in parts) else sum((p[key] for p in parts), Decimal("0")) for key in _NUTRIENTS}


async def _owned(session, model, resource_id: uuid.UUID, account_id: uuid.UUID):
    row = (await session.execute(select(model).where(model.id == resource_id, model.account_id == account_id))).scalars().first()
    if row is None:
        _not_found()
    return row


async def _food_nutrition(food: Food, quantity: Decimal) -> dict[str, Decimal | None]:
    return {key: (getattr(food, f"{key}_per_100g") * quantity / Decimal("100") if getattr(food, f"{key}_per_100g") is not None else None) for key in _NUTRIENTS}


async def _recipe_nutrition(session, recipe: Recipe, account_id: uuid.UUID, multiplier=Decimal("1"), visited=None):
    visited = set() if visited is None else visited
    if recipe.id in visited:
        raise HTTPException(422, "Recipe nesting may not contain cycles")
    visited.add(recipe.id)
    ingredients = (await session.execute(select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id, RecipeIngredient.account_id == account_id))).scalars().all()
    values = []
    for ingredient in ingredients:
        if ingredient.food_id:
            food = await _owned(session, Food, ingredient.food_id, account_id)
            values.append(await _food_nutrition(food, ingredient.quantity))
        else:
            nested = await _owned(session, Recipe, ingredient.nested_recipe_id, account_id)
            nested_total = await _recipe_nutrition(session, nested, account_id, ingredient.quantity / nested.servings, visited.copy())
            values.append(nested_total)
    total = _sum(values) if values else {key: Decimal("0") for key in _NUTRIENTS}
    return {key: value * multiplier / recipe.servings if value is not None else None for key, value in total.items()}


async def _replace_recipe_ingredients(session, recipe: Recipe, inputs: list[RecipeIngredientInput], account_id: uuid.UUID):
    if len({item.sort_order for item in inputs}) != len(inputs):
        raise HTTPException(422, "Ingredient sort_order values must be unique")
    # Validate the *prospective* directed recipe graph before mutating it.
    # Checking only self references lets A -> B -> A slip into storage and
    # turns a later nutrition read into a surprising 422.
    existing = (await session.execute(select(RecipeIngredient).where(RecipeIngredient.account_id == account_id))).scalars().all()
    graph: dict[uuid.UUID, set[uuid.UUID]] = {}
    for ingredient in existing:
        if ingredient.recipe_id != recipe.id and ingredient.nested_recipe_id:
            graph.setdefault(ingredient.recipe_id, set()).add(ingredient.nested_recipe_id)
    graph[recipe.id] = {item.nested_recipe_id for item in inputs if item.nested_recipe_id is not None}

    def reaches_current(node: uuid.UUID, visited: set[uuid.UUID]) -> bool:
        if node == recipe.id:
            return True
        if node in visited:
            return False
        return any(reaches_current(child, visited | {node}) for child in graph.get(node, set()))

    if any(reaches_current(child, set()) for child in graph[recipe.id]):
        raise HTTPException(422, "Recipe nesting may not contain cycles")

    for old in (await session.execute(select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id, RecipeIngredient.account_id == account_id))).scalars():
        await session.delete(old)
    for data in inputs:
        if data.food_id:
            if data.unit != "g":
                raise HTTPException(422, "Food quantities require grams until a density is configured")
            await _owned(session, Food, data.food_id, account_id)
        else:
            nested = await _owned(session, Recipe, data.nested_recipe_id, account_id)
            if nested.id == recipe.id:
                raise HTTPException(422, "A recipe cannot contain itself")
        session.add(RecipeIngredient(account_id=account_id, recipe_id=recipe.id, **data.model_dump()))


async def _validate_active_recipe(session, recipe: Recipe, account_id: uuid.UUID) -> None:
    """Ensure published recipes have auditable, complete direct ingredients.

    Drafts intentionally remain flexible so a recipe can be composed over
    time.  Once active, every direct food must be verified and contain every
    nutrient used by the totals endpoint; otherwise a displayed value could be
    mistaken for a validated result.
    """
    ingredients = (await session.execute(select(RecipeIngredient).where(
        RecipeIngredient.recipe_id == recipe.id,
        RecipeIngredient.account_id == account_id,
    ))).scalars().all()
    if not ingredients:
        raise HTTPException(422, "An active recipe requires at least one ingredient")
    for ingredient in ingredients:
        if ingredient.food_id is None:
            continue
        food = await _owned(session, Food, ingredient.food_id, account_id)
        if food.confidence != "verified" or any(getattr(food, f"{key}_per_100g") is None for key in _NUTRIENTS):
            raise HTTPException(422, "Active recipe foods require verified, complete nutrient values")
    nutrition = await _recipe_nutrition(session, recipe, account_id)
    if any(value is None for value in nutrition.values()):
        raise HTTPException(422, "Active recipes require complete nutrient values, including nested recipes")


async def _recipe_response(session, recipe: Recipe, account_id: uuid.UUID):
    ingredients = (await session.execute(select(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id, RecipeIngredient.account_id == account_id).order_by(RecipeIngredient.sort_order))).scalars().all()
    return RecipeResponse(id=recipe.id, name=recipe.name, status=recipe.status, servings=recipe.servings, notes=recipe.notes, instructions=recipe.instructions,
        ingredients=[RecipeIngredientResponse.model_validate(item) for item in ingredients],
        nutrition=Nutrition(**await _recipe_nutrition(session, recipe, account_id)), updated_at=recipe.updated_at)


def _conflict(row, expected):
    if expected and row.updated_at and row.updated_at != expected:
        raise HTTPException(409, "The resource has changed; refresh before saving")


@router.get("/meal-categories", response_model=list[MealCategoryResponse])
async def list_categories(include_inactive: bool = False, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        stmt = select(MealCategory).where(MealCategory.account_id == account_id)
        if not include_inactive: stmt = stmt.where(MealCategory.is_active.is_(True))
        return list((await session.execute(stmt.order_by(MealCategory.sort_order, MealCategory.name))).scalars())

@router.post("/meal-categories", response_model=MealCategoryResponse, status_code=201)
async def create_category(body: MealCategoryCreate, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        row = MealCategory(account_id=account_id, **body.model_dump()); session.add(row)
        try: await session.commit()
        except IntegrityError: await session.rollback(); raise HTTPException(409, "A category with this name already exists")
        await session.refresh(row); return row


@router.put("/meal-categories/reorder", response_model=list[MealCategoryResponse])
async def reorder_categories(body: MealCategoryReorder, account_id: uuid.UUID = Depends(get_current_user)):
    """Atomically reorder all supplied categories; foreign or partial lists fail."""
    async with async_session() as session:
        rows = (await session.execute(select(MealCategory).where(
            MealCategory.account_id == account_id, MealCategory.id.in_(body.ids)
        ))).scalars().all()
        if len(rows) != len(body.ids):
            _not_found()
        by_id = {row.id: row for row in rows}
        for order, category_id in enumerate(body.ids):
            by_id[category_id].sort_order = order
        await session.commit()
        return [by_id[category_id] for category_id in body.ids]

@router.put("/meal-categories/{category_id}", response_model=MealCategoryResponse)
async def update_category(category_id: uuid.UUID, body: MealCategoryUpdate, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        row = await _owned(session, MealCategory, category_id, account_id); _conflict(row, body.expected_updated_at)
        for key, value in body.model_dump(exclude_unset=True, exclude={"expected_updated_at"}).items(): setattr(row, key, value)
        try: await session.commit()
        except IntegrityError: await session.rollback(); raise HTTPException(409, "A category with this name already exists")
        await session.refresh(row); return row

@router.delete("/meal-categories/{category_id}", status_code=204)
async def delete_category(category_id: uuid.UUID, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        row = await _owned(session, MealCategory, category_id, account_id)
        used = await session.scalar(select(func.count()).select_from(MealEntry).where(MealEntry.category_id == row.id, MealEntry.account_id == account_id))
        if used: raise HTTPException(409, "A category with historical entries may only be deactivated")
        await session.delete(row); await session.commit()


@router.get("/foods", response_model=list[FoodResponse])
async def list_foods(q: str | None = None, include_archived: bool = False, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        stmt = select(Food).where(Food.account_id == account_id)
        if not include_archived: stmt = stmt.where(Food.is_archived.is_(False))
        if q: stmt = stmt.where(Food.name.ilike(f"%{q}%"))
        return [_food_response(row) for row in (await session.execute(stmt.order_by(Food.name))).scalars()]

@router.post("/foods", response_model=FoodResponse, status_code=201)
async def create_food(body: FoodCreate, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        data = body.model_dump(); row = Food(account_id=account_id, tags=data.pop("tags"), **{f"{key}_per_100g": data.pop(key) for key in _NUTRIENTS}, **data); session.add(row)
        try: await session.commit()
        except IntegrityError: await session.rollback(); raise HTTPException(409, "A food with this name already exists")
        await session.refresh(row); return _food_response(row)

def _food_response(row):
    return FoodResponse(id=row.id, name=row.name, tags=row.tags or [], source=row.source, confidence=row.confidence, is_archived=row.is_archived, updated_at=row.updated_at,
        **{key: getattr(row, f"{key}_per_100g") for key in _NUTRIENTS})

@router.get("/foods/{food_id}", response_model=FoodResponse)
async def get_food(food_id: uuid.UUID, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session: return _food_response(await _owned(session, Food, food_id, account_id))

@router.put("/foods/{food_id}", response_model=FoodResponse)
async def update_food(food_id: uuid.UUID, body: FoodUpdate, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        row = await _owned(session, Food, food_id, account_id); _conflict(row, body.expected_updated_at)
        for key, value in body.model_dump(exclude_unset=True, exclude={"expected_updated_at"}).items(): setattr(row, f"{key}_per_100g" if key in _NUTRIENTS else key, value)
        try: await session.commit()
        except IntegrityError: await session.rollback(); raise HTTPException(409, "A food with this name already exists")
        await session.refresh(row); return _food_response(row)

@router.delete("/foods/{food_id}", status_code=204)
async def archive_food(food_id: uuid.UUID, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        row = await _owned(session, Food, food_id, account_id); row.is_archived = True; await session.commit()

@router.get("/recipes", response_model=list[RecipeResponse])
async def list_recipes(account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        rows = (await session.execute(select(Recipe).where(Recipe.account_id == account_id).order_by(Recipe.name))).scalars().all()
        return [await _recipe_response(session, row, account_id) for row in rows]

@router.post("/recipes", response_model=RecipeResponse, status_code=201)
async def create_recipe(body: RecipeCreate, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        data = body.model_dump(exclude={"ingredients"}); row = Recipe(account_id=account_id, **data); session.add(row); await session.flush()
        await _replace_recipe_ingredients(session, row, body.ingredients, account_id)
        if row.status == "active": await _validate_active_recipe(session, row, account_id)
        try: await session.commit()
        except IntegrityError: await session.rollback(); raise HTTPException(409, "A recipe with this name already exists")
        await session.refresh(row); return await _recipe_response(session, row, account_id)

@router.get("/recipes/{recipe_id}", response_model=RecipeResponse)
async def get_recipe(recipe_id: uuid.UUID, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session: return await _recipe_response(session, await _owned(session, Recipe, recipe_id, account_id), account_id)

@router.put("/recipes/{recipe_id}", response_model=RecipeResponse)
async def update_recipe(recipe_id: uuid.UUID, body: RecipeUpdate, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        row = await _owned(session, Recipe, recipe_id, account_id); _conflict(row, body.expected_updated_at)
        for key, value in body.model_dump(exclude_unset=True, exclude={"ingredients", "expected_updated_at"}).items(): setattr(row, key, value)
        if body.ingredients is not None: await _replace_recipe_ingredients(session, row, body.ingredients, account_id)
        if row.status == "active": await _validate_active_recipe(session, row, account_id)
        await session.commit(); await session.refresh(row); return await _recipe_response(session, row, account_id)

@router.delete("/recipes/{recipe_id}", status_code=204)
async def archive_recipe(recipe_id: uuid.UUID, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        row = await _owned(session, Recipe, recipe_id, account_id); row.status = "archived"; await session.commit()


async def _replace_plan_items(session, plan: MealPlan, inputs: list[MealPlanItemInput], account_id: uuid.UUID):
    # Do not delete old plan items: a historic MealEntry references the item
    # that created it.  Retiring and reusing item rows preserves that FK while
    # version snapshots below retain the exact old configuration.
    existing = (await session.execute(select(MealPlanItem).where(MealPlanItem.meal_plan_id == plan.id, MealPlanItem.account_id == account_id))).scalars().all()
    by_sort = {item.sort_order: item for item in existing}
    for old in existing:
        old.is_active = False
    for data in inputs:
        await _owned(session, MealCategory, data.category_id, account_id)
        if data.recipe_id: await _owned(session, Recipe, data.recipe_id, account_id)
        item = by_sort.get(data.sort_order)
        if item is None:
            session.add(MealPlanItem(account_id=account_id, meal_plan_id=plan.id, is_active=True, **data.model_dump()))
        else:
            for key, value in data.model_dump().items():
                setattr(item, key, value)
            item.is_active = True


async def _record_plan_version(session, plan: MealPlan, account_id: uuid.UUID):
    items = (await session.execute(select(MealPlanItem).where(
        MealPlanItem.meal_plan_id == plan.id, MealPlanItem.account_id == account_id, MealPlanItem.is_active.is_(True)
    ).order_by(MealPlanItem.sort_order))).scalars().all()
    snapshot = [{
        "category_id": str(item.category_id), "recipe_id": str(item.recipe_id) if item.recipe_id else None,
        "name": item.name, "planned_time": item.planned_time.isoformat() if item.planned_time else None,
        "weekdays": item.weekdays, "portion": str(item.portion), "sort_order": item.sort_order,
    } for item in items]
    session.add(MealPlanVersion(account_id=account_id, meal_plan_id=plan.id, version=plan.version, name=plan.name, items_snapshot=snapshot))


async def _plan_response(session, plan: MealPlan, account_id: uuid.UUID):
    items = (await session.execute(select(MealPlanItem).where(MealPlanItem.meal_plan_id == plan.id, MealPlanItem.account_id == account_id, MealPlanItem.is_active.is_(True)).order_by(MealPlanItem.sort_order))).scalars().all()
    return MealPlanResponse(id=plan.id, name=plan.name, version=plan.version, is_active=plan.is_active, updated_at=plan.updated_at,
        items=[MealPlanItemResponse.model_validate(item) for item in items])


async def _set_active(session, plan: MealPlan, account_id: uuid.UUID):
    if plan.is_active:
        for other in (await session.execute(select(MealPlan).where(MealPlan.account_id == account_id, MealPlan.id != plan.id, MealPlan.is_active.is_(True)))).scalars(): other.is_active = False


@router.get("/meal-plans", response_model=list[MealPlanResponse])
async def list_plans(account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        rows = (await session.execute(select(MealPlan).where(MealPlan.account_id == account_id).order_by(MealPlan.name))).scalars().all()
        return [await _plan_response(session, row, account_id) for row in rows]

@router.post("/meal-plans", response_model=MealPlanResponse, status_code=201)
async def create_plan(body: MealPlanCreate, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        data = body.model_dump(exclude={"items"}); row = MealPlan(account_id=account_id, **data); session.add(row); await session.flush()
        await _set_active(session, row, account_id); await _replace_plan_items(session, row, body.items, account_id); await session.flush(); await _record_plan_version(session, row, account_id)
        await session.commit(); await session.refresh(row); return await _plan_response(session, row, account_id)

@router.get("/meal-plans/{plan_id}", response_model=MealPlanResponse)
async def get_plan(plan_id: uuid.UUID, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session: return await _plan_response(session, await _owned(session, MealPlan, plan_id, account_id), account_id)

@router.put("/meal-plans/{plan_id}", response_model=MealPlanResponse)
async def update_plan(plan_id: uuid.UUID, body: MealPlanUpdate, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        row = await _owned(session, MealPlan, plan_id, account_id); _conflict(row, body.expected_updated_at)
        for key, value in body.model_dump(exclude_unset=True, exclude={"items", "expected_updated_at"}).items(): setattr(row, key, value)
        if body.is_active is True: await _set_active(session, row, account_id)
        if body.items is not None:
            row.version += 1; await _replace_plan_items(session, row, body.items, account_id); await session.flush(); await _record_plan_version(session, row, account_id)
        await session.commit(); await session.refresh(row); return await _plan_response(session, row, account_id)

@router.delete("/meal-plans/{plan_id}", status_code=204)
async def delete_plan(plan_id: uuid.UUID, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        row = await _owned(session, MealPlan, plan_id, account_id)
        if row.is_active: raise HTTPException(409, "Deactivate a plan before deleting it")
        used = await session.scalar(select(func.count()).select_from(MealEntry).where(
            MealEntry.account_id == account_id, MealEntry.meal_plan_id == row.id
        ))
        if used:
            raise HTTPException(409, "A plan with historical entries may not be deleted")
        await session.delete(row); await session.commit()


@router.get("/meal-plans/{plan_id}/versions", response_model=list[MealPlanVersionResponse])
async def list_plan_versions(plan_id: uuid.UUID, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        await _owned(session, MealPlan, plan_id, account_id)
        rows = (await session.execute(select(MealPlanVersion).where(
            MealPlanVersion.account_id == account_id, MealPlanVersion.meal_plan_id == plan_id
        ).order_by(MealPlanVersion.version.desc()))).scalars().all()
        return [MealPlanVersionResponse(version=row.version, name=row.name, items_snapshot=row.items_snapshot, created_at=row.created_at) for row in rows]


async def _entry_item(session, data: MealEntryItemInput, account_id: uuid.UUID):
    if data.food_id:
        if data.unit != "g":
            raise HTTPException(422, "Food quantities require grams until a density is configured")
        food = await _owned(session, Food, data.food_id, account_id)
        nutrition = await _food_nutrition(food, data.quantity)
        source = {"kind": "food", "name": food.name, "per_100g": _snapshot({key: getattr(food, f"{key}_per_100g") for key in _NUTRIENTS})}
    else:
        recipe = await _owned(session, Recipe, data.recipe_id, account_id)
        # recipe quantities are servings; a gram request is deliberately not guessed.
        if data.unit != "serving": raise HTTPException(422, "Recipe quantities must use serving")
        nutrition = await _recipe_nutrition(session, recipe, account_id, data.quantity)
        source = {"kind": "recipe", "name": recipe.name, "servings": str(recipe.servings)}
    return MealEntryItem(account_id=account_id, food_id=data.food_id, recipe_id=data.recipe_id, quantity=data.quantity, unit=data.unit,
        nutrition_snapshot=_snapshot(nutrition), source_snapshot=source)


async def _replace_entry_items(session, entry: MealEntry, inputs: list[MealEntryItemInput], account_id: uuid.UUID):
    for old in (await session.execute(select(MealEntryItem).where(MealEntryItem.meal_entry_id == entry.id, MealEntryItem.account_id == account_id))).scalars(): await session.delete(old)
    items = [await _entry_item(session, data, account_id) for data in inputs]
    for item in items: item.meal_entry_id = entry.id; session.add(item)
    entry.nutrition_snapshot = _snapshot(_sum([_nutrition_from_snapshot(item.nutrition_snapshot).model_dump() for item in items]) if items else {key: Decimal("0") for key in _NUTRIENTS})


async def _entry_response(session, entry: MealEntry, account_id: uuid.UUID):
    items = (await session.execute(select(MealEntryItem).where(MealEntryItem.meal_entry_id == entry.id, MealEntryItem.account_id == account_id))).scalars().all()
    return MealEntryResponse(id=entry.id, date=entry.date, category_id=entry.category_id, name=entry.name, status=entry.status, consumed_at=entry.consumed_at,
        source=entry.source, nutrition=_nutrition_from_snapshot(entry.nutrition_snapshot), updated_at=entry.updated_at,
        items=[MealEntryItemResponse(id=i.id, food_id=i.food_id, recipe_id=i.recipe_id, quantity=i.quantity, unit=i.unit, nutrition_snapshot=i.nutrition_snapshot, source_snapshot=i.source_snapshot) for i in items])


@router.post("/meal-entries/instantiate", response_model=list[MealEntryResponse])
async def instantiate_entries(day: date_type = Query(alias="date"), account_id: uuid.UUID = Depends(get_current_user)):
    """Explicit, idempotent active-plan projection; GET never creates data."""
    async with async_session() as session:
        plan = (await session.execute(select(MealPlan).where(MealPlan.account_id == account_id, MealPlan.is_active.is_(True)))).scalars().first()
        if not plan: return []
        items = (await session.execute(select(MealPlanItem).where(MealPlanItem.account_id == account_id, MealPlanItem.meal_plan_id == plan.id, MealPlanItem.is_active.is_(True)))).scalars().all()
        for item in items:
            if item.weekdays is not None and day.weekday() not in item.weekdays: continue
            exists = await session.scalar(select(func.count()).select_from(MealEntry).where(MealEntry.account_id == account_id, MealEntry.date == day, MealEntry.meal_plan_id == plan.id, MealEntry.meal_plan_item_id == item.id))
            if exists: continue
            name = item.name
            item_inputs = []
            if item.recipe_id:
                recipe = await _owned(session, Recipe, item.recipe_id, account_id); name = name or recipe.name
                item_inputs = [MealEntryItemInput(recipe_id=recipe.id, quantity=item.portion, unit="serving")]
            # The database uniqueness constraint is the concurrency boundary.
            # A savepoint also handles the case where the conflicting INSERT is
            # raised by flush (rather than only by the final commit).
            try:
                async with session.begin_nested():
                    entry = MealEntry(account_id=account_id, date=day, category_id=item.category_id, name=name or "Meal", status="planned", source="plan", meal_plan_id=plan.id, meal_plan_item_id=item.id, meal_plan_version=plan.version, nutrition_snapshot={})
                    session.add(entry); await session.flush(); await _replace_entry_items(session, entry, item_inputs, account_id)
            except IntegrityError:
                continue
        try:
            await session.commit()
        except IntegrityError:
            # The unique plan-instance constraint is authoritative under
            # concurrent requests; a racing caller observes the projection.
            await session.rollback()
        rows = (await session.execute(select(MealEntry).where(MealEntry.account_id == account_id, MealEntry.date == day).order_by(MealEntry.created_at))).scalars().all()
        return [await _entry_response(session, row, account_id) for row in rows]

@router.get("/meal-entries", response_model=list[MealEntryResponse])
async def list_entries(from_date: date_type = Query(alias="from"), to_date: date_type = Query(alias="to"), account_id: uuid.UUID = Depends(get_current_user)):
    if to_date < from_date: raise HTTPException(422, "to must not precede from")
    async with async_session() as session:
        rows = (await session.execute(select(MealEntry).where(MealEntry.account_id == account_id, MealEntry.date.between(from_date, to_date)).order_by(MealEntry.date, MealEntry.created_at))).scalars().all()
        return [await _entry_response(session, row, account_id) for row in rows]

@router.post("/meal-entries", response_model=MealEntryResponse, status_code=201)
async def create_entry(body: MealEntryCreate, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        await _owned(session, MealCategory, body.category_id, account_id)
        entry = MealEntry(account_id=account_id, **body.model_dump(exclude={"items"}), nutrition_snapshot={})
        if entry.status == "consumed" and entry.consumed_at is None: entry.consumed_at = datetime.now(timezone.utc)
        session.add(entry); await session.flush(); await _replace_entry_items(session, entry, body.items, account_id)
        await session.commit(); await session.refresh(entry); return await _entry_response(session, entry, account_id)

@router.get("/meal-entries/{entry_id}", response_model=MealEntryResponse)
async def get_entry(entry_id: uuid.UUID, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session: return await _entry_response(session, await _owned(session, MealEntry, entry_id, account_id), account_id)

@router.put("/meal-entries/{entry_id}", response_model=MealEntryResponse)
async def update_entry(entry_id: uuid.UUID, body: MealEntryUpdate, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        entry = await _owned(session, MealEntry, entry_id, account_id); _conflict(entry, body.expected_updated_at)
        if body.category_id: await _owned(session, MealCategory, body.category_id, account_id)
        for key, value in body.model_dump(exclude_unset=True, exclude={"items", "expected_updated_at"}).items(): setattr(entry, key, value)
        if entry.status == "consumed" and entry.consumed_at is None: entry.consumed_at = datetime.now(timezone.utc)
        if body.items is not None: await _replace_entry_items(session, entry, body.items, account_id)
        await session.commit(); await session.refresh(entry); return await _entry_response(session, entry, account_id)

@router.delete("/meal-entries/{entry_id}", status_code=204)
async def delete_entry(entry_id: uuid.UUID, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session: await session.delete(await _owned(session, MealEntry, entry_id, account_id)); await session.commit()

@router.post("/meal-entries/{entry_id}/consume", response_model=MealEntryResponse)
async def consume_entry(entry_id: uuid.UUID, body: MealEntryStatusCommand | None = None, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        entry = await _owned(session, MealEntry, entry_id, account_id); _conflict(entry, body.expected_updated_at if body else None); entry.status = "consumed"; entry.consumed_at = datetime.now(timezone.utc)
        await session.commit(); await session.refresh(entry); return await _entry_response(session, entry, account_id)

@router.post("/meal-entries/{entry_id}/skip", response_model=MealEntryResponse)
async def skip_entry(entry_id: uuid.UUID, body: MealEntryStatusCommand | None = None, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        entry = await _owned(session, MealEntry, entry_id, account_id); _conflict(entry, body.expected_updated_at if body else None); entry.status = "skipped"; entry.consumed_at = None
        await session.commit(); await session.refresh(entry); return await _entry_response(session, entry, account_id)


@router.post("/meal-entries/{entry_id}/photo-analyses", response_model=MealPhotoAnalysisResponse, status_code=201)
async def create_photo_analysis(
    entry_id: uuid.UUID,
    file: UploadFile = File(...),
    account_id: uuid.UUID = Depends(get_current_user),
):
    """Upload a photo and persist its vision result as a reviewable proposal.

    Neither this command nor the vision provider mutates a ``MealEntry``.  A
    user must select and submit items to the separate ``accept`` command.
    """
    async with async_session() as session:
        await _owned(session, MealEntry, entry_id, account_id)

    contents = await file.read()
    mime_type, extension = _image_metadata(contents, file.content_type)
    photo_id = uuid.uuid4()
    photo_directory = os.path.abspath(settings.PHOTO_DIR)
    os.makedirs(photo_directory, exist_ok=True)
    file_path = os.path.join(photo_directory, f"{photo_id}{extension}")
    try:
        with open(file_path, "xb") as photo_file:
            photo_file.write(contents)
    except OSError:
        logger.exception("Could not persist configurable meal photo")
        raise HTTPException(500, "Could not save photo")

    try:
        async with async_session() as session:
            # Recheck after writing: a concurrent delete must not attach a
            # visible photo to an entry that no longer belongs to this account.
            await _owned(session, MealEntry, entry_id, account_id)
            photo = Photo(id=photo_id, account_id=account_id, meal_entry_id=entry_id,
                file_path=file_path, original_filename=file.filename, mime_type=mime_type)
            proposal = MealPhotoAnalysis(account_id=account_id, photo_id=photo_id,
                meal_entry_id=entry_id, state="pending", provider="vision-proxy", schema_version="1")
            session.add_all([photo, proposal])
            await session.commit()
            await session.refresh(proposal)
            analysis_id = proposal.id
    except Exception:
        # This request created the UUID-derived path, so this unlink cannot
        # affect an unrelated user file.
        try:
            os.unlink(file_path)
        except FileNotFoundError:
            pass
        raise

    proposal_state, analysis, error_code = await _vision_proposal(contents)
    async with async_session() as session:
        proposal = await _owned(session, MealPhotoAnalysis, analysis_id, account_id)
        # Preserve any terminal state imposed by an administrative operation
        # while the remote vision service was processing the image.
        if proposal.state == "pending":
            proposal.state = proposal_state
            proposal.analysis = analysis
            proposal.error_code = error_code
            await session.commit()
            await session.refresh(proposal)
        return MealPhotoAnalysisResponse(id=proposal.id, meal_entry_id=proposal.meal_entry_id,
            state=proposal.state, analysis=proposal.analysis, error_code=proposal.error_code,
            created_at=proposal.created_at)


@router.post("/meal-entries/{entry_id}/photo-analyses/{analysis_id}/accept", response_model=MealEntryResponse)
async def accept_photo_analysis(entry_id: uuid.UUID, analysis_id: uuid.UUID, body: MealPhotoAnalysisAccept, account_id: uuid.UUID = Depends(get_current_user)):
    """Apply only user-reviewed item IDs; model output never writes nutrition directly."""
    async with async_session() as session:
        entry = await _owned(session, MealEntry, entry_id, account_id)
        analysis = await _owned(session, MealPhotoAnalysis, analysis_id, account_id)
        if analysis.meal_entry_id != entry.id or analysis.state != "pending":
            _not_found()
        if body.name is not None: entry.name = body.name
        if body.status is not None: entry.status = body.status
        if entry.status == "consumed" and entry.consumed_at is None: entry.consumed_at = datetime.now(timezone.utc)
        entry.source = "photo"
        await _replace_entry_items(session, entry, body.items, account_id)
        analysis.state, analysis.accepted_at = "accepted", datetime.now(timezone.utc)
        await session.commit(); await session.refresh(entry)
        return await _entry_response(session, entry, account_id)


@router.post("/meal-entries/{entry_id}/photo-analyses/{analysis_id}/reject", response_model=MealPhotoAnalysisResponse)
async def reject_photo_analysis(entry_id: uuid.UUID, analysis_id: uuid.UUID, account_id: uuid.UUID = Depends(get_current_user)):
    async with async_session() as session:
        await _owned(session, MealEntry, entry_id, account_id)
        analysis = await _owned(session, MealPhotoAnalysis, analysis_id, account_id)
        if analysis.meal_entry_id != entry_id or analysis.state != "pending": _not_found()
        analysis.state, analysis.rejected_at = "rejected", datetime.now(timezone.utc)
        await session.commit()
        return MealPhotoAnalysisResponse(id=analysis.id, meal_entry_id=entry_id, state="rejected", analysis=analysis.analysis, error_code=analysis.error_code, created_at=analysis.created_at)
