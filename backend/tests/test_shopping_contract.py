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
from app.routes.shopping import _icon_for_title, _owned
from app.schemas import ShoppingItemCreate, ShoppingMealImportCommand
from app.services.shopping_aggregation import classify_article
from app.services.shopping_icons import category_for_icon, normalize_article_title


class _Scalars:
    def first(self): return None


class _Result:
    def scalars(self): return _Scalars()


class _Session:
    def __init__(self): self.statements = []; self.added = []
    async def execute(self, statement): self.statements.append(statement); return _Result()
    async def scalar(self, statement): self.statements.append(statement); return None
    def add(self, row): self.added.append(row)


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

    def test_deterministic_local_article_icon_catalogue(self):
        self.assertEqual(classify_article("Paprika"), ("produce", "carrot"))
        self.assertEqual(classify_article("Haferflocken"), ("pantry", "canned"))
        self.assertEqual(classify_article("Bio-Hafermilch"), ("dairy", "milk"))
        self.assertEqual(classify_article("Klopapier"), ("household", "toilet-paper"))
        self.assertEqual(classify_article("Zahnpasta"), ("household", "toothpaste"))
        self.assertEqual(classify_article("Lachs"), ("dairy", "fish"))
        self.assertEqual(classify_article("Schokolade"), ("pantry", "chocolate"))
        self.assertEqual(classify_article("Irgendein Artikel"), ("other", "initials"))
        self.assertEqual(normalize_article_title("  Äpfel – bio "), "apfel bio")
        self.assertEqual(category_for_icon("pasta"), "pantry")

    def test_icon_choice_is_a_supported_public_value(self):
        item = ShoppingItemCreate(title="Lieblingspasta", icon_key="pasta")
        self.assertEqual(item.icon_key, "pasta")
        with self.assertRaises(ValidationError):
            ShoppingItemCreate(title="Unbekannt", icon_key="not-an-icon")

    async def test_owned_lookup_has_explicit_account_predicate(self):
        session = _Session()
        with self.assertRaises(HTTPException) as error:
            await _owned(session, ShoppingItem, uuid.uuid4(), uuid.uuid4())
        self.assertEqual(error.exception.status_code, 404)
        self.assertIn("shopping_items.account_id", str(session.statements[0]))

    async def test_learned_icon_lookup_is_explicitly_account_scoped(self):
        session = _Session()
        self.assertEqual(await _icon_for_title(session, uuid.uuid4(), "Hafermilch"), ("dairy", "milk"))
        self.assertIn("shopping_icon_preferences.account_id", str(session.statements[0]))


if __name__ == "__main__":
    unittest.main()
