<script lang="ts">
  import { createEventDispatcher, onMount, tick } from 'svelte';
  import MetricRow from './MetricRow.svelte';
  import ProgressBar from './ProgressBar.svelte';
  import PillBadge from './PillBadge.svelte';
  import TrainingDetail from './TrainingDetail.svelte';
  import MealEntryEditorSheet from './MealEntryEditorSheet.svelte';
  import Icon from './Icon.svelte';
  import { api } from '$lib/api';
  import { dailyGoals } from '$lib/stores';
  import { buildTrendLine, trendSegmentPaths } from '$lib/trend-lines';
  import type { DayEntry, Todo, TrainingSuggestion, DayData, TrendPoint, MealEntry, Nutrition } from '$lib/types';

  export let dayData: DayData;
  export let currentDate: string;
  const dispatch = createEventDispatcher();

  let entry: DayEntry = dayData.dayEntry ?? { date: currentDate };
  let mealEntries: MealEntry[] = dayData.mealEntries ?? [];
  let todos: Todo[] = dayData.todos ?? [];
  let trainingSuggestion: TrainingSuggestion | null = dayData.trainingSuggestion ?? null;
  $: entry = dayData.dayEntry ?? { date: currentDate };
  $: mealEntries = dayData.mealEntries ?? [];
  $: todos = dayData.todos ?? [];
  $: trainingSuggestion = dayData.trainingSuggestion ?? null;

  $: goals = $dailyGoals;

  let weightEditing = false;

  type UnifiedItem = { id: string; type: 'metric' | 'meal' | 'training' | 'cardio' | 'todo'; icon: string; title: string; done: boolean; sortKey: string; metricField?: string; metricValue?: string | number | null; metricUnit?: string; metricEditable?: boolean; metricCheckable?: boolean; metricDoneField?: string; hasProgress?: boolean; progressCurrent?: number; progressTarget?: number; kcal?: number | null; protein?: number | null; fiber?: number | null; sugar?: number | null; mealTime?: string | null; entryData?: MealEntry; todoData?: Todo; travelLabel?: string | null; sleepQuality?: number; sleepDetails?: { deep: number; rem: number; light: number; awake: number; efficiency: number }; stepsConfirmed?: boolean; biometric?: boolean; weightSource?: string | null; weightDetails?: { bmi: number | null }; weightEstimate?: { value: number; beforeDate: string; afterDate: string }; };

  $: unifiedItems = buildUnifiedItems(entry, mealEntries, todos, trainingSuggestion);

  function buildUnifiedItems(entry: DayEntry | null, mealList: MealEntry[], todoList: Todo[], suggestion: TrainingSuggestion | null): UnifiedItem[] {
    const items: UnifiedItem[] = [];
    if (!entry) return items;
    // Weight: biometric — automated from ESP32 scale, but manually editable too
    const hasBmi = entry.bmi != null;
    const weightEstimate = entry.weight_kg == null ? estimatedWeight : null;
    items.push({ id: 'metric-weight', type: 'metric', icon: 'weight', title: 'Gewicht', done: false, sortKey: '00-00', metricField: 'weight_kg', metricValue: entry.weight_kg ?? weightEstimate?.value ?? null, metricUnit: 'kg', metricEditable: true, biometric: true, weightSource: entry.weight_source ?? null, weightDetails: hasBmi ? { bmi: Number(entry.bmi) } : undefined, weightEstimate: weightEstimate ?? undefined });
    // Steps: biometric — automated from Google Fit, not manually checkable
    items.push({ id: 'metric-steps', type: 'metric', icon: 'steps', title: 'Schritte', done: false, sortKey: '00-01', metricField: 'steps', metricValue: entry.steps ?? null, hasProgress: true, progressCurrent: entry.steps ?? 0, progressTarget: goals.steps, stepsConfirmed: entry.steps_confirmed ?? false, biometric: true });
    // Sleep: biometric — automated from Google Fit, shows quality score and details instead
    items.push({ id: 'metric-sleep', type: 'metric', icon: 'sleep', title: 'Schlaf', done: false, sortKey: '00-02', metricField: 'sleep_hours', metricValue: entry.sleep_hours ?? null, metricUnit: 'h', hasProgress: true, progressCurrent: entry.sleep_hours ?? 0, progressTarget: goals.sleepHours, sleepQuality: entry.sleep_quality ?? 0, sleepDetails: (entry.sleep_deep_hours != null || entry.sleep_rem_hours != null) ? { deep: Number(entry.sleep_deep_hours) || 0, rem: Number(entry.sleep_rem_hours) || 0, light: Number(entry.sleep_light_hours) || 0, awake: Number(entry.sleep_awake_hours) || 0, efficiency: Number(entry.sleep_efficiency) || 0 } : undefined, biometric: true });
    // Mahlzeiten gehören in denselben Tagesfluss wie Training und freie To-dos.
    const sortedMeals = [...mealList].sort((a, b) => (a.category_sort_order ?? 99) - (b.category_sort_order ?? 99));
    for (const m of sortedMeals) {
      const slotLabel = m.category_name || 'Mahlzeit';
      const dishName = m.name || '— Mahlzeit wählen —';
      items.push({ id: `meal-${m.id}`, type: 'meal', icon: 'meal', title: `${slotLabel}: ${dishName}`, done: m.status !== 'planned', sortKey: `01-${String(m.category_sort_order ?? 99).padStart(2, '0')}`, kcal: Number(m.nutrition?.kcal) || null, protein: Number(m.nutrition?.protein_g) || null, fiber: Number(m.nutrition?.fiber_g) || null, sugar: Number(m.nutrition?.sugar_g) || null, mealTime: null, entryData: m });
    }
    const trainingType = suggestion?.training_type ?? entry.training_type;
    if (trainingType && trainingType !== 'Ruhetag') {
      items.push({ id: 'training', type: 'training', icon: 'training', title: trainingType, done: entry.training_done ?? false, sortKey: '02-00' });
    }
    for (const t of todoList) { items.push({ id: `todo-${t.id}`, type: 'todo', icon: 'todo', title: t.title, done: t.status === 'done', sortKey: `03-${t.start_time ?? t.due_time ?? '99:99'}`, todoData: t, travelLabel: travelSummary(t) }); }
    // Alles, was abgehakt ist, wird im Tagesfluss ans Ende verschoben.
    // Innerhalb der offenen bzw. erledigten Gruppe bleibt die Tagesreihenfolge erhalten.
    return items.sort((a, b) => {
      const completionOrder = Number(a.done) - Number(b.done);
      return completionOrder || a.sortKey.localeCompare(b.sortKey);
    });
  }

  function travelSummary(todo: Todo): string | null {
    if (!todo.place_name) return null;
    const place = `📍 ${todo.place_name}`;
    if (!todo.travel_monitoring_enabled) return place;
    if (!todo.travel_depart_at) return `${place} · Anreise aktiv`;
    const departure = new Date(todo.travel_depart_at);
    const time = Number.isNaN(departure.getTime()) ? null : departure.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
    const minutes = todo.travel_duration_seconds ? Math.round(todo.travel_duration_seconds / 60) : null;
    return `${place} · ${time ? `Los ${time}` : 'Anreise aktiv'}${minutes ? ` · ${minutes} Min.` : ''}`;
  }

  function todoTime(todo: Todo): number {
    const value = todo.travel_depart_at ?? (todo.due_date && (todo.start_time ?? todo.due_time)
      ? `${todo.due_date}T${todo.start_time ?? todo.due_time}`
      : null);
    const timestamp = value ? new Date(value).getTime() : Number.POSITIVE_INFINITY;
    return Number.isNaN(timestamp) ? Number.POSITIVE_INFINITY : timestamp;
  }

  function openNavigation(todo: Todo) {
    if (!todo.place_id && !todo.place_name) return;
    const travelmode = { drive: 'driving', bicycle: 'bicycling', walk: 'walking', transit: 'transit' }[todo.travel_mode ?? 'drive'];
    const params = new URLSearchParams({ api: '1', travelmode });
    if (todo.place_id) params.set('destination_place_id', todo.place_id);
    params.set('destination', todo.place_name ?? todo.place_address ?? '');
    window.open(`https://www.google.com/maps/dir/?${params.toString()}`, '_blank', 'noopener,noreferrer');
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
  let metricTrendRange = 7;
  let metricTrendLoading = false;
  let metricTrendError = '';
  let metricTrendTrigger: HTMLElement | null = null;
  let metricTrendCloseButton: HTMLButtonElement | null = null;
  let metricTrendOverlay: HTMLDialogElement | null = null;
  let metricTrendOverlayTop: number | null = null;
  let estimatedWeight: { value: number; beforeDate: string; afterDate: string } | null = null;
  let estimateRequest = 0;
  let nutritionDetailsOpen = false;
  let nutritionDetailsTrigger: HTMLElement | null = null;
  let nutritionDetailsCloseButton: HTMLButtonElement | null = null;
  let nutritionDetailsOverlay: HTMLDialogElement | null = null;
  let nutritionDetailsOverlayTop: number | null = null;
  let detailItemTrigger: HTMLElement | null = null;
  let detailItemOverlay: HTMLDialogElement | null = null;
  let detailItemOverlayTop: number | null = null;
  let travelUpdateError = '';

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
    mealEntries = mealEntries.map((meal) => meal.id === updated?.id ? { ...meal, ...updated, nutrition } : meal);
    dispatch('mealentrychange', { entry: updated });
  }

  async function refreshMealEntryFromServer(entryId: string): Promise<MealEntry | null> {
    const currentEntries = await api.getMealEntries(currentDate);
    const refreshed = currentEntries.find((entry) => entry.id === entryId);
    if (!refreshed) return null;

    // Category labels are display metadata supplied by the dashboard, not the
    // meal-entry API. Keep them while replacing the authoritative nutrition
    // snapshot and status from the server.
    mealEntries = mealEntries.map((entry) => entry.id === entryId
      ? { ...entry, ...refreshed }
      : entry);
    return mealEntries.find((entry) => entry.id === entryId) ?? null;
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

  async function updateTravel(todo: Todo) {
    if (!todo.id || !navigator.geolocation) { travelUpdateError = 'Der aktuelle Standort ist auf diesem Gerät nicht verfügbar.'; return; }
    travelUpdateError = '';
    navigator.geolocation.getCurrentPosition(async (position) => {
      const estimate = await api.estimateTodoTravel(todo.id!, position.coords.latitude, position.coords.longitude);
      if (!estimate) { travelUpdateError = 'Die Reisezeit konnte nicht aktualisiert werden.'; return; }
      todos = todos.map((item) => item.id === todo.id ? { ...item, travel_duration_seconds: estimate.duration_seconds, travel_depart_at: estimate.depart_at, travel_last_checked_at: estimate.checked_at } : item);
      detailItem = detailItem ? { ...detailItem, todoData: { ...todo, travel_duration_seconds: estimate.duration_seconds, travel_depart_at: estimate.depart_at, travel_last_checked_at: estimate.checked_at } } : null;
    }, () => { travelUpdateError = 'Bitte erlaube den Standortzugriff, um die Anreise zu aktualisieren.'; }, { enableHighAccuracy: false, timeout: 10_000, maximumAge: 60_000 });
  }

  async function refreshMonitoredTravel() {
    const monitored = todos.filter((todo) => todo.travel_monitoring_enabled && todo.place_id && todo.start_time && todo.travel_mode && todo.status === 'open' && todo.id);
    if (!monitored.length || !navigator.geolocation) return;
    try {
      const permission = await navigator.permissions?.query({ name: 'geolocation' as PermissionName });
      if (permission?.state !== 'granted') return;
    } catch {
      // Browsers without the Permissions API must wait for an explicit update.
      return;
    }
    navigator.geolocation.getCurrentPosition(async (position) => {
      const estimates = await Promise.all(monitored.map(async (todo) => ({ todo, estimate: await api.estimateTodoTravel(todo.id!, position.coords.latitude, position.coords.longitude) })));
      const updates = new Map(estimates.filter((entry) => entry.estimate).map((entry) => [entry.todo.id, entry.estimate!]));
      if (!updates.size) return;
      todos = todos.map((todo) => {
        const estimate = updates.get(todo.id);
        return estimate ? { ...todo, travel_duration_seconds: estimate.duration_seconds, travel_depart_at: estimate.depart_at, travel_last_checked_at: estimate.checked_at } : todo;
      });
    }, () => {}, { enableHighAccuracy: false, timeout: 10_000, maximumAge: 60_000 });
  }

  function handleTap(item: UnifiedItem, e: MouseEvent) {
    if (longPressTriggered) { longPressTriggered = false; return; }
    if (item.type === 'training' || item.type === 'meal' || item.type === 'todo') return;
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
      const meal = item.entryData;
      if (!meal?.id) return;
      const previousMeal = meal;
      const nextStatus = meal.status === 'consumed' ? 'planned' : 'consumed';
      // Give immediate feedback: the intake total is derived from this local
      // state, so it changes in the same UI update as the checkmark.
      mealEntries = mealEntries.map((current) => current.id === meal.id
        ? { ...current, status: nextStatus, consumed_at: nextStatus === 'consumed' ? new Date().toISOString() : null }
        : current);
      try {
        // A status toggle is intentionally independent of an older edit
        // timestamp.  Otherwise a harmless background refresh can reject the
        // checkmark and leave the nutrient intake unchanged.
        const updated = await api.setMealEntryStatus(meal.id, nextStatus);
        if (!updated) {
          mealEntries = mealEntries.map((current) => current.id === meal.id ? previousMeal : current);
          return;
        }
        mealEntries = mealEntries.map((current) => current.id === meal.id ? { ...current, ...updated } : current);
        // Re-read after the mutation so the tile always uses the server's
        // complete nutrition snapshot, including after a fast double tap or
        // another client changed the same day.
        const refreshed = await refreshMealEntryFromServer(meal.id).catch(() => null);
        dispatch('mealentrychange', { entry: refreshed ?? updated });
      } catch {
        mealEntries = mealEntries.map((current) => current.id === meal.id ? previousMeal : current);
      }
      return;
    }
    if (item.type === 'training' && entry) { const newVal = !entry.training_done; try { await api.upsertDayEntry({ ...entry, training_done: newVal, date: currentDate }); entry = { ...entry, training_done: newVal }; dispatch('trainingtoggle', newVal); } catch {} return; }
    if (item.type === 'cardio' && entry) { const newVal = !entry.cardio_done; try { await api.upsertDayEntry({ ...entry, cardio_done: newVal, date: currentDate }); entry = { ...entry, cardio_done: newVal }; dispatch('cardiotoggle', newVal); } catch {} return; }
    if (item.type === 'todo') { const todoId = item.id.replace('todo-', ''); try { const updated = await api.markTodoDone(todoId); if (!updated) return; todos = todos.map((t) => String(t.id) === todoId ? { ...t, ...updated } : t); dispatch('todotoggle', { id: todoId, status: updated.status }); } catch {} return; }
  }

  async function updateMetric(field: string, value: any) { if (!entry) return; entry = { ...entry, [field]: value }; if (field === 'weight_kg') { entry = { ...entry, weight_source: 'manual' }; } try { await api.upsertDayEntry({ ...entry, date: currentDate }); dispatch('update', { field, value }); } catch {} }

  async function loadWeightEstimate() {
    const request = ++estimateRequest;
    estimatedWeight = null;
    if (entry?.weight_kg != null) return;

    const selected = new Date(`${currentDate}T00:00`);
    const end = new Date(selected);
    end.setDate(end.getDate() + 30);
    try {
      const response = await api.getStatsTrend('weight', 61, localDateStr(end));
      if (request !== estimateRequest || entry?.weight_kg != null) return;
      const points = (response?.points ?? [])
        .filter((point) => point.value != null)
        .map((point) => ({ date: point.date, value: Number(point.value) }));
      const before = points.filter((point) => point.date < currentDate).at(-1);
      const after = points.find((point) => point.date > currentDate);
      if (!before || !after) return;
      const beforeDate = new Date(`${before.date}T00:00`);
      const afterDate = new Date(`${after.date}T00:00`);
      const spanDays = (afterDate.getTime() - beforeDate.getTime()) / 86_400_000;
      const offsetDays = (selected.getTime() - beforeDate.getTime()) / 86_400_000;
      if (spanDays <= 0 || offsetDays > 30 || spanDays - offsetDays > 30) return;
      estimatedWeight = { value: Math.round((before.value + (after.value - before.value) * offsetDays / spanDays) * 10) / 10, beforeDate: before.date, afterDate: after.date };
    } catch {
      // An unavailable trend must never turn a missing measurement into a value.
    }
  }

  function finishWeightEdit(value: string) {
    const parsed = parseFloat(value);
    if (!Number.isNaN(parsed) || entry.weight_kg != null) updateMetric('weight_kg', Number.isNaN(parsed) ? null : parsed);
    weightEditing = false;
  }

  $: if (currentDate && entry?.weight_kg == null) loadWeightEstimate();
  function handleTrainingComplete() { if (entry) { entry = { ...entry, training_done: true }; dispatch('trainingtoggle', true); } }


  function openItemDetails(item: UnifiedItem, trigger?: HTMLElement) {
    if (item.id === 'metric-steps' || item.id === 'metric-sleep') {
      openMetricTrend(item, trigger);
      return;
    }
    closeOpenTodoDetails();
    detailItemTrigger = trigger ?? null;
    detailItemOverlayTop = null;
    detailItem = item;
    void tick().then(positionDetailItemOverlay);
  }
  function closeItemDetails() {
    detailItem = null;
    weightEditing = false;
    detailItemOverlayTop = null;
    const trigger = detailItemTrigger;
    detailItemTrigger = null;
    setTimeout(() => trigger?.focus(), 0);
  }

  function overlayTopFor(trigger: HTMLElement | null, overlay: HTMLDialogElement | null) {
    const card = overlay?.firstElementChild as HTMLElement | null;
    if (!trigger || !card || typeof window === 'undefined') return null;
    const viewportHeight = window.visualViewport?.height ?? window.innerHeight;
    const headerBottom = document.querySelector<HTMLElement>('.hdr')?.getBoundingClientRect().bottom ?? 16;
    const navTop = document.querySelector<HTMLElement>('.day-footer')?.getBoundingClientRect().top ?? viewportHeight - 16;
    const safeTop = Math.max(16, headerBottom + 12);
    const safeBottom = Math.min(viewportHeight - 16, navTop - 12);
    const triggerRect = trigger.getBoundingClientRect();
    const cardHeight = card.getBoundingClientRect().height;
    const preferredTop = triggerRect.top + triggerRect.height / 2 - cardHeight / 2;
    const maximumTop = Math.max(safeTop, safeBottom - cardHeight);
    return Math.round(Math.min(Math.max(preferredTop, safeTop), maximumTop));
  }

  function positionDetailItemOverlay() { detailItemOverlayTop = overlayTopFor(detailItemTrigger, detailItemOverlay); }
  function positionMetricTrendOverlay() { metricTrendOverlayTop = overlayTopFor(metricTrendTrigger, metricTrendOverlay); }
  function positionNutritionDetailsOverlay() { nutritionDetailsOverlayTop = overlayTopFor(nutritionDetailsTrigger, nutritionDetailsOverlay); }

  onMount(() => {
    const reposition = () => {
      if (detailItem) positionDetailItemOverlay();
      if (metricTrendItem) positionMetricTrendOverlay();
      if (nutritionDetailsOpen) positionNutritionDetailsOverlay();
    };
    window.addEventListener('resize', reposition);
    window.visualViewport?.addEventListener('resize', reposition);
    void refreshMonitoredTravel();
    const travelTimer = window.setInterval(() => { if (document.visibilityState === 'visible') void refreshMonitoredTravel(); }, 5 * 60_000);
    return () => {
      window.removeEventListener('resize', reposition);
      window.visualViewport?.removeEventListener('resize', reposition);
      window.clearInterval(travelTimer);
    };
  });

  async function openMetricTrend(item: UnifiedItem, trigger?: HTMLElement) {
    closeOpenTodoDetails();
    metricTrendItem = item;
    metricTrend = [];
    metricTrendRange = 7;
    metricTrendError = '';
    metricTrendLoading = true;
    metricTrendTrigger = trigger ?? null;
    metricTrendOverlayTop = null;
    await tick();
    positionMetricTrendOverlay();
    metricTrendCloseButton?.focus();
    try {
      const metric = item.id === 'metric-weight' ? 'weight' : item.id === 'metric-steps' ? 'steps' : 'sleep_hours';
      const response = await api.getStatsTrend(metric, 365);
      metricTrend = (response?.points ?? []).filter((point) => point.value != null);
    } catch {
      metricTrendError = 'Der Verlauf konnte gerade nicht geladen werden.';
    } finally {
      metricTrendLoading = false;
      await tick();
      positionMetricTrendOverlay();
    }
  }

  function closeMetricTrend() {
    metricTrendItem = null;
    metricTrend = [];
    metricTrendOverlayTop = null;
    const trigger = metricTrendTrigger;
    metricTrendTrigger = null;
    setTimeout(() => trigger?.focus(), 0);
  }

  async function openNutritionDetails(trigger: HTMLElement) {
    closeOpenTodoDetails();
    nutritionDetailsTrigger = trigger;
    nutritionDetailsOverlayTop = null;
    nutritionDetailsOpen = true;
    await tick();
    positionNutritionDetailsOverlay();
    nutritionDetailsCloseButton?.focus();
  }

  function closeNutritionDetails() {
    nutritionDetailsOpen = false;
    nutritionDetailsOverlayTop = null;
    const trigger = nutritionDetailsTrigger;
    nutritionDetailsTrigger = null;
    setTimeout(() => trigger?.focus(), 0);
  }

  function metricChart(points: TrendPoint[], numDays: number, item: UnifiedItem) {
    if (!points.length) return null;
    const anchor = new Date(); anchor.setHours(0, 0, 0, 0);
    const days = buildTrendLine(points, localDateStr(anchor), numDays);
    if (!days.length) return null;
    const displayDays = numDays === 365 ? aggregateWeeks(days) : days;
    const values = displayDays.map((day) => day.value);
    const actualValues = days.filter((day) => day.state === 'actual').map((day) => day.value);
    const min = Math.min(...actualValues);
    const max = Math.max(...actualValues);
    const minimumRange = item.id === 'metric-weight' ? 5 : Math.max(Math.abs(max - min) * 1.5, Math.abs(max) * 0.2, 1);
    const scaleMin = Math.floor(min - Math.max((minimumRange - (max - min)) / 2, minimumRange * 0.1));
    const scaleMax = Math.ceil(max + Math.max((minimumRange - (max - min)) / 2, minimumRange * 0.1));
    const range = scaleMax - scaleMin || 1;
    const width = 300;
    const height = 120;
    const plotLeft = 42;
    const plotRight = 8;
    const plotTop = 8;
    const plotBottom = 22;
    const plotHeight = height - plotTop - plotBottom;
    const coords = values.map((value, index) => ({
      x: displayDays.length === 1 ? (plotLeft + width - plotRight) / 2 : plotLeft + index * ((width - plotLeft - plotRight) / (displayDays.length - 1)),
      y: plotTop + plotHeight - ((value - scaleMin) / range) * plotHeight,
    }));
    const paths = trendSegmentPaths(displayDays, coords);
    const average = actualValues.reduce((sum, value) => sum + value, 0) / actualValues.length;
    const yTicks = Array.from({ length: 4 }, (_, index) => {
      const value = scaleMax - index * range / 3;
      return { value, y: plotTop + index * plotHeight };
    });
    const labelStep = numDays <= 7 ? 1 : numDays <= 30 ? 5 : Math.max(1, Math.floor(displayDays.length / 12));
    const labels = displayDays.map((day, index) => {
      if (index % labelStep !== 0 && index !== displayDays.length - 1) return null;
      const date = new Date(`${day.date}T00:00`);
      return { date: day.date, label: numDays <= 7 ? date.toLocaleDateString('de-DE', { weekday: 'short', day: '2-digit' }).replace('.', '') : date.toLocaleDateString('de-DE', { day: 'numeric', month: 'short' }) };
    }).filter((label) => label !== null) as { date: string; label: string }[];
    return { ...paths, coords, days: displayDays, labels, yTicks, plotLeft, plotRight, plotBottom, first: days[0].date, last: days[days.length - 1].date, min, max, average };
  }

  function aggregateWeeks(days: ReturnType<typeof buildTrendLine>) {
    const weeks = [] as ReturnType<typeof buildTrendLine>;
    for (let start = 0; start < days.length; start += 7) {
      const week = days.slice(start, start + 7);
      const measurements = week.filter((day) => day.state === 'actual');
      const value = measurements.length
        ? measurements.reduce((sum, day) => sum + day.value, 0) / measurements.length
        : week.reduce((sum, day) => sum + day.value, 0) / week.length;
      weeks.push({
        date: week.at(-1)!.date,
        value,
        state: measurements.length ? 'actual' : week.some((day) => day.state === 'interpolated') ? 'interpolated' : 'baseline',
      });
    }
    return weeks;
  }

  function formatTrendDate(value: string) { return new Date(`${value}T00:00`).toLocaleDateString('de-DE', { day: '2-digit', month: 'short', year: 'numeric' }); }
  function trendRangeLabel(days: number) { return days === 7 ? 'letzte 7 Tage' : days === 30 ? 'letzte 30 Tage' : 'letzte 365 Tage · Wochenwerte'; }
  function formatTrendValue(value: number, item: UnifiedItem) {
    if (item.id === 'metric-weight') return `${value.toLocaleString('de-DE', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} kg`;
    if (item.id === 'metric-sleep') return `${value.toLocaleString('de-DE', { maximumFractionDigits: 1 })} h`;
    return Math.round(value).toLocaleString('de-DE');
  }

  function metricTrendColor(_item: UnifiedItem) { return 'var(--status-info)'; }

  function getMealFromItem(item: UnifiedItem): MealEntry | undefined { return item.entryData; }

  $: weightItem = unifiedItems.find((i) => i.id === 'metric-weight');
  $: biometricItems = unifiedItems.filter((i) => i.biometric && i.id !== 'metric-weight');
  $: manualItems = unifiedItems.filter((i) => !i.biometric);
  $: openCount = manualItems.filter((i) => !i.done).length;
  $: recommendedTodo = [...todos]
    .filter((todo) => todo.status === 'open')
    .sort((a, b) => todoTime(a) - todoTime(b) || b.priority - a.priority)[0] ?? null;
  $: recommendedTodoItem = recommendedTodo ? unifiedItems.find((item) => item.type === 'todo' && item.todoData?.id === recommendedTodo?.id) ?? null : null;
  $: recommendedTodoReadyForTravel = Boolean(recommendedTodo?.place_id && recommendedTodo?.start_time && recommendedTodo?.travel_mode);
  const NUTRIENT_GROUPS: Array<{ title: string; values: Array<{ key: keyof Nutrition; label: string; unit: string }> }> = [
    { title: 'Makronährstoffe', values: [
      { key: 'kcal', label: 'Energie', unit: 'kcal' }, { key: 'protein_g', label: 'Protein', unit: 'g' },
      { key: 'carbs_g', label: 'Kohlenhydrate', unit: 'g' }, { key: 'fat_g', label: 'Fett', unit: 'g' },
      { key: 'saturated_fat_g', label: 'Gesättigte Fettsäuren', unit: 'g' }, { key: 'fiber_g', label: 'Ballaststoffe', unit: 'g' },
      { key: 'sugar_g', label: 'Zucker', unit: 'g' }, { key: 'free_sugar_g', label: 'Freie Zucker', unit: 'g' },
    ] },
    { title: 'Mineralstoffe', values: [
      { key: 'sodium_mg', label: 'Natrium', unit: 'mg' }, { key: 'potassium_mg', label: 'Kalium', unit: 'mg' },
      { key: 'calcium_mg', label: 'Calcium', unit: 'mg' }, { key: 'magnesium_mg', label: 'Magnesium', unit: 'mg' },
      { key: 'iron_mg', label: 'Eisen', unit: 'mg' }, { key: 'zinc_mg', label: 'Zink', unit: 'mg' },
    ] },
    { title: 'Vitamine', values: [
      { key: 'vitamin_a_ug', label: 'Vitamin A', unit: 'µg' }, { key: 'vitamin_c_mg', label: 'Vitamin C', unit: 'mg' },
      { key: 'vitamin_d_ug', label: 'Vitamin D', unit: 'µg' }, { key: 'vitamin_b12_ug', label: 'Vitamin B12', unit: 'µg' },
      { key: 'folate_ug', label: 'Folat', unit: 'µg' },
    ] },
  ];
  // The tile is an intake balance: only entries explicitly checked as
  // consumed count.  Updating a meal's status updates this reactive total
  // immediately, without waiting for a page reload.
  $: nutritionDayEntries = mealEntries.filter((entry) => entry.status === 'consumed');
  $: nutritionTotals = Object.fromEntries(NUTRIENT_GROUPS.flatMap((group) => group.values.map(({ key }) => {
    const values = nutritionDayEntries.map((entry) => entry.nutrition?.[key]);
    const known = values.filter((value): value is number => value != null).map(Number);
    return [key, known.length ? known.reduce((sum, value) => sum + value, 0) : null];
  }))) as Record<keyof Nutrition, number | null>;
  $: nutritionIncomplete = Object.fromEntries(NUTRIENT_GROUPS.flatMap((group) => group.values.map(({ key }) => [
    key,
    nutritionDayEntries.some((entry) => entry.nutrition?.[key] == null),
  ]))) as Record<keyof Nutrition, boolean>;
  function formatNutrient(value: number | null, incomplete: boolean, unit: string) {
    if (value == null) return '-';
    const digits = unit === 'kcal' ? 0 : value < 10 ? 1 : 0;
    const prefix = incomplete ? '≥ ' : '';
    return `${prefix}${value.toLocaleString('de-DE', { maximumFractionDigits: digits })} ${unit}`;
  }
  // Keep display strings in an explicit reactive value. The compact tile must
  // re-render its macros in the same update cycle as the kcal total.
  $: nutritionDisplay = Object.fromEntries(NUTRIENT_GROUPS.flatMap((group) => group.values.map(({ key, unit }) => [
    key,
    formatNutrient(nutritionTotals[key], nutritionIncomplete[key], unit),
  ]))) as Record<keyof Nutrition, string>;

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

</script>

<div class="daily-overview" aria-label="Tagesübersicht">
<!-- Biometrics: Schritte + Schlaf nebeneinander -->
{#if biometricItems.length > 0}
  <div class="biometrics-row">
    {#each biometricItems as item (item.id)}
      {#if item.id === 'metric-steps'}
        {@const reached = (item.progressCurrent ?? 0) >= (item.progressTarget ?? 1)}
        <div class="bio-section biometric-trend-target" role="group" aria-label="Schritte"
          onpointerdown={(event) => handlePressStart(item, event)}
          onpointerup={handlePressEnd}
          onpointermove={handlePressMove}
          onpointerleave={handlePressEnd}
          onpointercancel={handlePressEnd}
          oncontextmenu={(event) => handleContextMenu(item, event)}>
          <div class="bio-hdr">
            <span class="bio-title"><Icon name={item.icon} size={14} /> {item.title}</span>
            <button class="longpress-indicator" type="button" onpointerdown={(event) => event.stopPropagation()} onclick={(event) => { event.stopPropagation(); openMetricTrend(item, event.currentTarget); }} aria-label="Schritte-Details anzeigen. Langes Drücken auf die Kachel öffnet sie ebenfalls."><span aria-hidden="true"></span></button>
          </div>
          <div class="bio-value-lg">
            {(item.metricValue ?? 0).toLocaleString('de')}
            <span class="bio-target">/ {item.progressTarget?.toLocaleString('de') ?? '—'}</span>
          </div>
          <ProgressBar current={item.progressCurrent ?? 0} target={item.progressTarget ?? 1} color={reached ? 'var(--status-success)' : 'var(--text-secondary)'} />
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
            <button class="longpress-indicator" type="button" onpointerdown={(event) => event.stopPropagation()} onclick={(event) => { event.stopPropagation(); openMetricTrend(item, event.currentTarget); }} aria-label="Schlaf-Details anzeigen. Langes Drücken auf die Kachel öffnet sie ebenfalls."><span aria-hidden="true"></span></button>
          </div>
          <div class="bio-value-lg">{sleepTotal > 0 ? fmtShort(sleepTotal) : '—'}</div>
          <ProgressBar current={item.progressCurrent ?? 0} target={item.progressTarget ?? 1} color="var(--text-secondary)" />
        </div>
      {/if}
    {/each}
  </div>
{/if}

<!-- Tageswerte: Gewicht und Ernährung -->
<div class="feature-card-row">
{#if weightItem}
  <section class="weight-section" role="group" aria-label="Gewicht"
    onpointerdown={(event) => handlePressStart(weightItem, event)}
    onpointerup={handlePressEnd}
    onpointermove={handlePressMove}
    onpointerleave={handlePressEnd}
    onpointercancel={handlePressEnd}
    oncontextmenu={(event) => handleContextMenu(weightItem, event)}>
    <div class="bio-hdr">
      <span class="bio-title"><Icon name={weightItem.icon} size={14} /> {weightItem.title}</span>
      <button class="longpress-indicator" type="button" onpointerdown={(event) => event.stopPropagation()} onclick={(event) => { event.stopPropagation(); openItemDetails(weightItem, event.currentTarget); }} aria-label="Gewichts-Details anzeigen. Langes Drücken auf die Kachel öffnet sie ebenfalls."><span aria-hidden="true"></span></button>
    </div>
    <div class="weight-value-row">
      <span class="weight-value">{weightItem.metricValue != null ? Number(weightItem.metricValue).toFixed(1) : '—'} <span class="bio-unit">kg</span></span>
    </div>
  </section>
{/if}
  <section class="nutrition-section" aria-labelledby="nutrition-title">
    <div class="bio-hdr">
      <span class="bio-title" id="nutrition-title"><Icon name="meal" size={14} /> Energie</span>
      <button class="longpress-indicator" type="button" onclick={(event) => openNutritionDetails(event.currentTarget)} aria-label="Nährwertdetails anzeigen"><span aria-hidden="true"></span></button>
    </div>
    <div class="nutrition-kcal"><span>{nutritionTotals.kcal == null ? '—' : Math.round(nutritionTotals.kcal).toLocaleString('de-DE')}</span><small>kcal{goals.kcal ? ` / ${Number(goals.kcal).toLocaleString('de-DE')}` : ''}</small></div>
  </section>
</div>

</div>

{#if recommendedTodo}
  <section class="todo-highlight" aria-labelledby="todo-highlight-title">
    <div class="todo-highlight-copy">
      <p>NÄCHSTE AUFGABE</p>
      <h2 id="todo-highlight-title">{recommendedTodo.title}</h2>
      {#if recommendedTodoReadyForTravel}
        <span>{recommendedTodo.start_time} · {recommendedTodo.place_name}{#if recommendedTodo.travel_depart_at} · los {new Date(recommendedTodo.travel_depart_at).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })}{/if}</span>
      {:else if recommendedTodo.start_time || recommendedTodo.due_time}
        <span>{recommendedTodo.start_time ?? recommendedTodo.due_time} · Planung ergänzen</span>
      {:else}
        <span>Als nächste offene Aufgabe empfohlen</span>
      {/if}
    </div>
    <div class="todo-highlight-actions">
      {#if recommendedTodoReadyForTravel}
        <button type="button" class="highlight-secondary" onclick={() => updateTravel(recommendedTodo)}>Anreise aktualisieren</button>
        <button type="button" class="highlight-primary" onclick={() => openNavigation(recommendedTodo)}>Navigation</button>
      {:else if recommendedTodoItem}
        <button type="button" class="highlight-primary" onclick={(event) => openItemDetails(recommendedTodoItem!, event.currentTarget)}>Planung öffnen</button>
      {/if}
    </div>
    {#if travelUpdateError}<p class="todo-highlight-error" role="alert">{travelUpdateError}</p>{/if}
  </section>
{/if}

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
          {#if item.type === 'todo' && item.travelLabel}<span class="item-travel">{item.travelLabel}</span>{/if}
        </div>
      </div>
      {#if item.type === 'meal' || item.type === 'todo' || item.type === 'training'}
        <button class="longpress-indicator item-detail-indicator" type="button" onpointerdown={(event) => event.stopPropagation()} onclick={(event) => { event.stopPropagation(); openItemDetails(item, event.currentTarget); }} aria-label={`Details zu ${item.title} anzeigen. Langes Drücken auf die Zeile öffnet sie ebenfalls.`}><span aria-hidden="true"></span></button>
      {/if}
      {#if item.type === 'metric'}
        <MetricRow icon="" label="" value={item.metricValue} unit={item.metricUnit ?? ''} editable={item.metricEditable ?? false} checkable={false} on:change={(e) => updateMetric(item.metricField!, e.detail)} />
      {/if}
      {#if item.hasProgress}<div class="item-prog"><ProgressBar current={item.progressCurrent ?? 0} target={item.progressTarget ?? 1} color="var(--text-secondary)" /></div>{/if}
    </div>

  {/each}

</div>

<MealEntryEditorSheet meal={mealEntryEditorItem ? getMealFromItem(mealEntryEditorItem) ?? null : null} open={Boolean(mealEntryEditorItem)} autoOpenCamera={mealEntryEditorCamera} on:close={closeMealEntryEditor} on:saved={(event) => { applyMealEntryUpdate(event.detail.entry); closeMealEntryEditor(); }} />

{#if nutritionDetailsOpen}
  <dialog bind:this={nutritionDetailsOverlay} class="modal-overlay trend-overlay" class:overlay-positioned={nutritionDetailsOverlayTop !== null} style={nutritionDetailsOverlayTop === null ? undefined : `--overlay-offset-top: ${nutritionDetailsOverlayTop}px`} open aria-labelledby="nutrition-detail-title" onclick={(event) => { if (event.target === event.currentTarget) closeNutritionDetails(); }} oncancel={(event) => { event.preventDefault(); closeNutritionDetails(); }}>
    <section class="modal-card trend-detail ui-dialog">
      <header class="detail-header ui-dialog__header"><div><p class="detail-kind ui-dialog__eyebrow">Tagesübersicht</p><h2 id="nutrition-detail-title">Nährstoffe</h2></div><button bind:this={nutritionDetailsCloseButton} class="detail-close ui-dialog__close" type="button" aria-label="Nährwertdetails schließen" onclick={closeNutritionDetails}>×</button></header>
      <p class="nutrition-intro">Summen aus den verzehrten Mahlzeiten dieses Tages. „≥“ bedeutet: Ein Teil der Zutaten hat noch keine Referenzwerte.</p>
      {#each NUTRIENT_GROUPS as group}
        <section class="nutrient-group ui-dialog__section" aria-labelledby={`nutrient-group-${group.title}`}>
          <h3 id={`nutrient-group-${group.title}`}>{group.title}</h3>
          <div class="nutrition-detail-grid">
            {#each group.values as nutrient}
              <span><b>{nutritionDisplay[nutrient.key]}</b>{nutrient.label}</span>
            {/each}
          </div>
        </section>
      {/each}
    </section>
  </dialog>
{/if}

{#if metricTrendItem}
  {@const chart = metricChart(metricTrend, metricTrendRange, metricTrendItem)}
  <dialog bind:this={metricTrendOverlay} class="modal-overlay trend-overlay" class:overlay-positioned={metricTrendOverlayTop !== null} style={metricTrendOverlayTop === null ? undefined : `--overlay-offset-top: ${metricTrendOverlayTop}px`} open aria-labelledby="metric-trend-title" onclick={(event) => { if (event.target === event.currentTarget) closeMetricTrend(); }} oncancel={(event) => { event.preventDefault(); closeMetricTrend(); }}>
    <section class="modal-card trend-detail ui-dialog">
      <header class="detail-header ui-dialog__header">
        <div><p class="detail-kind ui-dialog__eyebrow">Verlauf · {trendRangeLabel(metricTrendRange)}</p><h2 id="metric-trend-title">{metricTrendItem.title}</h2></div>
        <button bind:this={metricTrendCloseButton} class="detail-close ui-dialog__close" type="button" aria-label="Verlauf schließen" onclick={closeMetricTrend}>×</button>
      </header>
      {#if metricTrendLoading}
        <p class="detail-meta">Verlauf wird geladen …</p>
      {:else if metricTrendError}
        <p class="detail-meta">{metricTrendError}</p>
      {:else if chart}
        <div class="trend-range-tabs" aria-label="Zeitraum auswählen">
          <button class:active={metricTrendRange === 7} type="button" onclick={() => (metricTrendRange = 7)}>W</button>
          <button class:active={metricTrendRange === 30} type="button" onclick={() => (metricTrendRange = 30)}>M</button>
          <button class:active={metricTrendRange === 365} type="button" onclick={() => (metricTrendRange = 365)}>J</button>
        </div>
        <div class="trend-summary ui-dialog__section" aria-label={`Zusammenfassung für ${metricTrendItem.title}`}>
          <span><b>{formatTrendValue(chart.average, metricTrendItem)}</b> Ø</span>
          <span><b>{formatTrendValue(chart.min, metricTrendItem)}</b> min.</span>
          <span><b>{formatTrendValue(chart.max, metricTrendItem)}</b> max.</span>
        </div>
        <p class="trend-legend"><span class="trend-key actual"></span>Messwert <span class="trend-key interpolated"></span>interpoliert <span class="trend-key baseline"></span>Baseline</p>
        <svg class="metric-trend-chart" viewBox="0 0 300 120" role="img" aria-label={`${metricTrendItem.title} von ${formatTrendDate(chart.first)} bis ${formatTrendDate(chart.last)}`}>
          {#each chart.yTicks as tick}
            <line x1={chart.plotLeft} y1={tick.y} x2={300 - chart.plotRight} y2={tick.y} stroke="var(--border-subtle)" stroke-width="1" />
            <text x={chart.plotLeft - 6} y={tick.y + 3} text-anchor="end" fill="var(--text-tertiary)" font-size="9">{formatTrendValue(tick.value, metricTrendItem)}</text>
          {/each}
          <line x1={chart.plotLeft} y1={120 - chart.plotBottom} x2={300 - chart.plotRight} y2={120 - chart.plotBottom} stroke="var(--border-default)" stroke-width="1" />
          {#if chart.baseline}<path d={chart.baseline} fill="none" stroke="var(--text-tertiary)" stroke-width="1.5" stroke-dasharray="3 3" stroke-linecap="round" />{/if}
          {#if chart.interpolated}<path d={chart.interpolated} fill="none" stroke={metricTrendColor(metricTrendItem)} stroke-width="1.8" stroke-dasharray="3 3" stroke-linecap="round" stroke-linejoin="round" />{/if}
          {#if chart.actual}<path d={chart.actual} fill="none" stroke={metricTrendColor(metricTrendItem)} stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />{/if}
          {#each chart.coords as point, index}
            {#if chart.days[index].state === 'actual'}<circle cx={point.x} cy={point.y} r={metricTrendRange === 365 ? 0 : 2.5} fill={metricTrendColor(metricTrendItem)}><title>{formatTrendDate(chart.days[index].date)}: {formatTrendValue(chart.days[index].value, metricTrendItem)}</title></circle>{/if}
          {/each}
        </svg>
        <div class="trend-axis">{#each chart.labels as label}<span>{label.label}</span>{/each}</div>
      {:else}
        <p class="detail-empty">Für diesen Zeitraum sind noch keine Daten vorhanden.</p>
      {/if}
    </section>
  </dialog>
{/if}

{#if detailItem}
  <dialog bind:this={detailItemOverlay} class="modal-overlay compact-overlay" class:overlay-positioned={detailItemOverlayTop !== null} style={detailItemOverlayTop === null ? undefined : `--overlay-offset-top: ${detailItemOverlayTop}px`} open aria-labelledby="detail-title" onclick={(event) => { if (event.target === event.currentTarget) closeItemDetails(); }} oncancel={(event) => { event.preventDefault(); closeItemDetails(); }}>
    <div class="modal-card compact-detail ui-dialog">
      <header class="detail-header ui-dialog__header"><div><p class="detail-kind ui-dialog__eyebrow">{detailItem.type === 'meal' ? 'Mahlzeit' : detailItem.type === 'training' ? 'Training' : detailItem.type === 'todo' ? 'To-do' : 'Tageswert'}</p><h2 id="detail-title">{detailItem.title}</h2></div><button class="detail-close ui-dialog__close" type="button" aria-label="Details schließen" onclick={closeItemDetails}>×</button></header>
      {#if detailItem.type === 'meal'}
        {@const detailMeal = getMealFromItem(detailItem)}
        <div class="modal-pills">
          {#if detailMeal?.nutrition?.kcal != null}<PillBadge value={Math.round(Number(detailMeal.nutrition.kcal))} unit="kcal" color="var(--data-nutrition-energy)" />{/if}
          {#if detailMeal?.nutrition?.protein_g != null}<PillBadge value={Math.round(Number(detailMeal.nutrition.protein_g))} unit="g Protein" color="var(--data-nutrition-protein)" />{/if}
          {#if detailMeal?.nutrition?.carbs_g != null}<PillBadge value={Math.round(Number(detailMeal.nutrition.carbs_g))} unit="g KH" color="var(--data-nutrition-carbs)" />{/if}
          {#if detailMeal?.nutrition?.fat_g != null}<PillBadge value={Math.round(Number(detailMeal.nutrition.fat_g))} unit="g Fett" color="var(--data-nutrition-fat)" />{/if}
        </div>
        <div class="modal-actions ui-dialog__actions"><button class="modal-secondary" onclick={() => { mealEntryEditorItem = detailItem; closeItemDetails(); }}>Mahlzeit anpassen</button><button class="modal-primary" onclick={() => { mealEntryEditorCamera = true; mealEntryEditorItem = detailItem; closeItemDetails(); }}>Mahlzeit fotografieren</button></div>
      {:else if detailItem.type === 'todo'}
        <div class="detail-section ui-dialog__section">
          {#if detailItem.todoData?.category}<p class="detail-meta">Kategorie: {detailItem.todoData.category}</p>{/if}
          {#if detailItem.todoData?.due_time || detailItem.todoData?.start_time}<p class="detail-meta">{detailItem.todoData.start_time ? `Beginn um ${detailItem.todoData.start_time}` : `Fällig um ${detailItem.todoData?.due_time}`}</p>{/if}
          {#if detailItem.todoData?.place_name}<p class="detail-meta">Ort: {detailItem.todoData.place_name}{#if detailItem.todoData.place_address} · {detailItem.todoData.place_address}{/if}</p>{/if}
          {#if detailItem.todoData?.travel_monitoring_enabled}<p class="detail-meta">Anreise aktiv{#if detailItem.todoData.travel_last_checked_at} · zuletzt geprüft {new Date(detailItem.todoData.travel_last_checked_at).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })}{/if}</p>{/if}
          {#if !detailItem.todoData?.category && !detailItem.todoData?.due_time && !detailItem.todoData?.start_time && !detailItem.todoData?.place_name}<p class="detail-meta">Keine zusätzlichen Angaben.</p>{/if}
        </div>
        {#if detailItem.todoData?.place_id && detailItem.todoData?.travel_mode && detailItem.todoData?.start_time}
          <div class="travel-actions"><button class="modal-secondary" onclick={() => updateTravel(detailItem!.todoData!)}>Anreise aktualisieren</button><button class="modal-primary" onclick={() => openNavigation(detailItem!.todoData!)}>Navigation</button></div>
        {/if}
        {#if travelUpdateError}<p class="detail-meta detail-error" role="alert">{travelUpdateError}</p>{/if}
        <button class="modal-secondary" onclick={() => { actionSheetItem = detailItem; closeItemDetails(); }}>Bearbeiten</button>
      {:else if detailItem.type === 'training'}
        <TrainingDetail training_type={trainingSuggestion?.training_type ?? entry?.training_type ?? 'Training'} date={currentDate} oncomplete={handleTrainingComplete} onclose={closeItemDetails} showClose={false} />
      {:else if detailItem.id === 'metric-weight'}
        <div class="detail-section ui-dialog__section">
          <p class="detail-meta">{detailItem.metricValue != null ? `${Number(detailItem.metricValue).toFixed(1)} kg` : 'Noch kein Gewicht erfasst'}</p>
          {#if detailItem.weightDetails?.bmi != null}<p class="detail-meta">BMI: {detailItem.weightDetails.bmi}</p>{/if}
          {#if detailItem.weightSource === 'scale_esp'}<p class="detail-meta">Quelle: Waage</p>{:else if detailItem.weightSource === 'manual'}<p class="detail-meta">Quelle: manuell</p>{:else if detailItem.weightEstimate}<p class="detail-meta">Schätzung aus Messungen vom {formatTrendDate(detailItem.weightEstimate.beforeDate)} und {formatTrendDate(detailItem.weightEstimate.afterDate)}.</p>{/if}
          {#if weightEditing}
            <label class="detail-field">Gewicht in kg<input class="weight-input" type="number" step="0.1" min="0" max="300" value={entry.weight_kg ?? ''} onblur={(event) => finishWeightEdit(event.currentTarget.value)} onkeydown={(event) => { if (event.key === 'Enter') event.currentTarget.blur(); if (event.key === 'Escape') weightEditing = false; }}></label>
          {:else}
            <button class="modal-secondary" type="button" onclick={() => weightEditing = true}>Gewicht erfassen</button>
          {/if}
        </div>
        <button class="modal-primary" type="button" onclick={(event) => openMetricTrend(detailItem!, event.currentTarget)}>Verlauf öffnen</button>
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
  .daily-overview { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:6px; }
  .daily-overview > .biometrics-row,.daily-overview > .feature-card-row { display:contents; }
  .daily-overview .bio-section,.daily-overview .weight-section,.daily-overview .nutrition-section { min-width:0; }
  .todo-highlight { display:grid; gap:10px; padding:12px; border:1px solid var(--border-default); border-radius:var(--radius-surface); background:var(--surface-accent); }
  .todo-highlight-copy { display:grid; gap:3px; min-width:0; }
  .todo-highlight-copy p { margin:0; color:var(--text-secondary); font-size:10px; font-weight:750; letter-spacing:.06em; }
  .todo-highlight-copy h2 { margin:0; overflow:hidden; color:var(--text-primary); font-size:16px; line-height:1.25; text-overflow:ellipsis; white-space:nowrap; }
  .todo-highlight-copy span,.todo-highlight-error { color:var(--text-secondary); font-size:12px; line-height:1.35; }
  .todo-highlight-actions,.travel-actions { display:flex; flex-wrap:wrap; gap:6px; }
  .todo-highlight-actions button { min-height:var(--control-min); padding:7px 10px; border-radius:var(--radius-control); font:inherit; font-size:12px; font-weight:700; cursor:pointer; }
  .highlight-primary { border:0; background:var(--action-primary); color:var(--text-on-accent); }
  .highlight-secondary { border:1px solid var(--border-default); background:var(--surface-raised); color:var(--text-primary); }
  .todo-highlight-error { margin:0; color:var(--status-danger); }
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
  .item-travel { max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--text-tertiary); font-size:11px; }
  .item-prog { flex: 0 0 70px; }
  /* Biometrics — Schritte + Schlaf nebeneinander */
  .biometrics-row { display: flex; gap: 6px; padding: 0 0 3px; }
  .biometrics-row .bio-section { flex: 1; }
  .bio-section { display: flex; flex-direction: column; gap: 5px; padding: 8px; background: var(--surface-default); border: 1px solid var(--border-subtle); border-radius:var(--radius-surface); touch-action:manipulation; }
  .bio-section:active { background: var(--surface-raised); }
  .bio-hdr { display: flex; align-items: center; justify-content: space-between; }
  .bio-title { min-width:0; overflow:hidden; font-size:9px; color:var(--text-secondary); display:flex; align-items:center; gap:2px; font-weight:600; white-space:nowrap; }
  .bio-value-lg { min-width:0; overflow:hidden; font-size:16px; font-weight:700; color:var(--text-primary); line-height:1.1; white-space:nowrap; }
  .bio-target { font-size: 11px; font-weight: 400; color: var(--text-tertiary); }
  .bio-unit { font-size: 13px; font-weight: 400; color: var(--text-tertiary); }
  .longpress-indicator { display:grid; place-items:center; flex:0 0 26px; width:26px; min-height:26px; padding:0; border:0; border-radius:50%; background:transparent; color:var(--text-tertiary); cursor:pointer; }
  .longpress-indicator span { position:relative; display:block; width:17px; height:17px; border:1.5px solid currentColor; border-radius:50%; }
  .longpress-indicator span::after { content:''; position:absolute; inset:3px; border:1.5px solid currentColor; border-radius:50%; }
  .longpress-indicator:focus-visible { outline:2px solid var(--status-info); outline-offset:2px; color:var(--text-primary); }
  .longpress-indicator:active { color:var(--text-primary); }
  .item-detail-indicator { margin-left:auto; }

  /* Tageswerte */
  .feature-card-row { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:6px; margin-bottom:3px; }
  .weight-section,.nutrition-section { display:flex; flex-direction:column; gap:3px; min-width:0; padding:8px; border-radius:var(--radius-surface); }
  .weight-section { background:var(--surface-default); border:1px solid var(--border-subtle); }
  .nutrition-section { background:var(--surface-default); border:1px solid var(--border-subtle); }
  .weight-value-row { display: flex; align-items: baseline; gap: 6px; }
  .weight-value { font-size:16px; font-weight:700; color:var(--text-primary); white-space:nowrap; }
  .weight-input { width: 84px; padding: 3px 6px; border-radius: 6px; background: var(--surface-raised); border: 1px solid var(--border-default); color: var(--text-primary); font-size: 18px; font-weight: 700; }
  .weight-input:focus { border-color: var(--status-info); outline: none; }
  .trend-legend { display:flex; align-items:center; flex-wrap:wrap; gap:5px; margin:0; color:var(--text-tertiary); font-size:11px; }
  .trend-key { width:16px; border-top:2px solid var(--status-info); }
  .trend-key.interpolated { border-top-style:dashed; }
  .trend-key.baseline { border-color:var(--text-tertiary); border-top-style:dashed; }

  .nutrition-kcal { display:flex; align-items:baseline; gap:3px; min-height:22px; }
  .nutrition-kcal span { font-size:16px; font-weight:700; color:var(--text-primary); line-height:1.1; }
  .nutrition-kcal small { margin:0; color:var(--text-tertiary); font-size:10px; line-height:1.25; }

  .modal-pills { display: flex; flex-wrap: wrap; justify-content: center; gap: 4px; }

  .action-overlay { position: fixed; inset: 0; background: var(--overlay-backdrop); z-index: 1000; display: flex; align-items: flex-end; justify-content: center; animation: fadeIn 0.15s; }
  .modal-overlay, .action-overlay { margin: 0; max-width: none; max-height: none; width: auto; height: auto; border: 0; }
  .action-overlay { padding: 0; }
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
  .compact-detail { width:min(100%, 420px); max-height:min(58dvh, 520px); overflow:auto; border-radius:var(--radius-modal); }
  .detail-header { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }
  .detail-header h2,.detail-header p { margin:0; }
  .detail-header h2 { font-size:17px; line-height:1.3; }
  .detail-kind,.detail-meta,.detail-empty { color:var(--text-secondary); font-size:13px; line-height:1.45; }
  .detail-close { width:32px; min-height:32px; border:1px solid var(--border-default); border-radius:50%; background:var(--surface-raised); color:var(--text-primary); font-size:20px; line-height:1; }
  .detail-section { display:grid; gap:8px; color:var(--text-primary); font-size:14px; line-height:1.45; }
  .detail-field { display:grid; gap:5px; color:var(--text-secondary); font-size:12px; }
  .trend-detail { width:min(100%, 560px); max-height:min(76dvh, 620px); overflow:auto; border-radius:var(--radius-modal); }
  .trend-summary { grid-template-columns:repeat(3, 1fr); gap:8px; }
  .trend-summary span { display:grid; gap:2px; padding:9px; border-radius:var(--radius-control); background:var(--surface-raised); color:var(--text-tertiary); font-size:11px; }
  .trend-summary b { color:var(--text-primary); font-size:13px; }
  .metric-trend-chart { width:100%; height:auto; min-height:160px; overflow:visible; }
  .trend-axis { display:flex; justify-content:space-between; gap:8px; padding-left:14%; padding-right:2.7%; color:var(--text-tertiary); font-size:10px; }
  .trend-range-tabs { display:flex; gap:4px; }
  .trend-range-tabs button { min-width:var(--control-min); min-height:30px; padding:4px 9px; border:1px solid var(--border-default); border-radius:var(--radius-control); background:var(--surface-raised); color:var(--text-secondary); font:inherit; font-size:11px; font-weight:700; cursor:pointer; }
  .trend-range-tabs button.active { background:var(--action-primary); border-color:var(--action-primary); color:var(--text-on-accent); }
  .nutrition-detail-grid { grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; }
  .nutrition-detail-grid span { display:grid; gap:2px; color:var(--text-tertiary); font-size:12px; }
  .nutrition-detail-grid b { color:var(--text-primary); font-size:15px; }
  .nutrition-intro { margin:0; color:var(--text-secondary); font-size:13px; line-height:1.45; }
  .nutrient-group { display:grid; gap:var(--space-2); }
  .nutrient-group h3 { margin:0; font-size:13px; color:var(--text-secondary); }
  .nutrition-detail-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .nutrition-detail-grid span { min-height:58px; }
  @media (min-width:560px) { .nutrition-detail-grid { grid-template-columns:repeat(3,minmax(0,1fr)); } }
  @media (min-width: 700px) { .modal-overlay { padding:32px 24px; } .compact-detail { max-width:360px; } }

  @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
  @keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
</style>
