"""Seed default data for a newly initialized account."""
from __future__ import annotations

import logging
import re
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Exercise, Goal, TrainingRotation, TrainingUnit

logger = logging.getLogger(__name__)

# Default daily/weekly goals (mirror app/routes/goals.py defaults)
DEFAULT_GOALS = {
    "kcal": Decimal("2480"),
    "protein": Decimal("194"),
    "carbs": Decimal("258"),
    "fat": Decimal("78"),
    "fiber_g": Decimal("36"),
    "free_sugar_g": Decimal("31"),
    "free_sugar_limit_g": Decimal("62"),
    "steps": Decimal("10000"),
    "sleep_hours": Decimal("7"),
    "training_days_per_week": Decimal("4"),
}


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
def _set_count(value: str) -> int:
    counts = [int(count) for count in re.findall(r"(\d+)\s*[×x]", value)]
    return sum(counts) if counts else max(1, int(value))


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


async def seed_default_data(session: AsyncSession, account_id) -> None:
    """Populate optional starter data for exactly one already-authenticated account."""
    # --- Training units ---
    unit_names = sorted({entry[0] for entry in EXERCISES} | {entry[1] for entry in TRAINING_ROTATION} | {"Cardio"})
    cardio_unit_names = {name for _, name, cardio in TRAINING_ROTATION if cardio is not None} | {"Cardio"}
    cardio_unit_names |= {name for name in unit_names if any(term in name.lower() for term in ("cardio", "laufen", "spaziergang", "rad", "bike", "run"))}
    result = await session.execute(select(TrainingUnit).where(TrainingUnit.account_id == account_id))
    existing_units = {unit.name: unit for unit in result.scalars().all()}
    cardio_unit_names |= {name for name in existing_units if any(term in name.lower() for term in ("cardio", "laufen", "spaziergang", "rad", "bike", "run"))}
    cardio_minutes_by_name = {name: max(((cardio or 0) for _, rotation_name, cardio in TRAINING_ROTATION if rotation_name == name), default=0) for name in cardio_unit_names}
    for name in unit_names:
        description = "Cardio-Trainingseinheit" if name in cardio_unit_names else "Gym-Trainingseinheit"
        unit_type = "cardio" if name in cardio_unit_names else "gym"
        duration = cardio_minutes_by_name.get(name) or None
        if name not in existing_units:
            session.add(TrainingUnit(account_id=account_id, name=name, description=description, unit_type=unit_type, cardio_minutes=duration))
        elif name in cardio_unit_names:
            existing_units[name].unit_type = "cardio"
            if existing_units[name].cardio_minutes is None and duration is not None:
                existing_units[name].cardio_minutes = duration
            if existing_units[name].description in (None, "Gym-Trainingseinheit"):
                existing_units[name].description = description
    for name, unit in existing_units.items():
        if name in cardio_unit_names and unit.description in (None, "Gym-Trainingseinheit"):
            unit.description = "Cardio-Trainingseinheit"
    if unit_names:
        logger.info("Ensured %d training units", len(unit_names))

    # --- Training rotation ---
    result = await session.execute(select(TrainingRotation).where(TrainingRotation.account_id == account_id))
    if not result.scalars().first():
        for slot, ttype, cardio in TRAINING_ROTATION:
            session.add(TrainingRotation(
                account_id=account_id, slot=slot, training_type=ttype,
            ))
        logger.info("Seeded %d training rotation entries", len(TRAINING_ROTATION))

    # --- Exercises ---
    result = await session.execute(select(Exercise).where(Exercise.account_id == account_id))
    if not result.scalars().first():
        for entry in EXERCISES:
            (ttype, exname, tsets, rlow, rhigh, base_rlow, base_rhigh, weight, strat, topset, rir, sort, incr) = entry
            session.add(Exercise(
                account_id=account_id, training_type=ttype, exercise_name=exname,
                target_sets=str(_set_count(tsets)), target_reps_low=rlow, target_reps_high=rhigh,
                base_reps_low=base_rlow, base_reps_high=base_rhigh,
                target_weight_kg=weight, progression_strategy=strat,
                progression_increment_weight=incr, is_topset=topset,
                top_set_count=1 if topset else 0,
                backoff_set_count=max(_set_count(tsets) - 1, 0) if topset else 0,
                backoff_reps_low=base_rlow if topset else None,
                backoff_reps_high=base_rhigh if topset else None,
                backoff_weight_percent=Decimal("90") if topset else None,
                target_rir=rir, sort_order=sort,
            ))
        logger.info("Seeded %d exercises", len(EXERCISES))

    # --- Goals ---
    result = await session.execute(select(Goal).where(Goal.account_id == account_id))
    if not result.scalars().first():
        for key, value in DEFAULT_GOALS.items():
            session.add(Goal(
                account_id=account_id, key=key, value=value,
            ))
        logger.info("Seeded %d goals", len(DEFAULT_GOALS))

    await session.commit()
