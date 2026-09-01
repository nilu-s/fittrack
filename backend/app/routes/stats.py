from __future__ import annotations

from datetime import date as date_type, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.database import async_session
from app.models import DayEntry, Goal, MealEntry, Todo
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


_MEAL_NUTRIENTS = (
    "kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g", "free_sugar_g",
    "saturated_fat_g", "sodium_mg", "potassium_mg", "calcium_mg", "magnesium_mg",
    "iron_mg", "zinc_mg", "vitamin_a_ug", "vitamin_c_mg", "vitamin_d_ug",
    "vitamin_b12_ug", "folate_ug",
)


async def _meal_totals_by_date(session, account_id, start: date_type, end: date_type) -> dict[date_type, dict[str, Decimal | None]]:
    """Sum consumed configurable-meal snapshots without reviving legacy Meals.

    A null snapshot value remains unknown for that day; it is never silently
    converted to zero.  Planned and skipped entries are not intake data.
    """
    rows = (await session.execute(select(MealEntry).where(
        MealEntry.account_id == account_id,
        MealEntry.date.between(start, end),
        MealEntry.status == "consumed",
    ))).scalars().all()
    totals: dict[date_type, dict[str, Decimal | None]] = {}
    for entry in rows:
        daily = totals.setdefault(entry.date, {key: Decimal("0") for key in _MEAL_NUTRIENTS})
        for key in _MEAL_NUTRIENTS:
            raw = (entry.nutrition_snapshot or {}).get(key)
            if raw is None or daily[key] is None:
                daily[key] = None
            else:
                daily[key] += Decimal(str(raw))
    return totals


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
async def week_summary(
    date: Optional[date_type] = Query(None),
    rolling_days: Optional[int] = Query(None, ge=1, le=365),
    user: str = Depends(get_current_user),
):
    """Calendar-week summary, or a rolling window ending at ``date``."""
    target = date or _berlin_today()
    if rolling_days is not None:
        week_end = target
        week_start = target - timedelta(days=rolling_days - 1)
    else:
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

        # Consumed configurable meal snapshots are the single source of truth.
        meal_totals = await _meal_totals_by_date(session, user, week_start, week_end)
        daily_kcal: list[Decimal] = []
        daily_protein: list[Decimal] = []
        daily_carbs: list[Decimal] = []
        daily_fat: list[Decimal] = []
        daily_fiber: list[Decimal] = []
        daily_sugar: list[Decimal] = []
        daily_free_sugar: list[Decimal] = []
        for total in meal_totals.values():
            if total["kcal"] is not None: daily_kcal.append(total["kcal"])
            if total["protein_g"] is not None: daily_protein.append(total["protein_g"])
            if total["carbs_g"] is not None: daily_carbs.append(total["carbs_g"])
            if total["fat_g"] is not None: daily_fat.append(total["fat_g"])
            if total["fiber_g"] is not None: daily_fiber.append(total["fiber_g"])
            if total["sugar_g"] is not None: daily_sugar.append(total["sugar_g"])
            if total["free_sugar_g"] is not None: daily_free_sugar.append(total["free_sugar_g"])

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
        window_days = rolling_days or 7
        creatine_compliance = Decimal(str(round(creatine_done_days / window_days * 100, 1))) if creatine_done_days else Decimal("0")

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
    end_date: Optional[date_type] = Query(None, description="Inclusive end date; defaults to today in Europe/Berlin"),
    user: str = Depends(get_current_user),
):
    """Trend data as array of {date, value}."""
    end = end_date or _berlin_today()
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
        elif metric in {"kcal", "protein", "carbs", "fat"}:
            nutrient = {"kcal": "kcal", "protein": "protein_g", "carbs": "carbs_g", "fat": "fat_g"}[metric]
            totals = await _meal_totals_by_date(session, user, start, end)
            points = [TrendPoint(date=day, value=values[nutrient]) for day, values in sorted(totals.items()) if values[nutrient] is not None]
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
