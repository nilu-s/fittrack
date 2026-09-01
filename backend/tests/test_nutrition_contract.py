from decimal import Decimal
import unittest

from app.routes.goals import DEFAULT_GOALS
from app.schemas import Nutrition


class NutritionContractTests(unittest.TestCase):
    def test_default_goals_use_personalized_fiber_and_free_sugar_targets(self):
        self.assertEqual(DEFAULT_GOALS["fiber_g"], Decimal("36"))
        self.assertEqual(DEFAULT_GOALS["free_sugar_g"], Decimal("31"))
        self.assertEqual(DEFAULT_GOALS["free_sugar_limit_g"], Decimal("62"))

    def test_nutrition_contract_keeps_total_and_free_sugars_separate(self):
        nutrition = Nutrition(
            sugar_g=Decimal("18"),
            free_sugar_g=Decimal("6"),
        )

        self.assertEqual(nutrition.sugar_g, Decimal("18"))
        self.assertEqual(nutrition.free_sugar_g, Decimal("6"))

    def test_nutrition_contract_supports_micronutrients_without_inventing_defaults(self):
        nutrition = Nutrition(sodium_mg=Decimal("320"), vitamin_b12_ug=Decimal("1.2"))

        self.assertEqual(nutrition.sodium_mg, Decimal("320"))
        self.assertEqual(nutrition.vitamin_b12_ug, Decimal("1.2"))
        self.assertIsNone(nutrition.calcium_mg)


if __name__ == "__main__":
    unittest.main()
