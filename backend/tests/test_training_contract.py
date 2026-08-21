from decimal import Decimal
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from app.models import Exercise
from app.routes.training import _validate_exercise_plan, calculate_progression, create_rotation
from app.seed import _set_count
from app.schemas import TrainingCompleteSetItem, TrainingRotationCreate, TrainingSuggestionExercise
from pydantic import ValidationError


class ProgressionContractTests(unittest.TestCase):
    def test_reps_only_never_changes_weight(self):
        result = calculate_progression(
            strategy="reps_only",
            actual_reps=12,
            actual_rir=2,
            target_reps_low=8,
            target_reps_high=15,
            target_rir=2,
            target_weight_kg=Decimal("40"),
            increment=Decimal("2.5"),
            base_reps_low=8,
            base_reps_high=15,
        )

        self.assertEqual(result.action, "rep_increase")
        self.assertEqual(result.weight_kg, Decimal("40"))
        self.assertEqual(result.reps_low, 13)

    def test_weight_only_never_changes_rep_target(self):
        result = calculate_progression(
            strategy="weight_increase",
            actual_reps=12,
            actual_rir=2,
            target_reps_low=10,
            target_reps_high=12,
            target_rir=2,
            target_weight_kg=Decimal("40"),
            increment=Decimal("2.5"),
            base_reps_low=8,
            base_reps_high=12,
        )

        self.assertEqual(result.action, "weight_increase")
        self.assertEqual(result.weight_kg, Decimal("42.5"))
        self.assertEqual(result.reps_low, 10)

    def test_double_progression_resets_to_base_range_after_weight_increase(self):
        result = calculate_progression(
            strategy="double_progression",
            actual_reps=12,
            actual_rir=2,
            target_reps_low=12,
            target_reps_high=12,
            target_rir=2,
            target_weight_kg=Decimal("40"),
            increment=Decimal("2.5"),
            base_reps_low=8,
            base_reps_high=12,
        )

        self.assertEqual(result.action, "weight_increase")
        self.assertEqual(result.weight_kg, Decimal("42.5"))
        self.assertEqual(result.reps_low, 8)

    def test_set_count_flattens_legacy_formula_to_plain_number(self):
        self.assertEqual(_set_count("1×5-8+2×6-10 Back-off"), 3)
        self.assertEqual(_set_count("3×8-12"), 3)

    def test_exercise_plan_rejects_inconsistent_set_or_rep_configuration(self):
        with self.assertRaises(ValueError):
            _validate_exercise_plan(Exercise(target_sets="0", target_reps_low=8, target_reps_high=12, is_topset=False))
        with self.assertRaises(ValueError):
            _validate_exercise_plan(Exercise(target_sets="3", target_reps_low=8, target_reps_high=12, is_topset=True, top_set_count=2, backoff_set_count=1, backoff_reps_low=8, backoff_reps_high=12, backoff_weight_percent=90))
        with self.assertRaises(ValueError):
            _validate_exercise_plan(Exercise(target_sets="3", target_reps_low=12, target_reps_high=8, is_topset=True, top_set_count=1, backoff_set_count=2, backoff_reps_low=10, backoff_reps_high=8, backoff_weight_percent=90))

    def test_topset_plan_exposes_backoff_configuration(self):
        plan = TrainingSuggestionExercise(
            exercise_name="Bench",
            target_sets="3",
            is_topset=True,
            top_set_count=1,
            backoff_set_count=2,
            backoff_reps_low=6,
            backoff_reps_high=10,
            backoff_weight_percent=Decimal("90"),
        )
        self.assertEqual(plan.top_set_count + plan.backoff_set_count, 3)
        self.assertEqual(plan.backoff_weight_percent, Decimal("90"))

    def test_training_set_rejects_invalid_set_type_and_negative_values(self):
        with self.assertRaises(ValidationError):
            TrainingCompleteSetItem.model_validate({"exercise_name": "Bench", "set_number": 1, "set_type": "invalid"})
        with self.assertRaises(ValidationError):
            TrainingCompleteSetItem.model_validate({"exercise_name": "Bench", "set_number": 0, "reps": -1})


class RotationContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_allows_identical_training_on_same_day(self):
        class Scalars:
            def __init__(self, value):
                self.value = value

            def first(self):
                return self.value

        class Result:
            def __init__(self, value):
                self.value = value

            def scalars(self):
                return Scalars(self.value)

        class Session:
            max_slot = 0

            async def execute(self, statement):
                return Result(object() if self.max_slot else None)

            async def scalar(self, statement):
                return self.max_slot

            def add(self, rotation):
                rotation.id = uuid.uuid4()
                self.max_slot = rotation.slot

            async def commit(self):
                pass

            async def refresh(self, rotation):
                pass

        class Context:
            def __init__(self, session):
                self.session = session

            async def __aenter__(self):
                return self.session

            async def __aexit__(self, *args):
                pass

        body = TrainingRotationCreate(
            slot=0,
            training_type="Push A",
            weekday=4,
            frequency_weeks=1,
            week_offset=0,
            start_date=None,
        )
        session = Session()

        with patch("app.routes.training.async_session", return_value=Context(session)), patch("app.routes.training._require_active_training_unit", new=AsyncMock()):
            first = await create_rotation(body, user="luis")
            second = await create_rotation(body, user="luis")

        self.assertEqual([first.slot, second.slot], [1, 2])


if __name__ == "__main__":
    unittest.main()
