"""Seed default data for a newly initialized account."""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    DayEntry, Exercise, Food, Goal, MealCategory, MealCategoryRecipePreset,
    MealEntry, MealEntryItem, MealPlan, MealPlanItem, MealPlanVersion, Recipe,
    RecipeIngredient, Todo, TrainingRotation, TrainingUnit,
)
from app.tz import BERLIN_TZ

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

_PRESET_NUTRIENTS = ("kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g", "free_sugar_g")
_PRESET_FOODS = {
    "Haferflocken": ("Getreide", "372", "13", "59", "7", "10", "1", "1"),
    "Skyr natur": ("Milchprodukt", "63", "11", "4", "0.2", "0", "4", "0"),
    "Banane": ("Obst", "89", "1.1", "23", "0.3", "2.6", "12", "0"),
    "Beeren-Mix": ("Obst", "45", "1", "8", "0.3", "4", "5", "0"),
    "Hähnchenbrust": ("Protein", "110", "23", "0", "1.5", "0", "0", "0"),
    "Reis, gekocht": ("Beilage", "130", "2.7", "28", "0.3", "0.4", "0", "0"),
    "Brokkoli": ("Gemüse", "34", "2.8", "7", "0.4", "2.6", "1.7", "0"),
    "Lachs": ("Protein", "208", "20", "0", "13", "0", "0", "0"),
    "Kartoffeln, gekocht": ("Beilage", "77", "2", "17", "0.1", "2.2", "0.8", "0"),
    "Magerquark": ("Milchprodukt", "67", "12", "4", "0.2", "0", "4", "0"),
    "Walnüsse": ("Snack", "654", "15", "14", "65", "7", "2.6", "0"),
}
_PRESET_RECIPES = {
    "Protein-Porridge": [("Haferflocken", "80"), ("Skyr natur", "250"), ("Beeren-Mix", "100"), ("Banane", "120")],
    "Hähnchen-Reis-Bowl": [("Hähnchenbrust", "220"), ("Reis, gekocht", "250"), ("Brokkoli", "200")],
    "Lachs mit Kartoffeln": [("Lachs", "180"), ("Kartoffeln, gekocht", "300"), ("Brokkoli", "180")],
    "Quark mit Walnüssen": [("Magerquark", "250"), ("Beeren-Mix", "100"), ("Walnüsse", "20")],
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


def _preset_snapshot(ingredients: list[tuple[Food, Decimal]]) -> dict[str, str | None]:
    """Create the same immutable, per-entry nutrition shape used by meals."""
    snapshot: dict[str, str | None] = {}
    for nutrient in _PRESET_NUTRIENTS:
        values = [getattr(food, f"{nutrient}_per_100g") for food, _ in ingredients]
        if any(value is None for value in values):
            snapshot[nutrient] = None
        else:
            snapshot[nutrient] = str(sum(
                (value * quantity / Decimal("100") for value, (_, quantity) in zip(values, ingredients)),
                Decimal("0"),
            ))
    return snapshot


async def _seed_development_meals(session: AsyncSession, account_id, anchor: date, start: date, end: date) -> dict[str, int]:
    """Ensure a complete, account-private food → recipe → plan → entry fixture."""
    categories = (await session.execute(select(MealCategory).where(MealCategory.account_id == account_id))).scalars().all()
    by_category = {category.name: category for category in categories}
    for order, name in enumerate(("Frühstück", "Mittagessen", "Abendessen", "Snack")):
        if name not in by_category:
            by_category[name] = MealCategory(account_id=account_id, name=name, sort_order=order)
            session.add(by_category[name])

    foods = (await session.execute(select(Food).where(Food.account_id == account_id))).scalars().all()
    by_food = {food.name: food for food in foods}
    for name, (tag, kcal, protein, carbs, fat, fiber, sugar, free_sugar) in _PRESET_FOODS.items():
        if name not in by_food:
            food = Food(account_id=account_id, name=name, tags=[tag], source="development_preset", confidence="verified",
                        kcal_per_100g=Decimal(kcal), protein_g_per_100g=Decimal(protein), carbs_g_per_100g=Decimal(carbs),
                        fat_g_per_100g=Decimal(fat), fiber_g_per_100g=Decimal(fiber), sugar_g_per_100g=Decimal(sugar),
                        free_sugar_g_per_100g=Decimal(free_sugar))
            by_food[name] = food
            session.add(food)
    await session.flush()

    recipes = (await session.execute(select(Recipe).where(Recipe.account_id == account_id))).scalars().all()
    by_recipe = {recipe.name: recipe for recipe in recipes}
    for name, ingredients in _PRESET_RECIPES.items():
        if name in by_recipe:
            continue
        recipe = Recipe(account_id=account_id, name=name, status="active", servings=Decimal("1"),
                        instructions=["Zutaten vorbereiten.", "Zubereiten und servieren."], nutrition_per_serving={})
        by_recipe[name] = recipe
        session.add(recipe)
        await session.flush()
        for order, (food_name, quantity) in enumerate(ingredients):
            session.add(RecipeIngredient(account_id=account_id, recipe_id=recipe.id, food_id=by_food[food_name].id,
                                         quantity=Decimal(quantity), unit="g", sort_order=order))
    await session.flush()

    shortcuts = (("Frühstück", "Protein-Porridge"), ("Mittagessen", "Hähnchen-Reis-Bowl"),
                 ("Abendessen", "Lachs mit Kartoffeln"), ("Snack", "Quark mit Walnüssen"))
    for category_name, recipe_name in shortcuts:
        exists = await session.scalar(select(MealCategoryRecipePreset.id).where(
            MealCategoryRecipePreset.account_id == account_id,
            MealCategoryRecipePreset.category_id == by_category[category_name].id,
            MealCategoryRecipePreset.recipe_id == by_recipe[recipe_name].id,
        ))
        if not exists:
            session.add(MealCategoryRecipePreset(account_id=account_id, category_id=by_category[category_name].id,
                                                 recipe_id=by_recipe[recipe_name].id, rank=0))

    plan = (await session.execute(select(MealPlan).where(
        MealPlan.account_id == account_id, MealPlan.name == "Chronickel Entwicklungswoche"
    ))).scalars().first()
    if plan is None:
        plan = MealPlan(account_id=account_id, name="Chronickel Entwicklungswoche", version=1, is_active=True)
        session.add(plan)
        await session.flush()
        plan_rows = (("Frühstück", "Protein-Porridge", time(8, 0)), ("Mittagessen", "Hähnchen-Reis-Bowl", time(12, 30)),
                     ("Abendessen", "Lachs mit Kartoffeln", time(19, 0)), ("Snack", "Quark mit Walnüssen", time(15, 30)))
        plan_items = []
        for order, (category_name, recipe_name, planned_time) in enumerate(plan_rows):
            item = MealPlanItem(account_id=account_id, meal_plan_id=plan.id, category_id=by_category[category_name].id,
                                recipe_id=by_recipe[recipe_name].id, planned_time=planned_time, weekdays=None,
                                portion=Decimal("1"), sort_order=order)
            session.add(item)
            plan_items.append(item)
        await session.flush()
        session.add(MealPlanVersion(account_id=account_id, meal_plan_id=plan.id, version=1, name=plan.name,
                                    items_snapshot=[{"category_id": str(item.category_id), "recipe_id": str(item.recipe_id),
                                                     "planned_time": item.planned_time.isoformat(), "weekdays": None,
                                                     "portion": "1", "sort_order": item.sort_order} for item in plan_items]))
    await session.flush()

    old_entries = (await session.execute(select(MealEntry).where(
        MealEntry.account_id == account_id, MealEntry.date.between(start, end),
        or_(MealEntry.source == "development_preset", MealEntry.meal_plan_id == plan.id),
    ))).scalars().all()
    for entry in old_entries:
        await session.delete(entry)
    await session.flush()

    plan_items = (await session.execute(select(MealPlanItem).where(
        MealPlanItem.account_id == account_id, MealPlanItem.meal_plan_id == plan.id, MealPlanItem.is_active.is_(True)
    ).order_by(MealPlanItem.sort_order))).scalars().all()
    recipe_ingredients = {name: [(by_food[food_name], Decimal(quantity)) for food_name, quantity in ingredients]
                          for name, ingredients in _PRESET_RECIPES.items()}
    entries = 0
    for offset in range(-14, 15):
        current = anchor + timedelta(days=offset)
        for item in plan_items:
            recipe = next(recipe for recipe in by_recipe.values() if recipe.id == item.recipe_id)
            ingredients = recipe_ingredients[recipe.name]
            status = "consumed" if offset <= 0 else "planned"
            entry = MealEntry(account_id=account_id, date=current, category_id=item.category_id, name=recipe.name,
                              status=status, consumed_at=datetime.combine(current, item.planned_time, tzinfo=BERLIN_TZ) if status == "consumed" else None,
                              source="development_preset", meal_plan_id=plan.id, meal_plan_item_id=item.id,
                              meal_plan_version=plan.version, nutrition_snapshot=_preset_snapshot(ingredients))
            session.add(entry)
            await session.flush()
            session.add(MealEntryItem(account_id=account_id, meal_entry_id=entry.id, recipe_id=recipe.id,
                                      quantity=Decimal("1"), unit="serving", nutrition_snapshot=_preset_snapshot(ingredients),
                                      source_snapshot={"kind": "recipe", "name": recipe.name, "servings": "1"}))
            entries += 1
    return {"foods": len(_PRESET_FOODS), "recipes": len(_PRESET_RECIPES), "meal_entries": entries}


async def seed_development_preset(session: AsyncSession, account_id, anchor: date | None = None) -> dict[str, int]:
    """Create a repeatable 14-day history and 14-day outlook for one account.

    This is deliberately an explicit development tool. It never runs at
    application startup and only changes the selected account's 29-day range.
    """
    anchor = anchor or date.today()
    start, end = anchor - timedelta(days=14), anchor + timedelta(days=14)
    await seed_default_data(session, account_id)

    existing = (await session.execute(
        select(DayEntry).where(DayEntry.account_id == account_id, DayEntry.date.between(start, end))
    )).scalars().all()
    by_date = {entry.date: entry for entry in existing}
    for offset in range(-14, 15):
        current = anchor + timedelta(days=offset)
        history = max(0, offset + 14)
        entry = by_date.get(current)
        values = {
            "weight_kg": Decimal("96.8") - Decimal(history) * Decimal("0.03"),
            "weight_source": "manual",
            "steps": 7200 + (history * 431) % 5200,
            "steps_confirmed": offset <= 0,
            "steps_source": "manual" if offset <= 0 else None,
            "sleep_hours": Decimal("6.4") + Decimal((history * 3) % 12) / Decimal("10"),
            "sleep_quality": 3 + history % 3,
            "training_type": "Oberkörper A" if current.weekday() in (0, 3) else None,
            "training_done": offset < 0 and current.weekday() in (0, 3),
            "cardio_minutes": 35 if current.weekday() == 2 else None,
            "cardio_done": offset < 0 and current.weekday() == 2,
            "notes": "Entwicklungs-Preset" if current == anchor else None,
        }
        if entry is None:
            session.add(DayEntry(account_id=account_id, date=current, **values))
        else:
            for key, value in values.items():
                setattr(entry, key, value)

    preset_todos = (await session.execute(
        select(Todo).where(Todo.account_id == account_id, Todo.source == "development_preset", Todo.deleted.is_(False))
    )).scalars().all()
    for todo in preset_todos:
        todo.deleted = True

    arrival = datetime.combine(anchor + timedelta(days=1), time(18, 30), tzinfo=BERLIN_TZ)
    session.add_all([
        Todo(account_id=account_id, title="Einkauf planen", due_date=anchor, due_time=time(17, 0), is_all_day=False, priority=2, source="development_preset"),
        Todo(account_id=account_id, title="Termin am Brandenburger Tor", due_date=anchor + timedelta(days=1), start_time=time(18, 30), is_all_day=False, priority=1, source="development_preset", place_id="ChIJAVkDPzdOqEcRcDteW0YgIQQ", place_name="Brandenburger Tor", place_address="Pariser Platz, 10117 Berlin", travel_mode="drive", travel_buffer_minutes=10, travel_monitoring_enabled=True, travel_duration_seconds=1500, travel_depart_at=arrival - timedelta(minutes=35), travel_last_checked_at=datetime.now(BERLIN_TZ)),
        Todo(account_id=account_id, title="Wocheneinkauf", due_date=anchor + timedelta(days=5), due_time=time(10, 0), is_all_day=False, priority=2, source="development_preset"),
        Todo(account_id=account_id, title="Training abschließen", due_date=anchor - timedelta(days=2), due_time=time(18, 0), is_all_day=False, priority=2, status="done", source="development_preset", completed_at=datetime.now(BERLIN_TZ)),
    ])
    meal_summary = await _seed_development_meals(session, account_id, anchor, start, end)
    await session.commit()
    return {"days": 29, "todos": 4, **meal_summary}
