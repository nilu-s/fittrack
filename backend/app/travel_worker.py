"""Run separately: python -m app.travel_worker. No request lifetime dependency."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import delete, select, text

from app.config import settings, validate_runtime_settings
from app.database import async_session
from app.models import NativeLogin, NativeSession, Todo, TravelNotification, TravelWatch
from app.services.native_auth import utcnow
from app.services.travel import estimate, origin_for, plan_hash, stop_watch, usable_fix
from app.services.travel_push import InvalidPushToken, PushUnavailable, send_alert

logger = logging.getLogger(__name__)


def next_check(depart, lead, now):
    starts = depart - timedelta(minutes=lead)
    if starts > now:
        return min(starts, now + timedelta(hours=12))
    return now + timedelta(minutes=2 if depart - now < timedelta(minutes=15) else 5)


async def queue_event(session, watch, kind, now):
    key = kind if kind != "change" else f"change:{watch.sequence}"
    exists = await session.scalar(select(TravelNotification.id).where(
        TravelNotification.watch_id == watch.id, TravelNotification.account_id == watch.account_id,
        TravelNotification.generation == watch.generation, TravelNotification.event_key == key))
    if not exists:
        session.add(TravelNotification(account_id=watch.account_id, watch_id=watch.id,
            generation=watch.generation, event_key=key, kind=kind,
            expires_at=min(now + timedelta(minutes=10), watch.expires_at), next_attempt_at=now))


async def process_watch(session, watch, now, estimator=estimate):
    todo = await session.scalar(select(Todo).where(Todo.id == watch.todo_id, Todo.account_id == watch.account_id))
    device = await session.scalar(select(NativeSession).where(NativeSession.id == watch.device_id,
        NativeSession.account_id == watch.account_id)) if watch.device_id else None
    if not todo or watch.expires_at <= now or plan_hash(todo) != watch.plan_hash or (watch.device_id and (not device or device.protocol_version != 2 or device.platform != "android" or device.revoked or device.expires_at <= now)):
        stop_watch(watch)
        return
    if watch.live_fix and not usable_fix(watch.live_fix, now):
        watch.live_fix = None
    origin = origin_for(watch, now)
    if not origin:
        stop_watch(watch)
        return
    try:
        result = await estimator(todo, origin, now, watch.timezone)
    except HTTPException:
        watch.error = "Verkehrsdaten konnten nicht aktualisiert werden."
        watch.next_check_at = now + timedelta(minutes=5)
        return
    if watch.depart_at and abs((result["depart_at"] - watch.depart_at).total_seconds()) >= 300:
        watch.departure_change_minutes = round((result["depart_at"] - watch.depart_at).total_seconds() / 60)
        watch.departure_changed_at = now
    for name in ("depart_at", "arrival_at", "duration_seconds", "checked_at"):
        setattr(watch, name, result[name])
    watch.error = None
    watch.next_check_at = next_check(watch.depart_at, watch.lead_minutes, now)
    if now < watch.depart_at - timedelta(minutes=watch.lead_minutes):
        return
    if now >= watch.depart_at:
        await queue_event(session, watch, "leave", now)
    elif watch.notified_depart_at is None:
        await queue_event(session, watch, "lead", now)
    elif abs((watch.depart_at - watch.notified_depart_at).total_seconds()) >= 300 and (not watch.notified_at or now - watch.notified_at >= timedelta(minutes=10)):
        watch.sequence += 1
        await queue_event(session, watch, "change", now)
    else:
        return
    watch.notified_depart_at, watch.notified_at = watch.depart_at, now


async def deliver(session, event, now, sender=send_alert):
    watch = await session.scalar(select(TravelWatch).where(TravelWatch.id == event.watch_id,
        TravelWatch.account_id == event.account_id).with_for_update())
    todo = await session.scalar(select(Todo).where(Todo.id == watch.todo_id, Todo.account_id == event.account_id)) if watch else None
    device = await session.scalar(select(NativeSession).where(NativeSession.id == watch.device_id,
        NativeSession.account_id == event.account_id)) if watch else None
    if (event.expires_at <= now or not watch or not watch.active or watch.expires_at <= now or
        event.generation != watch.generation or not todo or plan_hash(todo) != watch.plan_hash or
        not device or device.protocol_version != 2 or device.platform != "android" or device.revoked or device.expires_at <= now or not device.push_token):
        event.discarded = True
        return
    event.attempts += 1
    try:
        await sender(device, event, todo)
        event.sent_at = now
    except InvalidPushToken:
        device.push_token = None
        event.discarded = True
    except Exception:
        # Do not log provider exceptions: they can contain device tokens/URLs.
        event.discarded = event.attempts >= 3
        event.next_attempt_at = now + timedelta(seconds=30 * 2 ** event.attempts)


async def tick():
    # The coordinator holds only an advisory lock. Each job commits separately:
    # one slow provider response cannot lock every household's travel state.
    async with async_session() as coordinator:
        if not await coordinator.scalar(text("SELECT pg_try_advisory_xact_lock(609082026)")):
            return
        now = utcnow()
        async with async_session() as session:
            await session.execute(delete(NativeLogin).where(NativeLogin.expires_at < now))
            cleanup = (await session.scalars(select(TravelWatch).where(
                TravelWatch.expires_at <= now).with_for_update(skip_locked=True))).all()
            for watch in cleanup:
                if watch.active:
                    stop_watch(watch)
                watch.origin = watch.live_fix = watch.live_until = None
                watch.depart_at = watch.arrival_at = watch.checked_at = watch.duration_seconds = None
            fixes = (await session.scalars(select(TravelWatch).where(TravelWatch.live_fix.is_not(None)).with_for_update(skip_locked=True))).all()
            for watch in fixes:
                if not usable_fix(watch.live_fix, now):
                    watch.live_fix = None
            await session.execute(delete(TravelNotification).where(TravelNotification.expires_at < now - timedelta(days=1)))
            await session.commit()
        for _ in range(max(1, min(50, settings.TRAVEL_MAX_CHECKS_PER_TICK))):
            async with async_session() as session:
                watch = await session.scalar(select(TravelWatch).where(TravelWatch.active.is_(True),
                    TravelWatch.next_check_at <= utcnow()).order_by(TravelWatch.next_check_at).limit(1).with_for_update(skip_locked=True))
                if not watch:
                    break
                await process_watch(session, watch, utcnow())
                await session.commit()
        for _ in range(50):
            async with async_session() as session:
                event = await session.scalar(select(TravelNotification).where(TravelNotification.sent_at.is_(None),
                    TravelNotification.discarded.is_(False), TravelNotification.next_attempt_at <= utcnow())
                    .order_by(TravelNotification.next_attempt_at).limit(1).with_for_update(skip_locked=True))
                if not event:
                    break
                await deliver(session, event, utcnow())
                await session.commit()


async def main():
    validate_runtime_settings()
    while True:
        try:
            await tick()
        except Exception:
            logger.error("Travel worker tick failed; pending work will be retried.")
        await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(main())
