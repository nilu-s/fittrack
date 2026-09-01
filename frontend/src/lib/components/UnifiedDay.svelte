<script lang="ts">
  import { createEventDispatcher } from 'svelte';
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

  type UnifiedItem = { id: string; type: 'metric' | 'meal' | 'training' | 'cardio' | 'todo'; icon: string; title: string; done: boolean; sortKey: string; metricField?: string; metricValue?: string | number | null; metricUnit?: string; metricEditable?: boolean; metricCheckable?: boolean; metricDoneField?: string; hasProgress?: boolean; progressCurrent?: number; progressTarget?: number; kcal?: number | null; protein?: number | null; fiber?: number | null; sugar?: number | null; mealTime?: string | null; todoData?: Todo; sleepQuality?: number; sleepDetails?: { deep: number; rem: number; light: number; awake: number; efficiency: number }; stepsConfirmed?: boolean; biometric?: boolean; weightSource?: string | null; weightDetails?: { bodyFat: number | null; muscle: number | null; water: number | null; bone: number | null; bmi: number | null; bmr: number | null; visceralFat: number | null; metabolicAge: number | null }; };

  $: unifiedItems = buildUnifiedItems(entry, meals, todos, trainingSuggestion);

  function buildUnifiedItems(entry: DayEntry | null, mealList: Meal[], todoList: Todo[], suggestion: TrainingSuggestion | null): UnifiedItem[] {
    const items: UnifiedItem[] = [];
    if (!entry) return items;
    // Weight: biometric — automated from ESP32 scale, but manually editable too
    const hasBmi = entry.bmi != null;
    items.push({ id: 'metric-weight', type: 'metric', icon: 'weight', title: 'Gewicht', done: false, sortKey: '00-00', metricField: 'weight_kg', metricValue: entry.weight_kg ?? null, metricUnit: 'kg', metricEditable: true, biometric: true, weightSource: entry.weight_source ?? null, weightDetails: hasBmi ? { bodyFat: null, muscle: null, water: null, bone: null, bmi: Number(entry.bmi), bmr: null, visceralFat: null, metabolicAge: null } : undefined });
    // Steps: biometric — automated from Google Fit, not manually checkable
    items.push({ id: 'metric-steps', type: 'metric', icon: 'steps', title: 'Schritte', done: false, sortKey: '00-01', metricField: 'steps', metricValue: entry.steps ?? null, hasProgress: true, progressCurrent: entry.steps ?? 0, progressTarget: goals.steps, stepsConfirmed: entry.steps_confirmed ?? false, biometric: true });
    // Sleep: biometric — automated from Google Fit, shows quality score and details instead
    items.push({ id: 'metric-sleep', type: 'metric', icon: 'sleep', title: 'Schlaf', done: false, sortKey: '00-02', metricField: 'sleep_hours', metricValue: entry.sleep_hours ?? null, metricUnit: 'h', hasProgress: true, progressCurrent: entry.sleep_hours ?? 0, progressTarget: goals.sleepHours, sleepQuality: entry.sleep_quality ?? 0, sleepDetails: (entry.sleep_deep_hours != null || entry.sleep_rem_hours != null) ? { deep: Number(entry.sleep_deep_hours) || 0, rem: Number(entry.sleep_rem_hours) || 0, light: Number(entry.sleep_light_hours) || 0, awake: Number(entry.sleep_awake_hours) || 0, efficiency: Number(entry.sleep_efficiency) || 0 } : undefined, biometric: true });
    items.push({ id: 'metric-creatine', type: 'metric', icon: 'creatine', title: 'Kreatin', done: entry.creatine_done ?? false, sortKey: '00-03', metricField: 'creatine_done', metricValue: entry.creatine_done ? 'Eingenommen' : 'Ausstehend', metricCheckable: true, metricDoneField: 'creatine_done', metricEditable: false });
    items.push({ id: 'metric-belly', type: 'metric', icon: 'belly', title: 'Bauchumfang', done: false, sortKey: '00-04', metricField: 'belly_cm', metricValue: entry.belly_cm ?? null, metricUnit: 'cm', metricEditable: true });
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
  let actionSheetItem: UnifiedItem | null = null;
  let editingTodo: Todo | null = null;
  let editTitle = ''; let editCategory = ''; let editPriority = 2; let editDueDate = ''; let editDueTime = '';
  let detailItem: UnifiedItem | null = null;
  let mealEntryEditorItem: UnifiedItem | null = null;
  let mealEntryEditorCamera = false;

  /** Only one task detail may be open in the daily list at a time. */
  function closeOpenTodoDetails() {
    actionSheetItem = null;
    editingTodo = null;
    detailItem = null;
    mealEntryEditorItem = null;
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
      meal_entry_status: updated.status, is_done: updated.status === 'consumed',
      kcal: nutrition.kcal, protein_g: nutrition.protein_g, carbs_g: nutrition.carbs_g, fat_g: nutrition.fat_g,
      fiber_g: nutrition.fiber_g, sugar_g: nutrition.sugar_g, free_sugar_g: nutrition.free_sugar_g,
    } : meal);
    dispatch('mealtoggle', { id: updated.id, is_done: updated.status === 'consumed', data: { name: updated.name, kcal: nutrition.kcal, protein_g: nutrition.protein_g, carbs_g: nutrition.carbs_g, fat_g: nutrition.fat_g, fiber_g: nutrition.fiber_g, sugar_g: nutrition.sugar_g, free_sugar_g: nutrition.free_sugar_g } });
  }

  function toggleTodoActions(item: UnifiedItem) {
    if (actionSheetItem?.id === item.id) { actionSheetItem = null; return; }
    closeOpenTodoDetails();
    actionSheetItem = item;
  }

  function handlePressStart(item: UnifiedItem, event: PointerEvent) {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    longPressTriggered = false;
    longPressTimer = setTimeout(() => {
      longPressTriggered = true;
      if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(50);
      openItemDetails(item);
    }, 500);
  }
  function handlePressEnd() {
    if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null; }
  }
  function handlePressMove() {
    if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null; }
  }
  function handleContextMenu(item: UnifiedItem, e: MouseEvent) { e.preventDefault(); openItemDetails(item); }

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
    if (e.key === 'Enter') { e.preventDefault(); openItemDetails(item); return; }
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
          const nextStatus = meal.is_done ? 'skipped' : 'consumed';
          const updated = await api.setMealEntryStatus(meal.id, nextStatus, meal.updated_at);
          if (!updated) return;
          meals = meals.map((m) => m.id === meal.id ? { ...m, is_done: updated.status === 'consumed', meal_entry_status: updated.status, updated_at: updated.updated_at } : m);
          dispatch('mealtoggle', { id: meal.id, is_done: updated.status === 'consumed' });
        }
      } catch {}
      return;
    }
    if (item.type === 'training' && entry) { const newVal = !entry.training_done; try { await api.upsertDayEntry({ ...entry, training_done: newVal, date: currentDate }); entry = { ...entry, training_done: newVal }; dispatch('trainingtoggle', newVal); } catch {} return; }
    if (item.type === 'cardio' && entry) { const newVal = !entry.cardio_done; try { await api.upsertDayEntry({ ...entry, cardio_done: newVal, date: currentDate }); entry = { ...entry, cardio_done: newVal }; dispatch('cardiotoggle', newVal); } catch {} return; }
    if (item.type === 'todo') { const todoId = item.id.replace('todo-', ''); try { await api.markTodoDone(todoId); todos = todos.map((t) => String(t.id) === todoId ? { ...t, status: t.status === 'open' ? 'done' : 'open' } : t); dispatch('todotoggle', { id: todoId }); } catch {} return; }
  }

  async function updateMetric(field: string, value: any) { if (!entry) return; entry = { ...entry, [field]: value }; if (field === 'weight_kg') { entry = { ...entry, weight_source: 'manual' }; } try { await api.upsertDayEntry({ ...entry, date: currentDate }); dispatch('update', { field, value }); } catch {} }
  function handleTrainingComplete() { if (entry) { entry = { ...entry, training_done: true }; dispatch('trainingtoggle', true); } }

  async function addQuick() { const title = quickAdd.trim(); if (!title) return; try { const n = await api.createTodo({ due_date: currentDate, title, status: 'open', priority: 2, source: 'manual' } as any); if (n) { todos = [...todos, n]; dispatch('todoadd', n); } quickAdd = ''; } catch {} }
  function handleKey(e: KeyboardEvent) { if (e.key === 'Enter') { e.preventDefault(); addQuick(); } }

  function openItemDetails(item: UnifiedItem) {
    closeOpenTodoDetails();
    detailItem = item;
  }
  function closeItemDetails() { detailItem = null; }

  function getMealFromItem(item: UnifiedItem): Meal | undefined {
    const id = String(item.id).replace('meal-', '');
    return meals.find((m) => String(m.id) === id || `meal-${m.meal_slot}` === item.id);
  }

  $: weightItem = unifiedItems.find((i) => i.id === 'metric-weight');
  $: biometricItems = unifiedItems.filter((i) => i.biometric && i.id !== 'metric-weight');
  $: manualItems = unifiedItems.filter((i) => !i.biometric);
  $: openCount = manualItems.filter((i) => !i.done).length;

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
      { val: sd.deep, color: '#1e40af', label: 'Tief' },
      { val: sd.rem, color: '#7c3aed', label: 'REM' },
      { val: sd.light, color: '#60a5fa', label: 'Leicht' },
      { val: sd.awake, color: '#6b7280', label: 'Wach' },
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
        <div class="bio-section">
          <div class="bio-hdr">
            <span class="bio-title"><Icon name={item.icon} size={14} /> {item.title}</span>
            {#if reached}
              <span class="bio-goal-reached">✓</span>
            {/if}
          </div>
          <div class="bio-value-lg">
            {(item.metricValue ?? 0).toLocaleString('de')}
            <span class="bio-target">/ {item.progressTarget?.toLocaleString('de') ?? '—'}</span>
          </div>
          <ProgressBar current={item.progressCurrent ?? 0} target={item.progressTarget ?? 1} color={reached ? 'var(--green)' : 'var(--text-dim)'} />
          {#if !reached && item.metricValue != null}
            <div class="bio-status"><span class="bio-pending">noch {remaining.toLocaleString('de')}</span></div>
          {/if}
        </div>
      {:else if item.id === 'metric-sleep'}
        {@const sd = item.sleepDetails}
        {@const sleepTotal = sd ? sd.deep + sd.rem + sd.light : 0}
        {@const fmtShort = (h: number) => { const m = Math.round(h * 60); return m >= 60 ? `${Math.floor(m/60)}h${m%60 > 0 ? ` ${m%60}m` : ''}` : `${m}m`; }}
        <div class="bio-section">
          <div class="bio-hdr">
            <span class="bio-title"><Icon name={item.icon} size={14} /> {item.title}</span>
          </div>
          <div class="sleep-donut-row">
            <svg class="sleep-donut" viewBox="0 0 100 100">
              {#if sd && sleepTotal > 0}
                {#each sleepDonut(sd) as seg}
                  <circle cx="50" cy="50" r="38" fill="none" stroke={seg.color} stroke-width="10"
                    stroke-dasharray="{seg.dash.toFixed(2)} {(2 * Math.PI * 38 - seg.dash).toFixed(2)}"
                    stroke-dashoffset={seg.offset.toFixed(2)} transform="rotate(-90 50 50)" />
                {/each}
                <text x="50" y="47" text-anchor="middle" fill="var(--text)" font-size="13" font-weight="700">{fmtShort(sleepTotal)}</text>
                <text x="50" y="59" text-anchor="middle" fill="var(--text-faint)" font-size="7">Schlaf</text>
              {:else}
                <!-- Gray empty donut -->
                <circle cx="50" cy="50" r="38" fill="none" stroke="var(--border-2)" stroke-width="10" />
                <text x="50" y="52" text-anchor="middle" fill="var(--text-faint)" font-size="10">—</text>
              {/if}
            </svg>
            {#if sd && sleepTotal > 0}
              <div class="sleep-legend-col">
                {#each [{ val: sd.deep, color: '#1e40af', label: 'Tief' }, { val: sd.rem, color: '#7c3aed', label: 'REM' }, { val: sd.light, color: '#60a5fa', label: 'Leicht' }, { val: sd.awake, color: '#6b7280', label: 'Wach' }] as p}
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

<!-- Weight section — direkt über der To-Do-Liste -->
{#if weightItem}
  <div class="weight-section">
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
        {#if wd.bodyFat != null}<span class="wms"><b>{wd.bodyFat}%</b> Fett</span>{/if}
        {#if wd.muscle != null}<span class="wms"><b>{wd.muscle}</b> Muskel</span>{/if}
        {#if wd.water != null}<span class="wms"><b>{wd.water}%</b> Wasser</span>{/if}
        {#if wd.bone != null}<span class="wms"><b>{wd.bone}</b> Knochen</span>{/if}
        {#if wd.bmr != null}<span class="wms"><b>{wd.bmr}</b> BMR</span>{/if}
        {#if wd.visceralFat != null}<span class="wms"><b>{wd.visceralFat}</b> Visz.</span>{/if}
        {#if wd.metabolicAge != null}<span class="wms"><b>{wd.metabolicAge}</b> Met.-Alter</span>{/if}
      </div>
    {/if}
    {#if weightTrend.length > 0 && !weightEditing}
      {@const wc = weightChart(weightTrend, realTodayStr, currentDate, weightRange)}
      {#if wc}
        <svg class="weight-chart-full" viewBox="0 0 200 50" preserveAspectRatio="none">
          <!-- Background area (faint) -->
          <path d={wc.fullAreaD} fill="var(--blue)" fill-opacity="0.05" />
          <!-- Assumed segments (gray, dashed) -->
          {#if wc.assumedPathD}
            <path d={wc.assumedPathD} fill="none" stroke="var(--text-faint)" stroke-width="1.5" stroke-dasharray="3,2" stroke-linecap="round" />
          {/if}
          <!-- Verified segments (blue, solid) -->
          {#if wc.verifiedPathD}
            <path d={wc.verifiedPathD} fill="none" stroke="var(--blue)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
          {/if}
          <!-- Dots: verified=blue, assumed=gray hollow, selected=ring -->
          {#each wc.dots as d}
            <circle cx={d.x} cy={d.y}
              r={d.isSelected ? 3.5 : d.hasData ? 2 : 1.5}
              fill={d.hasData ? 'var(--blue)' : 'var(--text-faint)'}
              stroke={d.isSelected ? 'var(--bg)' : 'none'}
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
  </div>
{/if}

<!-- Day list -->
<div class="daylist">
  <div class="daylist-hdr">
    <span>{openCount} offen</span>
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
          {#if item.type === 'meal' && item.kcal}<PillBadge value={Math.round(item.kcal)} unit="kcal" color="var(--amber)" />{/if}
          {#if item.type === 'meal' && item.protein}<PillBadge value={Math.round(item.protein)} unit="g P" color="var(--blue)" />{/if}
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
      {#if item.type === 'metric'}
        <MetricRow icon="" label="" value={item.metricValue} unit={item.metricUnit ?? ''} editable={item.metricEditable ?? false} checkable={false} on:change={(e) => updateMetric(item.metricField!, e.detail)} />
      {/if}
      {#if item.hasProgress}<div class="item-prog"><ProgressBar current={item.progressCurrent ?? 0} target={item.progressTarget ?? 1} color="var(--text-dim)" /></div>{/if}
    </div>

  {/each}

  <div class="quickadd">
    <input placeholder="+ To-Do hinzufügen…" bind:value={quickAdd} onkeydown={handleKey} />
    <button onclick={addQuick} disabled={!quickAdd.trim()} aria-label="Hinzufügen"><Icon name="plus" size={16} /></button>
  </div>
</div>

<MealEntryEditorSheet meal={mealEntryEditorItem ? getMealFromItem(mealEntryEditorItem) ?? null : null} open={Boolean(mealEntryEditorItem)} autoOpenCamera={mealEntryEditorCamera} on:close={closeMealEntryEditor} on:saved={(event) => { applyMealEntryUpdate(event.detail.entry); closeMealEntryEditor(); }} />

{#if detailItem}
  <dialog class="modal-overlay compact-overlay" open aria-labelledby="detail-title" onclick={(event) => { if (event.target === event.currentTarget) closeItemDetails(); }} oncancel={(event) => { event.preventDefault(); closeItemDetails(); }}>
    <div class="modal-card compact-detail">
      <header class="detail-header"><div><p class="detail-kind">{detailItem.type === 'meal' ? 'Mahlzeit' : detailItem.type === 'training' ? 'Training' : detailItem.type === 'todo' ? 'To-do' : 'Tageswert'}</p><h2 id="detail-title">{detailItem.title}</h2></div><button class="detail-close" type="button" aria-label="Details schließen" onclick={closeItemDetails}>×</button></header>
      {#if detailItem.type === 'meal'}
        {@const detailMeal = getMealFromItem(detailItem)}
        <div class="modal-pills">
          {#if detailMeal?.kcal != null}<PillBadge value={Math.round(Number(detailMeal.kcal))} unit="kcal" color="var(--amber)" />{/if}
          {#if detailMeal?.protein_g != null}<PillBadge value={Math.round(Number(detailMeal.protein_g))} unit="g Protein" color="var(--blue)" />{/if}
          {#if detailMeal?.carbs_g != null}<PillBadge value={Math.round(Number(detailMeal.carbs_g))} unit="g KH" color="var(--purple)" />{/if}
          {#if detailMeal?.fat_g != null}<PillBadge value={Math.round(Number(detailMeal.fat_g))} unit="g Fett" color="var(--pink)" />{/if}
        </div>
        {#if detailMeal?.recipe_instructions?.length}
          <div class="detail-section"><strong>Kochanleitung</strong><ol>{#each detailMeal.recipe_instructions as step}<li>{step}</li>{/each}</ol></div>
        {:else}<p class="detail-empty">Für diese Mahlzeit ist noch keine Kochanleitung hinterlegt.</p>{/if}
      {:else if detailItem.type === 'todo'}
        {#if detailItem.todoData?.category}<p class="detail-meta">Kategorie: {detailItem.todoData.category}</p>{/if}
        {#if detailItem.todoData?.due_time}<p class="detail-meta">Fällig um {detailItem.todoData.due_time}</p>{/if}
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
    <div class="action-sheet">
      <div class="action-handle"></div>
      <div class="action-title">{actionSheetItem.title}</div>
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
    <div class="modal-card edit-card">
      <div class="modal-title">To-Do bearbeiten</div>
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
      <div class="modal-actions">
        <button class="modal-primary" onclick={saveEdit}>Speichern</button>
        <button class="modal-secondary" onclick={cancelEdit}>Abbrechen</button>
      </div>
    </div>
  </dialog>
{/if}

<style>
  .daylist { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
  .daylist-hdr { display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; border-bottom: 1px solid var(--border); font-size: 13px; color: var(--text-dim); font-weight: 500; }

  .item { position: relative; z-index: 1; display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-bottom: 0; cursor: pointer; transition: transform 0.2s ease, background 0.15s, opacity 0.15s; min-height: 56px; -webkit-user-select: none; user-select: none; background: var(--card); }
  .item:last-of-type { border-bottom: none; }
  .item.done { opacity: 0.5; }
  .item:active { background: var(--card-2); }

  .item-check { width: 40px; height: 40px; border-radius: 50%; border: 0; flex-shrink: 0; display: flex; align-items: center; justify-content: center; color: transparent; cursor: pointer; position: relative; }
  .item-check::before { content: ''; position: absolute; width: 20px; height: 20px; border-radius: 50%; border: 1.5px solid var(--border-2); transition: background .15s, border-color .15s; }
  .item-check.done { color: #07120a; }
  .item-check.done::before { background: var(--green); border-color: var(--green); }
  .item-check :global(svg) { position: relative; z-index: 1; }
  .item-check:focus-visible { outline: 2px solid var(--blue); outline-offset: -2px; }

  .item-body { flex: 1; display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .item-title { font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: 500; color: var(--text); }
  .item-title.strike { text-decoration: line-through; }
  .item-badges { display: flex; align-items: center; gap: 4px; }
  .item-time { font-size: 11px; color: var(--text-faint); font-weight: 500; }
  .recipe-marker { font-size:10px; color:var(--green); border:1px solid color-mix(in srgb, var(--green) 55%, var(--border-2)); border-radius:999px; padding:2px 6px; white-space:nowrap; }
  .item-prog { flex: 0 0 70px; }
  .meal-row-actions { display: flex; align-items: center; gap: 2px; flex: 0 0 auto; }
  .meal-action-icon { width: 30px; height: 30px; display: grid; place-items: center; border: 0; border-radius: 6px; background: transparent; color: var(--text-faint); cursor: pointer; }
  .meal-action-icon:hover, .meal-action-icon:focus-visible { background: var(--card-2); color: var(--text-dim); }
  .meal-action-icon:focus-visible { outline: 2px solid var(--blue); outline-offset: 1px; }
  .meal-action-icon:active { background: var(--border); color: var(--text); }
  /* Biometrics — Schritte + Schlaf nebeneinander */
  .biometrics-row { display: flex; gap: 8px; padding: 0 0 4px; }
  .biometrics-row .bio-section { flex: 1; }
  .bio-section { display: flex; flex-direction: column; gap: 6px; padding: 12px 14px; background: var(--card); border: 1px solid var(--border); border-radius: 10px; }
  .bio-section:active { background: var(--card-2); }
  .bio-hdr { display: flex; align-items: center; justify-content: space-between; }
  .bio-title { font-size: 11px; color: var(--text-dim); display: flex; align-items: center; gap: 4px; font-weight: 600; }
  .bio-value-lg { font-size: 22px; font-weight: 700; color: var(--text); line-height: 1.2; }
  .bio-target { font-size: 13px; font-weight: 400; color: var(--text-faint); }
  .bio-status { font-size: 11px; min-height: 14px; }
  .bio-goal-reached { color: var(--green); font-weight: 600; }
  .bio-pending { color: var(--text-faint); }
  .bio-unit { font-size: 13px; font-weight: 400; color: var(--text-faint); }
  .bio-source-badge { font-size: 9px; color: var(--green); font-weight: 600; background: rgba(34,197,94,0.15); padding: 1px 5px; border-radius: 4px; }
  .bio-source-manual { font-size: 9px; color: var(--text-faint); font-weight: 500; }
  .bio-hdr-right { display: flex; align-items: center; gap: 4px; }

  /* Weight section — direkt über der To-Do-Liste */
  .weight-section { display: flex; flex-direction: column; gap: 6px; padding: 12px 14px; background: var(--card); border: 1px solid var(--border); border-radius: 10px; margin-bottom: 4px; }
  .weight-value-row { display: flex; align-items: baseline; gap: 6px; }
  .weight-value-btn { background: none; border: none; cursor: pointer; font-size: 22px; font-weight: 700; color: var(--text); padding: 0; display: flex; align-items: baseline; gap: 4px; }
  .weight-value-btn:active { opacity: 0.7; }
  .weight-edit-hint { font-size: 12px; color: var(--text-faint); font-weight: 400; margin-left: 4px; }
  .weight-input { width: 100px; padding: 4px 8px; border-radius: 6px; background: var(--card-2); border: 1px solid var(--border-2); color: var(--text); font-size: 22px; font-weight: 700; }
  .weight-input:focus { border-color: var(--blue); outline: none; }
  .weight-chart-full { width: 100%; height: 60px; }
  .weight-chart-labels { display: flex; justify-content: space-between; padding: 0 2px; }
  .weight-chart-label { font-size: 8px; color: var(--text-faint); text-align: center; flex: 1; white-space: nowrap; overflow: hidden; }
  .weight-chart-label.today { color: var(--blue); font-weight: 700; }

  /* Weight mini stats — compact inline metrics */
  .weight-mini-stats { display: flex; flex-wrap: wrap; gap: 4px 8px; }
  .wms { font-size: 10px; color: var(--text-faint); display: flex; align-items: baseline; gap: 2px; }
  .wms b { font-size: 11px; font-weight: 600; color: var(--text-dim); }

  /* Weight range selector */
  .weight-range-tabs { display: flex; gap: 2px; }
  .weight-range-tabs button { font-size: 10px; font-weight: 600; padding: 2px 6px; border: 1px solid var(--border-2); border-radius: 4px; background: transparent; color: var(--text-faint); cursor: pointer; line-height: 1.4; }
  .weight-range-tabs button.active { background: var(--blue); color: var(--bg); border-color: var(--blue); }

  /* Sleep donut */
  .sleep-donut-row { display: flex; align-items: center; gap: 12px; }
  .sleep-donut { width: 80px; height: 80px; flex-shrink: 0; }
  .sleep-legend-col { display: flex; flex-direction: column; gap: 3px; flex: 1; min-width: 0; }
  .sleep-leg-row { display: flex; align-items: center; gap: 6px; font-size: 11px; line-height: 1.4; }
  .sleep-leg-label { color: var(--text-dim); flex: 1; white-space: nowrap; }
  .sleep-leg-time { color: var(--text); font-weight: 600; text-align: right; min-width: 42px; }
  .sleep-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }

  .quickadd { display: flex; gap: 8px; padding: 12px 14px; border-top: 1px solid var(--border); }
  .quickadd input { flex: 1; padding: 8px 12px; border-radius: 8px; background: var(--card-2); border: 1px solid var(--border-2); color: var(--text); font-size: 14px; }
  .quickadd input:focus { border-color: var(--blue); }
  .quickadd input::placeholder { color: var(--text-faint); }
  .quickadd button { width: 34px; height: 34px; border-radius: 8px; background: var(--green); color: #000; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: opacity 0.15s; }
  .quickadd button:disabled { opacity: 0.3; }
  .quickadd button:active { opacity: 0.7; }

  .modal-pills { display: flex; flex-wrap: wrap; justify-content: center; gap: 4px; }

  .action-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: flex-end; justify-content: center; animation: fadeIn 0.15s; }
  .modal-overlay, .action-overlay { margin: 0; max-width: none; max-height: none; width: auto; height: auto; border: 0; padding: 0; }
  .action-sheet { background: var(--card); border-radius: 16px 16px 0 0; width: 100%; max-width: 420px; padding: 8px 0 20px; box-shadow: 0 -4px 24px rgba(0,0,0,0.4); animation: slideUp 0.2s; }
  .action-handle { width: 36px; height: 4px; border-radius: 2px; background: var(--border-2); margin: 8px auto 12px; }
  .action-title { text-align: center; font-size: 14px; font-weight: 600; color: var(--text-dim); padding: 0 16px 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .action-btn { display: flex; align-items: center; gap: 12px; width: calc(100% - 16px); margin: 0 8px; padding: 14px 16px; border: none; border-radius: 10px; background: var(--card-2); color: var(--text); font-size: 15px; font-weight: 500; cursor: pointer; transition: background 0.15s; }
  .action-btn:active { background: var(--bg); }
  .action-del { color: var(--red); }
  .action-cancel { display: block; width: calc(100% - 16px); margin: 12px 8px 0; padding: 14px 16px; border: none; border-radius: 10px; background: var(--card-2); color: var(--text-dim); font-size: 15px; font-weight: 500; cursor: pointer; }
  .action-cancel:active { background: var(--bg); }

  .edit-card { display: flex; flex-direction: column; gap: 10px; }
  .edit-input { flex: 1; padding: 8px 10px; border-radius: 8px; background: var(--bg); border: 1px solid var(--border-2); color: var(--text); font-size: 14px; }
  .edit-input:focus { border-color: var(--blue); }
  .edit-select { flex: 1; padding: 8px 10px; border-radius: 8px; background: var(--bg); border: 1px solid var(--border-2); color: var(--text); font-size: 14px; }
  .edit-row { display: flex; gap: 8px; }
  .modal-actions { display: flex; gap: 8px; margin-top: 4px; }
  .modal-primary { flex: 1; padding: 10px 14px; border-radius: 8px; background: var(--green); color: #000; border: none; font-weight: 600; cursor: pointer; font-size: 14px; }
  .modal-secondary { flex: 1; padding: 10px 14px; border-radius: 8px; background: var(--card-2); color: var(--text-dim); border: 1px solid var(--border-2); font-weight: 500; cursor: pointer; font-size: 14px; }
  .compact-overlay { align-items:center; justify-content:center; padding:16px; }
  .compact-detail { width:min(100%, 420px); max-height:min(58dvh, 520px); overflow:auto; display:flex; flex-direction:column; gap:14px; padding:16px; border-radius:16px; }
  .detail-header { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }
  .detail-header h2,.detail-header p { margin:0; }
  .detail-header h2 { font-size:17px; line-height:1.3; }
  .detail-kind,.detail-meta,.detail-empty { color:var(--text-dim); font-size:13px; line-height:1.45; }
  .detail-close { width:32px; min-height:32px; border:1px solid var(--border-2); border-radius:50%; background:var(--card-2); color:var(--text); font-size:20px; line-height:1; }
  .detail-section { display:grid; gap:8px; color:var(--text); font-size:14px; line-height:1.45; }
  .detail-section ol { display:grid; gap:7px; margin:0; padding-left:22px; color:var(--text-dim); }
  @media (min-width: 700px) { .compact-overlay { padding:24px; } .compact-detail { max-width:360px; } }

  @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
  @keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
</style>
