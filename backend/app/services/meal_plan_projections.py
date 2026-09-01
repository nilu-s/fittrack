"""Lifecycle rules for disposable meal-plan projections."""
from __future__ import annotations

import uuid

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MealEntry, MealPlan


def is_current_plan_projection(
    *, source: str, status: str, entry_plan_id: uuid.UUID | None,
    entry_plan_version: int | None, active_plan_id: uuid.UUID | None,
    active_plan_version: int | None,
) -> bool:
    """Whether an entry is the disposable projection of the current plan."""
    return (
        source == "plan"
        and status == "planned"
        and active_plan_id is not None
        and entry_plan_id == active_plan_id
        and entry_plan_version == active_plan_version
    )


async def discard_stale_plan_projections(session: AsyncSession, account_id: uuid.UUID) -> int:
    """Delete only pending plan projections superseded by the active plan.

    Manual entries and entries explicitly consumed or skipped are historical
    records; this function never changes them.
    """
    active_plan = await session.scalar(select(MealPlan).where(
        MealPlan.account_id == account_id,
        MealPlan.is_active.is_(True),
    ))
    conditions = [
        MealEntry.account_id == account_id,
        MealEntry.source == "plan",
        MealEntry.status == "planned",
    ]
    if active_plan is None:
        statement = delete(MealEntry).where(*conditions)
    else:
        statement = delete(MealEntry).where(*conditions, or_(
            MealEntry.meal_plan_id.is_distinct_from(active_plan.id),
            MealEntry.meal_plan_version.is_distinct_from(active_plan.version),
        ))
    result = await session.execute(statement)
    return result.rowcount or 0
