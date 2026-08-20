from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.database import async_session
from app.models import Goal
from app.routes.auth import get_current_user
from app.schemas import GoalResponse, GoalUpdate, GoalsBatchUpdate

router = APIRouter(prefix="/goals", tags=["goals"])

USER_ID = "luis"

# Default daily/weekly goals used when no DB row exists yet.
DEFAULT_GOALS: dict[str, Decimal] = {
    "kcal": Decimal("2480"),
    "protein": Decimal("194"),
    "carbs": Decimal("258"),
    "fat": Decimal("78"),
    "steps": Decimal("10000"),
    "sleep_hours": Decimal("7"),
    "training_days_per_week": Decimal("4"),
}


def _to_response(goal: Goal) -> GoalResponse:
    return GoalResponse.model_validate(goal)


async def _get_goal_map(session) -> dict[str, Goal]:
    """Return all persisted goals keyed by goal key."""
    result = await session.execute(select(Goal).where(Goal.user_id == USER_ID))
    return {g.key: g for g in result.scalars().all()}


async def _resolve_goal_value(key: str, session) -> Decimal:
    """Return persisted value for a key, falling back to DEFAULT_GOALS."""
    result = await session.execute(select(Goal).where(Goal.user_id == USER_ID, Goal.key == key))
    goal = result.scalar_one_or_none()
    if goal is not None:
        return goal.value
    return DEFAULT_GOALS.get(key, Decimal("0"))


@router.get("", response_model=dict[str, Decimal])
async def list_goals(user: str = Depends(get_current_user)):
    """Return all goal values (persisted + defaults merged)."""
    async with async_session() as session:
        goals = await _get_goal_map(session)
        merged = {key: DEFAULT_GOALS.get(key, Decimal("0")) for key in DEFAULT_GOALS}
        merged.update({g.key: g.value for g in goals.values()})
        return merged


@router.get("/{key}", response_model=GoalResponse)
async def get_goal(key: str, user: str = Depends(get_current_user)):
    async with async_session() as session:
        result = await session.execute(select(Goal).where(Goal.user_id == USER_ID, Goal.key == key))
        goal = result.scalar_one_or_none()
        if goal is None:
            if key not in DEFAULT_GOALS:
                raise HTTPException(status_code=404, detail="Goal not found")
            # Persist a default row so the API always has a real record.
            goal = Goal(
                user_id=USER_ID,
                key=key,
                value=DEFAULT_GOALS[key],
                effective_from=date_type.today(),
            )
            session.add(goal)
            await session.commit()
            await session.refresh(goal)
        return _to_response(goal)


@router.put("/{key}", response_model=GoalResponse)
async def update_goal(key: str, body: GoalUpdate, user: str = Depends(get_current_user)):
    async with async_session() as session:
        result = await session.execute(select(Goal).where(Goal.user_id == USER_ID, Goal.key == key))
        goal = result.scalar_one_or_none()
        if goal is None:
            goal = Goal(
                user_id=USER_ID,
                key=key,
                value=body.value,
                effective_from=body.effective_from or date_type.today(),
            )
            session.add(goal)
        else:
            goal.value = body.value
            if body.effective_from is not None:
                goal.effective_from = body.effective_from
        await session.commit()
        await session.refresh(goal)
        return _to_response(goal)


@router.post("/batch", response_model=dict[str, Decimal])
async def update_goals_batch(body: GoalsBatchUpdate, user: str = Depends(get_current_user)):
    """Batch update multiple goals at once."""
    async with async_session() as session:
        for key, value in body.goals.items():
            result = await session.execute(select(Goal).where(Goal.user_id == USER_ID, Goal.key == key))
            goal = result.scalar_one_or_none()
            if goal is None:
                goal = Goal(
                    user_id=USER_ID,
                    key=key,
                    value=value,
                    effective_from=date_type.today(),
                )
                session.add(goal)
            else:
                goal.value = value
        await session.commit()

        # Return merged result
        goals = await _get_goal_map(session)
        merged = {key: DEFAULT_GOALS.get(key, Decimal("0")) for key in DEFAULT_GOALS}
        merged.update({g.key: g.value for g in goals.values()})
        return merged
