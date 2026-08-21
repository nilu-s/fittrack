"""Dish routes — CRUD + recommend + search + fuzzy duplicate check.

Dishes are slot-independent: any dish can be assigned to any meal slot.
The recommend endpoint returns the default dish for a slot + 2 alternatives with similar macros.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, cast, Numeric

from app.database import async_session
from app.models import Dish
from app.routes.auth import get_current_user
from app.schemas import (
    DishCreate,
    DishResponse,
    DishUpdate,
    DishMatchResult,
    DishRecommendResult,
)

router = APIRouter(prefix="/dishes", tags=["dishes"])


def _dish_to_response(dish: Dish) -> DishResponse:
    return DishResponse.model_validate(dish)


def _normalize(name: str) -> str:
    return " ".join(name.strip().lower().split())


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


@router.get("", response_model=list[DishResponse])
async def list_dishes(
    slot: Optional[int] = Query(None, description="Filter by preferred slot"),
    q: Optional[str] = Query(None, description="Search query (case-insensitive name match)"),
    user: str = Depends(get_current_user),
):
    """List all dishes. Optionally filter by slot or search by name.
    Sorted by is_default desc, usage_count desc, name."""
    async with async_session() as session:
        stmt = select(Dish).where(Dish.user_id == "luis")
        if slot is not None:
            # A slot is a meal category.  Slot-filtered alternatives must be
            # explicitly categorized; uncategorized dishes belong only to the
            # global search, never to a category recommendation.
            stmt = stmt.where(Dish.slot == slot)
        if q:
            stmt = stmt.where(func.lower(Dish.name).like(f"%{q.lower()}%"))
        stmt = stmt.order_by(Dish.is_default.desc(), Dish.usage_count.desc(), Dish.name)
        result = await session.execute(stmt)
        return [_dish_to_response(d) for d in result.scalars().all()]


@router.get("/recommend", response_model=DishRecommendResult)
async def recommend_for_slot(
    slot: int = Query(..., description="Meal slot 1-4"),
    user: str = Depends(get_current_user),
):
    """Get the default dish for a slot and alternatives from that same slot.

    A meal slot is a product category (breakfast, lunch, snack, dinner), so an
    alternative must have the same preferred slot. Macro distance is only used
    to rank dishes inside that category; it must never broaden the category.
    """
    async with async_session() as session:
        # 1. Default dish for this slot
        default_result = await session.execute(
            select(Dish).where(
                Dish.user_id == "luis",
                Dish.is_default == True,
                Dish.slot == slot,
            ).order_by(Dish.usage_count.desc())
        )
        default_dish = default_result.scalars().first()

        # Fallback: most-used dish with this slot
        if not default_dish:
            fallback_result = await session.execute(
                select(Dish).where(
                    Dish.user_id == "luis",
                    Dish.slot == slot,
                ).order_by(Dish.usage_count.desc())
            )
            default_dish = fallback_result.scalars().first()

        # 2. Find alternatives strictly inside this meal category.  Never
        # fall back to dishes from another slot: lunch must stay lunch, etc.
        alternatives: list[Dish] = []
        if default_dish and default_dish.kcal is not None:
            target_kcal = float(default_dish.kcal)
            alternatives_result = await session.execute(
                select(Dish).where(
                    Dish.user_id == "luis",
                    Dish.slot == slot,
                    Dish.id != default_dish.id,
                    Dish.kcal.is_not(None),
                ).order_by(
                    func.abs(cast(Dish.kcal, Numeric) - target_kcal),
                    Dish.usage_count.desc(),
                    Dish.name,
                ).limit(2)
            )
            alternatives = list(alternatives_result.scalars().all())
        elif default_dish:
            alternatives_result = await session.execute(
                select(Dish).where(
                    Dish.user_id == "luis",
                    Dish.slot == slot,
                    Dish.id != default_dish.id,
                ).order_by(Dish.usage_count.desc(), Dish.name).limit(2)
            )
            alternatives = list(alternatives_result.scalars().all())

        return DishRecommendResult(
            default=_dish_to_response(default_dish) if default_dish else None,
            alternatives=[_dish_to_response(d) for d in alternatives],
        )


@router.post("", response_model=DishResponse, status_code=201)
async def create_dish(body: DishCreate, user: str = Depends(get_current_user)):
    async with async_session() as session:
        # Check for exact duplicate (user_id, name) — dishes are slot-independent now
        existing = await session.execute(
            select(Dish).where(
                Dish.user_id == "luis",
                func.lower(func.trim(Dish.name)) == func.lower(func.trim(body.name)),
            )
        )
        dup = existing.scalars().first()
        if dup:
            # Return existing dish instead of creating a duplicate
            dup.usage_count += 1
            await session.commit()
            await session.refresh(dup)
            return _dish_to_response(dup)

        dish = Dish(**body.model_dump())
        session.add(dish)
        await session.commit()
        await session.refresh(dish)
        return _dish_to_response(dish)


@router.put("/{dish_id}", response_model=DishResponse)
async def update_dish(dish_id: uuid.UUID, body: DishUpdate, user: str = Depends(get_current_user)):
    async with async_session() as session:
        result = await session.execute(select(Dish).where(Dish.id == dish_id))
        dish = result.scalars().first()
        if dish is None:
            raise HTTPException(status_code=404, detail="Dish not found")

        # If setting this dish as default, unset other defaults for the same slot
        if body.is_default is True and dish.slot is not None:
            other_defaults = await session.execute(
                select(Dish).where(
                    Dish.user_id == "luis",
                    Dish.slot == dish.slot,
                    Dish.is_default == True,
                    Dish.id != dish_id,
                )
            )
            for other in other_defaults.scalars().all():
                other.is_default = False

        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(dish, field, value)
        await session.commit()
        await session.refresh(dish)
        return _dish_to_response(dish)


@router.delete("/{dish_id}", status_code=204)
async def delete_dish(dish_id: uuid.UUID, user: str = Depends(get_current_user)):
    async with async_session() as session:
        result = await session.execute(select(Dish).where(Dish.id == dish_id))
        dish = result.scalars().first()
        if dish is None:
            raise HTTPException(status_code=404, detail="Dish not found")
        if dish.is_default:
            raise HTTPException(status_code=400, detail="Cannot delete default dish. Set another dish as default first.")
        await session.delete(dish)
        await session.commit()


@router.get("/match", response_model=DishMatchResult)
async def match_dish(
    name: str = Query(..., description="Dish name to match against existing dishes"),
    threshold: float = Query(0.75, description="Similarity threshold 0-1"),
    user: str = Depends(get_current_user),
):
    """Fuzzy-match a dish name against ALL existing dishes (slot-independent)."""
    async with async_session() as session:
        result = await session.execute(
            select(Dish).where(Dish.user_id == "luis")
        )
        dishes = list(result.scalars().all())

    best_dish = None
    best_score = 0.0

    for dish in dishes:
        score = _similarity(name, dish.name)
        if score > best_score:
            best_score = score
            best_dish = dish

    if best_dish and best_score >= threshold:
        return DishMatchResult(matched=True, dish=_dish_to_response(best_dish), similarity=best_score)
    return DishMatchResult(matched=False, similarity=best_score)


@router.post("/{dish_id}/use", response_model=DishResponse)
async def increment_usage(dish_id: uuid.UUID, user: str = Depends(get_current_user)):
    """Increment usage_count when a dish is selected for a meal."""
    async with async_session() as session:
        result = await session.execute(select(Dish).where(Dish.id == dish_id))
        dish = result.scalars().first()
        if dish is None:
            raise HTTPException(status_code=404, detail="Dish not found")
        dish.usage_count += 1
        await session.commit()
        await session.refresh(dish)
        return _dish_to_response(dish)