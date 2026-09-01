<script lang="ts">
  import { createEventDispatcher, tick } from 'svelte';
  import MetricRow from './MetricRow.svelte';
  import ProgressBar from './ProgressBar.svelte';
  import PillBadge from './PillBadge.svelte';
  import TrainingDetail from './TrainingDetail.svelte';
  import MealEntryEditorSheet from './MealEntryEditorSheet.svelte';
  import Icon from './Icon.svelte';
  import { api } from '$lib/api';
  import { dailyGoals } from '$lib/stores';
  import type { DayEntry, Meal, Todo, TrainingSuggestion, DayData, TrendPoint } from '$lib/types';

  export let dayData: DayData;
  export let currentDate: string;
  const dispatch = createEventDispatcher();
  const SLOT_NAMES: Record<number, string> = { 1: 'Frühstück', 2: 'Mittag', 3: 'Snack', 4: 'Abendessen' };

  let entry: DayEntry = dayData.dayEntry ?? { date: currentDate };
  let meals: Meal[] = dayData.meals ?? [];
  let todos: Todo[] = dayData.todos ?? [];
  let trainingSuggestion: TrainingSuggestion | null = dayData.trainingSuggestion ?? null;
  $: entry = dayData.dayEntry ?? { date: currentDate };
  $: meals = dayData.meals ?? [];
  $: todos = dayData.todos ?? [];
  $: trainingSuggestion = dayData.trainingSuggestion ?? null;

  let weightTrend: TrendPoint[] = [];
  let weightRange = 7; // 7 | 30 | 365
  $: if (currentDate) loadWeightTrend();
  async function loadWeightTrend() { try { const wt = await api.getStatsTrend('weight', weightRange); weightTrend = (wt?.points ?? []).filter((p: any) => p.value != null && p.value > 0); } catch {} }

  $: goals = $dailyGoals;

  let expandedSleep = false;
  let expandedWeight = false;
  let weightEditing = false;
  let quickAdd = '';

  type UnifiedItem = { id: string; type: 'metric' | 'meal' | 'training' | 'cardio' | 'todo'; icon: string; title: string; done: boolean; sortKey: string; metricField?: string; metricValue?: string | number | null; metricUnit?: string; metricEditable?: boolean; metricCheckable?: boolean; metricDoneField?: string; hasProgress?: boolean; progressCurrent?: number; progressTarget?: number; kcal?: number | null; protein?: number | null; fiber?: number | null; sugar?: number | null; mealTime?: string | null; todoData?: Todo; sleepQuality?: number; sleepDetails?: { deep: number; rem: number; light: number; awake: number; efficiency: number }; stepsConfirmed?: boolean; biometric?: boolean; weightSource?: string | null; weightDetails?: { bmi: number | null }; };

  $: unifiedItems = buildUnifiedItems(entry, meals, todos, trainingSuggestion);

  function buildUnifiedItems(entry: DayEntry | null, mealList: Meal[], todoList: Todo[], suggestion: TrainingSuggestion | null): UnifiedItem[] {
    const items: UnifiedItem[] = [];
    if (!entry) return items;
    // Weight: biometric — automated from ESP32 scale, but manually editable too
    const hasBmi = entry.bmi != null;
    items.push({ id: 'metric-weight', type: 'metric', icon: 'weight', title: 'Gewicht', done: false, sortKey: '00-00', metricField: 'weight_kg', metricValue: entry.weight_kg ?? null, metricUnit: 'kg', metricEditable: true, biometric: true, weightSource: entry.weight_source ?? null, weightDetails: hasBmi ? { bmi: Number(entry.bmi) } : undefined });
    // Steps: biometric — automated from Google Fit, not manually checkable
    items.push({ id: 'metric-steps', type: 'metric', icon: 'steps', title: 'Schritte', done: false, sortKey: '00-01', metricField: 'steps', metricValue: entry.steps ?? null, hasProgress: true, progressCurrent: entry.steps ?? 0, progressTarget: goals.steps, stepsConfirmed: entry.steps_confirmed ?? false, biometric: true });
    // Sleep: biometric — automated from Google Fit, shows quality score and details instead
    items.push({ id: 'metric-sleep', type: 'metric', icon: 'sleep', title: 'Schlaf', done: false, sortKey: '00-02', metricField: 'sleep_hours', metricValue: entry.sleep_hours ?? null, metricUnit: 'h', hasProgress: true, progressCurrent: entry.sleep_hours ?? 0, progressTarget: goals.sleepHours, sleepQuality: entry.sleep_quality ?? 0, sleepDetails: (entry.sleep_deep_hours != null || entry.sleep_rem_hours != null) ? { deep: Number(entry.sleep_deep_hours) || 0, rem: Number(entry.sleep_rem_hours) || 0, light: Number(entry.sleep_light_hours) || 0, awake: Number(entry.sleep_awake_hours) || 0, efficiency: Number(entry.sleep_efficiency) || 0 } : undefined, biometric: true });
    // Mahlzeiten gehören in denselben Tagesfluss wie Training und freie To-dos.
    const sortedMeals = [...mealList].sort((a, b) => (a.meal_slot ?? 99) - (b.meal_slot ?? 99));
    for (const m of sortedMeals) {
      const slotLabel = m.category_name || SLOT_NAMES[m.meal_slot] || `Slot ${m.meal_slot}`;
      const dishName = m.name || '— Mahlzeit wählen —';
      items.push({ id: `meal-${m.id ?? m.meal_slot}`, type: 'meal', icon: 'meal', title: `${slotLabel}: ${dishName}`, done: m.is_done ?? false, sortKey: `01-${String(m.meal_slot).padStart(2, '0')}`, kcal: Number(m.kcal) || null, protein: Number(m.protein_g) || null, fiber: Number(m.fiber_g) || null, sugar: Number(m.sugar_g) || null, mealTime: m.default_time ? m.default_time.slice(0, 5) : null });
    }
    const trainingType = suggestion?.training_type ?? entry.training_type;
    if (trainingType && trainingType !== 'Ruhetag') {
      items.push({ id: 'training', type: 'training', icon: 'training', title: trainingType, done: entry.training_done ?? false, sortKey: '02-00' });
    }
    for (const t of todoList) { items.push({ id: `todo-${t.id}`, type: 'todo', icon: 'todo', title: t.title, done: t.status === 'done', sortKey: `03-${t.due_time ?? '99:99'}`, todoData: t }); }
    // Alles, was abgehakt ist, wird im Tagesfluss ans Ende verschoben.
    // Innerhalb der offenen bzw. erledigten Gruppe bleibt die Tagesreihenfolge erhalten.
    return items.sort((a, b) => {
      const completionOrder = Number(a.done) - Number(b.done);
      return completionOrder || a.sortKey.localeCompare(b.sortKey);
    });
  }

  let longPressTimer: ReturnType<typeof setTimeout> | null = null;
  let longPressTriggered = false;
  let longPressStart: { x: number; y: number } | null = null;
  let actionSheetItem: UnifiedItem | null = null;
  let editingTodo: Todo | null = null;
  let editTitle = ''; let editCategory = ''; let editPriority = 2; let editDueDate = ''; let editDueTime = '';
  let detailItem: UnifiedItem | null = null;
  let mealEntryEditorItem: UnifiedItem | null = null;
  let mealEntryEditorCamera = false;
  let metricTrendItem: UnifiedItem | null = null;
  let metricTrend: TrendPoint[] = [];
  let metricTrendLoading = false;
  let metricTrendError = '';
  let metricTrendTrigger: HTMLElement | null = null;
  let metricTrendCloseButton: HTMLButtonElement | null = null;
  let nutritionDetailsOpen = false;
  let nutritionDetailsTrigger: HTMLElement | null = null;
  let nutritionDetailsCloseButton: HTMLButtonElement | null = null;

  /** Only one task detail may be open in the daily list at a time. */
  function closeOpenTodoDetails() {
    actionSheetItem = null;
    editingTodo = null;
    detailItem = null;
    mealEntryEditorItem = null;
    nutritionDetailsOpen = false;
  }

  function openMealEntryEditor(item: UnifiedItem, openCamera = false) {
    closeOpenTodoDetails();
    mealEntryEditorCamera = openCamera;
    mealEntryEditorItem = item;
  }

  function closeMealEntryEditor() { mealEntryEditorItem = null; mealEntryEditorCamera = false; }

  function applyMealEntryUpdate(updated: any) {
    const nutrition = updated?.nutrition ?? {};
    meals = meals.map((meal) => meal.id === updated?.id ? {
      ...meal, name: updated.name, meal_entry_items: updated.items, updated_at: updated.updated_at,
      meal_entry_status: updated.status, is_done: updated.status !== 'planned',
      kcal: nutrition.kcal, protein_g: nutrition.protein_g, carbs_g: nutrition.carbs_g, fat_g: nutrition.fat_g,
      fiber_g: nutrition.fiber_g, sugar_g: nutrition.sugar_g, free_sugar_g: nutrition.free_sugar_g,
    } : meal);
    dispatch('mealtoggle', { id: updated.id, is_done: updated.status !== 'planned', data: { name: updated.name, meal_entry_status: updated.status, updated_at: updated.updated_at, kcal: nutrition.kcal, protein_g: nutrition.protein_g, carbs_g: nutrition.carbs_g, fat_g: nutrition.fat_g, fiber_g: nutrition.fiber_g, sugar_g: nutrition.sugar_g, free_sugar_g: nutrition.free_sugar_g } });
  }

  function toggleTodoActions(item: UnifiedItem) {
    if (actionSheetItem?.id === item.id) { actionSheetItem = null; return; }
    closeOpenTodoDetails();
    actionSheetItem = item;
  }

  function handlePressStart(item: UnifiedItem, event: PointerEvent) {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    const trigger = event.currentTarget as HTMLElement;
    longPressTriggered = false;
    longPressStart = { x: event.clientX, y: event.clientY };
    longPressTimer = setTimeout(() => {
      longPressTriggered = true;
      if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(50);
      openItemDetails(item, trigger);
    }, 500);
  }
  function handlePressEnd() {
    if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null; }
    longPressStart = null;
  }
  function handlePressMove(event: PointerEvent) {
    if (!longPressTimer || !longPressStart) return;
    const moved = Math.hypot(event.clientX - longPressStart.x, event.clientY - longPressStart.y);
    if (moved > 12) handlePressEnd();
  }
  function handleContextMenu(item: UnifiedItem, e: MouseEvent) { e.preventDefault(); openItemDetails(item, e.currentTarget as HTMLElement); }

  function startEdit() {
    if (!actionSheetItem?.todoData) return;
    const t = actionSheetItem.todoData;
    editingTodo = t;
    editTitle = t.title; editCategory = t.category ?? ''; editPriority = t.priority; editDueDate = t.due_date ?? ''; editDueTime = t.due_time ?? '';
    actionSheetItem = null;
  }
  function confirmDelete() {
    if (!actionSheetItem?.todoData) return;
    const todoId = String(actionSheetItem.todoData.id);
    api.deleteTodo(todoId).then(() => { todos = todos.filter((t) => String(t.id) !== todoId); }).catch(() => {});
    actionSheetItem = null;
  }
  function saveEdit() {
    if (!editingTodo?.id) return;
    const id = editingTodo.id;
    const data = { title: editTitle, category: editCategory || null, priority: editPriority, due_date: editDueDate || null, due_time: editDueTime || null };
    api.updateTodo(id, data).then((updated) => { if (updated) { todos = todos.map((t) => t.id === id ? { ...t, ...data } : t); } }).catch(() => {});
    editingTodo = null;
  }
  function cancelEdit() { editingTodo = null; }

  function handleTap(item: UnifiedItem, e: MouseEvent) {
    if (longPressTriggered) { longPressTriggered = false; return; }
    if (item.type === 'training' || item.type === 'meal' || item.type === 'todo') return;
    if (item.id === 'metric-sleep') { expandedSleep = !expandedSleep; return; }
    if (item.id === 'metric-weight' && item.weightDetails) { expandedWeight = !expandedWeight; return; }
  }

  function handleItemKey(item: UnifiedItem, e: KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); openItemDetails(item, e.currentTarget as HTMLElement); return; }
    if (e.key !== ' ') return;
    e.preventDefault();
    handleTap(item, e as unknown as MouseEvent);
  }

  function handleCheck(item: UnifiedItem, e: MouseEvent) {
    e.stopPropagation();
    if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(25);
    toggleDone(item);
  }

  async function toggleDone(item: UnifiedItem) {
    if (item.type === 'metric' && item.metricDoneField) { const newVal = !(entry as any)[item.metricDoneField]; try { await api.upsertDayEntry({ ...entry, [item.metricDoneField]: newVal, date: currentDate }); entry = { ...entry, [item.metricDoneField]: newVal }; dispatch('update', { field: item.metricDoneField, value: newVal }); } catch {} return; }
    if (item.type === 'meal') {
      const mealId = item.id.replace('meal-', '');
      const meal = meals.find((m) => String(m.id) === mealId || `meal-${m.meal_slot}` === item.id);
      if (!meal?.id) return;
      try {
        if (meal.meal_entry) {
          const nextStatus = meal.meal_entry_status === 'consumed' ? 'planned' : 'consumed';
          const updated = await api.setMealEntryStatus(meal.id, nextStatus, meal.updated_at);
          if (!updated) return;
          meals = meals.map((m) => m.id === meal.id ? { ...m, is_done: updated.status !== 'planned', meal_entry_status: updated.status, updated_at: updated.updated_at } : m);
          dispatch('mealtoggle', { id: meal.id, is_done: updated.status !== 'planned', data: { meal_entry_status: updated.status, updated_at: updated.updated_at } });
        }
      } catch {}
      return;
    }
    if (item.type === 'training' && entry) { const newVal = !entry.training_done; try { await api.upsertDayEntry({ ...entry, training_done: newVal, date: currentDate }); entry = { ...entry, training_done: newVal }; dispatch('trainingtoggle', newVal); } catch {} return; }
    if (item.type === 'cardio' && entry) { const newVal = !entry.cardio_done; try { await api.upsertDayEntry({ ...entry, cardio_done: newVal, date: currentDate }); entry = { ...entry, cardio_done: newVal }; dispatch('cardiotoggle', newVal); } catch {} return; }
    if (item.type === 'todo') { const todoId = item.id.replace('todo-', ''); try { const updated = await api.markTodoDone(todoId); if (!updated) return; todos = todos.map((t) => String(t.id) === todoId ? { ...t, ...updated } : t); dispatch('todotoggle', { id: todoId, status: updated.status }); } catch {} return; }
  }

  async function updateMetric(field: string, value: any) { if (!entry) return; entry = { ...entry, [field]: value }; if (field === 'weight_kg') { entry = { ...entry, weight_source: 'manual' }; } try { await api.upsertDayEntry({ ...entry, date: currentDate }); dispatch('update', { field, value }); } catch {} }
  function handleTrainingComplete() { if (entry) { entry = { ...entry, training_done: true }; dispatch('trainingtoggle', true); } }

  async function addQuick() { const title = quickAdd.trim(); if (!title) return; try { const n = await api.createTodo({ due_date: currentDate, title, status: 'open', priority: 2, source: 'manual' } as any); if (n) { todos = [...todos, n]; dispatch('todoadd', n); } quickAdd = ''; } catch {} }
  function handleKey(e: KeyboardEvent) { if (e.key === 'Enter') { e.preventDefault(); addQuick(); } }

  function openItemDetails(item: UnifiedItem, trigger?: HTMLElement) {
    if (item.id === 'metric-steps' || item.id === 'metric-sleep') {
      openMetricTrend(item, trigger);
      return;
    }
    closeOpenTodoDetails();
    detailItem = item;
  }
  function closeItemDetails() { detailItem = null; }

  async function openMetricTrend(item: UnifiedItem, trigger?: HTMLElement) {
    closeOpenTodoDetails();
    metricTrendItem = item;
    metricTrend = [];
    metricTrendError = '';
    metricTrendLoading = true;
    metricTrendTrigger = trigger ?? null;
    await tick();
    metricTrendCloseButton?.focus();
    try {
      const response = await api.getStatsTrend(item.id === 'metric-steps' ? 'steps' : 'sleep_hours', 365);
      metricTrend = (response?.points ?? []).filter((point) => point.value != null);
    } catch {
      metricTrendError = 'Der Verlauf konnte gerade nicht geladen werden.';
    } finally {
      metricTrendLoading = false;
    }
  }

  function closeMetricTrend() {
    metricTrendItem = null;
    metricTrend = [];
    const trigger = metricTrendTrigger;
    metricTrendTrigger = null;
    setTimeout(() => trigger?.focus(), 0);
  }

  async function openNutritionDetails(trigger: HTMLElement) {
    closeOpenTodoDetails();
    nutritionDetailsTrigger = trigger;
    nutritionDetailsOpen = true;
    await tick();
    nutritionDetailsCloseButton?.focus();
  }

  function closeNutritionDetails() {
    nutritionDetailsOpen = false;
    const trigger = nutritionDetailsTrigger;
    nutritionDetailsTrigger = null;
    setTimeout(() => trigger?.focus(), 0);
  }

  function metricChart(points: TrendPoint[]) {
    if (!points.length) return null;
    const values = points.map((point) => Number(point.value));
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const width = 300;
    const height = 120;
    const coords = values.map((value, index) => ({
      x: points.length === 1 ? width / 2 : 8 + index * ((width - 16) / (points.length - 1)),
      y: 8 + (height - 20) - ((value - min) / range) * (height - 20),
    }));
    const path = coords.map((coord, index) => `${index ? 'L' : 'M'}${coord.x.toFixed(1)},${coord.y.toFixed(1)}`).join(' ');
    const average = values.reduce((sum, value) => sum + value, 0) / values.length;
    return { path, coords, first: points[0].date, last: points[points.length - 1].date, min, max, average };
  }

  function formatTrendDate(value: string) { return new Date(`${value}T00:00`).toLocaleDateString('de-DE', { day: '2-digit', month: 'short', year: 'numeric' }); }
  function formatTrendValue(value: number, item: UnifiedItem) {
    if (item.id === 'metric-sleep') return `${value.toLocaleString('de-DE', { maximumFractionDigits: 1 })} h`;
    return Math.round(value).toLocaleString('de-DE');
  }

  function getMealFromItem(item: UnifiedItem): Meal | undefined {
    const id = String(item.id).replace('meal-', '');
    return meals.find((m) => String(m.id) === id || `meal-${m.meal_slot}` === item.id);
  }

  $: weightItem = unifiedItems.find((i) => i.id === 'metric-weight');
  $: biometricItems = unifiedItems.filter((i) => i.biometric && i.id !== 'metric-weight');
  $: manualItems = unifiedItems.filter((i) => !i.biometric);
  $: openCount = manualItems.filter((i) => !i.done).length;
  $: consumedMeals = meals.filter((meal) => meal.meal_entry_status === 'consumed');
  $: nutritionTotals = consumedMeals.reduce((totals, meal) => ({
    kcal: totals.kcal + (Number(meal.kcal) || 0), protein: totals.protein + (Number(meal.protein_g) || 0),
    carbs: totals.carbs + (Number(meal.carbs_g) || 0), fat: totals.fat + (Number(meal.fat_g) || 0),
  }), { kcal: 0, protein: 0, carbs: 0, fat: 0 });

  // Local date string (avoids UTC offset bug)
  function localDateStr(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  // Real today — chart always anchors here, selected day just gets highlighted
  function localTodayStr(): string {
    return localDateStr(new Date());
  }
  $: realTodayStr = localTodayStr();

  // Precompute weight chart — anchors to real today, splits verified vs assumed
  function weightChart(points: TrendPoint[], realToday: string, selectedDate: string, numDays: number) {
    if (!points || points.length === 0) return null;
    const valMap = new Map<string, number>();
    for (const p of points) {
      if (p.value != null) valMap.set(p.date, Number(p.value));
    }
    if (valMap.size === 0) return null;
    // Generate all dates for the range, anchored to real today
    const days: { date: string; val: number; hasData: boolean }[] = [];
    const anchorDate = new Date(realToday + 'T00:00');
    let firstKnown: number | null = null;
    for (const p of points) {
      if (p.value != null) { firstKnown = Number(p.value); break; }
    }
    let lastKnown = firstKnown ?? 0;
    for (let i = numDays - 1; i >= 0; i--) {
      const d = new Date(anchorDate);
      d.setDate(d.getDate() - i);
      const ds = localDateStr(d);
      if (valMap.has(ds)) {
        lastKnown = valMap.get(ds)!;
        days.push({ date: ds, val: lastKnown, hasData: true });
      } else {
        days.push({ date: ds, val: lastKnown, hasData: false });
      }
    }
    const vals = days.map((d) => d.val);
    const min = Math.min(...vals) - 0.5;
    const max = Math.max(...vals) + 0.5;
    const range = max - min || 1;
    const stepX = vals.length > 1 ? 190 / (vals.length - 1) : 0;
    const coords = vals.map((v, i) => ({ x: 5 + i * stepX, y: 45 - ((v - min) / range) * 38 }));

    // Build segment paths: verified (both endpoints have data) vs assumed
    const verifiedSegs: string[] = [];
    const assumedSegs: string[] = [];
    for (let i = 0; i < coords.length - 1; i++) {
      const bothVerified = days[i].hasData && days[i + 1].hasData;
      const seg = `M${coords[i].x.toFixed(1)},${coords[i].y.toFixed(1)} L${coords[i + 1].x.toFixed(1)},${coords[i + 1].y.toFixed(1)}`;
      if (bothVerified) verifiedSegs.push(seg);
      else assumedSegs.push(seg);
    }
    const verifiedPathD = verifiedSegs.join(' ');
    const assumedPathD = assumedSegs.join(' ');
    // Full area for background
    const fullPathD = coords.map((c, i) => `${i === 0 ? 'M' : 'L'}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(' ');
    const fullAreaD = `${fullPathD} L${coords[coords.length - 1].x.toFixed(1)},50 L${coords[0].x.toFixed(1)},50 Z`;

    const dots = coords.map((c, i) => ({
      ...c,
      isSelected: days[i].date === selectedDate,
      hasData: days[i].hasData,
    }));

    // Labels — deduplicate month names in year view by including year
    const labelStep = numDays <= 7 ? 1 : numDays <= 30 ? 5 : Math.floor(numDays / 12);
    const seen = new Set<string>();
    const labels = days.map((d, i) => {
      if (i % labelStep !== 0 && i !== days.length - 1) return null;
      const dt = new Date(d.date + 'T00:00');
      let lbl: string;
      if (numDays <= 7) {
        lbl = dt.toLocaleDateString('de', { weekday: 'short' }).slice(0, 2);
      } else if (numDays <= 30) {
        lbl = dt.toLocaleDateString('de', { day: 'numeric', month: 'short' });
      } else {
        // Year view: month + 2-digit year to avoid duplicates
        lbl = dt.toLocaleDateString('de', { month: 'short', year: '2-digit' });
      }
      // Deduplicate
      const key = numDays <= 30 ? lbl : dt.toLocaleDateString('de', { month: 'short', year: 'numeric' });
      if (seen.has(key)) return null;
      seen.add(key);
      return { date: d.date, isSelected: d.date === selectedDate, label: lbl };
    }).filter((l) => l !== null) as { date: string; isSelected: boolean; label: string }[];

    return { verifiedPathD, assumedPathD, fullPathD, fullAreaD, dots, labels };
  }

  // Precompute sleep donut segments
  function sleepDonut(sd: { deep: number; rem: number; light: number; awake: number } | undefined) {
    if (!sd) return [];
    const r = 38;
    const circ = 2 * Math.PI * r;
    const phases = [
      { val: sd.deep, color: 'var(--data-sleep-deep)', label: 'Tief' },
      { val: sd.rem, color: 'var(--data-sleep-rem)', label: 'REM' },
      { val: sd.light, color: 'var(--data-sleep-light)', label: 'Leicht' },
      { val: sd.awake, color: 'var(--data-sleep-awake)', label: 'Wach' },
    ].filter((p) => p.val > 0);
    const total = phases.reduce((s, p) => s + p.val, 0) || 1;
    let offset = 0;
    return phases.map((p) => {
      const frac = p.val / total;
      const dash = frac * circ;
      const seg = { ...p, dash, offset: -offset, frac };
      offset += dash;
      return seg;
    });
  }
</script>

<!-- Biometrics: Schritte + Schlaf nebeneinander -->
{#if biometricItems.length > 0}
  <div class="biometrics-row">
    {#each biometricItems as item (item.id)}
      {#if item.id === 'metric-steps'}
        {@const reached = (item.progressCurrent ?? 0) >= (item.progressTarget ?? 1)}
        {@const remaining = Math.max(0, (item.progressTarget ?? 1) - (item.progressCurrent ?? 0))}
        <div class="bio-section biometric-trend-target" role="group" aria-label="Schritte"
          onpointerdown={(event) => handlePressStart(item, event)}
          onpointerup={handlePressEnd}
          onpointermove={handlePressMove}
          onpointerleave={handlePressEnd}
          onpointercancel={handlePressEnd}
          oncontextmenu={(event) => handleContextMenu(item, event)}>
          <div class="bio-hdr">
            <span class="bio-title"><Icon name={item.icon} size={14} /> {item.title}</span>
            <div class="bio-hdr-right">
              {#if reached}
              <span class="bio-goal-reached">✓</span>
              {/if}
              <button class="bio-trend-button" type="button" onpointerdown={(event) => event.stopPropagation()} onclick={(event) => { event.stopPropagation(); openMetricTrend(item, event.currentTarget); }} aria-label="Schritte-Verlauf anzeigen"><Icon name="chart" size={16} /></button>
            </div>
          </div>
          <div class="bio-value-lg">
            {(item.metricValue ?? 0).toLocaleString('de')}
            <span class="bio-target">/ {item.progressTarget?.toLocaleString('de') ?? '—'}</span>
          </div>
          <ProgressBar current={item.progressCurrent ?? 0} target={item.progressTarget ?? 1} color={reached ? 'var(--status-success)' : 'var(--text-secondary)'} />
          {#if !reached && item.metricValue != null}
            <div class="bio-status"><span class="bio-pending">noch {remaining.toLocaleString('de')}</span></div>
          {/if}
        </div>
      {:else if item.id === 'metric-sleep'}
        {@const sd = item.sleepDetails}
        {@const sleepTotal = sd ? sd.deep + sd.rem + sd.light : 0}
        {@const fmtShort = (h: number) => { const m = Math.round(h * 60); return m >= 60 ? `${Math.floor(m/60)}h${m%60 > 0 ? ` ${m%60}m` : ''}` : `${m}m`; }}
        <div class="bio-section biometric-trend-target" role="group" aria-label="Schlaf"
          onpointerdown={(event) => handlePressStart(item, event)}
          onpointerup={handlePressEnd}
          onpointermove={handlePressMove}
          onpointerleave={handlePressEnd}
          onpointercancel={handlePressEnd}
          oncontextmenu={(event) => handleContextMenu(item, event)}>
          <div class="bio-hdr">
            <span class="bio-title"><Icon name={item.icon} size={14} /> {item.title}</span>
            <button class="bio-trend-button" type="button" onpointerdown={(event) => event.stopPropagation()} onclick={(event) => { event.stopPropagation(); openMetricTrend(item, event.currentTarget); }} aria-label="Schlafverlauf anzeigen"><Icon name="chart" size={16} /></button>
          </div>
          <div class="sleep-donut-row">
            <svg class="sleep-donut" viewBox="0 0 100 100">
              {#if sd && sleepTotal > 0}
                {#each sleepDonut(sd) as seg}
                  <circle cx="50" cy="50" r="38" fill="none" stroke={seg.color} stroke-width="10"
                    stroke-dasharray="{seg.dash.toFixed(2)} {(2 * Math.PI * 38 - seg.dash).toFixed(2)}"
                    stroke-dashoffset={seg.offset.toFixed(2)} transform="rotate(-90 50 50)" />
                {/each}
                <text x="50" y="47" text-anchor="middle" fill="var(--text-primary)" font-size="13" font-weight="700">{fmtShort(sleepTotal)}</text>
                <text x="50" y="59" text-anchor="middle" fill="var(--text-tertiary)" font-size="7">Schlaf</text>
              {:else}
                <!-- Gray empty donut -->
                <circle cx="50" cy="50" r="38" fill="none" stroke="var(--border-default)" stroke-width="10" />
                <text x="50" y="52" text-anchor="middle" fill="var(--text-tertiary)" font-size="10">—</text>
              {/if}
            </svg>
            {#if sd && sleepTotal > 0}
              <div class="sleep-legend-col">
                {#each [{ val: sd.deep, color: 'var(--data-sleep-deep)', label: 'Tief' }, { val: sd.rem, color: 'var(--data-sleep-rem)', label: 'REM' }, { val: sd.light, color: 'var(--data-sleep-light)', label: 'Leicht' }, { val: sd.awake, color: 'var(--data-sleep-awake)', label: 'Wach' }] as p}
                  <div class="sleep-leg-row">
                    <span class="sleep-dot" style="background:{p.color}"></span>
                    <span class="sleep-leg-label">{p.label}</span>
                    <span class="sleep-leg-time">{fmtShort(p.val)}</span>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        </div>
      {/if}
    {/each}
  </div>
{/if}

<!-- Tageswerte: Gewicht und Ernährung -->
<div class="feature-card-row">
{#if weightItem}
  <section class="weight-section">
    <div class="bio-hdr">
      <span class="bio-title"><Icon name={weightItem.icon} size={14} /> {weightItem.title}</span>
      <div class="bio-hdr-right">
        {#if weightItem.weightSource === 'scale_esp'}
          <span class="bio-source-badge">Waage ✓</span>
        {:else if weightItem.weightSource === 'manual'}
          <span class="bio-source-manual">manuell</span>
        {/if}
        <div class="weight-range-tabs">
          <button class:active={weightRange === 7} onclick={() => { weightRange = 7; loadWeightTrend(); }}>W</button>
          <button class:active={weightRange === 30} onclick={() => { weightRange = 30; loadWeightTrend(); }}>M</button>
          <button class:active={weightRange === 365} onclick={() => { weightRange = 365; loadWeightTrend(); }}>J</button>
        </div>
      </div>
    </div>
    <div class="weight-value-row">
      {#if weightEditing}
        <input class="weight-input" type="number" step="0.1" min="0" max="300"
          value={weightItem.metricValue ?? ''}
          placeholder="Gewicht eingeben"
          onblur={(e) => { const v = parseFloat(e.currentTarget.value); updateMetric('weight_kg', isNaN(v) ? null : v); weightEditing = false; }}
          onkeydown={(e) => { if (e.key === 'Enter') { e.currentTarget.blur(); } if (e.key === 'Escape') { weightEditing = false; } }}
          onclick={(e) => e.stopPropagation()}
        />
        <span class="bio-unit">kg</span>
      {:else}
        <button class="weight-value-btn" onclick={() => { weightEditing = true; }}>
          {weightItem.metricValue != null ? Number(weightItem.metricValue).toFixed(1) : '—'}
          <span class="bio-unit">kg</span>
          <span class="weight-edit-hint">✎</span>
        </button>
      {/if}
    </div>
    {#if weightItem.weightDetails && !weightEditing}
      {@const wd = weightItem.weightDetails}
      <div class="weight-mini-stats">
        {#if wd.bmi != null}<span class="wms"><b>{wd.bmi}</b> BMI</span>{/if}
      </div>
    {/if}
    {#if weightTrend.length > 0 && !weightEditing}
      {@const wc = weightChart(weightTrend, realTodayStr, currentDate, weightRange)}
      {#if wc}
        <svg class="weight-chart-full" viewBox="0 0 200 50" preserveAspectRatio="none">
          <!-- Background area (faint) -->
          <path d={wc.fullAreaD} fill="var(--status-info)" fill-opacity="0.05" />
          <!-- Assumed segments (gray, dashed) -->
          {#if wc.assumedPathD}
            <path d={wc.assumedPathD} fill="none" stroke="var(--text-tertiary)" stroke-width="1.5" stroke-dasharray="3,2" stroke-linecap="round" />
          {/if}
          <!-- Verified segments (blue, solid) -->
          {#if wc.verifiedPathD}
            <path d={wc.verifiedPathD} fill="none" stroke="var(--status-info)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
          {/if}
          <!-- Dots: verified=blue, assumed=gray hollow, selected=ring -->
          {#each wc.dots as d}
            <circle cx={d.x} cy={d.y}
              r={d.isSelected ? 3.5 : d.hasData ? 2 : 1.5}
              fill={d.hasData ? 'var(--status-info)' : 'var(--text-tertiary)'}
              stroke={d.isSelected ? 'var(--color-bg)' : 'none'}
              stroke-width={d.isSelected ? '1.5' : '0'}
              opacity={d.hasData ? 1 : 0.5}
            />
          {/each}
        </svg>
        <div class="weight-chart-labels">
          {#each wc.labels as l}
            <span class="weight-chart-label" class:today={l.isSelected}>{l.label}</span>
          {/each}
        </div>
      {/if}
    {/if}
  </section>
{/if}
  <section class="nutrition-section" aria-labelledby="nutrition-title">
    <div class="bio-hdr">
      <span class="bio-title" id="nutrition-title"><Icon name="meal" size={14} /> Ernährung</span>
      <button class="bio-trend-button" type="button" onclick={(event) => openNutritionDetails(event.currentTarget)} aria-label="Nährwertdetails anzeigen"><Icon name="chart" size={16} /></button>
    </div>
    <div class="nutrition-kcal"><span>{Math.round(nutritionTotals.kcal).toLocaleString('de-DE')}</span><small>kcal{goals.kcal ? ` / ${Number(goals.kcal).toLocaleString('de-DE')}` : ''}</small></div>
    <div class="nutrition-macros" aria-label="Verzehrte Makronährstoffe">
      <span><b>{Math.round(nutritionTotals.protein)} g</b> Protein</span>
      <span><b>{Math.round(nutritionTotals.carbs)} g</b> KH</span>
      <span><b>{Math.round(nutritionTotals.fat)} g</b> Fett</span>
    </div>
    <p class="nutrition-status">{consumedMeals.length ? `${consumedMeals.length} Mahlzeit${consumedMeals.length === 1 ? '' : 'en'} verzehrt` : 'Noch nichts verzehrt'}</p>
  </section>
</div>

<!-- Day list -->
<div class="daylist">
  <div class="daylist-hdr">
    <span>Tagesablauf</span><span>{openCount} offen</span>
  </div>

  {#each manualItems as item (item.id)}
    <div class="item tap-area" class:done={item.done}
      onclick={(e) => handleTap(item, e)}
      oncontextmenu={(e) => handleContextMenu(item, e)}
      onpointerdown={(e) => handlePressStart(item, e)}
      onpointerup={handlePressEnd}
      onpointermove={handlePressMove}
      onpointerleave={handlePressEnd}
      onpointercancel={handlePressEnd}
      onkeydown={(e) => handleItemKey(item, e)}
      role="button" tabindex="0" aria-label={`${item.title}. Lange drücken oder Eingabetaste für Details.`}>
      <button class="item-check" class:done={item.done} onclick={(e) => handleCheck(item, e)} aria-label={item.done ? `${item.title} als offen markieren` : `${item.title} erledigen`}>
        {#if item.done}<Icon name="check" size={14} />{/if}
      </button>
      <Icon name={item.icon} size={18} />
      <div class="item-body">
        <span class="item-title" class:strike={item.done}>{item.title}</span>
        <div class="item-badges">
          {#if item.type === 'meal' && item.kcal}<PillBadge value={Math.round(item.kcal)} unit="kcal" color="var(--data-nutrition-energy)" />{/if}
          {#if item.type === 'meal' && item.protein}<PillBadge value={Math.round(item.protein)} unit="g P" color="var(--data-nutrition-protein)" />{/if}
          {#if item.mealTime}<span class="item-time">{item.mealTime}</span>{/if}
          {#if item.type === 'meal'}<span class="recipe-marker" title="Lange drücken für Rezeptdetails">Rezeptdetails</span>{/if}
        </div>
      </div>
      {#if item.type === 'meal' && !item.done}
        <div class="meal-row-actions">
          <button class="meal-action-icon" onclick={(e) => { e.stopPropagation(); openMealEntryEditor(item); }} aria-label="Mahlzeit anpassen" title="Mahlzeit anpassen"><Icon name="edit" size={16} /></button>
          <button class="meal-action-icon" onclick={(e) => { e.stopPropagation(); openMealEntryEditor(item, true); }} aria-label="Mahlzeit fotografieren" title="Foto analysieren"><Icon name="camera" size={16} /></button>
        </div>
      {/if}
      {#if item.type === 'todo'}
        <button class="more-action" onclick={(e) => { e.stopPropagation(); toggleTodoActions(item); }} aria-label={`${item.title} bearbeiten oder löschen`}>•••</button>
      {/if}
      {#if item.type === 'metric'}
        <MetricRow icon="" label="" value={item.metricValue} unit={item.metricUnit ?? ''} editable={item.metricEditable ?? false} checkable={false} on:change={(e) => updateMetric(item.metricField!, e.detail)} />
      {/if}
      {#if item.hasProgress}<div class="item-prog"><ProgressBar current={item.progressCurrent ?? 0} target={item.progressTarget ?? 1} color="var(--text-secondary)" /></div>{/if}
    </div>

  {/each}

  <div class="quickadd">
    <input placeholder="+ To-Do hinzufügen…" bind:value={quickAdd} onkeydown={handleKey} />
    <button onclick={addQuick} disabled={!quickAdd.trim()} aria-label="Hinzufügen"><Icon name="plus" size={16} /></button>
  </div>
</div>

<MealEntryEditorSheet meal={mealEntryEditorItem ? getMealFromItem(mealEntryEditorItem) ?? null : null} open={Boolean(mealEntryEditorItem)} autoOpenCamera={mealEntryEditorCamera} on:close={closeMealEntryEditor} on:saved={(event) => { applyMealEntryUpdate(event.detail.entry); closeMealEntryEditor(); }} />

{#if nutritionDetailsOpen}
  <dialog class="modal-overlay trend-overlay" open aria-labelledby="nutrition-detail-title" onclick={(event) => { if (event.target === event.currentTarget) closeNutritionDetails(); }} oncancel={(event) => { event.preventDefault(); closeNutritionDetails(); }}>
    <section class="modal-card trend-detail ui-dialog">
      <header class="detail-header ui-dialog__header"><div><p class="detail-kind ui-dialog__eyebrow">Tagesübersicht</p><h2 id="nutrition-detail-title">Nährwerte & Kalorien</h2></div><button bind:this={nutritionDetailsCloseButton} class="detail-close ui-dialog__close" type="button" aria-label="Nährwertdetails schließen" onclick={closeNutritionDetails}>×</button></header>
      <div class="nutrition-detail-grid ui-dialog__section">
        <span><b>{Math.round(nutritionTotals.kcal).toLocaleString('de-DE')}</b> kcal</span>
        <span><b>{Math.round(nutritionTotals.protein)} g</b> Protein</span>
        <span><b>{Math.round(nutritionTotals.carbs)} g</b> Kohlenhydrate</span>
        <span><b>{Math.round(nutritionTotals.fat)} g</b> Fett</span>
      </div>
      {#if consumedMeals.length}
        <section class="nutrition-meal-list ui-dialog__section" aria-labelledby="consumed-meals-title">
          <strong id="consumed-meals-title">Verzehrte Mahlzeiten</strong>
          {#each consumedMeals as meal (meal.id ?? meal.meal_slot)}
            <div><span>{meal.name ?? meal.category_name ?? 'Mahlzeit'}</span><b>{Math.round(Number(meal.kcal) || 0)} kcal</b></div>
          {/each}
        </section>
      {:else}
        <p class="detail-empty">Noch keine verzehrte Mahlzeit für diesen Tag.</p>
      {/if}
    </section>
  </dialog>
{/if}

{#if metricTrendItem}
  {@const chart = metricChart(metricTrend)}
  <dialog class="modal-overlay trend-overlay" open aria-labelledby="metric-trend-title" onclick={(event) => { if (event.target === event.currentTarget) closeMetricTrend(); }} oncancel={(event) => { event.preventDefault(); closeMetricTrend(); }}>
    <section class="modal-card trend-detail ui-dialog">
      <header class="detail-header ui-dialog__header">
        <div><p class="detail-kind ui-dialog__eyebrow">Verlauf · letzte 365 Tage</p><h2 id="metric-trend-title">{metricTrendItem.title}</h2></div>
        <button bind:this={metricTrendCloseButton} class="detail-close ui-dialog__close" type="button" aria-label="Verlauf schließen" onclick={closeMetricTrend}>×</button>
      </header>
      {#if metricTrendLoading}
        <p class="detail-meta">Verlauf wird geladen …</p>
      {:else if metricTrendError}
        <p class="detail-meta">{metricTrendError}</p>
      {:else if chart}
        <div class="trend-summary ui-dialog__section" aria-label={`Zusammenfassung für ${metricTrendItem.title}`}>
          <span><b>{formatTrendValue(chart.average, metricTrendItem)}</b> Ø</span>
          <span><b>{formatTrendValue(chart.min, metricTrendItem)}</b> min.</span>
          <span><b>{formatTrendValue(chart.max, metricTrendItem)}</b> max.</span>
        </div>
        <svg class="metric-trend-chart" viewBox="0 0 300 120" role="img" aria-label={`${metricTrendItem.title} von ${formatTrendDate(chart.first)} bis ${formatTrendDate(chart.last)}`}>
          <line x1="8" y1="108" x2="292" y2="108" stroke="var(--border-default)" stroke-width="1" />
          <path d={chart.path} fill="none" stroke={metricTrendItem.id === 'metric-sleep' ? 'var(--data-sleep-deep)' : 'var(--status-success)'} stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
          {#each chart.coords as point, index}
            <circle cx={point.x} cy={point.y} r={metricTrend.length > 90 ? 0 : 2.5} fill={metricTrendItem.id === 'metric-sleep' ? 'var(--data-sleep-deep)' : 'var(--status-success)'}><title>{formatTrendDate(metricTrend[index].date)}: {formatTrendValue(Number(metricTrend[index].value), metricTrendItem)}</title></circle>
          {/each}
        </svg>
        <div class="trend-axis"><span>{formatTrendDate(chart.first)}</span><span>{formatTrendDate(chart.last)}</span></div>
      {:else}
        <p class="detail-empty">Für diesen Zeitraum sind noch keine Daten vorhanden.</p>
      {/if}
    </section>
  </dialog>
{/if}

{#if detailItem}
  <dialog class="modal-overlay compact-overlay" open aria-labelledby="detail-title" onclick={(event) => { if (event.target === event.currentTarget) closeItemDetails(); }} oncancel={(event) => { event.preventDefault(); closeItemDetails(); }}>
    <div class="modal-card compact-detail ui-dialog">
      <header class="detail-header ui-dialog__header"><div><p class="detail-kind ui-dialog__eyebrow">{detailItem.type === 'meal' ? 'Mahlzeit' : detailItem.type === 'training' ? 'Training' : detailItem.type === 'todo' ? 'To-do' : 'Tageswert'}</p><h2 id="detail-title">{detailItem.title}</h2></div><button class="detail-close ui-dialog__close" type="button" aria-label="Details schließen" onclick={closeItemDetails}>×</button></header>
      {#if detailItem.type === 'meal'}
        {@const detailMeal = getMealFromItem(detailItem)}
        <div class="modal-pills">
          {#if detailMeal?.kcal != null}<PillBadge value={Math.round(Number(detailMeal.kcal))} unit="kcal" color="var(--data-nutrition-energy)" />{/if}
          {#if detailMeal?.protein_g != null}<PillBadge value={Math.round(Number(detailMeal.protein_g))} unit="g Protein" color="var(--data-nutrition-protein)" />{/if}
          {#if detailMeal?.carbs_g != null}<PillBadge value={Math.round(Number(detailMeal.carbs_g))} unit="g KH" color="var(--data-nutrition-carbs)" />{/if}
          {#if detailMeal?.fat_g != null}<PillBadge value={Math.round(Number(detailMeal.fat_g))} unit="g Fett" color="var(--data-nutrition-fat)" />{/if}
        </div>
        {#if detailMeal?.recipe_instructions?.length}
          <div class="detail-section ui-dialog__section"><strong>Kochanleitung</strong><ol>{#each detailMeal.recipe_instructions as step}<li>{step}</li>{/each}</ol></div>
        {:else}<p class="detail-empty">Für diese Mahlzeit ist noch keine Kochanleitung hinterlegt.</p>{/if}
      {:else if detailItem.type === 'todo'}
        <div class="detail-section ui-dialog__section">
          {#if detailItem.todoData?.category}<p class="detail-meta">Kategorie: {detailItem.todoData.category}</p>{/if}
          {#if detailItem.todoData?.due_time}<p class="detail-meta">Fällig um {detailItem.todoData.due_time}</p>{/if}
          {#if !detailItem.todoData?.category && !detailItem.todoData?.due_time}<p class="detail-meta">Keine zusätzlichen Angaben.</p>{/if}
        </div>
        <button class="modal-secondary" onclick={() => { actionSheetItem = detailItem; closeItemDetails(); }}>Bearbeiten</button>
      {:else if detailItem.type === 'training'}
        <TrainingDetail training_type={trainingSuggestion?.training_type ?? entry?.training_type ?? 'Training'} date={currentDate} oncomplete={handleTrainingComplete} onclose={closeItemDetails} showClose={false} />
      {:else}
        <p class="detail-meta">{detailItem.metricValue ?? 'Noch kein Wert erfasst'}{detailItem.metricUnit ? ` ${detailItem.metricUnit}` : ''}</p>
      {/if}
    </div>
  </dialog>
{/if}

{#if actionSheetItem}
  <dialog class="action-overlay" open aria-label="To-do-Aktionen" onclick={(event) => { if (event.target === event.currentTarget) actionSheetItem = null; }} oncancel={(event) => { event.preventDefault(); actionSheetItem = null; }}>
    <div class="action-sheet ui-dialog">
      <header class="action-header ui-dialog__header"><div><p class="ui-dialog__eyebrow">To-do</p><h2>{actionSheetItem.title}</h2></div><button class="detail-close ui-dialog__close" type="button" aria-label="Aktionen schließen" onclick={() => (actionSheetItem = null)}>×</button></header>
      <button class="action-btn" onclick={startEdit}>
        <Icon name="edit" size={18} />
        <span>Bearbeiten</span>
      </button>
      <button class="action-btn action-del" onclick={confirmDelete}>
        <Icon name="trash" size={18} />
        <span>Löschen</span>
      </button>
      <button class="action-cancel" onclick={() => (actionSheetItem = null)}>Abbrechen</button>
    </div>
  </dialog>
{/if}

{#if editingTodo}
  <dialog class="modal-overlay" open aria-label="To-do bearbeiten" onclick={(event) => { if (event.target === event.currentTarget) cancelEdit(); }} oncancel={(event) => { event.preventDefault(); cancelEdit(); }}>
    <div class="modal-card edit-card ui-dialog">
      <header class="ui-dialog__header"><div><p class="ui-dialog__eyebrow">To-do</p><h2>To-do bearbeiten</h2></div><button class="detail-close ui-dialog__close" type="button" aria-label="Bearbeiten schließen" onclick={cancelEdit}>×</button></header>
      <input class="edit-input" placeholder="Titel" bind:value={editTitle} />
      <div class="edit-row">
        <input class="edit-input" placeholder="Kategorie" bind:value={editCategory} />
        <select class="edit-select" bind:value={editPriority}>
          <option value={1}>Niedrig</option>
          <option value={2}>Mittel</option>
          <option value={3}>Hoch</option>
        </select>
      </div>
      <div class="edit-row">
        <input class="edit-input" type="date" bind:value={editDueDate} />
        <input class="edit-input" type="time" bind:value={editDueTime} />
      </div>
      <div class="modal-actions ui-dialog__actions">
        <button class="modal-primary" onclick={saveEdit}>Speichern</button>
        <button class="modal-secondary" onclick={cancelEdit}>Abbrechen</button>
      </div>
    </div>
  </dialog>
{/if}

<style>
  .daylist { background: var(--surface-default); border: 1px solid var(--border-subtle); border-radius: var(--radius-surface); overflow: hidden; }
  .daylist-hdr { display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; border-bottom: 1px solid var(--border-subtle); font-size: 12px; color: var(--text-secondary); font-weight: 700; }

  .item { position: relative; z-index: 1; display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-bottom: 1px solid var(--border-subtle); cursor: pointer; transition: transform .2s ease, background var(--motion-fast), opacity var(--motion-fast); min-height: 58px; -webkit-user-select: none; user-select: none; background: var(--surface-default); }
  .item:last-of-type { border-bottom: none; }
  .item.done { opacity: 0.5; }
  .item:active { background: var(--surface-raised); }

  .item-check { width: 40px; height: 40px; border-radius: 50%; border: 0; flex-shrink: 0; display: flex; align-items: center; justify-content: center; color: transparent; cursor: pointer; position: relative; }
  .item-check::before { content: ''; position: absolute; width: 20px; height: 20px; border-radius: 50%; border: 1.5px solid var(--border-default); transition: background .15s, border-color .15s; }
  .item-check.done { color: var(--text-on-accent); }
  .item-check.done::before { background: var(--status-success); border-color: var(--status-success); }
  .item-check :global(svg) { position: relative; z-index: 1; }
  .item-check:focus-visible { outline: 2px solid var(--status-info); outline-offset: -2px; }

  .item-body { flex: 1; display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .item-title { font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: 500; color: var(--text-primary); }
  .item-title.strike { text-decoration: line-through; }
  .item-badges { display: flex; align-items: center; gap: 4px; }
  .item-time { font-size: 11px; color: var(--text-tertiary); font-weight: 500; }
  .recipe-marker { font-size:10px; color:var(--status-success); border:1px solid color-mix(in srgb, var(--status-success) 55%, var(--border-default)); border-radius:999px; padding:2px 6px; white-space:nowrap; }
  .item-prog { flex: 0 0 70px; }
  .meal-row-actions { display: flex; align-items: center; gap: 2px; flex: 0 0 auto; }
  .meal-action-icon { width: 30px; height: 30px; display: grid; place-items: center; border: 0; border-radius: 6px; background: transparent; color: var(--text-tertiary); cursor: pointer; }
  .meal-action-icon:hover, .meal-action-icon:focus-visible { background: var(--surface-raised); color: var(--text-secondary); }
  .meal-action-icon:focus-visible { outline: 2px solid var(--status-info); outline-offset: 1px; }
  .meal-action-icon:active { background: var(--border-subtle); color: var(--text-primary); }
  .more-action { width:34px; height:34px; border-radius:var(--radius-control); color:var(--text-tertiary); font-size:15px; letter-spacing:1px; }
  .more-action:focus-visible,.more-action:active { background:var(--surface-raised); color:var(--text-primary); }
  /* Biometrics — Schritte + Schlaf nebeneinander */
  .biometrics-row { display: flex; gap: 8px; padding: 0 0 4px; }
  .biometrics-row .bio-section { flex: 1; }
  .bio-section { display: flex; flex-direction: column; gap: 6px; padding: 12px 14px; background: var(--surface-default); border: 1px solid var(--border-subtle); border-radius:var(--radius-surface); touch-action:manipulation; }
  .bio-section:active { background: var(--surface-raised); }
  .bio-hdr { display: flex; align-items: center; justify-content: space-between; }
  .bio-title { font-size: 11px; color: var(--text-secondary); display: flex; align-items: center; gap: 4px; font-weight: 600; }
  .bio-value-lg { font-size: 22px; font-weight: 700; color: var(--text-primary); line-height: 1.2; }
  .bio-target { font-size: 13px; font-weight: 400; color: var(--text-tertiary); }
  .bio-status { font-size: 11px; min-height: 14px; }
  .bio-goal-reached { color: var(--status-success); font-weight: 600; }
  .bio-pending { color: var(--text-tertiary); }
  .bio-unit { font-size: 13px; font-weight: 400; color: var(--text-tertiary); }
  .bio-source-badge { font-size: 9px; color: var(--status-success); font-weight: 600; background: color-mix(in srgb, var(--status-success) 15%, transparent); padding: 1px 5px; border-radius: 4px; }
  .bio-source-manual { font-size: 9px; color: var(--text-tertiary); font-weight: 500; }
  .bio-hdr-right { display: flex; align-items: center; gap: 4px; }
  .bio-trend-button { display:grid; place-items:center; width:var(--control-min); min-height:var(--control-min); padding:0; border:1px solid var(--border-default); border-radius:var(--radius-control); background:var(--surface-raised); color:var(--text-secondary); cursor:pointer; }
  .bio-trend-button:focus-visible { outline:2px solid var(--status-info); outline-offset:2px; }
  .bio-trend-button:active { background:var(--surface-pressed); }

  /* Tageswerte */
  .feature-card-row { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; margin-bottom:4px; }
  .weight-section,.nutrition-section { display:flex; flex-direction:column; gap:6px; min-width:0; padding:14px; border-radius:var(--radius-surface); }
  .weight-section { background:var(--surface-accent); border:1px solid var(--border-accent); }
  .nutrition-section { background:var(--surface-default); border:1px solid var(--border-subtle); }
  .weight-value-row { display: flex; align-items: baseline; gap: 6px; }
  .weight-value-btn { background: none; border: none; cursor: pointer; font-size: 22px; font-weight: 700; color: var(--text-primary); padding: 0; display: flex; align-items: baseline; gap: 4px; }
  .weight-value-btn:active { opacity: 0.7; }
  .weight-edit-hint { font-size: 12px; color: var(--text-tertiary); font-weight: 400; margin-left: 4px; }
  .weight-input { width: 100px; padding: 4px 8px; border-radius: 6px; background: var(--surface-raised); border: 1px solid var(--border-default); color: var(--text-primary); font-size: 22px; font-weight: 700; }
  .weight-input:focus { border-color: var(--status-info); outline: none; }
  .weight-chart-full { width: 100%; height: 60px; }
  .weight-chart-labels { display: flex; justify-content: space-between; padding: 0 2px; }
  .weight-chart-label { font-size: 8px; color: var(--text-tertiary); text-align: center; flex: 1; white-space: nowrap; overflow: hidden; }
  .weight-chart-label.today { color: var(--status-info); font-weight: 700; }

  /* Weight mini stats — compact inline metrics */
  .weight-mini-stats { display: flex; flex-wrap: wrap; gap: 4px 8px; }
  .wms { font-size: 10px; color: var(--text-tertiary); display: flex; align-items: baseline; gap: 2px; }
  .wms b { font-size: 11px; font-weight: 600; color: var(--text-secondary); }

  /* Weight range selector */
  .weight-range-tabs { display: flex; gap: 2px; }
  .weight-range-tabs button { font-size: 10px; font-weight: 600; padding: 2px 6px; border: 1px solid var(--border-default); border-radius: 4px; background: transparent; color: var(--text-tertiary); cursor: pointer; line-height: 1.4; }
  .weight-range-tabs button.active { background: var(--status-info); color: var(--color-bg); border-color: var(--status-info); }

  .nutrition-kcal { display:flex; align-items:baseline; gap:4px; min-height:29px; }
  .nutrition-kcal span { font-size:22px; font-weight:700; color:var(--text-primary); line-height:1.2; }
  .nutrition-kcal small,.nutrition-status { margin:0; color:var(--text-tertiary); font-size:11px; line-height:1.4; }
  .nutrition-macros { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:4px; padding-top:6px; border-top:1px solid var(--border-subtle); }
  .nutrition-macros span { display:grid; gap:1px; min-width:0; color:var(--text-tertiary); font-size:9px; line-height:1.25; }
  .nutrition-macros b { color:var(--text-primary); font-size:11px; white-space:nowrap; }

  /* Sleep donut */
  .sleep-donut-row { display: flex; align-items: center; gap: 12px; }
  .sleep-donut { width: 80px; height: 80px; flex-shrink: 0; }
  .sleep-legend-col { display: flex; flex-direction: column; gap: 3px; flex: 1; min-width: 0; }
  .sleep-leg-row { display: flex; align-items: center; gap: 6px; font-size: 11px; line-height: 1.4; }
  .sleep-leg-label { color: var(--text-secondary); flex: 1; white-space: nowrap; }
  .sleep-leg-time { color: var(--text-primary); font-weight: 600; text-align: right; min-width: 42px; }
  .sleep-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }

  .quickadd { display: flex; gap: 8px; padding: 12px 14px; border-top: 1px solid var(--border-subtle); }
  .quickadd input { flex: 1; padding: 8px 12px; border-radius: 8px; background: var(--surface-raised); border: 1px solid var(--border-default); color: var(--text-primary); font-size: 14px; }
  .quickadd input:focus { border-color: var(--status-info); }
  .quickadd input::placeholder { color: var(--text-tertiary); }
  .quickadd button { width: 34px; height: 34px; border-radius: 8px; background: var(--action-primary); color: var(--text-on-accent); border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: opacity 0.15s; }
  .quickadd button:disabled { opacity: 0.3; }
  .quickadd button:active { opacity: 0.7; }

  .modal-pills { display: flex; flex-wrap: wrap; justify-content: center; gap: 4px; }

  .action-overlay { position: fixed; inset: 0; background: var(--overlay-backdrop); z-index: 1000; display: flex; align-items: flex-end; justify-content: center; animation: fadeIn 0.15s; }
  .modal-overlay, .action-overlay { margin: 0; max-width: none; max-height: none; width: auto; height: auto; border: 0; padding: 0; }
  .action-sheet { background: var(--surface-default); border:1px solid var(--border-default); border-radius:var(--radius-modal) var(--radius-modal) 0 0; width:100%; max-width:420px; box-shadow:var(--shadow-modal); animation:slideUp var(--motion-standard); }
  .action-header h2 { max-width:290px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .action-btn { display:flex; align-items:center; gap:12px; width:100%; min-height:var(--control-min); padding:12px; border:1px solid var(--border-default); border-radius:var(--radius-control); background:var(--surface-raised); color:var(--text-primary); font-size:14px; font-weight:600; cursor:pointer; transition:background var(--motion-fast); }
  .action-btn:active { background:var(--surface-pressed); }
  .action-del { color: var(--status-danger); }
  .action-cancel { width:100%; min-height:var(--control-min); padding:8px 12px; border:1px solid var(--border-default); border-radius:var(--radius-control); background:transparent; color:var(--text-secondary); font-size:14px; font-weight:600; cursor:pointer; }
  .action-cancel:active { background:var(--surface-pressed); }

  .edit-card { display: flex; flex-direction: column; gap: 10px; }
  .edit-input { flex: 1; padding: 8px 10px; border-radius: 8px; background: var(--color-bg); border: 1px solid var(--border-default); color: var(--text-primary); font-size: 14px; }
  .edit-input:focus { border-color: var(--status-info); }
  .edit-select { flex: 1; padding: 8px 10px; border-radius: 8px; background: var(--color-bg); border: 1px solid var(--border-default); color: var(--text-primary); font-size: 14px; }
  .edit-row { display: flex; gap: 8px; }
  .modal-actions { display: flex; gap: 8px; margin-top: 4px; }
  .modal-primary { flex: 1; padding: 10px 14px; border-radius: 8px; background: var(--action-primary); color: var(--text-on-accent); border: none; font-weight: 600; cursor: pointer; font-size: 14px; }
  .modal-secondary { flex: 1; padding: 10px 14px; border-radius: 8px; background: var(--surface-raised); color: var(--text-secondary); border: 1px solid var(--border-default); font-weight: 500; cursor: pointer; font-size: 14px; }
  .compact-overlay { align-items:center; justify-content:center; padding:16px; }
  .compact-detail { width:min(100%, 420px); max-height:min(58dvh, 520px); overflow:auto; border-radius:var(--radius-modal); }
  .detail-header { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }
  .detail-header h2,.detail-header p { margin:0; }
  .detail-header h2 { font-size:17px; line-height:1.3; }
  .detail-kind,.detail-meta,.detail-empty { color:var(--text-secondary); font-size:13px; line-height:1.45; }
  .detail-close { width:32px; min-height:32px; border:1px solid var(--border-default); border-radius:50%; background:var(--surface-raised); color:var(--text-primary); font-size:20px; line-height:1; }
  .detail-section { display:grid; gap:8px; color:var(--text-primary); font-size:14px; line-height:1.45; }
  .detail-section ol { display:grid; gap:7px; margin:0; padding-left:22px; color:var(--text-secondary); }
  .trend-overlay { align-items:center; justify-content:center; padding:16px; }
  .trend-detail { width:min(100%, 560px); max-height:min(76dvh, 620px); overflow:auto; border-radius:var(--radius-modal); }
  .trend-summary { grid-template-columns:repeat(3, 1fr); gap:8px; }
  .trend-summary span { display:grid; gap:2px; padding:9px; border-radius:var(--radius-control); background:var(--surface-raised); color:var(--text-tertiary); font-size:11px; }
  .trend-summary b { color:var(--text-primary); font-size:13px; }
  .metric-trend-chart { width:100%; height:auto; min-height:160px; overflow:visible; }
  .trend-axis { display:flex; justify-content:space-between; gap:12px; color:var(--text-tertiary); font-size:11px; }
  .nutrition-detail-grid { grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; }
  .nutrition-detail-grid span { display:grid; gap:2px; color:var(--text-tertiary); font-size:12px; }
  .nutrition-detail-grid b { color:var(--text-primary); font-size:15px; }
  .nutrition-meal-list > div { display:flex; justify-content:space-between; gap:var(--space-3); color:var(--text-secondary); font-size:13px; }
  .nutrition-meal-list > div + div { padding-top:var(--space-2); border-top:1px solid var(--border-subtle); }
  .nutrition-meal-list b { color:var(--text-primary); white-space:nowrap; }
  @media(max-width:420px) { .feature-card-row { grid-template-columns:1fr; } }
  @media (min-width: 700px) { .trend-overlay { padding:24px; } }
  @media (min-width: 700px) { .compact-overlay { padding:24px; } .compact-detail { max-width:360px; } }

  @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
  @keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
</style>
