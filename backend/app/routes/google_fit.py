from __future__ import annotations

import logging
from datetime import date as date_type
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

from app.tz import BERLIN_TZ

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

# Google Fit sleep segment types
# https://developers.google.com/fit/scos/read-data/rest/reference/rest/v1/users/me/dataset:aggregate
SLEEP_AWAKE = 1      # Awake (in bed)
SLEEP_LIGHT = 2      # Sleep, light
SLEEP_DEEP = 3       # Sleep, deep
SLEEP_REM = 4        # Sleep, REM


def _day_bounds(day: date_type) -> tuple[datetime, datetime]:
    """Return UTC start/end for the requested date in local timezone (Europe/Berlin)."""
    tz = BERLIN_TZ
    start_local = datetime.combine(day, time.min, tzinfo=tz)
    end_local = datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


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


def _parse_sleep_segments(data: dict) -> dict:
    """Parse Google Fit sleep segments into detailed metrics.

    Returns dict with:
        total_hours, deep_hours, rem_hours, light_hours, awake_hours,
        efficiency (0-100), quality (1-5)
    """
    stage_nanos: dict[int, int] = {SLEEP_AWAKE: 0, SLEEP_LIGHT: 0, SLEEP_DEEP: 0, SLEEP_REM: 0}

    for bucket in data.get("bucket", []):
        for dataset in bucket.get("dataset", []):
            for point in dataset.get("point", []):
                # Google Fit sleep segment value: valValInt = sleep stage type
                stage = None
                for val in point.get("value", []):
                    if "intVal" in val:
                        stage = val["intVal"]
                    elif "mapVal" in val:
                        for mv in val["mapVal"]:
                            if mv.get("key") == "sleepStageType":
                                stage = mv.get("value", {}).get("intVal")
                if stage is None:
                    continue

                start_nanos = int(point.get("startTimeNanos", 0))
                end_nanos = int(point.get("endTimeNanos", 0))
                duration = max(0, end_nanos - start_nanos)

                if stage in stage_nanos:
                    stage_nanos[stage] += duration

    ns_per_hour = 1_000_000_000 * 3600
    deep_h = Decimal(str(round(stage_nanos[SLEEP_DEEP] / ns_per_hour, 2)))
    rem_h = Decimal(str(round(stage_nanos[SLEEP_REM] / ns_per_hour, 2)))
    light_h = Decimal(str(round(stage_nanos[SLEEP_LIGHT] / ns_per_hour, 2)))
    awake_h = Decimal(str(round(stage_nanos[SLEEP_AWAKE] / ns_per_hour, 2)))
    total_h = deep_h + rem_h + light_h  # actual sleep (excluding awake)
    in_bed_h = total_h + awake_h  # total time in bed

    # Efficiency: actual sleep / time in bed * 100
    if in_bed_h > 0:
        efficiency = Decimal(str(round(float(total_h / in_bed_h * 100), 1)))
    else:
        efficiency = Decimal("0")

    # Quality score 1-5 based on efficiency and deep+REM ratio
    # Weighted: 60% efficiency, 40% deep+REM percentage of total sleep
    quality = _calc_sleep_quality(float(efficiency), float(total_h), float(deep_h + rem_h))

    return {
        "total_hours": total_h,
        "deep_hours": deep_h,
        "rem_hours": rem_h,
        "light_hours": light_h,
        "awake_hours": awake_h,
        "efficiency": efficiency,
        "quality": quality,
    }


def _calc_sleep_quality(efficiency: float, total_sleep_h: float, deep_rem_h: float) -> int:
    """Calculate sleep quality score 1-5.

    60% weight on sleep efficiency, 40% on deep+REM ratio.
    """
    if total_sleep_h < 0.1:
        return 0  # no data

    eff_score = min(100, max(0, efficiency))
    deep_rem_ratio = (deep_rem_h / total_sleep_h * 100) if total_sleep_h > 0 else 0
    deep_rem_score = min(100, deep_rem_ratio * 2.5)  # 40% deep+REM → 100

    combined = eff_score * 0.6 + deep_rem_score * 0.4

    if combined >= 85:
        return 5  # excellent
    elif combined >= 70:
        return 4  # good
    elif combined >= 55:
        return 3  # fair
    elif combined >= 40:
        return 2  # poor
    else:
        return 1  # very poor


@router.post("/sync")
async def sync_google_fit(
    date: date_type = Query(..., description="Date to sync in YYYY-MM-DD"),
    user: str = Depends(get_current_user),
):
    async with async_session() as session:
        access_token = await get_valid_access_token(session, user)
        if not access_token:
            raise HTTPException(status_code=400, detail="Google account not connected or token missing")

        start_dt, end_dt = _day_bounds(date)
        start_ms = int(start_dt.timestamp() * 1000)
        end_ms = int(end_dt.timestamp() * 1000)

        steps_data = await _aggregate_fit_data(access_token, DATA_TYPE_STEPS, start_ms, end_ms)
        sleep_data = await _aggregate_fit_data(access_token, DATA_TYPE_SLEEP, start_ms, end_ms)

        steps = _sum_steps(steps_data)
        sleep = _parse_sleep_segments(sleep_data)

        result = await session.execute(
            select(DayEntry).where(DayEntry.user_id == "luis", DayEntry.date == date)
        )
        entry = result.scalars().first()
        if entry is None:
            entry = DayEntry(
                user_id="luis",
                date=date,
                steps=steps,
                sleep_hours=sleep["total_hours"],
                sleep_deep_hours=sleep["deep_hours"],
                sleep_rem_hours=sleep["rem_hours"],
                sleep_light_hours=sleep["light_hours"],
                sleep_awake_hours=sleep["awake_hours"],
                sleep_efficiency=sleep["efficiency"],
                sleep_quality=sleep["quality"],
                steps_done=True,
                steps_confirmed=True,
                steps_source="google_fit",
            )
            session.add(entry)
        else:
            entry.steps = steps
            if sleep["total_hours"] > 0:
                entry.sleep_hours = sleep["total_hours"]
                entry.sleep_deep_hours = sleep["deep_hours"]
                entry.sleep_rem_hours = sleep["rem_hours"]
                entry.sleep_light_hours = sleep["light_hours"]
                entry.sleep_awake_hours = sleep["awake_hours"]
                entry.sleep_efficiency = sleep["efficiency"]
                entry.sleep_quality = sleep["quality"]
            entry.steps_done = True
            entry.steps_confirmed = True
            entry.steps_source = "google_fit"

        await session.commit()
        await session.refresh(entry)

        return {
            "date": str(date),
            "steps": steps,
            "steps_confirmed": True,
            "steps_source": "google_fit",
            "sleep_hours": float(sleep["total_hours"]),
            "sleep_deep_hours": float(sleep["deep_hours"]),
            "sleep_rem_hours": float(sleep["rem_hours"]),
            "sleep_light_hours": float(sleep["light_hours"]),
            "sleep_awake_hours": float(sleep["awake_hours"]),
            "sleep_efficiency": float(sleep["efficiency"]),
            "sleep_quality": sleep["quality"],
        }
