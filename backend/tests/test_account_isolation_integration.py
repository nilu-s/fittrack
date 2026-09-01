"""Database-backed regression tests for the browser account boundary.

Run only with the disposable PostgreSQL database created by CI. Unit and
contract tests remain fast and database-free for ordinary local edits.
"""
from __future__ import annotations

import os
import unittest
import uuid

import httpx
from sqlalchemy import delete, select

from app.database import async_session
from app.main import app
from app.models import Account, Todo, TodoRoutine
from app.routes.auth import SESSION_COOKIE_NAME, _create_session_jwt


@unittest.skipUnless(
    os.environ.get("FITTRACK_INTEGRATION_DATABASE") == "1",
    "requires a disposable PostgreSQL integration database",
)
class BrowserAccountIsolationIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.account_a = Account(
            id=uuid.uuid4(), google_subject=f"integration-a-{uuid.uuid4()}",
            email=f"a-{uuid.uuid4()}@example.test", display_name="Account A",
        )
        self.account_b = Account(
            id=uuid.uuid4(), google_subject=f"integration-b-{uuid.uuid4()}",
            email=f"b-{uuid.uuid4()}@example.test", display_name="Account B",
        )
        async with async_session() as session:
            session.add_all([self.account_a, self.account_b])
            await session.commit()

    async def asyncTearDown(self) -> None:
        async with async_session() as session:
            await session.execute(delete(TodoRoutine).where(TodoRoutine.account_id.in_([self.account_a.id, self.account_b.id])))
            await session.execute(delete(Todo).where(Todo.account_id.in_([self.account_a.id, self.account_b.id])))
            await session.execute(delete(Account).where(Account.id.in_([self.account_a.id, self.account_b.id])))
            await session.commit()

    def client_for(self, account: Account) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
            cookies={SESSION_COOKIE_NAME: _create_session_jwt(account)},
        )

    async def test_browser_cannot_read_update_or_delete_another_accounts_todo(self) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as anonymous_client:
            anonymous = await anonymous_client.get("/api/todos")
        self.assertEqual(anonymous.status_code, 401)

        async with self.client_for(self.account_a) as client_a:
            created = await client_a.post("/api/todos", json={"title": "private A todo"})
        self.assertEqual(created.status_code, 201, created.text)
        todo_id = created.json()["id"]

        async with self.client_for(self.account_b) as client_b:
            listed = await client_b.get("/api/todos")
            updated = await client_b.put(f"/api/todos/{todo_id}", json={"title": "stolen"})
            deleted = await client_b.delete(f"/api/todos/{todo_id}")

        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json(), [])
        self.assertEqual(updated.status_code, 404, updated.text)
        self.assertEqual(deleted.status_code, 404, deleted.text)

        async with async_session() as session:
            owner = await session.scalar(select(Todo.account_id).where(Todo.id == uuid.UUID(todo_id)))
        self.assertEqual(owner, self.account_a.id)

    async def test_browser_cannot_read_update_or_delete_another_accounts_todo_routine(self) -> None:
        async with self.client_for(self.account_a) as client_a:
            created = await client_a.post("/api/todo-routines", json={"title": "private A routine", "weekdays": [0, 2]})
        self.assertEqual(created.status_code, 201, created.text)
        routine_id = created.json()["id"]

        async with self.client_for(self.account_b) as client_b:
            listed = await client_b.get("/api/todo-routines")
            updated = await client_b.put(f"/api/todo-routines/{routine_id}", json={"title": "stolen"})
            deleted = await client_b.delete(f"/api/todo-routines/{routine_id}")

        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json(), [])
        self.assertEqual(updated.status_code, 404, updated.text)
        self.assertEqual(deleted.status_code, 404, deleted.text)
