"""Pure contract tests for the configurable meals target API.

Database-backed route tests run in deployment CI; these tests keep the most
important ownership-safe command and nutrition invariants executable locally.
"""
import asyncio
from decimal import Decimal
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from fastapi import HTTPException

from app.routes.configurable_meals import _MAX_PHOTO_BYTES, _image_metadata, _sum, _vision_proposal
from app.schemas import MealCategoryRecipePresetUpdate, MealCategoryReorder, MealEntryItemInput, MealPhotoAnalysisAccept, MealEntryStatusCommand, RecipeCreate, RecipeIngredientInput, RecipeUpdate
from app.main import app


class ConfigurableMealsContractTests(unittest.TestCase):
    def test_nutrition_total_is_unknown_when_any_item_is_unknown(self):
        total = _sum([
            {"kcal": Decimal("120"), "protein_g": Decimal("20"), "carbs_g": Decimal("4"), "fat_g": Decimal("2"), "fiber_g": Decimal("1"), "sugar_g": Decimal("2"), "free_sugar_g": Decimal("0")},
            {"kcal": Decimal("50"), "protein_g": None, "carbs_g": Decimal("5"), "fat_g": Decimal("1"), "fiber_g": Decimal("1"), "sugar_g": Decimal("1"), "free_sugar_g": Decimal("0")},
        ])
        self.assertEqual(total["kcal"], Decimal("170"))
        self.assertIsNone(total["protein_g"])

    def test_item_requires_exactly_one_owned_source(self):
        with self.assertRaises(ValidationError):
            MealEntryItemInput(quantity=Decimal("10"), unit="g")
        with self.assertRaises(ValidationError):
            RecipeIngredientInput(food_id="00000000-0000-0000-0000-000000000001", nested_recipe_id="00000000-0000-0000-0000-000000000002", quantity=Decimal("10"))

    def test_recipe_instructions_are_ordered_nonblank_steps(self):
        recipe = RecipeCreate(name="Porridge", instructions=[" Hafer kochen ", "Servieren"])
        self.assertEqual(recipe.instructions, ["Hafer kochen", "Servieren"])
        with self.assertRaises(ValidationError):
            RecipeCreate(name="Porridge", instructions=[" "])
        self.assertIsNone(RecipeUpdate(instructions=None).instructions)

    def test_reorder_rejects_duplicate_resource_ids(self):
        duplicate = "00000000-0000-0000-0000-000000000001"
        with self.assertRaises(ValidationError):
            MealCategoryReorder(ids=[duplicate, duplicate])

    def test_category_recipe_presets_are_limited_to_two_distinct_recipes(self):
        first = "00000000-0000-0000-0000-000000000001"
        second = "00000000-0000-0000-0000-000000000002"
        self.assertEqual([str(value) for value in MealCategoryRecipePresetUpdate(recipe_ids=[first, second]).recipe_ids], [first, second])
        with self.assertRaises(ValidationError):
            MealCategoryRecipePresetUpdate(recipe_ids=[first, first])
        with self.assertRaises(ValidationError):
            MealCategoryRecipePresetUpdate(recipe_ids=[first, second, "00000000-0000-0000-0000-000000000003"])

    def test_photo_accept_requires_user_selected_snapshot_items(self):
        with self.assertRaises(ValidationError):
            MealPhotoAnalysisAccept(items=[])

    def test_entry_status_command_forbids_client_controlled_fields(self):
        with self.assertRaises(ValidationError):
            MealEntryStatusCommand(status="consumed")

    def test_static_reorder_route_precedes_dynamic_category_route(self):
        # FastAPI 0.141 keeps included routers lazy, so OpenAPI is the stable
        # public-route inspection surface.
        paths = app.openapi()["paths"]
        self.assertIn("/api/meal-categories/reorder", paths)
        self.assertIn("put", paths["/api/meal-categories/reorder"])

    def test_category_recipe_presets_are_part_of_the_account_scoped_contract(self):
        paths = app.openapi()["paths"]
        path = "/api/meal-categories/{category_id}/recipe-presets"
        self.assertIn(path, paths)
        self.assertIn("get", paths[path])
        self.assertIn("put", paths[path])

    def test_legacy_meal_and_dish_routes_are_not_public(self):
        paths = app.openapi()["paths"]
        self.assertNotIn("/api/meals", paths)
        self.assertNotIn("/api/dishes", paths)
        self.assertNotIn("/api/meal-templates", paths)

    def test_meal_photo_upload_uses_validated_content_not_filename(self):
        mime_type, extension = _image_metadata(b"\x89PNG\r\n\x1a\nphoto", "image/png")
        self.assertEqual((mime_type, extension), ("image/png", ".png"))

    def test_meal_photo_upload_rejects_invalid_or_mismatched_content(self):
        with self.assertRaises(HTTPException) as malformed:
            _image_metadata(b"not an image", "image/jpeg")
        self.assertEqual(malformed.exception.status_code, 422)
        with self.assertRaises(HTTPException) as mismatched:
            _image_metadata(b"\xff\xd8\xffphoto", "image/png")
        self.assertEqual(mismatched.exception.status_code, 422)
        with self.assertRaises(HTTPException) as oversized:
            _image_metadata(b"\xff\xd8\xff" + b"x" * _MAX_PHOTO_BYTES, "image/jpeg")
        self.assertEqual(oversized.exception.status_code, 413)

    def test_photo_proposal_route_is_multipart_and_explicitly_separate_from_accept(self):
        paths = app.openapi()["paths"]
        path = "/api/meal-entries/{entry_id}/photo-analyses"
        self.assertIn(path, paths)
        self.assertIn("post", paths[path])
        self.assertIn("multipart/form-data", paths[path]["post"]["requestBody"]["content"])
        self.assertIn("/api/meal-entries/{entry_id}/photo-analyses/{analysis_id}/accept", paths)

    def test_plan_history_and_optimistic_entry_status_are_public_contracts(self):
        paths = app.openapi()["paths"]
        self.assertIn("/api/meal-plans/{plan_id}/versions", paths)
        consume_schema = paths["/api/meal-entries/{entry_id}/consume"]["post"]["requestBody"]["content"]["application/json"]["schema"]
        self.assertIn("MealEntryStatusCommand", str(consume_schema))

    def test_unavailable_vision_service_becomes_a_failed_proposal(self):
        class UnavailableClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def post(self, *args, **kwargs):
                import httpx
                raise httpx.ConnectError("offline")

        with patch("app.routes.configurable_meals.httpx.AsyncClient", return_value=UnavailableClient()):
            state, analysis, error_code = asyncio.run(_vision_proposal(b"\xff\xd8\xffphoto"))
        self.assertEqual(state, "failed")
        self.assertIsNone(analysis)
        self.assertEqual(error_code, "vision_unavailable")


if __name__ == "__main__":
    unittest.main()
