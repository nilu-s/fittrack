<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import MetricRow from './MetricRow.svelte';
  import ProgressBar from './ProgressBar.svelte';
  import PillBadge from './PillBadge.svelte';
  import TrainingDetail from './TrainingDetail.svelte';
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

  let expandedTraining = false;
  let expandedSleep = false;
  let expandedWeight = false;
  let weightEditing = false;
  let quickAdd = '';
  let photoInput: HTMLInputElement;
  let photoLoading = false;
  let photoStatus = '';  // '', 'upload', 'analyze', 'match', 'done'
  let confirmData: { slot: number; name: string; kcal: number; protein_g: number; carbs_g: number; fat_g: number; fiber_g: number; sugar_g: number; free_sugar_g: number } | null = null;
  let choosingSlot = false;

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
      const slotLabel = SLOT_NAMES[m.meal_slot] || `Slot ${m.meal_slot}`;
      const dishName = m.name || '— Mahlzeit wählen —';
      items.push({ id: `meal-${m.id ?? m.meal_slot}`, type: 'meal', icon: 'meal', title: `${slotLabel}: ${dishName}`, done: m.is_done ?? false, sortKey: `01-${String(m.meal_slot).padStart(2, '0')}`, kcal: Number(m.kcal) || null, protein: Number(m.protein_g) || null, fiber: Number(m.fiber_g) || null, sugar: Number(m.sugar_g) || null, mealTime: m.default_time ? m.default_time.slice(0, 5) : null });
    }
    const trainingType = suggestion?.training_type ?? entry.training_type;
    if (trainingType && trainingType !== 'Ruhetag') {
      items.push({ id: 'training', type: 'training', icon: 'training', title: trainingType, done: entry.training_done ?? false, sortKey: '02-00' });
    }
    for (const t of todoList) { items.push({ id: `todo-${t.id}`, type: 'todo', icon: 'todo', title: t.title, done: t.status === 'done', sortKey: `03-${t.due_time ?? '99:99'}`, todoData: t }); }
    return items.sort((a, b) => a.sortKey.localeCompare(b.sortKey));
  }

  let longPressTimer: ReturnType<typeof setTimeout> | null = null;
  let longPressTriggered = false;
  let actionSheetItem: UnifiedItem | null = null;
  let editingTodo: Todo | null = null;
  let editTitle = ''; let editCategory = ''; let editPriority = 2; let editDueDate = ''; let editDueTime = '';
  // Meal edit modal (long-press on meal)
  let mealEditItem: UnifiedItem | null = null;
  let editDishes: any[] = [];
  let editDishesLoading = false;
  let editPhotoInput: HTMLInputElement;
  let editPhotoLoading = false;
  let editPhotoStatus = '';
  // New: recommend + search + portion
  let recommendResult: any = null;
  let dishSearchQuery = '';
  let dishSearchResults: any[] = [];
  let dishSearching = false;

  /** Only one task detail may be open in the daily list at a time. */
  function closeOpenTodoDetails() {
    expandedTraining = false;
    closeMealEdit();
    actionSheetItem = null;
    editingTodo = null;
  }

  function toggleMealEdit(item: UnifiedItem) {
    if (mealEditItem?.id === item.id) { closeMealEdit(); return; }
    closeOpenTodoDetails();
    void openMealEdit(item);
  }

  function toggleTrainingDetail() {
    const wasExpanded = expandedTraining;
    closeOpenTodoDetails();
    expandedTraining = !wasExpanded;
  }

  function toggleTodoActions(item: UnifiedItem) {
    if (actionSheetItem?.id === item.id) { actionSheetItem = null; return; }
    closeOpenTodoDetails();
    actionSheetItem = item;
  }

  function handleTouchStart(item: UnifiedItem, e: TouchEvent) {
    longPressTriggered = false;
    if (item.type !== 'todo') return;
    longPressTimer = setTimeout(() => {
      longPressTriggered = true;
      if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(50);
      toggleTodoActions(item);
    }, 500);
  }
  function handleTouchEnd() {
    if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null; }
  }
  function handleTouchMove() {
    if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null; }
  }
  function handleContextMenu(item: UnifiedItem, e: MouseEvent) { if (item.type !== 'todo') return; e.preventDefault(); toggleTodoActions(item); }

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
    if (item.type === 'training') { toggleTrainingDetail(); return; }
    if (item.type === 'meal') return;
    if (item.type === 'todo') { toggleTodoActions(item); return; }
    if (item.id === 'metric-sleep') { expandedSleep = !expandedSleep; return; }
    if (item.id === 'metric-weight' && item.weightDetails) { expandedWeight = !expandedWeight; return; }
  }

  function handleItemKey(item: UnifiedItem, e: KeyboardEvent) {
    if (e.key !== 'Enter' && e.key !== ' ') return;
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
    if (item.type === 'meal') { const mealId = item.id.replace('meal-', ''); const meal = meals.find((m) => String(m.id) === mealId || `meal-${m.meal_slot}` === item.id); if (!meal?.id) return; try { await api.markMealDone(meal.id); meals = meals.map((m) => m.id === meal.id ? { ...m, is_done: !m.is_done } : m); dispatch('mealtoggle', { id: meal.id, is_done: !meal.is_done }); } catch {} return; }
    if (item.type === 'training' && entry) { const newVal = !entry.training_done; try { await api.upsertDayEntry({ ...entry, training_done: newVal, date: currentDate }); entry = { ...entry, training_done: newVal }; dispatch('trainingtoggle', newVal); } catch {} return; }
    if (item.type === 'cardio' && entry) { const newVal = !entry.cardio_done; try { await api.upsertDayEntry({ ...entry, cardio_done: newVal, date: currentDate }); entry = { ...entry, cardio_done: newVal }; dispatch('cardiotoggle', newVal); } catch {} return; }
    if (item.type === 'todo') { const todoId = item.id.replace('todo-', ''); try { await api.markTodoDone(todoId); todos = todos.map((t) => String(t.id) === todoId ? { ...t, status: t.status === 'open' ? 'done' : 'open' } : t); dispatch('todotoggle', { id: todoId }); } catch {} return; }
  }

  async function updateMetric(field: string, value: any) { if (!entry) return; entry = { ...entry, [field]: value }; if (field === 'weight_kg') { entry = { ...entry, weight_source: 'manual' }; } try { await api.upsertDayEntry({ ...entry, date: currentDate }); dispatch('update', { field, value }); } catch {} }
  function handleTrainingComplete() { expandedTraining = false; if (entry) { entry = { ...entry, training_done: true }; dispatch('trainingtoggle', true); } }

  async function addQuick() { const title = quickAdd.trim(); if (!title) return; try { const n = await api.createTodo({ due_date: currentDate, title, status: 'open', priority: 2, source: 'manual' } as any); if (n) { todos = [...todos, n]; dispatch('todoadd', n); } quickAdd = ''; } catch {} }
  function handleKey(e: KeyboardEvent) { if (e.key === 'Enter') { e.preventDefault(); addQuick(); } }

  function getCurrentSlot(): number { const now = new Date(); const t = now.getHours() * 60 + now.getMinutes(); if (t >= 240 && t < 630) return 1; if (t >= 630 && t < 840) return 2; if (t >= 840 && t < 1050) return 3; if (t >= 1050 && t < 1320) return 4; return 1; }
  function parseVisionResult(result: any) { if (!result?.analysis?.total) return null; const total = result.analysis.total; const firstItem = result.analysis.items?.[0]; return { name: firstItem?.name ?? 'Erkanntes Gericht', kcal: Number(total.kcal) || 0, protein_g: Number(total.protein_g) || 0, carbs_g: Number(total.carbs_g) || 0, fat_g: Number(total.fat_g) || 0, fiber_g: Number(total.fiber_g) || 0, sugar_g: Number(total.sugar_g) || 0, free_sugar_g: Number(total.free_sugar_g) || 0 }; }
  function triggerPhoto() { photoInput?.click(); }
  async function onPhotoSelected(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    photoLoading = true;
    photoStatus = 'upload';
    try {
      photoStatus = 'analyze';
      const result = await api.analyzePhoto(file) as any;
      photoStatus = 'match';
      const parsed = parseVisionResult(result);
      if (parsed) {
        confirmData = { slot: getCurrentSlot(), ...parsed };
        choosingSlot = false;
        photoStatus = 'done';
      }
    } catch {} finally {
      setTimeout(() => { photoLoading = false; photoStatus = ''; }, 300);
      input.value = '';
    }
  }
  async function assignToSlot(slot: number) {
    const data = confirmData;
    if (!data) return;
    const meal = meals.find((m) => m.meal_slot === slot);
    if (!meal?.id) { confirmData = null; choosingSlot = false; return; }
    try {
      await api.updateMeal(meal.id, { name: data.name, kcal: data.kcal, protein_g: data.protein_g, carbs_g: data.carbs_g, fat_g: data.fat_g, fiber_g: data.fiber_g, sugar_g: data.sugar_g, free_sugar_g: data.free_sugar_g });
      await api.markMealDone(meal.id);
      meals = meals.map((m) => m.id === meal.id ? { ...m, name: data.name, kcal: String(data.kcal), protein_g: String(data.protein_g), carbs_g: String(data.carbs_g), fat_g: String(data.fat_g), fiber_g: String(data.fiber_g), sugar_g: String(data.sugar_g), free_sugar_g: String(data.free_sugar_g), is_done: true } : m);
      dispatch('mealtoggle', { id: meal.id, is_done: true, data: { name: data.name, kcal: data.kcal, protein_g: data.protein_g, carbs_g: data.carbs_g, fat_g: data.fat_g, fiber_g: data.fiber_g, sugar_g: data.sugar_g, free_sugar_g: data.free_sugar_g } });
    } catch {}
    confirmData = null;
    choosingSlot = false;
  }
  function cancelConfirm() { confirmData = null; choosingSlot = false; }

  // --- Meal edit modal (long-press on meal) ---
  async function openMealEdit(item: UnifiedItem) {
    const mealId = String(item.id).replace('meal-', '');
    const meal = meals.find((m) => String(m.id) === mealId || `meal-${m.meal_slot}` === item.id);
    if (!meal) return;
    mealEditItem = item;
    dishSearchQuery = '';
    dishSearchResults = [];
    recommendResult = null;
    editDishesLoading = true;
    const slot = meal.meal_slot;
    try {
      recommendResult = await api.getDishRecommend(slot);
      // Also load all dishes for initial search display
      editDishes = await api.getDishes();
    } catch { editDishes = []; recommendResult = null; }
    editDishesLoading = false;
  }
  function closeMealEdit() { mealEditItem = null; }

  function getMealFromItem(item: UnifiedItem): Meal | undefined {
    const id = String(item.id).replace('meal-', '');
    return meals.find((m) => String(m.id) === id || `meal-${m.meal_slot}` === item.id);
  }

  function getMealSlotFromItem(item: UnifiedItem): number {
    const m = getMealFromItem(item);
    return m?.meal_slot ?? 0;
  }

  function selectDishForEdit(dish: any) {
    void saveDishSelection(dish);
  }

  function onDishSearch(e: Event) {
    const input = e.target as HTMLInputElement;
    dishSearchQuery = input.value;
    if (dishSearchQuery.trim().length < 2) { dishSearchResults = []; return; }
    const q = dishSearchQuery.trim().toLowerCase();
    dishSearchResults = editDishes.filter((d: any) => d.name.toLowerCase().includes(q)).slice(0, 8);
  }

  async function saveDishSelection(dish: any) {
    if (!mealEditItem) return;
    const item = mealEditItem;
    const mealId = String(item.id).replace('meal-', '');
    const meal = meals.find((m) => String(m.id) === mealId || `meal-${m.meal_slot}` === item.id);
    if (!meal?.id) return;
    const kcal = Math.round(Number(dish.kcal) || 0);
    const protein = Math.round(Number(dish.protein_g) || 0);
    const carbs = Math.round(Number(dish.carbs_g) || 0);
    const fat = Math.round(Number(dish.fat_g) || 0);
    const fiber = Math.round(Number(dish.fiber_g) || 0);
    const sugar = Math.round(Number(dish.sugar_g) || 0);
    const freeSugar = Math.round(Number(dish.free_sugar_g) || 0);
    try {
      await api.updateMeal(meal.id, {
        name: dish.name,
        kcal, protein_g: protein, carbs_g: carbs, fat_g: fat, fiber_g: fiber, sugar_g: sugar, free_sugar_g: freeSugar,
        portion_factor: 1,
        dish_id: dish.id,
      });
      meals = meals.map((m) => m.id === meal.id ? { ...m, name: dish.name, kcal: String(kcal), protein_g: String(protein), carbs_g: String(carbs), fat_g: String(fat), fiber_g: String(fiber), sugar_g: String(sugar), free_sugar_g: String(freeSugar) } : m);
      dispatch('mealtoggle', { id: meal.id, is_done: meal.is_done, data: { name: dish.name, kcal, protein_g: protein, carbs_g: carbs, fat_g: fat, fiber_g: fiber, sugar_g: sugar, free_sugar_g: freeSugar, dish_id: dish.id, portion_factor: 1 } });
      try { await api.incrementDishUsage(dish.id); } catch {}
    } catch {}
    closeMealEdit();
  }

  function triggerEditPhoto() { editPhotoInput?.click(); }
  function photoForMeal(item: UnifiedItem) {
    closeOpenTodoDetails();
    mealEditItem = item;
    triggerEditPhoto();
  }

  async function onEditPhotoSelected(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file || !mealEditItem) return;
    const item = mealEditItem;
    const mealId = String(item.id).replace('meal-', '');
    const meal = meals.find((m) => String(m.id) === mealId || `meal-${m.meal_slot}` === item.id);
    if (!meal?.id) return;
    editPhotoLoading = true;
    editPhotoStatus = 'analyze';
    try {
      const result = await api.analyzePhoto(file, meal.id) as any;
      editPhotoStatus = 'match';
      if (result?.analysis?.total) {
        const total = result.analysis.total;
        const firstName = result.analysis.items?.[0]?.name ?? 'Erkanntes Gericht';
        await api.updateMeal(meal.id, { name: firstName, kcal: Number(total.kcal) || 0, protein_g: Number(total.protein_g) || 0, carbs_g: Number(total.carbs_g) || 0, fat_g: Number(total.fat_g) || 0, fiber_g: Number(total.fiber_g) || 0, sugar_g: Number(total.sugar_g) || 0, free_sugar_g: Number(total.free_sugar_g) || 0 });
        meals = meals.map((m) => m.id === meal.id ? { ...m, name: firstName, kcal: String(total.kcal), protein_g: String(total.protein_g), carbs_g: String(total.carbs_g), fat_g: String(total.fat_g), fiber_g: String(total.fiber_g), sugar_g: String(total.sugar_g), free_sugar_g: String(total.free_sugar_g) } : m);
        dispatch('mealtoggle', { id: meal.id, is_done: meal.is_done, data: { name: firstName, kcal: Number(total.kcal) || 0, protein_g: Number(total.protein_g) || 0, carbs_g: Number(total.carbs_g) || 0, fat_g: Number(total.fat_g) || 0, fiber_g: Number(total.fiber_g) || 0, sugar_g: Number(total.sugar_g) || 0, free_sugar_g: Number(total.free_sugar_g) || 0 } });
        editPhotoStatus = 'done';
        if (result.dish_match?.matched && result.dish_match.dish) {
          try { await api.incrementDishUsage(result.dish_match.dish.id); } catch {}
        } else {
          const item = result.analysis.items?.[0] ?? {};
          try { await api.createDish({
            name: firstName, kcal: Number(total.kcal) || 0,
            protein_g: Number(total.protein_g) || 0, carbs_g: Number(total.carbs_g) || 0,
            fat_g: Number(total.fat_g) || 0, fiber_g: Number(total.fiber_g) || 0, sugar_g: Number(total.sugar_g) || 0, free_sugar_g: Number(total.free_sugar_g) || 0, source: 'photo',
            portion_label: item.portion_label || null,
            portion_grams: item.portion_grams || null,
            is_scalable: item.is_scalable || false,
          }); } catch {}
        }
      }
    } catch {} finally { setTimeout(() => { editPhotoLoading = false; editPhotoStatus = ''; }, 500); input.value = ''; mealEditItem = null; }
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
    <button class="photo-btn" onclick={triggerPhoto} disabled={photoLoading} aria-label="Foto">
      {#if photoLoading}<Icon name="refresh" size={16} />{:else}<Icon name="camera" size={16} />{/if}
    </button>
  </div>

  {#if photoLoading}
    <div class="photo-progress">
      <div class="photo-progress-bar">
        <div class="photo-progress-fill" class:animate-match={photoStatus === 'match'} class:animate-done={photoStatus === 'done'}></div>
      </div>
      <span class="photo-progress-label">
        {photoStatus === 'upload' ? 'Foto wird hochgeladen…' :
         photoStatus === 'analyze' ? 'Vitaly analysiert das Gericht…' :
         photoStatus === 'match' ? 'Gericht wird zugeordnet…' :
         photoStatus === 'done' ? 'Fertig!' : 'Verarbeite…'}
      </span>
    </div>
  {/if}

  {#each manualItems as item (item.id)}
    <div class="item tap-area" class:done={item.done}
      onclick={(e) => handleTap(item, e)}
      oncontextmenu={(e) => handleContextMenu(item, e)}
      ontouchstart={(e) => handleTouchStart(item, e)}
      ontouchend={handleTouchEnd}
      ontouchmove={handleTouchMove}
      ontouchcancel={() => handleTouchEnd()}
      onkeydown={(e) => handleItemKey(item, e)}
      role="button" tabindex="0">
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
        </div>
      </div>
      {#if item.type === 'meal' && !item.done}
        <div class="meal-row-actions">
          <button class="meal-change-button" onclick={(e) => { e.stopPropagation(); toggleMealEdit(item); }}>Gericht ändern</button>
          <button class="meal-photo-action" onclick={(e) => { e.stopPropagation(); photoForMeal(item); }} aria-label="Mahlzeit fotografieren"><Icon name="camera" size={16} /><span>Foto</span></button>
        </div>
      {/if}
      {#if item.type === 'metric'}
        <MetricRow icon="" label="" value={item.metricValue} unit={item.metricUnit ?? ''} editable={item.metricEditable ?? false} checkable={false} on:change={(e) => updateMetric(item.metricField!, e.detail)} />
      {/if}
      {#if item.hasProgress}<div class="item-prog"><ProgressBar current={item.progressCurrent ?? 0} target={item.progressTarget ?? 1} color="var(--text-dim)" /></div>{/if}
    </div>

    {#if item.type === 'meal' && mealEditItem?.id === item.id}
      <div class="meal-inline">
        <div class="meal-inline-heading"><div class="meal-inline-title">{SLOT_NAMES[getMealSlotFromItem(mealEditItem)] || `Slot ${getMealSlotFromItem(mealEditItem)}`} bearbeiten</div><button class="meal-collapse" onclick={closeMealEdit}>Einklappen</button></div>

          {#if editDishesLoading}
            <div class="modal-loading">Lade Empfehlungen…</div>
          {:else}
            {#if recommendResult?.default}
              <div class="modal-section-label">Empfohlen</div>
              <button class="dish-btn dish-default-highlight" onclick={() => selectDishForEdit(recommendResult.default)}>
                <div class="dish-info"><span class="dish-name">{recommendResult.default.name}</span>{#if recommendResult.default.is_default}<span class="dish-badge">Standard</span>{/if}</div>
                <span class="dish-summary">{Math.round(Number(recommendResult.default.kcal) || 0)} kcal · {Math.round(Number(recommendResult.default.protein_g) || 0)} g Protein</span>
              </button>
            {/if}
            {#if recommendResult?.alternatives?.length > 0}
              <div class="modal-section-label">Ähnliche Alternativen</div>
              <div class="dish-list">{#each recommendResult.alternatives as dish (dish.id)}<button class="dish-btn" onclick={() => selectDishForEdit(dish)}><div class="dish-info"><span class="dish-name">{dish.name}</span></div><span class="dish-summary">{Math.round(Number(dish.kcal) || 0)} kcal · {Math.round(Number(dish.protein_g) || 0)} g Protein</span></button>{/each}</div>
            {/if}
            <div class="modal-section-label">Anderes Gericht suchen</div>
            <input class="dish-search-input" type="text" placeholder="Gericht eingeben…" oninput={onDishSearch} value={dishSearchQuery} />
            {#if dishSearchResults.length > 0}
              <div class="dish-list">{#each dishSearchResults as dish (dish.id)}<button class="dish-btn" onclick={() => selectDishForEdit(dish)}><div class="dish-info"><span class="dish-name">{dish.name}</span>{#if dish.is_default}<span class="dish-badge">Standard</span>{/if}</div><span class="dish-summary">{Math.round(Number(dish.kcal) || 0)} kcal · {Math.round(Number(dish.protein_g) || 0)} g Protein</span></button>{/each}</div>
            {:else if dishSearchQuery.trim().length >= 2}<div class="modal-empty">Keine Treffer</div>{/if}
          {/if}
          <div class="modal-actions">
            {#if editPhotoLoading}<div class="photo-progress modal-progress"><div class="photo-progress-bar"><div class="photo-progress-fill" class:animate-match={editPhotoStatus === 'match'} class:animate-done={editPhotoStatus === 'done'}></div></div><span class="photo-progress-label">{editPhotoStatus === 'analyze' ? 'Vitaly analysiert das Gericht…' : editPhotoStatus === 'match' ? 'Gericht wird zugeordnet…' : editPhotoStatus === 'done' ? 'Fertig!' : 'Verarbeite…'}</span></div>{/if}
          </div>
      </div>
    {/if}

    {#if item.id === 'training' && expandedTraining}
      <div class="train-inline" onclick={(e) => e.stopPropagation()}>
        <TrainingDetail training_type={trainingSuggestion?.training_type ?? entry?.training_type ?? 'Training'} date={currentDate} oncomplete={handleTrainingComplete} onclose={() => (expandedTraining = false)} />
      </div>
    {/if}
  {/each}

  <div class="quickadd">
    <input placeholder="+ To-Do hinzufügen…" bind:value={quickAdd} onkeydown={handleKey} />
    <button onclick={addQuick} disabled={!quickAdd.trim()} aria-label="Hinzufügen"><Icon name="plus" size={16} /></button>
  </div>
</div>

<input bind:this={photoInput} type="file" accept="image/*" capture="environment" style="display:none" onchange={onPhotoSelected} />

{#if confirmData}
  <div class="modal-overlay" onclick={cancelConfirm}>
    <div class="modal-card" onclick={(e) => e.stopPropagation()}>
      {#if choosingSlot}
        <div class="modal-title">Mahlzeit wählen</div>
        <div class="slot-list">
          {#each [...meals].sort((a, b) => (a.meal_slot ?? 99) - (b.meal_slot ?? 99)) as meal (meal.id ?? meal.meal_slot)}
            <button class="slot-btn" onclick={() => assignToSlot(meal.meal_slot)}>
              <span>{meal.name || SLOT_NAMES[meal.meal_slot] || `Slot ${meal.meal_slot}`}</span>
              <span class="slot-t">{meal.default_time ? meal.default_time.slice(0, 5) : ''}</span>
            </button>
          {/each}
        </div>
        <button class="modal-secondary" onclick={cancelConfirm}>Abbrechen</button>
      {:else}
        {@const d = confirmData}
        <div class="modal-title">{d.name}</div>
        <p class="modal-hint">Zugewiesen zu <strong style="color:var(--green)">{SLOT_NAMES[d.slot] || `Slot ${d.slot}`}</strong></p>
        <div class="modal-pills">
          <PillBadge value={Math.round(d.kcal)} unit="kcal" color="var(--amber)" />
          <PillBadge value={Math.round(d.protein_g)} unit="g P" color="var(--blue)" />
          <PillBadge value={Math.round(d.carbs_g)} unit="g KH" color="var(--purple)" />
          <PillBadge value={Math.round(d.fat_g)} unit="g F" color="var(--pink)" />
          <PillBadge value={Math.round(d.fiber_g)} unit="g Ballaststoffe" color="var(--green)" />
          <PillBadge value={Math.round(d.sugar_g)} unit="g Zucker" color="var(--amber)" />
        </div>
        <div class="modal-actions">
          <button class="modal-primary" onclick={() => assignToSlot(d.slot)}>Akzeptieren</button>
          <button class="modal-secondary" onclick={() => (choosingSlot = true)}>Andere wählen</button>
        </div>
      {/if}
    </div>
  </div>
{/if}

{#if actionSheetItem}
  <div class="action-overlay" onclick={() => (actionSheetItem = null)} ontouchstart={(e) => { e.preventDefault(); actionSheetItem = null; }}>
    <div class="action-sheet" onclick={(e) => e.stopPropagation()} ontouchstart={(e) => e.stopPropagation()}>
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
  </div>
{/if}

{#if editingTodo}
  <div class="modal-overlay" onclick={cancelEdit}>
    <div class="modal-card edit-card" onclick={(e) => e.stopPropagation()}>
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
  </div>
{/if}

<input bind:this={editPhotoInput} type="file" accept="image/*" capture="environment" style="display:none" onchange={onEditPhotoSelected} />

<style>
  .macro { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
  .macro-l { font-size: 11px; text-transform: uppercase; font-weight: 600; }
  .macro-v { font-size: 13px; font-weight: 600; color: var(--text); white-space: nowrap; }

  .daylist { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
  .daylist-hdr { display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; border-bottom: 1px solid var(--border); font-size: 13px; color: var(--text-dim); font-weight: 500; }
  .photo-btn { width: 30px; height: 30px; border-radius: 6px; background: var(--card-2); border: 1px solid var(--border-2); color: var(--text-dim); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background 0.15s; }
  .photo-btn:active { background: #26272a; }
  .photo-btn:disabled { opacity: 0.5; }

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
  .item-prog { flex: 0 0 70px; }
  .meal-row-actions { display: flex; align-items: center; gap: 6px; flex: 0 0 auto; }
  .meal-change-button, .meal-photo-action { border: 1px solid var(--border-2); border-radius: 7px; background: var(--card-2); color: var(--text); cursor: pointer; font: inherit; font-size: 12px; font-weight: 600; padding: 7px 9px; white-space: nowrap; }
  .meal-photo-action { display: flex; align-items: center; gap: 4px; }
  .meal-change-button:active { background: var(--border); }
  .meal-photo-action:active { background: var(--border); }
  .spark-row { padding: 0 14px 8px; }
  .train-inline { padding: 0 14px 8px; }
  .meal-inline { display: flex; flex-direction: column; gap: 12px; margin: 4px 10px 10px 54px; padding: 14px; border: 1px solid var(--border); border-radius: 10px; background: var(--card-2); animation: inlineExpand 0.18s ease-out; }
  .meal-inline-heading { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .meal-inline-title { color: var(--text); font-size: 15px; font-weight: 650; }
  .meal-collapse { border: 0; background: transparent; color: var(--text-dim); cursor: pointer; font: inherit; font-size: 13px; padding: 4px; }
  .meal-collapse:focus-visible { outline: 2px solid var(--blue); outline-offset: 2px; border-radius: 4px; }

  .quality-stars { font-size: 11px; color: var(--amber); letter-spacing: 1px; }

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
  .bio-hint { color: var(--text-faint); }
  .bio-unit { font-size: 13px; font-weight: 400; color: var(--text-faint); }
  .bio-source-badge { font-size: 9px; color: var(--green); font-weight: 600; background: rgba(34,197,94,0.15); padding: 1px 5px; border-radius: 4px; }
  .bio-source-manual { font-size: 9px; color: var(--text-faint); font-weight: 500; }
  .bio-hdr-right { display: flex; align-items: center; gap: 4px; }
  .bio-edit-btn { width: 22px; height: 22px; border-radius: 5px; border: none; background: transparent; color: var(--text-faint); cursor: pointer; display: flex; align-items: center; justify-content: center; }
  .bio-edit-btn:active { background: var(--card-2); }
  .bio-edit-row { padding: 4px 0; }
  .bio-expand-btn { align-self: flex-start; background: none; border: none; color: var(--text-faint); font-size: 11px; cursor: pointer; padding: 2px 0; }

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

  /* Weight body composition detail */
  .weight-detail { padding: 0 14px 10px; }
  .weight-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
  .weight-stat { display: flex; flex-direction: column; gap: 2px; text-align: center; padding: 6px 4px; background: var(--card-2); border-radius: 6px; }
  .weight-stat-l { font-size: 9px; color: var(--text-faint); text-transform: uppercase; font-weight: 600; }
  .weight-stat-v { font-size: 12px; font-weight: 600; color: var(--text); }

  /* Sleep donut */
  .sleep-donut-row { display: flex; align-items: center; gap: 12px; }
  .sleep-donut { width: 80px; height: 80px; flex-shrink: 0; }
  .sleep-legend-col { display: flex; flex-direction: column; gap: 3px; flex: 1; min-width: 0; }
  .sleep-leg-row { display: flex; align-items: center; gap: 6px; font-size: 11px; line-height: 1.4; }
  .sleep-leg-label { color: var(--text-dim); flex: 1; white-space: nowrap; }
  .sleep-leg-time { color: var(--text); font-weight: 600; text-align: right; min-width: 42px; }
  .sleep-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }

  /* Sleep summary */
  .sleep-summary { display: flex; gap: 8px; margin-top: 4px; }
  .sleep-sum-stat { flex: 1; display: flex; flex-direction: column; gap: 2px; text-align: center; padding: 6px 4px; background: var(--card-2); border-radius: 6px; }
  .sleep-stat-l { font-size: 9px; color: var(--text-faint); text-transform: uppercase; font-weight: 600; }
  .sleep-sum-v { font-size: 12px; font-weight: 600; color: var(--text); }

  .quickadd { display: flex; gap: 8px; padding: 12px 14px; border-top: 1px solid var(--border); }
  .quickadd input { flex: 1; padding: 8px 12px; border-radius: 8px; background: var(--card-2); border: 1px solid var(--border-2); color: var(--text); font-size: 14px; }
  .quickadd input:focus { border-color: var(--blue); }
  .quickadd input::placeholder { color: var(--text-faint); }
  .quickadd button { width: 34px; height: 34px; border-radius: 8px; background: var(--green); color: #000; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: opacity 0.15s; }
  .quickadd button:disabled { opacity: 0.3; }
  .quickadd button:active { opacity: 0.7; }

  .slot-list { display: flex; flex-direction: column; gap: 8px; }
  .slot-btn { display: flex; align-items: center; justify-content: space-between; padding: 12px; border-radius: 8px; background: var(--card-2); border: 1px solid var(--border-2); color: var(--text); cursor: pointer; font-size: 14px; font-weight: 500; transition: background 0.15s; }
  .slot-btn:active { background: #26272a; }
  .slot-t { font-size: 12px; color: var(--text-faint); }
  .modal-hint { text-align: center; font-size: 14px; color: var(--text-dim); }
  .modal-pills { display: flex; flex-wrap: wrap; justify-content: center; gap: 4px; }

  .action-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: flex-end; justify-content: center; animation: fadeIn 0.15s; }
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

  @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
  @keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
  @keyframes inlineExpand { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }

  /* Meal edit modal — additional classes (modal-overlay/card/title/actions/primary/secondary already defined above) */
  .meal-inline .modal-section-label { font-size: 13px; color: var(--text-dim); margin: 4px 0 0; font-weight: 600; }
  .meal-inline .modal-loading, .meal-inline .modal-empty { text-align: center; padding: 12px; color: var(--text-dim); font-size: 14px; }
  .cam-action { display: flex; align-items: center; justify-content: center; gap: 8px; }
  .meal-inline .dish-list { display: flex; flex-direction: column; gap: 6px; max-height: 192px; margin: 0; overflow-y: auto; }
  .meal-inline .dish-btn { display: flex; flex-direction: column; align-items: flex-start; gap: 4px; padding: 11px 12px; border-radius: 8px; background: var(--card); border: 1px solid var(--border); color: var(--text); cursor: pointer; transition: border-color 0.15s, background 0.15s; text-align: left; }
  .dish-btn:active { background: #2a2b2e; }
  .dish-btn.default { border-color: var(--green); }
  .dish-info { display: flex; align-items: center; gap: 6px; flex: 1; min-width: 0; }
  .dish-name { font-size: 15px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .dish-badge { font-size: 12px; padding: 2px 6px; border-radius: 4px; background: var(--green); color: #000; font-weight: 600; flex-shrink: 0; }
  .dish-summary { font-size: 13px; color: var(--text-dim); }

  /* Photo progress bar */
  .photo-progress { padding: 10px 14px; border-bottom: 1px solid var(--border); }
  .modal-progress { padding: 0 0 8px; border: none; }
  .photo-progress-bar { height: 4px; border-radius: 2px; background: var(--card-2); overflow: hidden; margin-bottom: 6px; }
  .photo-progress-fill { height: 100%; border-radius: 2px; background: var(--blue); width: 0; animation: photoLoad 2s ease-in-out infinite; }
  .photo-progress-fill.animate-match { background: var(--amber); animation: photoLoad 1.5s ease-in-out infinite; }
  .photo-progress-fill.animate-done { background: var(--green); animation: photoDone 0.4s ease-out forwards; }
  .photo-progress-label { font-size: 12px; color: var(--text-dim); display: block; text-align: center; }
  @keyframes photoLoad { 0% { width: 0; } 50% { width: 65%; } 100% { width: 90%; } }
  @keyframes photoDone { from { width: 90%; } to { width: 100%; } }

  /* Dish selection modal — new styles */
  .meal-inline .dish-default-highlight { background: var(--card); border: 1px solid var(--green); margin: 0; }
  .dish-default-highlight .dish-name { font-weight: 700; color: var(--green); }
  .meal-inline .dish-search-input { width: 100%; padding: 10px 12px; border-radius: 8px; background: var(--card); border: 1px solid var(--border-2); color: var(--text); font-size: 14px; margin: 0; outline: none; }
  .dish-search-input:focus { border-color: var(--green); }

  @media (max-width: 520px) {
    .meal-inline { margin-left: 10px; }
  }
</style>
