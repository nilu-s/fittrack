from __future__ import annotations

from datetime import date as date_type, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.database import async_session
from app.models import DayEntry, Meal, Todo
from app.schemas import TrendPoint, TrendResponse, WeekSummary

router = APIRouter(prefix="/stats", tags=["stats"])

USER_ID = "luis"


@router.get("/week", response_model=WeekSummary)
async def week_summary(date: Optional[date] = Query(None)):
    """Summary for the week containing `date` (defaults to today)."""
    target = date or date.today()
    # Monday of that week
    week_start = target - timedelta(days=target.weekday())
    week_end = week_start + timedelta(days=6)

    async with async_session() as session:
        # Day entries
        de_result = await session.execute(
            select(DayEntry).where(
                DayEntry.user_id == USER_ID,
                DayEntry.date >= week_start,
                DayEntry.date <= week_end,
            )
        )
        entries = list(de_result.scalars().all())

        weights = [e.weight_kg for e in entries if e.weight_kg is not None]
        steps_list = [e.steps for e in entries if e.steps is not None]
        training_days = sum(1 for e in entries if e.training_done)

        # Meals — sum kcal per day then average
        meal_result = await session.execute(
            select(Meal.date, func.sum(Meal.kcal)).where(
                Meal.user_id == USER_ID,
                Meal.date >= week_start,
                Meal.date <= week_end,
            ).group_by(Meal.date)
        )
        daily_kcal = [row[1] for row in meal_result if row[1] is not None]

        # Todos
        todo_result = await session.execute(
            select(Todo).where(
                Todo.user_id == USER_ID,
                Todo.due_date >= week_start,
                Todo.due_date <= week_end,
            )
        )
        todos = list(todo_result.scalars().all())
        todo_total = len(todos)
        todo_done = sum(1 for t in todos if t.status == "done")

        avg_weight = Decimal(sum(weights) / len(weights)) if weights else None
        avg_kcal = Decimal(sum(daily_kcal) / len(daily_kcal)) if daily_kcal else None
        avg_steps = Decimal(sum(steps_list) / len(steps_list)) if steps_list else None

        training_completion = Decimal(str(round(training_days / 7 * 100, 1))) if training_days else Decimal("0")
        todo_completion = Decimal(str(round(todo_done / todo_total * 100, 1))) if todo_total else Decimal("0")

        return WeekSummary(
            week_start=week_start,
            week_end=week_end,
            avg_weight=avg_weight,
            avg_kcal=avg_kcal,
            avg_steps=avg_steps,
            training_days=training_days,
            training_completion=training_completion,
            todo_total=todo_total,
            todo_done=todo_done,
            todo_completion=todo_completion,
        )


@router.get("/trend", response_model=TrendResponse)
async def trend(
    metric: str = Query(..., description="weight | kcal | steps | sleep_hours"),
    days: int = Query(30, ge=1, le=365),
):
    """Trend data as array of {date, value}."""
    end = date.today()
    start = end - timedelta(days=days - 1)

    async with async_session() as session:
        if metric == "weight":
            result = await session.execute(
                select(DayEntry.date, DayEntry.weight_kg).where(
                    DayEntry.user_id == USER_ID,
                    DayEntry.date >= start,
                    DayEntry.date <= end,
                ).order_by(DayEntry.date)
            )
            points = [TrendPoint(date=row[0], value=row[1]) for row in result if row[1] is not None]
        elif metric == "kcal":
            result = await session.execute(
                select(Meal.date, func.sum(Meal.kcal)).where(
                    Meal.user_id == USER_ID,
                    Meal.date >= start,
                    Meal.date <= end,
                ).group_by(Meal.date).order_by(Meal.date)
            )
            points = [TrendPoint(date=row[0], value=row[1]) for row in result if row[1] is not None]
        elif metric == "steps":
            result = await session.execute(
                select(DayEntry.date, DayEntry.steps).where(
                    DayEntry.user_id == USER_ID,
                    DayEntry.date >= start,
                    DayEntry.date <= end,
                ).order_by(DayEntry.date)
            )
            points = [TrendPoint(date=row[0], value=Decimal(row[1]) if row[1] is not None else None) for row in result]
        elif metric == "sleep_hours":
            result = await session.execute(
                select(DayEntry.date, DayEntry.sleep_hours).where(
                    DayEntry.user_id == USER_ID,
                    DayEntry.date >= start,
                    DayEntry.date <= end,
                ).order_by(DayEntry.date)
            )
            points = [TrendPoint(date=row[0], value=row[1]) for row in result if row[1] is not None]
        else:
            return TrendResponse(metric=metric, points=[])

        return TrendResponse(metric=metric, points=points)