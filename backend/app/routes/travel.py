from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select

from app.database import async_session
from app.models import Todo, TravelWatch
from app.routes.auth import get_current_user
from app.services.native_auth import utcnow
from app.services.travel import appointment, owned_todo, owned_watch, plan_hash, stop_watch, watch_response

router = APIRouter(prefix="/travel", tags=["travel"])


class TravelSetup(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    origin_place_id: str | None = Field(default=None, min_length=1, max_length=512)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str = Field(default="Europe/Berlin", max_length=100)
    lead_minutes: int = Field(default=60, ge=15, le=180)

    @model_validator(mode="after")
    def exactly_one_origin(self):
        coordinates = self.latitude is not None and self.longitude is not None
        if bool(self.origin_place_id) == coordinates or ((self.latitude is None) != (self.longitude is None)):
            raise ValueError("Confirm exactly one origin: place or coordinates")
        return self


class LocationFix(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy: float = Field(ge=0, le=200)
    measured_at: datetime


class TravelState(BaseModel):
    id: uuid.UUID
    todo_id: uuid.UUID
    active: bool
    timezone: str
    lead_minutes: int
    live_active: bool
    origin_status: Literal["live", "stale", "fixed", "none"]
    location_checked_at: datetime | None
    checked_at: datetime | None
    depart_at: datetime | None
    arrival_at: datetime | None
    duration_seconds: int | None
    expires_at: datetime
    error: str | None
    push_available: bool
    starts_at: datetime | None
    departure_change_minutes: int | None
    departure_changed_at: datetime | None


@router.get("", response_model=list[TravelState])
async def list_watches(user=Depends(get_current_user)):
    async with async_session() as session:
        watches = (await session.scalars(select(TravelWatch).join(Todo, Todo.id == TravelWatch.todo_id).where(
            TravelWatch.account_id == user, Todo.account_id == user, Todo.deleted.is_(False), Todo.space_id.is_(None),
            TravelWatch.expires_at > utcnow() - timedelta(days=1)))).all()
        return [await watch_response(session, w) for w in watches]


@router.put("/{todo_id}", response_model=TravelState)
async def setup(todo_id: uuid.UUID, body: TravelSetup, request: Request, user=Depends(get_current_user)):
    async with async_session() as session:
        todo = await owned_todo(session, todo_id, user)
        target = appointment(todo, body.timezone)
        if not utcnow() < target <= utcnow() + timedelta(days=30):
            raise HTTPException(422, "Anreisen können für die nächsten 30 Tage überwacht werden.")
        # Serialize creation against another setup for this same private todo.
        await session.execute(select(Todo.id).where(Todo.id == todo.id, Todo.account_id == user).with_for_update())
        watch = await session.scalar(select(TravelWatch).where(TravelWatch.todo_id == todo.id, TravelWatch.account_id == user).with_for_update())
        if watch:
            stop_watch(watch)
        else:
            watch = TravelWatch(account_id=user, todo_id=todo.id)
            session.add(watch)
        todo.travel_monitoring_enabled = True
        watch.active, watch.plan_hash = True, plan_hash(todo)
        watch.device_id = getattr(request.state, "native_session_id", None)
        watch.timezone, watch.lead_minutes = body.timezone, body.lead_minutes
        watch.origin = {"placeId": body.origin_place_id} if body.origin_place_id else {"location": {"latLng": {"latitude": body.latitude, "longitude": body.longitude}}}
        watch.expires_at, watch.next_check_at = target + timedelta(minutes=30), utcnow()
        watch.checked_at = watch.depart_at = watch.arrival_at = watch.duration_seconds = None
        watch.notified_at = watch.notified_depart_at = None
        watch.departure_change_minutes = watch.departure_changed_at = None
        watch.sequence = 0
        await session.commit()
        return await watch_response(session, watch)


@router.post("/{todo_id}/start", response_model=TravelState)
async def start(todo_id: uuid.UUID, request: Request, user=Depends(get_current_user)):
    device_id = getattr(request.state, "native_session_id", None)
    if not device_id:
        raise HTTPException(403, "Live-Begleitung benötigt die iPhone-/Android-App.")
    async with async_session() as session:
        watch = await owned_watch(session, todo_id, user, lock=True)
        todo = await owned_todo(session, todo_id, user)
        now = utcnow()
        if not watch.active or watch.expires_at <= now or watch.plan_hash != plan_hash(todo):
            raise HTTPException(409, "Anreise bitte neu einrichten.")
        if not watch.depart_at or now < watch.depart_at - timedelta(minutes=watch.lead_minutes):
            raise HTTPException(409, "Die Live-Begleitung beginnt im Vorlauf vor der Abfahrt.")
        watch.device_id, watch.live_until, watch.live_fix = device_id, watch.expires_at, None
        watch.next_check_at = now
        await session.commit()
        return await watch_response(session, watch)


@router.post("/{todo_id}/location", status_code=204)
async def location(todo_id: uuid.UUID, body: LocationFix, request: Request, user=Depends(get_current_user)):
    now = utcnow()
    if body.measured_at.tzinfo is None or not timedelta(0) <= now - body.measured_at <= timedelta(minutes=2):
        raise HTTPException(422, "Standort muss eine aktuelle Messzeit mit Zeitzone enthalten.")
    async with async_session() as session:
        watch = await owned_watch(session, todo_id, user, lock=True)
        if not getattr(request.state, "native_session_id", None) or watch.device_id != request.state.native_session_id:
            raise HTTPException(403, "Dieses Gerät begleitet die Anreise nicht.")
        todo = await owned_todo(session, todo_id, user)
        if not watch.active or not watch.live_until or watch.live_until <= now or watch.plan_hash != plan_hash(todo):
            raise HTTPException(409, "Begleitung ist beendet.")
        if watch.live_fix and body.measured_at <= datetime.fromisoformat(watch.live_fix["measured_at"]):
            raise HTTPException(409, "Standort ist älter als die letzte Messung.")
        watch.live_fix = body.model_dump(mode="json")
        # Fresh location can bring the next check forward, but never trigger a
        # billable route for every GPS sample.
        earliest = (watch.checked_at + timedelta(minutes=2)) if watch.checked_at else now
        watch.next_check_at = min(watch.next_check_at, max(now, earliest))
        await session.commit()


@router.post("/{todo_id}/pause", response_model=TravelState)
async def pause(todo_id: uuid.UUID, user=Depends(get_current_user)):
    async with async_session() as session:
        watch = await owned_watch(session, todo_id, user, lock=True)
        watch.live_fix = watch.live_until = None
        watch.checked_at = None
        watch.next_check_at = utcnow()
        await session.commit()
        return await watch_response(session, watch)


@router.delete("/{todo_id}", status_code=204)
async def stop(todo_id: uuid.UUID, user=Depends(get_current_user)):
    async with async_session() as session:
        watch = await owned_watch(session, todo_id, user, lock=True)
        todo = await owned_todo(session, todo_id, user)
        todo.travel_monitoring_enabled = False
        stop_watch(watch)
        await session.commit()
