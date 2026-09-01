"""Regression contracts for the account-scoped configurable meal API.

These tests deliberately inspect the query given to the persistence layer: a
request-context ownership filter is valuable defense in depth, but routes must
also carry the explicit predicate when invoked by workers or tests.
"""
from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import HTTPException

from app.routes.configurable_meals import _owned, create_photo_analysis
from app.models import MealEntry
from app.routes.sync import sync_changes
from app.schemas import SyncChangeItem, SyncRequest


class _Scalars:
    def first(self):
        return None


class _Result:
    def scalars(self):
        return _Scalars()


class _Context:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *_args):
        pass


class _NoRecordSession:
    def __init__(self):
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return _Result()


class MealAccountIsolationTests(unittest.IsolatedAsyncioTestCase):

    async def test_configurable_entry_photo_rejects_foreign_entry_before_reading_upload(self):
        class Upload:
            filename = "meal.png"
            content_type = "image/png"
            read_called = False

            async def read(self):
                self.read_called = True
                return b"\x89PNG\r\n\x1a\nimage"

        session = _NoRecordSession()
        upload = Upload()
        with patch("app.routes.configurable_meals.async_session", return_value=_Context(session)):
            with self.assertRaises(HTTPException) as error:
                await create_photo_analysis(uuid.uuid4(), upload, account_id=uuid.uuid4())
        self.assertEqual(error.exception.status_code, 404)
        self.assertFalse(upload.read_called)
        self.assertIn("meal_entries.account_id", str(session.statements[0]))

    async def test_configurable_owned_lookup_always_scopes_account(self):
        session = _NoRecordSession()
        with self.assertRaises(HTTPException):
            await _owned(session, MealEntry, uuid.uuid4(), uuid.uuid4())
        self.assertIn("meal_entries.account_id", str(session.statements[0]))

    async def test_retired_meal_sync_changes_remain_visible_as_validation_errors(self):
        session = _NoRecordSession()
        session.commit = self._async_noop
        session.add = lambda _item: self.fail("foreign row must not create a sync log")
        request = SyncRequest(changes=[SyncChangeItem(
            entity_type="meal",
            entity_id=uuid.uuid4(),
            action="delete",
            payload={},
            client_timestamp=datetime.now(timezone.utc),
        )])
        with patch("app.routes.sync.async_session", return_value=_Context(session)):
            response = await sync_changes(request, user=uuid.uuid4())
        self.assertEqual(response.server_changes, [])
        self.assertEqual(session.statements, [])
        self.assertEqual(response.results[0].status, "validation_error")
        self.assertEqual(response.results[0].detail, "Unknown sync entity type")

    async def test_invalid_sync_action_is_a_per_change_validation_error(self):
        session = _NoRecordSession()
        session.commit = self._async_noop
        request = SyncRequest(changes=[SyncChangeItem(
            entity_type="todo",
            entity_id=uuid.uuid4(),
            action="rename",
            payload={},
            client_timestamp=datetime.now(timezone.utc),
        )])
        with patch("app.routes.sync.async_session", return_value=_Context(session)):
            response = await sync_changes(request, user=uuid.uuid4())
        self.assertEqual(response.results[0].status, "validation_error")
        self.assertEqual(response.results[0].detail, "Invalid sync action")
        self.assertEqual(session.statements, [])

    async def _async_noop(self):
        pass


if __name__ == "__main__":
    unittest.main()
