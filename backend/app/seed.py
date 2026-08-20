"""Seed default data: meal templates, training rotation, exercises, goals."""
from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Dish, Exercise, Goal, MealTemplate, TrainingRotation

logger = logging.getLogger(__name__)

USER_ID = "luis"

# ---------------------------------------------------------------------------
# Meal templates
# Total: 2480 kcal, 194g P, 258g KH, 78g F  → derive KH and F per meal
# ---------------------------------------------------------------------------
# Slot 1: Cheesecake-Bowl       610 kcal, 52g P
# Slot 2: Teriyaki-Tofu-Bowl    790 kcal, 51g P
# Slot 3: Banana-Whey-Cream     280 kcal, 34g P
# Slot 4: Smoky Loaded Potatoes 800 kcal, 57g P
# Totals:                       2480     194g P, 258g KH, 78g F
#
# kcal = 4*P + 4*KH + 9*F  →  KH + F derived: 4*KH + 9*F = kcal - 4*P
# We distribute KH and F proportional to remaining kcal after protein.
# Remaining kcal per meal = kcal - 4*P. Total remaining = 2480 - 4*194 = 2480-776 = 1704
# Total KH kcal = 4*258 = 1032; Total F kcal = 9*78 = 702; sum = 1734 — close to 1704 (rounding)
# We'll just distribute proportionally to the meal's share of total remaining kcal.

MEAL_TEMPLATES = [
    # slot, name, kcal, protein_g
    (1, "Cheesecake-Bowl", Decimal("610"), Decimal("52")),
    (2, "Teriyaki-Tofu-Bowl", Decimal("790"), Decimal("51")),
    (3, "Banana-Whey-Cream", Decimal("280"), Decimal("34")),
    (4, "Smoky Loaded Potatoes", Decimal("800"), Decimal("57")),
]

TOTAL_KCAL = Decimal("2480")
TOTAL_P = Decimal("194")
TOTAL_KH = Decimal("258")
TOTAL_F = Decimal("78")

# Default daily/weekly goals (mirror app/routes/goals.py defaults)
DEFAULT_GOALS = {
    "kcal": Decimal("2480"),
    "protein": Decimal("194"),
    "carbs": Decimal("258"),
    "fat": Decimal("78"),
    "steps": Decimal("10000"),
    "sleep_hours": Decimal("7"),
    "training_days_per_week": Decimal("4"),
}


def _derive_macros(kcal: Decimal, protein: Decimal) -> tuple[Decimal, Decimal]:
    """Derive carbs and fat from kcal and protein, distributing remainder proportionally."""
    protein_kcal = protein * 4
    remainder = kcal - protein_kcal
    total_remainder = TOTAL_KCAL - TOTAL_P * 4  # 2480 - 776 = 1704
    if total_remainder == 0:
        return Decimal("0"), Decimal("0")
    share = remainder / total_remainder
    kh = (TOTAL_KH * share).quantize(Decimal("0.1"))
    fat = (TOTAL_F * share).quantize(Decimal("0.1"))
    return kh, fat


# ---------------------------------------------------------------------------
# Training rotation (7-slot cycle)
# ---------------------------------------------------------------------------
TRAINING_ROTATION = [
    (1, "Oberkörper B", None),
    (2, "Cardio 35-45 min", 40),
    (3, "Unterkörper B", None),
    (4, "Cardio locker/Spaziergang", 30),
    (5, "Oberkörper A", None),
    (6, "Unterkörper A", None),
    (7, "Cardio 35-45 min", 40),
]


# ---------------------------------------------------------------------------
# Exercises  (training_type, exercise_name, target_sets, reps_low, reps_high,
#             base_reps_low, base_reps_high, weight, strategy, is_topset, rir,
#             sort_order, increment)
# ---------------------------------------------------------------------------
EXERCISES = [
    # --- Oberkörper A ---
    ("Oberkörper A", "Bankdrücken oder Smith-Bankdrücken", "1×5-8+2×6-10 Back-off", 5, 10, 5, 10, None, "double_progression", True, 2, 0, Decimal("2.5")),
    ("Oberkörper A", "Brustgestütztes Rudern", "3×6-10", 6, 10, 6, 10, None, "double_progression", False, 2, 1, Decimal("2.5")),
    ("Oberkörper A", "Schrägbank-Maschinen- oder KH-Drücken", "2×8-12", 8, 12, 8, 12, None, "double_progression", False, 2, 2, Decimal("2.5")),
    ("Oberkörper A", "Neutraler Latzug", "3×8-12", 8, 12, 8, 12, None, "double_progression", False, 2, 3, Decimal("2.5")),
    ("Oberkörper A", "Kabel-Seitheben", "3×12-20", 12, 20, 12, 20, None, "double_progression", False, 1, 4, Decimal("1.25")),
    ("Oberkörper A", "Überkopf-Kabel-Trizepsstrecken", "2×10-15", 10, 15, 10, 15, None, "double_progression", False, 1, 5, Decimal("1.25")),
    ("Oberkörper A", "Bayesian-/Incline-Curl", "2×10-15", 10, 15, 10, 15, None, "double_progression", False, 1, 6, Decimal("1.25")),

    # --- Unterkörper A ---
    ("Unterkörper A", "Hack Squat", "1×6-8+2×8-10 Back-off", 6, 10, 6, 10, None, "double_progression", True, 2, 0, Decimal("2.5")),
    ("Unterkörper A", "Romanian Deadlift", "3×6-10", 6, 10, 6, 10, None, "double_progression", False, 2, 1, Decimal("2.5")),
    ("Unterkörper A", "Beinpresse", "2×10-15", 10, 15, 10, 15, None, "double_progression", False, 2, 2, Decimal("2.5")),
    ("Unterkörper A", "Sitzender Beinbeuger", "3×8-15", 8, 15, 8, 15, None, "double_progression", False, 2, 3, Decimal("2.5")),
    ("Unterkörper A", "Stehendes Wadenheben", "3×8-15", 8, 15, 8, 15, None, "double_progression", False, 2, 4, Decimal("2.5")),
    ("Unterkörper A", "Kabel-Crunch / Maschine", "2×10-20", 10, 20, 10, 20, None, "double_progression", False, 2, 5, Decimal("1.25")),

    # --- Oberkörper B ---
    ("Oberkörper B", "Latzug oder assistierter Klimmzug", "1×6-8+2×8-10 Back-off", 6, 10, 6, 10, None, "double_progression", True, 2, 0, Decimal("2.5")),
    ("Oberkörper B", "Brustpresse / Smith-Schrägbank", "3×6-10", 6, 10, 6, 10, None, "double_progression", False, 2, 1, Decimal("2.5")),
    ("Oberkörper B", "Kabel- oder Maschinenrudern", "3×8-12", 8, 12, 8, 12, None, "double_progression", False, 2, 2, Decimal("2.5")),
    ("Oberkörper B", "Maschinen-Schulterdrücken", "2×8-12", 8, 12, 8, 12, None, "double_progression", False, 2, 3, Decimal("2.5")),
    ("Oberkörper B", "Pec Deck / Kabel-Fly", "2×10-15", 10, 15, 10, 15, None, "double_progression", False, 2, 4, Decimal("1.25")),
    ("Oberkörper B", "Kabel-Seitheben", "3×12-20", 12, 20, 12, 20, None, "double_progression", False, 1, 5, Decimal("1.25")),
    ("Oberkörper B", "Curl-Variante", "2×10-15", 10, 15, 10, 15, None, "double_progression", False, 1, 6, Decimal("1.25")),
    ("Oberkörper B", "Trizeps-Pushdown", "2×10-15", 10, 15, 10, 15, None, "double_progression", False, 1, 7, Decimal("1.25")),

    # --- Unterkörper B ---
    ("Unterkörper B", "Beinpresse oder Hack Squat", "1×8-10+2×10-12 Back-off", 8, 12, 8, 12, None, "double_progression", True, 2, 0, Decimal("2.5")),
    ("Unterkörper B", "Hip Thrust / Glute Drive", "2×8-12", 8, 12, 8, 12, None, "double_progression", False, 2, 1, Decimal("2.5")),
    ("Unterkörper B", "Beinstrecker", "2×10-15", 10, 15, 10, 15, None, "double_progression", False, 1, 2, Decimal("1.25")),
    ("Unterkörper B", "Sitzender oder liegender Beinbeuger", "3×10-15", 10, 15, 10, 15, None, "double_progression", False, 1, 3, Decimal("1.25")),
    ("Unterkörper B", "Wadenheben", "3×10-15", 10, 15, 10, 15, None, "double_progression", False, 1, 4, Decimal("1.25")),
    ("Unterkörper B", "Bauch", "2×10-20", 10, 20, 10, 20, None, "double_progression", False, 2, 5, Decimal("1.25")),
]


async def seed_default_data(session: AsyncSession) -> None:
    """Populate meal_templates, training_rotation, exercises, and goals if empty."""
    # --- Meal templates (legacy, kept for backward compat) ---
    result = await session.execute(select(MealTemplate).where(MealTemplate.user_id == USER_ID))
    if not result.scalars().first():
        for slot, name, kcal, protein in MEAL_TEMPLATES:
            kh, fat = _derive_macros(kcal, protein)
            session.add(MealTemplate(
                user_id=USER_ID, slot=slot, name=name,
                kcal=kcal, protein_g=protein, carbs_g=kh, fat_g=fat,
            ))
        logger.info("Seeded %d meal templates", len(MEAL_TEMPLATES))

    # --- Dishes (new: replaces meal_templates as source of truth) ---
    result = await session.execute(select(Dish).where(Dish.user_id == USER_ID))
    if not result.scalars().first():
        for slot, name, kcal, protein in MEAL_TEMPLATES:
            kh, fat = _derive_macros(kcal, protein)
            session.add(Dish(
                user_id=USER_ID, slot=slot, name=name,
                kcal=kcal, protein_g=protein, carbs_g=kh, fat_g=fat,
                is_default=True, source="seed",
            ))
        logger.info("Seeded %d default dishes", len(MEAL_TEMPLATES))

    # --- Training rotation ---
    result = await session.execute(select(TrainingRotation).where(TrainingRotation.user_id == USER_ID))
    if not result.scalars().first():
        for slot, ttype, cardio in TRAINING_ROTATION:
            session.add(TrainingRotation(
                user_id=USER_ID, slot=slot, training_type=ttype, cardio_minutes=cardio,
            ))
        logger.info("Seeded %d training rotation entries", len(TRAINING_ROTATION))

    # --- Exercises ---
    result = await session.execute(select(Exercise).where(Exercise.user_id == USER_ID))
    if not result.scalars().first():
        for entry in EXERCISES:
            (ttype, exname, tsets, rlow, rhigh, base_rlow, base_rhigh, weight, strat, topset, rir, sort, incr) = entry
            session.add(Exercise(
                user_id=USER_ID, training_type=ttype, exercise_name=exname,
                target_sets=tsets, target_reps_low=rlow, target_reps_high=rhigh,
                base_reps_low=base_rlow, base_reps_high=base_rhigh,
                target_weight_kg=weight, progression_strategy=strat,
                progression_increment_weight=incr, is_topset=topset,
                target_rir=rir, sort_order=sort,
            ))
        logger.info("Seeded %d exercises", len(EXERCISES))

    # --- Goals ---
    result = await session.execute(select(Goal).where(Goal.user_id == USER_ID))
    if not result.scalars().first():
        for key, value in DEFAULT_GOALS.items():
            session.add(Goal(
                user_id=USER_ID, key=key, value=value,
            ))
        logger.info("Seeded %d goals", len(DEFAULT_GOALS))

    await session.commit()
