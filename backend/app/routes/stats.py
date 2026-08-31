from __future__ import annotations

from datetime import date as date_type, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.database import async_session
from app.models import DayEntry, Goal, Meal, Todo
from app.routes.auth import get_current_user
from app.routes.goals import DEFAULT_GOALS, _resolve_goal_value
from app.schemas import TrendPoint, TrendResponse, WeekSummary
from app.tz import BERLIN_TZ

router = APIRouter(prefix="/stats", tags=["stats"])


def _berlin_today() -> date_type:
    """Return today's date in Europe/Berlin."""
    return datetime.now(BERLIN_TZ).date()


def _mean(values: list[Decimal]) -> Optional[Decimal]:
    if not values:
        return None
    return Decimal(str(round(sum(values) / len(values), 2)))


def _sum_int(values: list[Optional[int]]) -> int:
    return sum(v for v in values if v is not None)


def _consecutive_streak(entries: list[DayEntry], predicate) -> int:
    """Count how many consecutive days (ending at the most recent entry) match predicate."""
    sorted_entries = sorted(entries, key=lambda e: e.date, reverse=True)
    streak = 0
    for entry in sorted_entries:
        if predicate(entry):
            streak += 1
        else:
            break
    return streak


@router.get("/week", response_model=WeekSummary)
async def week_summary(date: Optional[date_type] = Query(None), user: str = Depends(get_current_user)):
    """Summary for the week containing `date` (defaults to Berlin today)."""
    target = date or _berlin_today()
    # Monday of that week in Berlin local date
    week_start = target - timedelta(days=target.weekday())
    week_end = week_start + timedelta(days=6)

    async with async_session() as session:
        # Day entries
        de_result = await session.execute(
            select(DayEntry).where(
                DayEntry.account_id == user,
                DayEntry.date >= week_start,
                DayEntry.date <= week_end,
            )
        )
        entries = list(de_result.scalars().all())
        entries_by_date = {e.date: e for e in entries}

        weights = [e.weight_kg for e in entries if e.weight_kg is not None]
        steps_list = [e.steps for e in entries if e.steps is not None]
        sleep_hours_list = [e.sleep_hours for e in entries if e.sleep_hours is not None]
        training_days = sum(1 for e in entries if e.training_done)
        total_cardio_minutes = _sum_int([e.cardio_minutes for e in entries])
        creatine_done_days = sum(1 for e in entries if e.creatine_done)

        # Meals — daily totals (skip soft-deleted)
        meal_result = await session.execute(
            select(Meal.date, func.sum(Meal.kcal), func.sum(Meal.protein_g),
                   func.sum(Meal.carbs_g), func.sum(Meal.fat_g),
                   func.sum(Meal.fiber_g), func.sum(Meal.sugar_g), func.sum(Meal.free_sugar_g))
            .where(
                Meal.account_id == user,
                Meal.date >= week_start,
                Meal.date <= week_end,
                Meal.deleted == False,
            )
            .group_by(Meal.date)
        )
        daily_kcal: list[Decimal] = []
        daily_protein: list[Decimal] = []
        daily_carbs: list[Decimal] = []
        daily_fat: list[Decimal] = []
        daily_fiber: list[Decimal] = []
        daily_sugar: list[Decimal] = []
        daily_free_sugar: list[Decimal] = []
        for row in meal_result:
            if row[1] is not None:
                daily_kcal.append(Decimal(row[1]))
            if row[2] is not None:
                daily_protein.append(Decimal(row[2]))
            if row[3] is not None:
                daily_carbs.append(Decimal(row[3]))
            if row[4] is not None:
                daily_fat.append(Decimal(row[4]))
            if row[5] is not None:
                daily_fiber.append(Decimal(row[5]))
            if row[6] is not None:
                daily_sugar.append(Decimal(row[6]))
            if row[7] is not None:
                daily_free_sugar.append(Decimal(row[7]))

        # Todos (skip soft-deleted)
        todo_result = await session.execute(
            select(Todo).where(
                Todo.account_id == user,
                Todo.due_date >= week_start,
                Todo.due_date <= week_end,
                Todo.deleted == False,
            )
        )
        todos = list(todo_result.scalars().all())
        todo_total = len(todos)
        todo_done = sum(1 for t in todos if t.status == "done")

        # Goals
        step_goal = int((await _resolve_goal_value("steps", session, user)))
        sleep_goal = Decimal((await _resolve_goal_value("sleep_hours", session, user)))
        training_days_goal = int((await _resolve_goal_value("training_days_per_week", session, user)))
        goals = {key: (await _resolve_goal_value(key, session, user)) for key in DEFAULT_GOALS}

        # Streaks (consecutive days ending at week_end)
        training_streak = _consecutive_streak(entries, lambda e: e.training_done)
        step_goal_streak = _consecutive_streak(entries, lambda e: e.steps is not None and e.steps >= step_goal)

        avg_weight = _mean(weights)
        avg_kcal = _mean(daily_kcal)
        avg_protein = _mean(daily_protein)
        avg_carbs = _mean(daily_carbs)
        avg_fat = _mean(daily_fat)
        avg_fiber = _mean(daily_fiber)
        avg_sugar = _mean(daily_sugar)
        avg_free_sugar = _mean(daily_free_sugar)
        avg_steps = _mean([Decimal(s) for s in steps_list]) if steps_list else None
        avg_sleep_hours = _mean(sleep_hours_list)
        sleep_quality_list = [e.sleep_quality for e in entries if e.sleep_quality is not None and e.sleep_quality > 0]
        avg_sleep_quality = _mean([Decimal(sq) for sq in sleep_quality_list]) if sleep_quality_list else None

        training_completion = Decimal(str(round(training_days / training_days_goal * 100, 1))) if training_days_goal else Decimal("0")
        if training_completion > 100:
            training_completion = Decimal("100")
        todo_completion = Decimal(str(round(todo_done / todo_total * 100, 1))) if todo_total else Decimal("0")
        creatine_compliance = Decimal(str(round(creatine_done_days / 7 * 100, 1))) if creatine_done_days else Decimal("0")

        # Macro compliance: compare weekly averages against goals
        def _compliance(actual: Optional[Decimal], target: Any) -> Optional[Decimal]:
            if actual is None or not target or float(target) == 0:
                return None
            return Decimal(str(round(min(float(actual) / float(target) * 100, 100), 1)))

        macro_compliance: Optional[dict[str, Decimal]] = None
        _mc: dict[str, Decimal] = {}
        for key, actual in [("kcal", avg_kcal), ("protein", avg_protein), ("carbs", avg_carbs), ("fat", avg_fat)]:
            goal_val = goals.get(key)
            if goal_val is not None:
                pct = _compliance(actual, goal_val)
                if pct is not None:
                    _mc[key] = pct
        if _mc:
            macro_compliance = _mc

        return WeekSummary(
            week_start=week_start,
            week_end=week_end,
            avg_weight=avg_weight,
            avg_kcal=avg_kcal,
            avg_protein=avg_protein,
            avg_carbs=avg_carbs,
            avg_fat=avg_fat,
            avg_fiber=avg_fiber,
            avg_sugar=avg_sugar,
            avg_free_sugar=avg_free_sugar,
            avg_steps=avg_steps,
            avg_sleep_hours=avg_sleep_hours,
            avg_sleep_quality=avg_sleep_quality,
            total_cardio_minutes=total_cardio_minutes,
            creatine_compliance=creatine_compliance,
            training_days=training_days,
            training_completion=training_completion,
            training_streak=training_streak,
            step_goal_streak=step_goal_streak,
            todo_total=todo_total,
            todo_done=todo_done,
            todo_completion=todo_completion,
            macro_compliance=macro_compliance,
            goals=goals,
        )


@router.get("/trend", response_model=TrendResponse)
async def trend(
    metric: str = Query(..., description="weight | kcal | steps | sleep_hours | protein | carbs | fat"),
    days: int = Query(30, ge=1, le=365),
    user: str = Depends(get_current_user),
):
    """Trend data as array of {date, value}."""
    end = _berlin_today()
    start = end - timedelta(days=days - 1)

    async with async_session() as session:
        if metric == "weight":
            result = await session.execute(
                select(DayEntry.date, DayEntry.weight_kg).where(
                    DayEntry.account_id == user,
                    DayEntry.date >= start,
                    DayEntry.date <= end,
                ).order_by(DayEntry.date)
            )
            points = [TrendPoint(date=row[0], value=row[1]) for row in result if row[1] is not None]
        elif metric == "kcal":
            result = await session.execute(
                select(Meal.date, func.sum(Meal.kcal)).where(
                    Meal.account_id == user,
                    Meal.date >= start,
                    Meal.date <= end,
                    Meal.deleted == False,
                ).group_by(Meal.date).order_by(Meal.date)
            )
            points = [TrendPoint(date=row[0], value=row[1]) for row in result if row[1] is not None]
        elif metric == "protein":
            result = await session.execute(
                select(Meal.date, func.sum(Meal.protein_g)).where(
                    Meal.account_id == user,
                    Meal.date >= start,
                    Meal.date <= end,
                    Meal.deleted == False,
                ).group_by(Meal.date).order_by(Meal.date)
            )
            points = [TrendPoint(date=row[0], value=row[1]) for row in result if row[1] is not None]
        elif metric == "carbs":
            result = await session.execute(
                select(Meal.date, func.sum(Meal.carbs_g)).where(
                    Meal.account_id == user,
                    Meal.date >= start,
                    Meal.date <= end,
                    Meal.deleted == False,
                ).group_by(Meal.date).order_by(Meal.date)
            )
            points = [TrendPoint(date=row[0], value=row[1]) for row in result if row[1] is not None]
        elif metric == "fat":
            result = await session.execute(
                select(Meal.date, func.sum(Meal.fat_g)).where(
                    Meal.account_id == user,
                    Meal.date >= start,
                    Meal.date <= end,
                    Meal.deleted == False,
                ).group_by(Meal.date).order_by(Meal.date)
            )
            points = [TrendPoint(date=row[0], value=row[1]) for row in result if row[1] is not None]
        elif metric == "steps":
            result = await session.execute(
                select(DayEntry.date, DayEntry.steps).where(
                    DayEntry.account_id == user,
                    DayEntry.date >= start,
                    DayEntry.date <= end,
                ).order_by(DayEntry.date)
            )
            points = [TrendPoint(date=row[0], value=Decimal(row[1]) if row[1] is not None else None) for row in result]
        elif metric == "sleep_hours":
            result = await session.execute(
                select(DayEntry.date, DayEntry.sleep_hours).where(
                    DayEntry.account_id == user,
                    DayEntry.date >= start,
                    DayEntry.date <= end,
                ).order_by(DayEntry.date)
            )
            points = [TrendPoint(date=row[0], value=row[1]) for row in result if row[1] is not None]
        else:
            return TrendResponse(metric=metric, points=[])

        return TrendResponse(metric=metric, points=points)
