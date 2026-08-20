"""Dish routes — CRUD + fuzzy duplicate check for the growing dish database."""
from __future__ import annotations

import uuid
from difflib import SequenceMatcher
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func

from app.database import async_session
from app.models import Dish
from app.routes.auth import get_current_user
from app.schemas import (
    DishCreate,
    DishResponse,
    DishUpdate,
    DishMatchResult,
)

router = APIRouter(prefix="/dishes", tags=["dishes"])

SLOT_NAMES = {1: "Frühstück", 2: "Mittag", 3: "Snack", 4: "Abend"}


def _dish_to_response(dish: Dish) -> DishResponse:
    return DishResponse.model_validate(dish)


def _normalize(name: str) -> str:
    """Normalize dish name for comparison: lowercase, strip, collapse whitespace."""
    return " ".join(name.strip().lower().split())


def _similarity(a: str, b: str) -> float:
    """Fuzzy similarity score between two normalized names (0.0–1.0)."""
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


@router.get("", response_model=list[DishResponse])
async def list_dishes(
    slot: Optional[int] = Query(None, description="Filter by meal slot 1-4"),
    user: str = Depends(get_current_user),
):
    """List all dishes, optionally filtered by slot. Defaults sorted by is_default desc, usage_count desc."""
    async with async_session() as session:
        stmt = select(Dish).where(Dish.user_id == "luis")
        if slot is not None:
            stmt = stmt.where(Dish.slot == slot)
        stmt = stmt.order_by(Dish.is_default.desc(), Dish.usage_count.desc(), Dish.name)
        result = await session.execute(stmt)
        return [_dish_to_response(d) for d in result.scalars().all()]


@router.post("", response_model=DishResponse, status_code=201)
async def create_dish(body: DishCreate, user: str = Depends(get_current_user)):
    async with async_session() as session:
        # Check for exact duplicate (user_id, slot, name)
        existing = await session.execute(
            select(Dish).where(
                Dish.user_id == "luis",
                Dish.slot == body.slot,
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
        if body.is_default is True:
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
    slot: Optional[int] = Query(None, description="Optional slot filter"),
    threshold: float = Query(0.75, description="Similarity threshold 0-1"),
    user: str = Depends(get_current_user),
):
    """Fuzzy-match a dish name against existing dishes to prevent duplicates.

    Returns the best match if similarity >= threshold, otherwise matched=false.
    """
    async with async_session() as session:
        stmt = select(Dish).where(Dish.user_id == "luis")
        if slot is not None:
            stmt = stmt.where(Dish.slot == slot)
        result = await session.execute(stmt)
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