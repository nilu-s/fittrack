"""Regression contracts for legacy meal endpoints' account boundary.

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

from app.routes.dishes import update_dish
from app.routes.meals import update_meal
from app.routes.photos import analyze_photo
from app.routes.configurable_meals import _owned, create_photo_analysis
from app.models import MealEntry
from app.routes.sync import sync_changes
from app.schemas import DishUpdate, MealUpdate, SyncChangeItem, SyncRequest


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
    async def test_meal_update_queries_id_and_authenticated_account(self):
        session = _NoRecordSession()
        with patch("app.routes.meals.async_session", return_value=_Context(session)):
            with self.assertRaises(HTTPException) as error:
                await update_meal(uuid.uuid4(), MealUpdate(name="forged"), user=uuid.uuid4())
        self.assertEqual(error.exception.status_code, 404)
        self.assertIn("meals.account_id", str(session.statements[0]))

    async def test_dish_update_queries_id_and_authenticated_account(self):
        session = _NoRecordSession()
        with patch("app.routes.dishes.async_session", return_value=_Context(session)):
            with self.assertRaises(HTTPException) as error:
                await update_dish(uuid.uuid4(), DishUpdate(name="forged"), user=uuid.uuid4())
        self.assertEqual(error.exception.status_code, 404)
        self.assertIn("dishes.account_id", str(session.statements[0]))

    async def test_photo_rejects_other_accounts_meal_before_reading_upload(self):
        class Upload:
            filename = "meal.jpg"
            content_type = "image/jpeg"
            read_called = False

            async def read(self):
                self.read_called = True
                return b"image"

        class Session:
            statement = None

            async def scalar(self, statement):
                self.statement = statement
                return None

        upload, session = Upload(), Session()
        with patch("app.routes.photos.async_session", return_value=_Context(session)):
            with self.assertRaises(HTTPException) as error:
                await analyze_photo(upload, meal_id=str(uuid.uuid4()), user=uuid.uuid4())
        self.assertEqual(error.exception.status_code, 404)
        self.assertFalse(upload.read_called)
        self.assertIn("meals.account_id", str(session.statement))

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

    async def test_sync_delete_of_other_accounts_row_is_not_reported_as_applied(self):
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
        self.assertIn("meals.account_id", str(session.statements[0]))

    async def _async_noop(self):
        pass


if __name__ == "__main__":
    unittest.main()
