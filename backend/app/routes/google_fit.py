from __future__ import annotations

import logging
from datetime import date as date_type
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.database import async_session
from app.models import DayEntry
from app.routes.auth import get_current_user, get_valid_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/google-fit", tags=["google-fit"])

GOOGLE_FIT_AGGREGATE_URL = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"

DATA_TYPE_STEPS = "com.google.step_count.delta"
DATA_TYPE_SLEEP = "com.google.sleep.segment"
MILLIS_PER_DAY = 24 * 60 * 60 * 1000


def _day_bounds(day: date_type) -> tuple[datetime, datetime]:
    """Return UTC midnight start/end for the requested date."""
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return start, end


def _aggregate_request_body(data_type_name: str, start_time_millis: int, end_time_millis: int) -> dict:
    return {
        "aggregateBy": [{"dataTypeName": data_type_name}],
        "bucketByTime": {"durationMillis": MILLIS_PER_DAY},
        "startTimeMillis": start_time_millis,
        "endTimeMillis": end_time_millis,
    }


async def _aggregate_fit_data(
    access_token: str, data_type_name: str, start_time_millis: int, end_time_millis: int
) -> dict:
    body = _aggregate_request_body(data_type_name, start_time_millis, end_time_millis)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GOOGLE_FIT_AGGREGATE_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=30,
        )
    if resp.status_code != 200:
        logger.error(f"Google Fit aggregate failed for {data_type_name}: {resp.status_code} {resp.text}")
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Google Fit API error ({data_type_name}): {resp.text}",
        )
    return resp.json()


def _sum_steps(data: dict) -> int:
    total = 0
    for bucket in data.get("bucket", []):
        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                for value in point.get("value", []):
                    total += value.get("intVal", 0)
    return total


def _sum_sleep_hours(data: dict) -> Decimal:
    total_nanos = 0
    for bucket in data.get("bucket", []):
        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                start_nanos = int(point.get("startTimeNanos", 0))
                end_nanos = int(point.get("endTimeNanos", 0))
                duration = max(0, end_nanos - start_nanos)
                total_nanos += duration
    hours = total_nanos / (1_000_000_000 * 3600)
    return Decimal(str(round(hours, 2)))


@router.post("/sync")
async def sync_google_fit(
    date: date_type = Query(..., description="Date to sync in YYYY-MM-DD"),
    user: str = Depends(get_current_user),
):
    async with async_session() as session:
        access_token = await get_valid_access_token(session)
        if not access_token:
            raise HTTPException(status_code=400, detail="Google account not connected or token missing")

        start_dt, end_dt = _day_bounds(date)
        start_ms = int(start_dt.timestamp() * 1000)
        end_ms = int(end_dt.timestamp() * 1000)

        steps_data = await _aggregate_fit_data(access_token, DATA_TYPE_STEPS, start_ms, end_ms)
        sleep_data = await _aggregate_fit_data(access_token, DATA_TYPE_SLEEP, start_ms, end_ms)

        steps = _sum_steps(steps_data)
        sleep_hours = _sum_sleep_hours(sleep_data)

        result = await session.execute(
            select(DayEntry).where(DayEntry.user_id == "luis", DayEntry.date == date)
        )
        entry = result.scalars().first()
        if entry is None:
            entry = DayEntry(
                user_id="luis",
                date=date,
                steps=steps,
                sleep_hours=sleep_hours,
                steps_done=True,
                sleep_done=True,
            )
            session.add(entry)
        else:
            entry.steps = steps
            entry.sleep_hours = sleep_hours
            entry.steps_done = True
            entry.sleep_done = True

        await session.commit()
        await session.refresh(entry)

        return {
            "date": str(date),
            "steps": steps,
            "sleep_hours": float(sleep_hours),
            "steps_done": True,
            "sleep_done": True,
        }
