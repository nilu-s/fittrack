"""Private travel planning; coordinates never leave this service for logs or AI."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from fastapi import HTTPException
from sqlalchemy import select

from app.config import settings
from app.models import NativeSession, Todo, TravelWatch
from app.services.native_auth import utcnow

FIX_TTL = timedelta(minutes=15)


def plan_hash(todo: Todo) -> str:
    values = [todo.place_id, str(todo.due_date), str(todo.start_time), todo.travel_mode,
              todo.travel_buffer_minutes, todo.status, todo.deleted, str(todo.space_id), todo.travel_monitoring_enabled]
    return hashlib.sha256(json.dumps(values).encode()).hexdigest()


def appointment(todo: Todo, tz: str = "Europe/Berlin") -> datetime:
    if todo.deleted or todo.space_id or todo.status != "open" or not all((todo.place_id, todo.due_date, todo.start_time, todo.travel_mode)):
        raise HTTPException(422, "Anreise benötigt ein offenes privates To-do mit Ort, Datum, Zeit und Verkehrsmittel.")
    try:
        zone = ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(422, "Ungültige Zeitzone.") from None
    local = datetime.combine(todo.due_date, todo.start_time.replace(tzinfo=None)).replace(tzinfo=zone, fold=0)
    # Nonexistent DST times must never silently move the appointment. Ambiguous
    # fall-back times use the first occurrence (fold=0), visible as ISO offset.
    if local.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) != local.replace(tzinfo=None):
        raise HTTPException(422, "Diese Uhrzeit existiert wegen der Zeitumstellung nicht.")
    return local.astimezone(timezone.utc)


def usable_fix(fix: dict | None, now: datetime) -> bool:
    if not fix:
        return False
    measured = datetime.fromisoformat(fix["measured_at"])
    return timedelta(0) <= now - measured <= FIX_TTL and fix["accuracy"] <= 200


def origin_for(watch: TravelWatch, now: datetime) -> dict | None:
    if watch.live_until and watch.live_until > now and usable_fix(watch.live_fix, now):
        return {"location": {"latLng": {"latitude": watch.live_fix["latitude"], "longitude": watch.live_fix["longitude"]}}}
    return watch.origin


async def estimate(todo: Todo, origin: dict, now: datetime, tz="Europe/Berlin", client=None) -> dict:
    if not settings.GOOGLE_MAPS_API_KEY:
        raise HTTPException(503, "Verkehrsdienst ist nicht eingerichtet.")
    target = appointment(todo, tz) - timedelta(minutes=todo.travel_buffer_minutes)
    if target <= now:
        target = appointment(todo, tz) - timedelta(minutes=todo.travel_buffer_minutes)
    mode = {"drive": "DRIVE", "bicycle": "BICYCLE", "walk": "WALK", "transit": "TRANSIT"}[todo.travel_mode]
    request = {"origin": origin, "destination": {"placeId": todo.place_id}, "travelMode": mode}
    guess = max(now, target - timedelta(seconds=todo.travel_duration_seconds or 1800))
    if mode == "DRIVE":
        request.update(routingPreference="TRAFFIC_AWARE", departureTime=guess.isoformat())
    elif mode == "TRANSIT":
        request["arrivalTime"] = max(target, now).isoformat()
    mask = "routes.duration, routes.legs.steps.transitDetails.stopDetails,routes.legs.steps.staticDuration, fallbackInfo".replace(" ", "") if mode == "TRANSIT" else "routes.duration,fallbackInfo"
    headers = {"X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY, "X-Goog-FieldMask": mask}

    async def compute(http):
        response = await http.post("https://routes.googleapis.com/directions/v2:computeRoutes", headers=headers, json=request)
        if response.status_code != 200:
            raise HTTPException(502, "Routenberechnung ist derzeit nicht verfügbar.")
        data = response.json()
        if not data.get("routes") or data.get("fallbackInfo"):
            raise HTTPException(502, "Keine verlässliche Route verfügbar.")
        return data["routes"][0]

    owned_client = client is None
    http = client or httpx.AsyncClient(timeout=15)
    try:
        route = await compute(http)
        duration = math.ceil(float(route["duration"].removesuffix("s")))
        if not 0 < duration <= 7 * 86400:
            raise ValueError("invalid duration")
        depart = target - timedelta(seconds=duration)
        if mode == "DRIVE" and depart > now and abs((depart - guess).total_seconds()) > 60:
            request["departureTime"] = depart.isoformat()
            route = await compute(http)
            duration = math.ceil(float(route["duration"].removesuffix("s")))
            if not 0 < duration <= 7 * 86400:
                raise ValueError("invalid duration")
            depart = min(depart, target - timedelta(seconds=duration))
        if mode == "TRANSIT":
            # Transit duration alone can hide a long wait before the first
            # vehicle. Derive the actual departure including walking access.
            access_seconds = 0
            found = False
            for leg in route.get("legs", []):
                for step in leg.get("steps", []):
                    stops = step.get("transitDetails", {}).get("stopDetails", {})
                    if stops.get("departureTime"):
                        depart = datetime.fromisoformat(stops["departureTime"].replace("Z", "+00:00")) - timedelta(seconds=access_seconds)
                        found = True
                        break
                    access_seconds += float(step.get("staticDuration", "0s").removesuffix("s"))
                if found:
                    break
            if not found:
                raise HTTPException(502, "Keine aktuelle ÖPNV-Verbindung verfügbar.")
        return {"duration_seconds": duration, "depart_at": depart, "arrival_at": max(now, depart) + timedelta(seconds=duration),
                "checked_at": now, "traffic_aware": mode == "DRIVE"}
    except (httpx.HTTPError, ValueError, KeyError, TypeError, OverflowError):
        raise HTTPException(502, "Routenberechnung ist derzeit nicht erreichbar.") from None
    finally:
        if owned_client:
            await http.aclose()


async def owned_todo(session, todo_id, user):
    todo = await session.scalar(select(Todo).where(Todo.id == todo_id, Todo.account_id == user,
        Todo.space_id.is_(None), Todo.deleted.is_(False)))
    if todo is None:
        raise HTTPException(404, "To-do nicht gefunden.")
    return todo


async def owned_watch(session, todo_id, user, lock=False):
    await owned_todo(session, todo_id, user)
    query = select(TravelWatch).where(TravelWatch.todo_id == todo_id, TravelWatch.account_id == user)
    watch = await session.scalar(query.with_for_update() if lock else query)
    if watch is None:
        raise HTTPException(404, "Keine Anreiseüberwachung eingerichtet.")
    return watch


def stop_watch(watch):
    watch.active = False
    watch.generation += 1
    watch.origin = watch.live_fix = watch.live_until = None
    watch.error = None
    watch.checked_at = watch.depart_at = watch.arrival_at = watch.duration_seconds = None


async def invalidate_watch(session, todo):
    watch = await session.scalar(select(TravelWatch).where(TravelWatch.todo_id == todo.id,
        TravelWatch.account_id == todo.account_id).with_for_update())
    if watch and watch.active and watch.plan_hash != plan_hash(todo):
        stop_watch(watch)


async def watch_response(session, watch, now=None):
    now = now or utcnow()
    device = await session.scalar(select(NativeSession).where(NativeSession.id == watch.device_id,
        NativeSession.account_id == watch.account_id, NativeSession.revoked.is_(False), NativeSession.expires_at > now)) if watch.device_id else None
    active = watch.active and watch.expires_at > now
    live = bool(active and device and watch.live_until and watch.live_until > now)
    fresh = bool(live and usable_fix(watch.live_fix, now))
    return dict(id=watch.id, todo_id=watch.todo_id, active=active, timezone=watch.timezone,
        lead_minutes=watch.lead_minutes, live_active=live, origin_status="live" if fresh else "stale" if live else "fixed" if active else "none",
        location_checked_at=watch.live_fix.get("measured_at") if watch.live_fix and fresh else None,
        checked_at=watch.checked_at, depart_at=watch.depart_at, arrival_at=watch.arrival_at,
        duration_seconds=watch.duration_seconds, expires_at=watch.expires_at, error=watch.error,
        departure_change_minutes=watch.departure_change_minutes, departure_changed_at=watch.departure_changed_at,
        push_available=bool(device and device.push_token and settings.TRAVEL_PUSH_ENABLED),
        starts_at=watch.depart_at - timedelta(minutes=watch.lead_minutes) if watch.depart_at else None)
