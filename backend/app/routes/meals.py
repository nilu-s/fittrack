from __future__ import annotations

import uuid
from datetime import date as date_type, time
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.database import async_session
from app.models import Dish, Meal, MealTemplate
from app.routes.auth import get_current_user
from app.schemas import (
    MealCreate,
    MealResponse,
    MealTemplateResponse,
    MealTemplateUpdate,
    MealUpdate,
)

router = APIRouter(prefix="/meals", tags=["meals"])

# Default times for meal slots
DEFAULT_TIMES = {1: time(8, 30), 2: time(12, 30), 3: time(16, 0), 4: time(19, 0)}


def _meal_to_response(meal: Meal) -> MealResponse:
    return MealResponse.model_validate(meal)


async def _auto_create_from_templates(session, user_id: str, day: date_type) -> list[Meal]:
    """Auto-create meals from templates only if NO meals exist for this date at all
    (including soft-deleted). If user deleted all meals, respect that."""
    # Check if ANY meals exist for this date (including deleted)
    result = await session.execute(
        select(Meal).where(Meal.user_id == user_id, Meal.date == day).order_by(Meal.meal_slot)
    )
    all_meals = list(result.scalars().all())
    if all_meals:
        # User has meals for this day — return only non-deleted
        return [m for m in all_meals if not m.deleted]

    # No meals at all → create from default dishes (fall back to templates)
    dish_result = await session.execute(
        select(Dish).where(Dish.user_id == user_id, Dish.is_default == True).order_by(Dish.slot)
    )
    default_dishes = list(dish_result.scalars().all())

    if default_dishes:
        for dish in default_dishes:
            meal = Meal(
                user_id=user_id,
                date=day,
                meal_slot=dish.slot,
                name=dish.name,
                default_time=DEFAULT_TIMES.get(dish.slot, time(12, 0)),
                kcal=dish.kcal,
                protein_g=dish.protein_g,
                carbs_g=dish.carbs_g,
                fat_g=dish.fat_g,
                fiber_g=dish.fiber_g,
                sugar_g=dish.sugar_g,
                free_sugar_g=dish.free_sugar_g,
                is_standard=True,
                is_done=False,
                dish_id=dish.id,
                portion_factor=Decimal("1.00"),
            )
            session.add(meal)
    else:
        # Fallback to meal_templates if no default dishes exist
        tpl_result = await session.execute(
            select(MealTemplate).where(MealTemplate.user_id == user_id).order_by(MealTemplate.slot)
        )
        templates = list(tpl_result.scalars().all())
        for tpl in templates:
            meal = Meal(
                user_id=user_id,
                date=day,
                meal_slot=tpl.slot,
                name=tpl.name,
                default_time=DEFAULT_TIMES.get(tpl.slot, time(12, 0)),
                kcal=tpl.kcal,
                protein_g=tpl.protein_g,
                carbs_g=tpl.carbs_g,
                fat_g=tpl.fat_g,
                fiber_g=tpl.fiber_g,
                sugar_g=tpl.sugar_g,
                free_sugar_g=tpl.free_sugar_g,
                is_standard=True,
                is_done=False,
            )
            session.add(meal)
    await session.flush()
    result = await session.execute(
        select(Meal).where(Meal.user_id == user_id, Meal.date == day).order_by(Meal.meal_slot)
    )
    return list(result.scalars().all())


# --- Meal endpoints ---

@router.get("", response_model=list[MealResponse])
async def get_meals(date: date_type = Query(...), user: str = Depends(get_current_user)):
    async with async_session() as session:
        meals = await _auto_create_from_templates(session, "luis", date)
        await session.commit()
        return [_meal_to_response(m) for m in meals]


@router.post("", response_model=MealResponse, status_code=201)
async def create_meal(body: MealCreate, user: str = Depends(get_current_user)):
    async with async_session() as session:
        meal = Meal(**body.model_dump())
        session.add(meal)
        await session.commit()
        await session.refresh(meal)
        return _meal_to_response(meal)


@router.put("/{meal_id}", response_model=MealResponse)
async def update_meal(meal_id: uuid.UUID, body: MealUpdate, user: str = Depends(get_current_user)):
    async with async_session() as session:
        result = await session.execute(select(Meal).where(Meal.id == meal_id))
        meal = result.scalars().first()
        if meal is None:
            raise HTTPException(status_code=404, detail="Meal not found")
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(meal, field, value)
        await session.commit()
        await session.refresh(meal)
        return _meal_to_response(meal)


@router.delete("/{meal_id}", status_code=204)
async def delete_meal(meal_id: uuid.UUID, user: str = Depends(get_current_user)):
    async with async_session() as session:
        result = await session.execute(select(Meal).where(Meal.id == meal_id, Meal.deleted == False))
        meal = result.scalars().first()
        if meal is None:
            raise HTTPException(status_code=404, detail="Meal not found")
        meal.deleted = True
        await session.commit()


@router.post("/{meal_id}/done", response_model=MealResponse)
async def mark_meal_done(meal_id: uuid.UUID, user: str = Depends(get_current_user)):
    async with async_session() as session:
        result = await session.execute(select(Meal).where(Meal.id == meal_id, Meal.deleted == False))
        meal = result.scalars().first()
        if meal is None:
            raise HTTPException(status_code=404, detail="Meal not found")
        meal.is_done = not meal.is_done
        await session.commit()
        await session.refresh(meal)
        return _meal_to_response(meal)


# --- Meal template endpoints (separate prefix) ---

templates_router = APIRouter(prefix="/meal-templates", tags=["meal-templates"])


@templates_router.get("", response_model=list[MealTemplateResponse])
async def list_meal_templates(user: str = Depends(get_current_user)):
    async with async_session() as session:
        result = await session.execute(
            select(MealTemplate).where(MealTemplate.user_id == "luis").order_by(MealTemplate.slot)
        )
        templates = result.scalars().all()
        return [MealTemplateResponse.model_validate(t) for t in templates]


@templates_router.put("/{slot}", response_model=MealTemplateResponse)
async def update_meal_template(slot: int, body: MealTemplateUpdate, user: str = Depends(get_current_user)):
    async with async_session() as session:
        result = await session.execute(
            select(MealTemplate).where(MealTemplate.user_id == "luis", MealTemplate.slot == slot)
        )
        tpl = result.scalars().first()
        if tpl is None:
            raise HTTPException(status_code=404, detail="Template not found")
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(tpl, field, value)
        await session.commit()
        await session.refresh(tpl)
        return MealTemplateResponse.model_validate(tpl)


# Attach templates_router to the main router so it's reachable under /api/meal-templates
# NOTE: templates_router is exported and included at the app level in main.py
# to avoid nesting under /meals prefix.