"""Production defaults must reject the vulnerable native login protocol."""
import os
import unittest
import uuid
from contextlib import ExitStack
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

import httpx
from sqlalchemy import delete

from app.config import settings
from app.database import async_session, engine
from app.main import app
from app.models import Account, AccountWeightRange, GoogleToken, NativeSession, Todo, TravelNotification, TravelWatch
from app.routes.auth import SESSION_COOKIE_NAME, _create_session_jwt, _create_state, _verify_state
from app.services.native_auth import credential_hash, utcnow
from app.travel_worker import deliver, process_watch
from app.services.travel import plan_hash


class NativeAuthContainment(unittest.IsolatedAsyncioTestCase):
    async def test_native_entry_exchange_and_callbacks_reject_before_io(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://testserver") as client:
            with ExitStack() as guards:
                for target in ("app.routes.native.async_session", "app.routes.auth.async_session",
                               "app.services.native_auth.async_session", "app.routes.auth.httpx.AsyncClient"):
                    guards.enter_context(patch(target, side_effect=AssertionError("No database or provider access")))
                requests = [
                    ("POST", "/api/native/login", {"challenge": "a" * 43, "platform": "android"}),
                    ("POST", "/api/native/exchange", {"login_id": str(uuid.uuid4()), "verifier": "a" * 64}),
                    ("GET", "/api/auth/google/login?native_request=" + str(uuid.uuid4()), None),
                    ("GET", "/api/auth/google/login?native_request=malformed", None),
                    ("GET", "/api/google/callback?state=native:synthetic&code=synthetic", None),
                    ("GET", "/api/google/callback?state=" + _create_state(str(uuid.uuid4())) + "&code=synthetic", None),
                    ("GET", "/api/google/callback?state=native:synthetic&error=access_denied", None),
                ]
                for method, url, body in requests:
                    with self.subTest(method=method, path=url.split("?")[0]):
                        response = await client.request(method, url, **({"json": body} if body else {}))
                        self.assertEqual(response.status_code, 503)
                        self.assertEqual(response.headers["cache-control"], "no-store")

    async def test_bearer_rejected_everywhere_without_database_access(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://testserver",
                                     headers={"Authorization": "Bearer crn_synthetic"}) as client:
            with ExitStack() as guards:
                for target in ("app.main.async_session", "app.routes.auth.async_session", "app.services.native_auth.async_session"):
                    guards.enter_context(patch(target, side_effect=AssertionError("No database access")))
                for method, path in (("GET", "/api/todos"), ("GET", "/api/travel"),
                                     ("POST", "/api/native/logout"), ("PUT", "/api/native/push")):
                    with self.subTest(path=path):
                        self.assertEqual((await client.request(method, path)).status_code, 401)
                self.assertFalse((await client.get("/api/auth/me")).json()["authenticated"])
                self.assertEqual((await client.get("/api/health")).status_code, 200)

    async def test_browser_login_still_redirects_to_google(self):
        with patch.object(settings, "GOOGLE_CLIENT_ID", "synthetic-client"):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://testserver") as client:
                response = await client.get("/api/auth/google/login")
        self.assertEqual(response.status_code, 307)
        redirect = urlparse(response.headers["location"])
        self.assertEqual(redirect.hostname, "accounts.google.com")
        state = parse_qs(redirect.query)["state"][0]
        self.assertTrue(_verify_state(state))
        self.assertFalse(state.startswith("native:"))

    async def test_native_watch_stops_before_estimation_and_clears_locations(self):
        todo = Todo(id=uuid.uuid4(), account_id=uuid.uuid4(), title="Synthetic trip", status="open")
        watch = SimpleNamespace(device_id=uuid.uuid4(), active=True, generation=1,
                                origin={"placeId": "synthetic"}, live_fix={"latitude": 52}, live_until=utcnow())
        watch.todo_id, watch.account_id, watch.expires_at, watch.plan_hash = todo.id, todo.account_id, utcnow() + timedelta(hours=1), plan_hash(todo)
        session = SimpleNamespace(scalar=AsyncMock(side_effect=[todo, SimpleNamespace(protocol_version=1)]))
        estimator = AsyncMock(side_effect=AssertionError("No provider call allowed"))
        await process_watch(session, watch, utcnow(), estimator)
        self.assertFalse(watch.active)
        self.assertEqual(watch.generation, 2)
        self.assertIsNone(watch.origin)
        self.assertIsNone(watch.live_fix)
        self.assertIsNone(watch.live_until)
        estimator.assert_not_awaited()

    async def test_queued_push_is_discarded_without_delivery_or_retry(self):
        event = SimpleNamespace(discarded=False, attempts=0, sent_at=None, watch_id=uuid.uuid4(), account_id=uuid.uuid4(), expires_at=utcnow() + timedelta(minutes=1))
        session = SimpleNamespace(scalar=AsyncMock(return_value=None))
        sender = AsyncMock(side_effect=AssertionError("No push allowed"))
        await deliver(session, event, utcnow(), sender)
        self.assertTrue(event.discarded)
        self.assertEqual(event.attempts, 0)
        self.assertIsNone(event.sent_at)
        sender.assert_not_awaited()


@unittest.skipUnless(os.environ.get("APP_INTEGRATION_DATABASE") == "1", "requires disposable PostgreSQL")
class NativeAuthContainmentIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Production defaults deliberately remain disabled in this test class.
        self.account = Account(id=uuid.uuid4(), google_subject=f"containment-{uuid.uuid4()}",
                               email=f"{uuid.uuid4()}@example.test", alias=f"t_{uuid.uuid4().hex[:10]}")
        # Even a v1 row with a new-looking prefix must remain rejected.
        self.credential = "crn2_" + uuid.uuid4().hex
        async with async_session() as session:
            session.add(self.account)
            await session.flush()
            session.add(NativeSession(account_id=self.account.id, credential_hash=credential_hash(self.credential),
                                      platform="android", revoked=False, expires_at=utcnow() + timedelta(days=1)))
            await session.commit()

    async def asyncTearDown(self):
        async with async_session() as session:
            for model in (TravelNotification, TravelWatch, Todo, NativeSession, GoogleToken, AccountWeightRange):
                await session.execute(delete(model).where(model.account_id == self.account.id))
            await session.execute(delete(Account).where(Account.id == self.account.id))
            await session.commit()
        await engine.dispose()

    async def test_browser_watch_with_fixed_origin_still_updates(self):
        from zoneinfo import ZoneInfo
        now = utcnow()
        target = (now + timedelta(hours=2)).astimezone(ZoneInfo("Europe/Berlin"))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://testserver",
                                     cookies={SESSION_COOKIE_NAME: _create_session_jwt(self.account)}) as client:
            created = await client.post("/api/todos", json={
                "title": "Synthetic trip", "due_date": target.date().isoformat(), "start_time": target.strftime("%H:%M:%S"),
                "place_id": "destination", "travel_mode": "drive", "travel_monitoring_enabled": True,
            })
            self.assertEqual(created.status_code, 201)
            response = await client.put(f"/api/travel/{created.json()['id']}", json={"origin_place_id": "origin"})
            self.assertEqual(response.status_code, 200)
        estimator = AsyncMock(return_value=dict(depart_at=now + timedelta(minutes=90),
            arrival_at=now + timedelta(hours=2), duration_seconds=1800, checked_at=now))
        async with async_session() as session:
            watch = await session.get(TravelWatch, uuid.UUID(response.json()["id"]))
            self.assertIsNone(watch.device_id)
            await process_watch(session, watch, now, estimator)
            await session.commit()
            self.assertTrue(watch.active)
            self.assertEqual(watch.checked_at, now)
        estimator.assert_awaited_once()

    async def test_existing_native_credential_is_rejected_while_browser_cookie_works(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://testserver",
                                     cookies={SESSION_COOKIE_NAME: _create_session_jwt(self.account)}) as client:
            self.assertEqual((await client.get("/api/auth/me")).json()["id"], str(self.account.id))
            self.assertEqual((await client.get("/api/todos")).status_code, 200)
            # A rejected bearer must not fall back to a valid browser cookie.
            self.assertEqual((await client.get("/api/todos", headers={"Authorization": f"Bearer {self.credential}"})).status_code, 401)
            client.cookies.clear()
            self.assertEqual((await client.get("/api/travel", headers={"Authorization": f"Bearer {self.credential}"})).status_code, 401)

    async def test_browser_callback_still_creates_a_browser_session(self):
        identity = {"sub": self.account.google_subject, "email": self.account.email, "name": "Synthetic account"}
        transport = httpx.MockTransport(lambda _: httpx.Response(200, json={
            "access_token": "synthetic-access", "id_token": "synthetic-identity", "expires_in": 3600,
        }))
        provider = httpx.AsyncClient(transport=transport)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://testserver") as client:
            with patch.object(settings, "ALLOWED_GOOGLE_EMAILS", self.account.email), \
                 patch("app.routes.auth.google_id_token.verify_oauth2_token", return_value=identity), \
                 patch("app.routes.auth.httpx.AsyncClient", return_value=provider):
                response = await client.get("/api/google/callback", params={"state": _create_state(), "code": "synthetic"})
            self.assertEqual(response.status_code, 302)
            self.assertIn(SESSION_COOKIE_NAME, response.cookies)
            self.assertEqual((await client.get("/api/auth/me")).json()["id"], str(self.account.id))
