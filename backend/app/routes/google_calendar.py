from __future__ import annotations

import logging
from datetime import date as date_type
from datetime import datetime, time, timedelta, timezone

from app.tz import BERLIN_TZ
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.database import async_session
from app.models import Todo
from app.routes.auth import get_current_user, get_valid_access_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/google-calendar", tags=["google-calendar"])

GOOGLE_CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


def _day_bounds(day: date_type) -> tuple[datetime, datetime]:
    """Return UTC start/end for the requested date in local timezone (Europe/Berlin)."""
    start_local = datetime.combine(day, time.min, tzinfo=BERLIN_TZ)
    end_local = datetime.combine(day + timedelta(days=1), time.min, tzinfo=BERLIN_TZ)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def _rfc3339_utc(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _naive_time(dt: datetime) -> time:
    """Convert a timezone-aware datetime to a naive Berlin local time for SQLAlchemy Time column."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(BERLIN_TZ)
    return dt.time()


def _parse_event_times(event: dict) -> tuple[date_type, Optional[time], Optional[time], bool]:
    """Extract due_date, start_time, end_time and all-day flag from a Calendar event."""
    start = event.get("start", {})
    end = event.get("end", {})

    if "date" in start:
        # All-day event
        event_date = date_type.fromisoformat(start["date"])
        return event_date, None, None, True

    start_dt = datetime.fromisoformat(start["dateTime"])
    end_dt = datetime.fromisoformat(end["dateTime"])
    event_date = start_dt.date()
    return event_date, _naive_time(start_dt), _naive_time(end_dt), False


@router.post("/sync")
async def sync_google_calendar(
    date: date_type = Query(..., description="Date to sync in YYYY-MM-DD"),
    user: str = Depends(get_current_user),
):
    async with async_session() as session:
        access_token = await get_valid_access_token(session)
        if not access_token:
            raise HTTPException(status_code=400, detail="Google account not connected or token missing")

        start_dt, end_dt = _day_bounds(date)
        params = {
            "timeMin": _rfc3339_utc(start_dt),
            "timeMax": _rfc3339_utc(end_dt),
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": "250",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                GOOGLE_CALENDAR_EVENTS_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
                timeout=30,
            )

        if resp.status_code != 200:
            logger.error(f"Google Calendar events fetch failed: {resp.status_code} {resp.text}")
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"Google Calendar API error: {resp.text}",
            )

        data = resp.json()
        events = data.get("items", [])

        created_count = 0
        updated_count = 0

        for event in events:
            external_id = event.get("id")
            if not external_id:
                continue

            title = event.get("summary") or "Untitled"
            event_date, start_time, end_time, is_all_day = _parse_event_times(event)

            result = await session.execute(
                select(Todo).where(
                    Todo.user_id == "luis",
                    Todo.external_id == external_id,
                    Todo.source == "google_calendar",
                )
            )
            todo = result.scalars().first()

            if todo is not None:
                todo.title = title
                todo.due_date = event_date
                todo.start_time = start_time
                todo.end_time = end_time
                todo.is_all_day = is_all_day
                updated_count += 1
            else:
                todo = Todo(
                    user_id="luis",
                    title=title,
                    category="calendar",
                    due_date=event_date,
                    start_time=start_time,
                    end_time=end_time,
                    is_all_day=is_all_day,
                    source="google_calendar",
                    external_id=external_id,
                )
                session.add(todo)
                created_count += 1

        await session.commit()

        return {
            "date": str(date),
            "created": created_count,
            "updated": updated_count,
            "total_events": len(events),
        }
