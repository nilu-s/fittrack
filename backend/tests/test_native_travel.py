"""Travel decisions plus real database/account/native-session boundaries."""
import os
import unittest
import uuid
from datetime import date, datetime, time, timedelta, timezone
from unittest.mock import patch
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import delete, select

from app.config import settings
from app.database import async_session, engine
from app.main import app
from app.models import Account, AccountWeightRange, NativeLogin, NativeSession, Todo, TravelNotification, TravelWatch
from app.routes.auth import SESSION_COOKIE_NAME, _create_session_jwt
from app.routes.travel import LocationFix, TravelSetup
from app.services.native_auth import credential_hash, proof_challenge, utcnow
from app.services.google_native_auth import start_login, exchange_google_login
from app.services.travel import appointment, estimate, plan_hash, usable_fix
from app.travel_worker import deliver, next_check, process_watch
from app.services.travel_push import send_alert, InvalidPushToken


def planned_todo(**changes):
    values = dict(id=uuid.uuid4(), account_id=uuid.uuid4(), title="Anreise", due_date=date(2026, 9, 9),
        start_time=time(18), place_id="confirmed-place", travel_mode="drive", travel_buffer_minutes=10,
        travel_monitoring_enabled=True, status="open", deleted=False, space_id=None)
    return Todo(**(values | changes))


def test_client_cannot_choose_identity_or_ambiguous_origin():
    with pytest.raises(ValidationError): TravelSetup(latitude=52, longitude=13, account_id=str(uuid.uuid4()))
    with pytest.raises(ValidationError): TravelSetup(latitude=52)
    with pytest.raises(ValidationError): TravelSetup(latitude=52, longitude=13, origin_place_id="place")
    with pytest.raises(ValidationError): LocationFix(latitude=float("nan"), longitude=13, accuracy=1, measured_at=utcnow())
    with pytest.raises(ValidationError): TravelSetup(origin_place_id="place", lead_minutes=181)


def test_freshness_never_promotes_future_or_stale_fix():
    now = utcnow()
    fix = dict(latitude=52, longitude=13, accuracy=40, measured_at=(now - timedelta(minutes=1)).isoformat())
    assert usable_fix(fix, now)
    assert not usable_fix(fix | {"measured_at": (now - timedelta(minutes=16)).isoformat()}, now)
    assert not usable_fix(fix | {"measured_at": (now + timedelta(seconds=1)).isoformat()}, now)
    assert not usable_fix(fix | {"accuracy": 500}, now)


def test_dst_and_shared_todos_are_explicit():
    with pytest.raises(HTTPException): appointment(planned_todo(due_date=date(2026, 3, 29), start_time=time(2, 30)))
    assert appointment(planned_todo(due_date=date(2026, 10, 25), start_time=time(2, 30))) == datetime(2026, 10, 25, 0, 30, tzinfo=timezone.utc)
    with pytest.raises(HTTPException): appointment(planned_todo(space_id=uuid.uuid4()))
    with pytest.raises(HTTPException): appointment(planned_todo(), "not/a/timezone")


def test_adaptive_window_is_relative_to_departure():
    now = utcnow()
    depart = now + timedelta(hours=4)
    assert next_check(depart, 60, now) == depart - timedelta(hours=1)
    assert next_check(now + timedelta(minutes=40), 60, now) == now + timedelta(minutes=5)
    assert next_check(now + timedelta(minutes=10), 60, now) == now + timedelta(minutes=2)


class RouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_push_contains_only_generic_copy_and_resource_references(self):
        now = utcnow()
        todo = planned_todo(title="Private medical appointment")
        event = SimpleNamespace(id=uuid.uuid4(), watch_id=uuid.uuid4(), kind="change", expires_at=now + timedelta(minutes=5))
        device = SimpleNamespace(platform="android", push_token="synthetic-registration")
        requests = []
        def provider(request):
            import json
            requests.append(json.loads(request.content))
            return httpx.Response(200, json={"name": "synthetic-message"})
        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as client:
            with patch.multiple(settings, TRAVEL_PUSH_ENABLED=True, FCM_PROJECT_ID="test-project", FCM_CREDENTIALS_FILE="unused"), patch("app.services.travel_push.fcm_access_token", return_value="synthetic-token"):
                await send_alert(device, event, todo, client)
        payload = requests[0]["message"]
        assert todo.title not in str(payload)
        assert todo.place_id not in str(payload)
        assert set(payload["data"]) == {"todo_id", "date", "event_id", "expires_at"}
        assert payload["android"]["collapse_key"] == str(event.watch_id)
        assert 0 < int(payload["android"]["ttl"].removesuffix("s")) <= 300

    async def test_unregistered_push_device_is_removed_instead_of_retried(self):
        todo = planned_todo()
        event = SimpleNamespace(id=uuid.uuid4(), watch_id=uuid.uuid4(), kind="leave", expires_at=utcnow() + timedelta(minutes=5))
        device = SimpleNamespace(platform="android", push_token="synthetic-registration")
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(404, json={}))) as client:
            with patch.multiple(settings, TRAVEL_PUSH_ENABLED=True, FCM_PROJECT_ID="test-project", FCM_CREDENTIALS_FILE="unused"), patch("app.services.travel_push.fcm_access_token", return_value="synthetic-token"), self.assertRaises(InvalidPushToken):
                await send_alert(device, event, todo, client)

    async def test_future_driving_uses_future_departure_and_bounds_calls(self):
        now = datetime(2026, 9, 9, 8, tzinfo=timezone.utc)
        requests = []
        def provider(request):
            import json
            requests.append(json.loads(request.content))
            return httpx.Response(200, json={"routes": [{"duration": "2400s"}]})
        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as client:
            with patch.object(settings, "GOOGLE_MAPS_API_KEY", "test-not-a-secret"):
                result = await estimate(planned_todo(), {"placeId": "origin"}, now, client=client)
        assert 1 <= len(requests) <= 2
        assert all(datetime.fromisoformat(r["departureTime"]) > now for r in requests)
        assert result["depart_at"] == datetime(2026, 9, 9, 15, 10, tzinfo=timezone.utc)

    async def test_transit_uses_connection_departure_including_walk(self):
        todo = planned_todo(travel_mode="transit")
        now = datetime(2026, 9, 9, 8, tzinfo=timezone.utc)
        def provider(request):
            import json
            body = json.loads(request.content)
            assert "arrivalTime" in body and "departureTime" not in body
            return httpx.Response(200, json={"routes": [{"duration": "1800s", "legs": [{"steps": [
                {"staticDuration": "300s"}, {"transitDetails": {"stopDetails": {"departureTime": "2026-09-09T15:10:00Z"}}}
            ]}]}]})
        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as client:
            with patch.object(settings, "GOOGLE_MAPS_API_KEY", "test-not-a-secret"):
                result = await estimate(todo, {"placeId": "origin"}, now, client=client)
        assert result["depart_at"] == datetime(2026, 9, 9, 15, 5, tzinfo=timezone.utc)
        assert not result["traffic_aware"]

    async def test_provider_fallback_is_not_advertised_as_live_traffic(self):
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"routes": [{"duration": "1000s"}], "fallbackInfo": {"reason": "test"}}))) as client:
            with patch.object(settings, "GOOGLE_MAPS_API_KEY", "test-not-a-secret"), self.assertRaises(HTTPException):
                await estimate(planned_todo(), {"placeId": "origin"}, utcnow(), client=client)


@unittest.skipUnless(os.environ.get("APP_INTEGRATION_DATABASE") == "1", "requires disposable PostgreSQL")
class NativeTravelIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        gate = patch.object(settings, "GOOGLE_NATIVE_CLIENT_ID", "synthetic-client")
        gate.start()
        self.addCleanup(gate.stop)
        self.ids = [uuid.uuid4(), uuid.uuid4()]
        self.accounts = [Account(id=i, google_subject=f"native-{i}", email=f"{i}@example.test", alias=f"t_{i.hex[:10]}") for i in self.ids]
        async with async_session() as session:
            session.add_all(self.accounts)
            await session.commit()

    async def asyncTearDown(self):
        async with async_session() as session:
            for model in (TravelNotification, TravelWatch, NativeLogin, NativeSession, Todo, AccountWeightRange):
                await session.execute(delete(model).where(model.account_id.in_(self.ids)))
            await session.execute(delete(Account).where(Account.id.in_(self.ids)))
            await session.commit()
        # IsolatedAsyncioTestCase creates a new event loop for every test.
        await engine.dispose()

    def client(self, index=0, token=None):
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://testserver",
            headers={"Authorization": f"Bearer {token}"} if token else {},
            cookies={} if token else {SESSION_COOKIE_NAME: _create_session_jwt(self.accounts[index])})

    async def device(self, index=0):
        verifier = "a" * 64
        login = await start_login(proof_challenge(verifier))
        identity = {"sub": self.accounts[index].google_subject, "email": self.accounts[index].email,
                    "nonce": login["nonce"]}
        with patch("app.services.google_native_auth.verify_identity", return_value=identity):
            return await exchange_google_login(login["login_id"], verifier, "synthetic-token")

    async def setup_watch(self, token=None):
        target = utcnow() + timedelta(hours=2)
        from zoneinfo import ZoneInfo
        local = target.astimezone(ZoneInfo("Europe/Berlin"))
        async with self.client(token=token) as client:
            created = await client.post("/api/todos", json={"title": "Private trip", "due_date": local.date().isoformat(), "start_time": local.strftime("%H:%M:%S"), "place_id": "destination", "travel_mode": "drive", "travel_monitoring_enabled": True})
            assert created.status_code == 201, created.text
            todo_id = created.json()["id"]
            watch = await client.put(f"/api/travel/{todo_id}", json={"origin_place_id": "origin"})
            assert watch.status_code == 200, watch.text
            return todo_id, watch.json()

    async def test_native_isolation_and_logout_revokes_background(self):
        a = await self.device(0); b = await self.device(1)
        todo_id, watch = await self.setup_watch(a["credential"])
        async with self.client(token=b["credential"]) as client:
            assert (await client.get("/api/travel")).json() == []
            for method, suffix in (("POST", "/start"), ("POST", "/pause"), ("DELETE", "")):
                assert (await client.request(method, f"/api/travel/{todo_id}{suffix}")).status_code == 404
        async with self.client(token=a["credential"]) as client:
            assert (await client.get("/api/auth/me")).json()["id"] == str(self.ids[0])
            assert (await client.post("/api/native/logout")).status_code == 204
            assert (await client.get("/api/travel")).status_code == 401
        async with async_session() as session:
            saved = await session.get(TravelWatch, uuid.UUID(watch["id"]))
            assert not saved.active and saved.origin is None and saved.live_fix is None

    async def test_expired_handoff_and_session_are_rejected(self):
        device = await self.device()
        async with async_session() as session:
            saved = await session.get(NativeSession, device["device_id"])
            saved.expires_at = utcnow() - timedelta(seconds=1)
            await session.commit()
        async with self.client(token=device["credential"]) as client:
            assert (await client.get("/api/auth/me")).json()["authenticated"] is False
            assert (await client.get("/api/travel")).status_code == 401

    async def test_outbox_retries_are_bounded_and_expired_events_never_send(self):
        device = await self.device()
        _, info = await self.setup_watch(device["credential"])
        now = utcnow()
        calls = 0
        async def failing_sender(*args):
            nonlocal calls
            calls += 1
            raise RuntimeError("synthetic provider unavailable")
        async with async_session() as session:
            saved = await session.get(NativeSession, device["device_id"])
            saved.push_token = "synthetic-registration"
            watch = await session.get(TravelWatch, uuid.UUID(info["id"]))
            event = TravelNotification(account_id=self.ids[0], watch_id=watch.id,
                generation=watch.generation, event_key="retry-test", kind="lead",
                expires_at=now + timedelta(minutes=10), next_attempt_at=now)
            session.add(event)
            await session.flush()
            for attempt, delay in ((1, 60), (2, 120), (3, 240)):
                await deliver(session, event, now, failing_sender)
                assert event.attempts == attempt
                assert event.next_attempt_at == now + timedelta(seconds=delay)
                assert event.discarded == (attempt == 3)
                now = event.next_attempt_at
            assert calls == 3 and event.sent_at is None
            expired = TravelNotification(account_id=self.ids[0], watch_id=watch.id,
                generation=watch.generation, event_key="expired-test", kind="leave",
                expires_at=now - timedelta(seconds=1), next_attempt_at=now)
            session.add(expired)
            await session.flush()
            await deliver(session, expired, now, failing_sender)
            assert expired.discarded and expired.attempts == 0 and calls == 3

    async def test_worker_deduplicates_then_cancels_changed_todo(self):
        device = await self.device()
        todo_id, info = await self.setup_watch(device["credential"])
        now = utcnow()
        async def provider(todo, origin, at, tz):
            return dict(depart_at=now + timedelta(minutes=30), arrival_at=now + timedelta(minutes=50), duration_seconds=1200, checked_at=at)
        async with async_session() as session:
            watch = await session.get(TravelWatch, uuid.UUID(info["id"]))
            await process_watch(session, watch, now, provider)
            await session.flush()
            await process_watch(session, watch, now + timedelta(minutes=5), provider)
            await session.commit()
            events = (await session.scalars(select(TravelNotification).where(TravelNotification.watch_id == watch.id))).all()
            assert len(events) == 1
        async with self.client(token=device["credential"]) as client:
            response = await client.put(f"/api/todos/{todo_id}", json={"place_id": "new-place"})
            assert response.status_code == 200, response.text
        async def forbidden_sender(*args):
            raise AssertionError("Cancelled event must never reach provider")
        async with async_session() as session:
            event = await session.get(TravelNotification, events[0].id)
            await deliver(session, event, now, forbidden_sender)
            assert event.discarded
            saved = await session.get(TravelWatch, uuid.UUID(info["id"]))
            assert not saved.active and saved.origin is None

    async def test_locations_require_active_selected_device_and_fresh_time(self):
        device = await self.device()
        other = await self.device()
        todo_id, info = await self.setup_watch(device["credential"])
        now = utcnow()
        async with async_session() as session:
            watch = await session.get(TravelWatch, uuid.UUID(info["id"]))
            watch.depart_at = now + timedelta(minutes=30)
            await session.commit()
        fix = dict(latitude=52, longitude=13, accuracy=30, measured_at=(now - timedelta(seconds=1)).isoformat())
        async with self.client(token=device["credential"]) as client:
            assert (await client.post(f"/api/travel/{todo_id}/location", json=fix)).status_code == 409
            assert (await client.post(f"/api/travel/{todo_id}/start")).status_code == 200
            assert (await client.post(f"/api/travel/{todo_id}/location", json=fix)).status_code == 204
            assert (await client.post(f"/api/travel/{todo_id}/location", json=fix)).status_code == 409
            assert (await client.post(f"/api/travel/{todo_id}/location", json=fix | {"measured_at": (now + timedelta(minutes=1)).isoformat()})).status_code == 422
        async with self.client(token=other["credential"]) as client:
            assert (await client.post(f"/api/travel/{todo_id}/location", json=fix)).status_code == 403
