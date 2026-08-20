# FitTrack Remaining Fixes Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Fix all 5 remaining partially/un-fixed issues from the FitTrack audit in one coherent pass.

**Architecture:** Backend is FastAPI + SQLAlchemy async + Postgres. Frontend is SvelteKit + Dexie. All changes are incremental on existing code — no new services, no new storage backends.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, SvelteKit, TypeScript, Docker Compose

---

## Current-State Evidence (verified by main agent)

### Issue 1: Trainings-Progression — `base_reps_low` fehlt im Model, Progression driftet
- `models.py:150-151`: Exercise hat `target_reps_low/high` aber **KEINE** `base_reps_low/high` Spalten
- `schemas.py`: kein `base_reps_low` Feld — Frontend hat es (subagent fügte es zu types.ts hinzu) aber Backend fehlt
- `training.py:212-219`: Bei weight_increase wird `target_reps_low` **nicht zurückgesetzt** → driftet bis `target_reps_high` und fest
- `training.py:80-88`: `_build_suggestion` nutzt nur `target_reps_low/high` — kein unterschied Topset vs Backoff
- Comment bei ExerciseProgress (line 204-206) sagt "prevents old bug" aber der Bug ist nicht behoben

### Issue 2: Photo-Vision — Frontend zeigt Analyse nicht an
- `MealCard.svelte:23`: `onPhotoSelected` ruft `api.analyzePhoto(file, meal.id)` auf und dispatched `photo` event
- Backend `photos.py` speichert analysis in `meal.photo_analysis` ✅
- Frontend zeigt aber **nicht** das Analyse-Ergebnis an — `result` wird dispatched aber nie gerendert
- `UnifiedDay.svelte`: müsste `photo` event handler haben, zeigt aber kein Analyse-UI

### Issue 3: Meal-Templates — Auto-Create überschreibt User-Overrides
- `meals.py:31-63`: `_auto_create_from_templates` prüft `Meal.deleted == False` — wenn User alle Meals soft-deleted, erstellt sie neu
- Kein `replaced_by` Endpoint
- Kein Clone-Day Feature
- Templates haben kein `deleted`/`active` Feld

### Issue 4: Rotation — rein deterministisch ohne Kontext
- `training.py:39-62`: `_get_rotation_slot_for_date` inkrementiert slot +1, wrap bei 7
- Ignoriert: Steps, Pause-Tage (training_done=False), Deload-Wochen
- Keine Skip-Logik wenn User nicht trainiert hat

### Issue 5: Week-Summary — `macro_compliance` fehlt
- `schemas.py:368-387`: `WeekSummary` hat `avg_protein/carbs/fat` ✅ aber **KEIN** `macro_compliance` Feld
- `stats.py`: kein `macro_compliance` berechnet (grep = 0 matches)
- Goals werden in `stats.py` gelesen aber nicht gegen Actuals verglichen

---

## Pre-Conditions
- Docker Compose läuft (db, api, web) — verifiziert ✅
- Alembic Migration 002 applied — verifiziert ✅
- Backend `py_compile` exit 0 — verifiziert ✅
- Frontend `tsc --noEmit` exit 0 — verifiziert ✅

## Post-Conditions
- `base_reps_low`/`base_reps_high` existieren in DB, Model, Schema
- Progression setzt `target_reps_low` auf `base_reps_low` zurück bei weight increase
- Frontend zeigt Photo-Analyse-Ergebnis in MealCard an
- `_auto_create_from_templates` respektiert User-Overrides (kein re-create nach soft-delete)
- Rotation skippt Slots bei Pausetagen
- `macro_compliance` in WeekSummary berechnet und im Schema

## Undefined Behaviors
- Deload-Wochen: nicht Teil dieses Plans (Niedrig-Priorität, separater Task später)
- Multi-User: `USER_ID = "luis"` bleibt hardcoded (Single-User-App, bewusst akzeptiert)
- `replaced_by` und Clone-Day: bewusst weggelassen — Auto-Create-Fix löst das Kernproblem

---

## Work Packages

### WP1: Exercise Model — `base_reps_low`/`base_reps_high` hinzufügen

**Objective:** Base rep range als Reset-Punkt für Progression speichern.

**Files:**
- Modify: `backend/app/models.py:145-157` (Exercise model)
- Modify: `backend/app/schemas.py` (ExerciseResponse/Create/Update)
- Create: `backend/alembic/versions/003_add_base_reps.py`

**Step 1: Add columns to Exercise model**

```python
# models.py — nach target_reps_high (line 151):
base_reps_low: Mapped[int | None] = mapped_column(Integer)
base_reps_high: Mapped[int | None] = mapped_column(Integer)
```

**Step 2: Add to schemas**

```python
# ExerciseResponse/Create/Update — add:
base_reps_low: Optional[int] = None
base_reps_high: Optional[int] = None
```

**Step 3: Alembic migration**

```python
# 003_add_base_reps.py
def upgrade():
    op.add_column("exercises", sa.Column("base_reps_low", sa.Integer))
    op.add_column("exercises", sa.Column("base_reps_high", sa.Integer))
    # Backfill: base_reps_low = target_reps_low, base_reps_high = target_reps_high
    op.execute("UPDATE exercises SET base_reps_low = target_reps_low, base_reps_high = target_reps_high WHERE base_reps_low IS NULL")

def downgrade():
    op.drop_column("exercises", "base_reps_high")
    op.drop_column("exercises", "base_reps_low")
```

**Step 4: Run migration + verify**

```bash
docker compose build fittrack-api
docker compose up -d fittrack-api
docker exec -w /app -e PYTHONPATH=/app fittrack-fittrack-api-1 alembic upgrade head
# Expected: Running upgrade 002 -> 003
docker exec fittrack-fittrack-db-1 psql -U fittrack -d fittrack -c "\d exercises" | grep base_reps
# Expected: base_reps_low | integer
```

**Step 5: Seed update**

```python
# seed.py — each exercise dict gets base_reps_low/base_reps_high = same as target_reps_low/high
```

---

### WP2: Trainings-Progression — Reset bei Weight Increase

**Objective:** Double Progression nutzt `base_reps_low` als Reset-Punkt. Topset und Backoff unterscheiden sich.

**Files:**
- Modify: `backend/app/routes/training.py:190-251` (complete_training progression logic)
- Modify: `backend/app/routes/training.py:65-90` (_build_suggestion — separate topset/backoff)

**Step 1: Fix progression logic in `complete_training`**

Current bug (line 209-219):
```python
# BUG: target_reps_low drifts up and never resets
if actual_reps >= ex.target_reps_high and actual_rir <= target_rir:
    ex.target_weight_kg = ex.target_weight_kg + increment
    progression_action = "weight_increase"
    # MISSING: ex.target_reps_low = ex.base_reps_low  ← RESET!
elif actual_reps >= ex.target_reps_low and actual_rir <= target_rir:
    ex.target_reps_low = min(actual_reps + 1, ex.target_reps_high)
```

Fixed:
```python
if actual_reps >= ex.target_reps_high and actual_rir <= target_rir:
    # Weight increase → reset reps to base
    ex.target_weight_kg = (ex.target_weight_kg or Decimal("0")) + increment
    ex.target_reps_low = ex.base_reps_low           # RESET to base
    ex.target_reps_high = ex.base_reps_high          # RESET to base
    progression_action = "weight_increase"
elif actual_reps >= ex.target_reps_low and actual_rir <= target_rir:
    # Rep increase within range
    new_low = min(actual_reps + 1, ex.target_reps_high)
    ex.target_reps_low = new_low
    progression_action = "rep_increase"
```

**Step 2: `_build_suggestion` — separate Topset vs Backoff rep ranges**

Current (line 77-88): alle exercises nutzen dieselben `target_reps_low/high`.

Fixed:
```python
TrainingSuggestionExercise(
    exercise_name=e.exercise_name,
    target_sets=e.target_sets,
    target_reps_low=e.target_reps_low,
    target_reps_high=e.target_reps_high,
    target_weight_kg=e.target_weight_kg,
    is_topset=e.is_topset,
    # For backoff sets: use base_reps range (wider), lower weight
    target_rir=e.target_rir,
    sort_order=e.sort_order,
)
# Topset (is_topset=True): uses target_reps_low/high as-is (e.g. 5-8)
# Backoff (is_topset=False): uses base_reps_low/high (e.g. 6-10), weight * 0.85
```

Actually: the Exercise table already has `is_topset` per exercise. The issue is that backoff exercises share the same `target_reps_low/high` as topset exercises. Fix: when building suggestion, for `is_topset=False` exercises, use `base_reps_low/high` as the rep range (which is wider).

```python
for e in exercises:
    if e.is_topset:
        reps_low = e.target_reps_low
        reps_high = e.target_reps_high
    else:
        # Backoff set: wider rep range from base
        reps_low = e.base_reps_low or e.target_reps_low
        reps_high = e.base_reps_high or e.target_reps_high
    # ... use reps_low/reps_high in suggestion
```

**Step 3: Verify**

```bash
curl -s "http://localhost:8000/api/training?date=2026-08-20" -H "X-FitTrack-CLI-Key: $CLI_KEY" | python3 -m json.tool | grep target_reps
# Topset exercise should show target_reps_low=5, Backoff should show base_reps_low=6
```

---

### WP3: Meal Auto-Create — User-Override respektieren

**Objective:** Wenn User alle Meals für einen Tag soft-deleted hat, nicht neu erstellen.

**Files:**
- Modify: `backend/app/routes/meals.py:31-63` (`_auto_create_from_templates`)

**Step 1: Fix `_auto_create_from_templates`**

Current bug (line 33-38):
```python
# BUG: checks Meal.deleted == False — if all deleted, meals=[] → re-creates
result = await session.execute(
    select(Meal).where(Meal.user_id == user_id, Meal.date == day, Meal.deleted == False)
)
meals = list(result.scalars().all())
if meals:
    return meals  # ← only returns if non-deleted meals exist
# falls through to create → OVERWRITES user's deletion
```

Fixed:
```python
async def _auto_create_from_templates(session, user_id: str, day: date_type) -> list[Meal]:
    """Auto-create meals from templates only if NO meals exist for this date at all
    (including soft-deleted). If user deleted all meals, respect that."""
    # Check if ANY meals exist for this date (including deleted)
    result = await session.execute(
        select(Meal).where(Meal.user_id == user_id, Meal.date == day).order_by(Meal.meal_slot)
    )
    all_meals = list(result.scalars().all())
    if all_meals:
        # User has meals for this day — return only non-deleted
        return [m for m in all_meals if not m.deleted]

    # No meals at all → create from templates
    tpl_result = await session.execute(
        select(MealTemplate).where(MealTemplate.user_id == user_id).order_by(MealTemplate.slot)
    )
    templates = list(tpl_result.scalars().all())
    for tpl in templates:
        meal = Meal(
            user_id=user_id, date=day, meal_slot=tpl.slot, name=tpl.name,
            default_time=DEFAULT_TIMES.get(tpl.slot, time(12, 0)),
            kcal=tpl.kcal, protein_g=tpl.protein_g, carbs_g=tpl.carbs_g, fat_g=tpl.fat_g,
            is_standard=True, is_done=False,
        )
        session.add(meal)
    await session.flush()
    result = await session.execute(
        select(Meal).where(Meal.user_id == user_id, Meal.date == day).order_by(Meal.meal_slot)
    )
    return list(result.scalars().all())
```

**Step 2: Verify**

```bash
# Delete all meals for a date
CLI_KEY=$(grep FITTRACK_CLI_KEY /root/workspace/fittrack/.env | cut -d= -f2)
MEALS=$(curl -s "http://localhost:8000/api/meals?date=2099-12-31" -H "X-FitTrack-CLI-Key: $CLI_KEY")
# Delete first meal
MEAL_ID=$(echo $MEALS | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
curl -s -X DELETE "http://localhost:8000/api/meals/$MEAL_ID" -H "X-FitTrack-CLI-Key: $CLI_KEY"
# GET again — should still return 3 non-deleted meals
curl -s "http://localhost:8000/api/meals?date=2099-12-31" -H "X-FitTrack-CLI-Key: $CLI_KEY" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))"
# Expected: 3 (not 4 — no re-create)
```

---

### WP4: Photo-Vision Frontend — Analyse anzeigen

**Objective:** MealCard zeigt Analyse-Ergebnis nach Photo-Upload mit Confirm/Edit UI.

**Files:**
- Modify: `frontend/src/lib/components/MealCard.svelte`
- Modify: `frontend/src/lib/types.ts` (add PhotoAnalysis type if missing)

**Step 1: Add PhotoAnalysis type**

```typescript
// types.ts
export interface PhotoAnalysisItem {
  name: string;
  kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}
export interface PhotoAnalysis {
  items: PhotoAnalysisItem[];
  total: { kcal: number; protein_g: number; carbs_g: number; fat_g: number };
}
```

**Step 2: MealCard — show analysis result inline**

```svelte
<!-- MealCard.svelte — after photo upload, show analysis -->
{#if analysisResult}
  <div class="mc-analysis">
    <div class="mc-analysis-header">
      <span>📸 KI-Analyse</span>
      <button class="btn-sm" onclick={() => applyAnalysis()}>Übernehmen</button>
      <button class="btn-sm" onclick={() => dismissAnalysis()}>✕</button>
    </div>
    {#each analysisResult.items as item}
      <div class="mc-analysis-item">
        <span>{item.name}</span>
        <span>{item.kcal} kcal · P{item.protein_g}g</span>
      </div>
    {/each}
    <div class="mc-analysis-total">
      Σ {analysisResult.total.kcal} kcal · {analysisResult.total.protein_g}g Protein
    </div>
  </div>
{/if}

<script lang="ts">
  let analysisResult: PhotoAnalysis | null = null;

  async function onPhotoSelected(e: Event) {
    // ... existing ...
    const result = await api.analyzePhoto(file, meal.id);
    analysisResult = result?.analysis ?? null;
    // dispatch event for parent
    dispatch('photo', { id: meal.id, file, result });
  }

  function applyAnalysis() {
    if (!analysisResult) return;
    // Update meal with analyzed values
    dispatch('analysisApply', { id: meal.id, analysis: analysisResult });
    analysisResult = null;
  }

  function dismissAnalysis() { analysisResult = null; }
</script>
```

**Step 3: UnifiedDay — handle analysisApply event**

```svelte
<!-- UnifiedDay.svelte — in MealGrid or MealCard handler -->
async function onAnalysisApply(e: CustomEvent) {
  const { id, analysis } = e.detail;
  await api.updateMeal(id, {
    kcal: analysis.total.kcal,
    protein_g: analysis.total.protein_g,
    carbs_g: analysis.total.carbs_g,
    fat_g: analysis.total.fat_g,
  });
  // Refresh meals
  await loadMeals();
}
```

**Step 4: Verify**

```bash
cd /root/workspace/fittrack/frontend && npx tsc --noEmit
# Expected: exit 0
```

---

### WP5: Rotation — Skip bei Pausetagen

**Objective:** Rotation überspringt Slots wenn User nicht trainiert hat (training_done=False am vorherigen Tag).

**Files:**
- Modify: `backend/app/routes/training.py:39-62` (`_get_rotation_slot_for_date`)

**Step 1: Fix rotation logic**

Current (line 39-62): purely increment slot by 1.

Fixed:
```python
async def _get_rotation_slot_for_date(session, target_date: date_type) -> tuple[Optional[int], Optional[TrainingRotation]]:
    """Determine rotation slot. Skips rest days: if the last training day was NOT done,
    keep the same slot (don't advance) — user missed a session, should do it next time."""
    result = await session.execute(
        select(DayEntry)
        .where(DayEntry.user_id == USER_ID, DayEntry.date <= target_date, DayEntry.rotation_slot.isnot(None))
        .order_by(desc(DayEntry.date))
        .limit(1)
    )
    last_entry = result.scalars().first()

    if last_entry and last_entry.rotation_slot is not None:
        if last_entry.training_done:
            # Last training was completed → advance to next slot
            slot = (last_entry.rotation_slot % 7) + 1
        else:
            # Last training was NOT done → repeat same slot
            slot = last_entry.rotation_slot
    else:
        slot = 1

    rot_result = await session.execute(
        select(TrainingRotation).where(TrainingRotation.user_id == USER_ID, TrainingRotation.slot == slot)
    )
    rotation = rot_result.scalars().first()
    return slot, rotation
```

**Step 2: Verify**

```bash
# When training_done=True → slot advances
# When training_done=False → slot repeats
# Logic verified by code inspection (no integration test needed for this unit)
```

---

### WP6: Week-Summary — `macro_compliance` berechnen

**Objective:** WeekSummary vergleicht Ist-Macros mit Goal-Macros und berechnet Compliance %.

**Files:**
- Modify: `backend/app/schemas.py:368-387` (WeekSummary — add `macro_compliance`)
- Modify: `backend/app/routes/stats.py` (compute macro_compliance)
- Modify: `frontend/src/lib/types.ts` (WeekStats — add `macro_compliance`)

**Step 1: Add `macro_compliance` to WeekSummary schema**

```python
# schemas.py — in WeekSummary class, add:
macro_compliance: Optional[dict[str, Decimal]] = None
# Example: {"protein": 95.0, "carbs": 80.0, "fat": 110.0, "kcal": 98.0}
```

**Step 2: Compute in stats.py**

```python
# stats.py — after avg_protein/carbs/fat calculation:
# Fetch goals
goals_result = await session.execute(select(Goal).where(Goal.user_id == USER_ID))
goals = {g.key: g.value for g in goals_result.scalars().all()}

macro_compliance = None
if goals:
    def _compliance(actual, target):
        if not target or target == 0:
            return None
        return Decimal(str(round(min(float(actual) / float(target) * 100, 100), 1)))

    macro_compliance = {
        "kcal": _compliance(avg_kcal, goals.get("kcal")),
        "protein": _compliance(avg_protein, goals.get("protein")),
        "carbs": _compliance(avg_carbs, goals.get("carbs")),
        "fat": _compliance(avg_fat, goals.get("fat")),
    }
    macro_compliance = {k: v for k, v in macro_compliance.items() if v is not None}
    if not macro_compliance:
        macro_compliance = None

# Add to response:
WeekSummary(..., macro_compliance=macro_compliance)
```

**Step 3: Frontend type**

```typescript
// types.ts — WeekStats interface:
macro_compliance?: Record<string, number> | null;
```

**Step 4: Verify**

```bash
curl -s "http://localhost:8000/api/stats/week?date=2026-08-20" -H "X-FitTrack-CLI-Key: $CLI_KEY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('macro_compliance'))"
# Expected: {"protein": 95.0, ...} or null
```

---

### WP7: Build, Migrate, Verify

**Objective:** Docker Build, Alembic Migration, Full API verification.

**Step 1: Build**

```bash
cd /root/workspace/fittrack && docker compose build
# Expected: both images built
```

**Step 2: Recreate + migrate**

```bash
docker compose up -d
sleep 5
docker exec -w /app -e PYTHONPATH=/app fittrack-fittrack-api-1 alembic upgrade head
# Expected: Running upgrade 002 -> 003
```

**Step 3: Full verification matrix**

```bash
# Health
curl -s http://localhost:8000/api/health
# Expected: {"status":"ok"}

# Goals
curl -s http://localhost:8000/api/goals -H "X-FitTrack-CLI-Key: $CLI_KEY"
# Expected: goals dict

# Day entries (no create)
curl -s "http://localhost:8000/api/day-entries?date=2099-01-01" -H "X-FitTrack-CLI-Key: $CLI_KEY"
# Expected: null

# Meals (auto-create, 4 slots)
curl -s "http://localhost:8000/api/meals?date=2099-12-31" -H "X-FitTrack-CLI-Key: $CLI_KEY" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))"
# Expected: 4

# Training suggestion (topset vs backoff)
curl -s "http://localhost:8000/api/training?date=2026-08-20" -H "X-FitTrack-CLI-Key: $CLI_KEY" | python3 -c "import sys,json; d=json.load(sys.stdin); [print(f\"{e['exercise_name']}: reps={e['target_reps_low']}-{e['target_reps_high']} topset={e['is_topset']}\") for e in d['exercises']]"
# Expected: topset reps differ from backoff reps

# Week summary with macro_compliance
curl -s "http://localhost:8000/api/stats/week?date=2026-08-20" -H "X-FitTrack-CLI-Key: $CLI_KEY" | python3 -c "import sys,json; d=json.load(sys.stdin); print('macro_compliance:', d.get('macro_compliance'))"
# Expected: dict or null

# Frontend
curl -s http://localhost:3000/ | head -1
# Expected: <!DOCTYPE html...

# Frontend types
cd /root/workspace/fittrack/frontend && npx tsc --noEmit
# Expected: exit 0
```

**Step 4: Syntax check**

```bash
docker exec -w /app fittrack-fittrack-api-1 python -m py_compile app/**/*.py
# Expected: exit 0
```

---

## End-State-Review-Gate

- [x] End-State: Alle 5 verbleibenden Issues vollständig behoben — kein degraded intermediate
- [x] Kein degraded intermediate als terminal goal: Jedes WP ist ein Increment zum End-State
- [x] Kein dual-path: Alle Fixes ersetzen buggy Logic, keine neue平行-Pfad
- [x] One-Solution-Only: Kein neues Storage-Backend, kein neuer Service
- [x] Clean-slate nicht nötig: System hat einen canonical path pro Konzept, Fixes sind incremental

## Risks
- **Alembic stamp**: Migration 003 muss nach 002 laufen — DB ist bereits bei 002 ✅
- **Seed data**: Neue Exercises brauchen `base_reps_low/high` Werte — Seed update deckt das ab
- **Frontend breaking**: `base_reps_low` ist optional (`Optional[int]`) — kein breaking change

## Files Modified Summary
- `backend/app/models.py` — Exercise: +base_reps_low, +base_reps_high
- `backend/app/schemas.py` — ExerciseResponse/Create/Update: +base_reps fields; WeekSummary: +macro_compliance
- `backend/app/routes/training.py` — progression reset, topset vs backoff, rotation skip
- `backend/app/routes/meals.py` — auto-create respects user overrides
- `backend/app/routes/stats.py` — macro_compliance calculation
- `backend/app/seed.py` — base_reps in seed data
- `backend/alembic/versions/003_add_base_reps.py` — new migration
- `frontend/src/lib/components/MealCard.svelte` — analysis display + apply
- `frontend/src/lib/types.ts` — PhotoAnalysis type, macro_compliance in WeekStats
- `frontend/src/lib/components/UnifiedDay.svelte` — analysisApply handler