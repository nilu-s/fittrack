"""Shopping-list contract, aggregation and ownership regression checks."""
from __future__ import annotations

import unittest
import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from app.main import app
from app.models import ShoppingItem
from app.routes.shopping import _owned
from app.schemas import ShoppingItemCreate, ShoppingMealImportCommand
from app.services.shopping_aggregation import classify_article


class _Scalars:
    def first(self): return None


class _Result:
    def scalars(self): return _Scalars()


class _Session:
    def __init__(self): self.statements = []
    async def execute(self, statement): self.statements.append(statement); return _Result()
    async def scalar(self, statement): self.statements.append(statement); return None


class ShoppingContractTests(unittest.IsolatedAsyncioTestCase):
    def test_public_routes_and_no_legacy_todo_reuse(self):
        paths = app.openapi()["paths"]
        self.assertIn("/api/shopping", paths)
        self.assertIn("/api/shopping/items/{item_id}/toggle", paths)
        self.assertIn("/api/shopping/meal-preview", paths)
        self.assertIn("/api/shopping/meal-import", paths)

    def test_item_schema_rejects_owner_and_invalid_amount(self):
        with self.assertRaises(ValidationError):
            ShoppingItemCreate(title="Milch", account_id=uuid.uuid4())
        with self.assertRaises(ValidationError):
            ShoppingItemCreate(title="Milch", quantity=Decimal("0"))

    def test_import_period_is_bounded_and_ordered(self):
        command = ShoppingMealImportCommand(from_date=date(2026, 9, 2), to_date=date(2026, 9, 15))
        self.assertEqual(command.to_date, date(2026, 9, 15))
        with self.assertRaises(ValidationError):
            ShoppingMealImportCommand(from_date=date(2026, 9, 2), to_date=date(2026, 9, 16))
        with self.assertRaises(ValidationError):
            ShoppingMealImportCommand(from_date=date(2026, 9, 3), to_date=date(2026, 9, 2))

    def test_deterministic_local_category_and_sketch_icon(self):
        self.assertEqual(classify_article("Paprika"), ("produce", "produce"))
        self.assertEqual(classify_article("Haferflocken"), ("pantry", "pantry"))
        self.assertEqual(classify_article("Irgendein Artikel"), ("other", "shopping"))

    async def test_owned_lookup_has_explicit_account_predicate(self):
        session = _Session()
        with self.assertRaises(HTTPException) as error:
            await _owned(session, ShoppingItem, uuid.uuid4(), uuid.uuid4())
        self.assertEqual(error.exception.status_code, 404)
        self.assertIn("shopping_items.account_id", str(session.statements[0]))


if __name__ == "__main__":
    unittest.main()
