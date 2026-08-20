<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import TodoItem from './TodoItem.svelte';
  import TrainingDetail from './TrainingDetail.svelte';
  import PillBadge from './PillBadge.svelte';
  import Icon from './Icon.svelte';
  import { api } from '$lib/api';
  import type { Todo, DayEntry, Meal, TrainingSuggestion } from '$lib/types';

  export let todos: Todo[];
  export let currentDate: string;
  export let dayEntry: DayEntry | null = null;
  export let meals: Meal[] = [];
  export let trainingSuggestion: TrainingSuggestion | null = null;
  const dispatch = createEventDispatcher();
  type FilterMode = 'all' | 'open' | 'done' | 'today';
  type SortMode = 'time' | 'priority' | 'due';
  let filter: FilterMode = 'all';
  let sort: SortMode = 'time';
  let categoryFilter: string = '';
  let quickAdd = '';
  let showFilters = false;
  let expandedTraining = false;
  let photoInput: HTMLInputElement;
  let photoLoading = false;
  let confirmData: { slot: number; name: string; kcal: number; protein_g: number; carbs_g: number; fat_g: number } | null = null;
  let choosingSlot = false;
  const SLOT_NAMES: Record<number, string> = { 1: 'Frühstück', 2: 'Mittag', 3: 'Snack', 4: 'Abend' };
  $: sortedMeals = [...(meals ?? [])].sort((a, b) => (a.meal_slot ?? 99) - (b.meal_slot ?? 99));
  $: virtualTodos = buildRoutineTodos(dayEntry, meals, trainingSuggestion);

  function buildRoutineTodos(entry: DayEntry | null, mealList: Meal[], suggestion: TrainingSuggestion | null): Todo[] {
    const items: Todo[] = [];
    for (const m of mealList ?? []) { items.push({ id: `routine-meal-${m.id ?? m.meal_slot}`, title: m.name || SLOT_NAMES[m.meal_slot] || 'Mahlzeit', status: m.is_done ? 'done' : 'open', due_time: m.default_time ? m.default_time.slice(0, 5) : null, due_date: currentDate, priority: 2, source: 'meal_routine', sort_order: m.meal_slot }); }
    if (entry || suggestion) { const trainingType = suggestion?.training_type ?? entry?.training_type ?? 'Training'; items.push({ id: 'routine-training', title: trainingType, status: entry?.training_done ? 'done' : 'open', due_time: null, due_date: currentDate, priority: 2, source: 'training', sort_order: 99 }); }
    const cardioMinutes = entry?.cardio_minutes ?? suggestion?.cardio_minutes ?? 0;
    if (entry || suggestion) { items.push({ id: 'routine-cardio', title: cardioMinutes > 0 ? `Cardio ${cardioMinutes}min` : 'Cardio', status: entry?.cardio_done ? 'done' : 'open', due_time: null, due_date: currentDate, priority: 2, source: 'cardio', sort_order: 100 }); }
    return items;
  }

  function getMealMacros(todo: Todo): { kcal: number | null; protein: number | null } {
    if (todo.source !== 'meal_routine') return { kcal: null, protein: null };
    const slotOrId = todo.id?.replace('routine-meal-', '') ?? '';
    const meal = meals.find((m) => String(m.id) === slotOrId || String(m.meal_slot) === slotOrId);
    if (!meal) return { kcal: null, protein: null };
    return { kcal: Number(meal.kcal) || null, protein: Number(meal.protein_g) || null };
  }

  $: categories = [...new Set((todos ?? []).map((t) => t.category).filter(Boolean))] as string[];
  $: allTodos = [...virtualTodos, ...(todos ?? [])];
  $: openCount = allTodos.filter((t) => t.status === 'open').length;
  $: filteredTodos = getFilteredSorted(allTodos, filter, sort, categoryFilter, currentDate);

  function getFilteredSorted(todos: Todo[], filter: FilterMode, sort: SortMode, catFilter: string, date: string): Todo[] {
    let result = [...todos];
    if (filter === 'open') result = result.filter((t) => t.status === 'open'); else if (filter === 'done') result = result.filter((t) => t.status === 'done'); else if (filter === 'today') result = result.filter((t) => t.due_date === date);
    if (catFilter) result = result.filter((t) => t.category === catFilter);
    if (sort === 'priority') { result.sort((a, b) => (b.priority ?? 2) - (a.priority ?? 2)); } else if (sort === 'due') { result.sort((a, b) => { const ad = a.due_date ?? '9999'; const bd = b.due_date ?? '9999'; return ad.localeCompare(bd); }); } else { result.sort((a, b) => { const aR = a.source === 'meal_routine' || a.source === 'training' || a.source === 'cardio'; const bR = b.source === 'meal_routine' || b.source === 'training' || b.source === 'cardio'; if (aR && bR) return (a.sort_order ?? 99) - (b.sort_order ?? 99); if (aR) return -1; if (bR) return 1; return (a.due_time ?? '99:99').localeCompare(b.due_time ?? '99:99'); }); }
    return result;
  }

  function isRoutineTodo(id?: string): boolean { return id?.startsWith('routine-') ?? false; }
  async function markDone(id: string | number) { if (!id) return; const idStr = String(id); if (isRoutineTodo(idStr)) { await toggleRoutineTodo(idStr); return; } try { await api.markTodoDone(id); todos = todos.map((t) => (t.id === id ? { ...t, status: t.status === 'open' ? 'done' : 'open' } : t)); } catch {} }
  async function toggleRoutineTodo(id: string) {
    if (id === 'routine-training' && dayEntry) { const newVal = !dayEntry.training_done; try { await api.upsertDayEntry({ ...dayEntry, training_done: newVal, date: currentDate }); dispatch('trainingtoggle', newVal); } catch {} return; }
    if (id === 'routine-cardio' && dayEntry) { const newVal = !dayEntry.cardio_done; try { await api.upsertDayEntry({ ...dayEntry, cardio_done: newVal, date: currentDate }); dispatch('cardiotoggle', newVal); } catch {} return; }
    if (id.startsWith('routine-meal-')) { const mealId = id.replace('routine-meal-', ''); const meal = meals.find((m) => String(m.id) === mealId); if (!meal) return; try { await api.markMealDone(mealId); dispatch('mealtoggle', { id: mealId, is_done: !meal.is_done }); } catch {} return; }
  }
  function handleExpand(id: string | number) { if (String(id) === 'routine-training') expandedTraining = !expandedTraining; }
  function handleTrainingComplete() { expandedTraining = false; if (dayEntry) dispatch('trainingtoggle', true); }
  async function updateTodo(event: CustomEvent) { const { id, data } = event.detail; if (!id || isRoutineTodo(String(id))) return; try { await api.updateTodo(id, data); todos = todos.map((t) => (t.id === id ? { ...t, ...data } : t)); } catch {} }
  async function deleteTodo(id: string | number) { if (!id || isRoutineTodo(String(id))) return; try { await api.deleteTodo(id); todos = todos.filter((t) => t.id !== id); } catch {} }
  async function addQuick() { const title = quickAdd.trim(); if (!title) return; try { const n = await api.createTodo({ due_date: currentDate, title, status: 'open', priority: 2, source: 'manual' } as any); if (n) todos = [...todos, n]; quickAdd = ''; } catch {} }
  function handleKey(e: KeyboardEvent) { if (e.key === 'Enter') { e.preventDefault(); addQuick(); } }
  function getCurrentSlot(): number { const now = new Date(); const t = now.getHours() * 60 + now.getMinutes(); if (t >= 240 && t < 630) return 1; if (t >= 630 && t < 840) return 2; if (t >= 840 && t < 1050) return 3; if (t >= 1050 && t < 1320) return 4; return 1; }
  function parseVisionResult(result: any) { if (!result?.analysis?.total) return null; const total = result.analysis.total; const firstItem = result.analysis.items?.[0]; return { name: firstItem?.name ?? 'Erkanntes Gericht', kcal: Number(total.kcal) || 0, protein_g: Number(total.protein_g) || 0, carbs_g: Number(total.carbs_g) || 0, fat_g: Number(total.fat_g) || 0 }; }
  async function patchMeal(id: string | number, data: Partial<Meal>) { if (!id) return; try { await api.updateMeal(id, data); dispatch('mealupdate', { id, data }); } catch {} }
  function triggerStandalonePhoto() { photoInput?.click(); }
  async function onStandalonePhotoSelected(e: Event) { const input = e.target as HTMLInputElement; const file = input.files?.[0]; if (!file) return; photoLoading = true; try { const result = await api.analyzePhoto(file); const parsed = parseVisionResult(result); if (parsed) { confirmData = { slot: getCurrentSlot(), ...parsed }; choosingSlot = false; } } catch {} finally { photoLoading = false; input.value = ''; } }
  async function assignToSlot(slot: number) { if (!confirmData) return; const meal = meals.find((m) => m.meal_slot === slot); if (!meal || !meal.id) { choosingSlot = false; confirmData = null; return; } await patchMeal(meal.id, { name: confirmData.name, kcal: confirmData.kcal, protein_g: confirmData.protein_g, carbs_g: confirmData.carbs_g, fat_g: confirmData.fat_g }); try { await api.markMealDone(meal.id); dispatch('mealtoggle', { id: meal.id, is_done: true }); } catch {} confirmData = null; choosingSlot = false; }
  function cancelConfirm() { confirmData = null; choosingSlot = false; }
</script>

<section class="section-card">
  <div class="section-header" onclick={() => (showFilters = !showFilters)}>
    <span>Tagesplan ({openCount} offen)</span>
    <div class="hdr-actions">
      <button class="photo-btn" onclick={(e) => { e.stopPropagation(); triggerStandalonePhoto(); }} disabled={photoLoading} aria-label="Foto">{#if photoLoading}<Icon name="refresh" size={16} />{:else}<Icon name="camera" size={16} />{/if}</button>
      <span class="filt-toggle">{showFilters ? '▲' : '▼'}</span>
    </div>
  </div>
  {#if showFilters}
    <div class="filters slide-down">
      <div class="filt-row"><button class="filt-pill" class:active={filter === 'all'} onclick={() => (filter = 'all')}>Alle</button><button class="filt-pill" class:active={filter === 'open'} onclick={() => (filter = 'open')}>Offen</button><button class="filt-pill" class:active={filter === 'done'} onclick={() => (filter = 'done')}>Erledigt</button><button class="filt-pill" class:active={filter === 'today'} onclick={() => (filter = 'today')}>Heute</button></div>
      <div class="filt-row"><select class="sort-sel" bind:value={sort}><option value="time">Zeit</option><option value="priority">Priorität</option><option value="due">Fälligkeit</option></select>{#if categories.length > 0}<select class="sort-sel" bind:value={categoryFilter}><option value="">Alle</option>{#each categories as cat}<option value={cat}>{cat}</option>{/each}</select>{/if}</div>
    </div>
  {/if}
  <div class="todo-list">
    {#if filteredTodos.length > 0}{#each filteredTodos as todo (todo.id)}{@const macros = getMealMacros(todo)}<TodoItem {todo} kcal={macros.kcal} protein={macros.protein} on:done={(e) => markDone(e.detail)} on:expand={(e) => handleExpand(e.detail)} on:update={updateTodo} on:delete={(e) => deleteTodo(e.detail)} />{#if todo.id === 'routine-training' && expandedTraining}<div class="train-inline"><TrainingDetail training_type={trainingSuggestion?.training_type ?? dayEntry?.training_type ?? 'Training'} date={currentDate} oncomplete={handleTrainingComplete} onclose={() => (expandedTraining = false)} /></div>{/if}{/each}{:else}<div class="empty">Keine To-Dos</div>{/if}
  </div>
  <div class="quickadd"><input placeholder="+ To-Do hinzufügen…" bind:value={quickAdd} onkeydown={handleKey} /><button onclick={addQuick} disabled={!quickAdd.trim()} aria-label="Hinzufügen"><Icon name="plus" size={16} /></button></div>
  <input bind:this={photoInput} type="file" accept="image/*" capture="environment" style="display:none" onchange={onStandalonePhotoSelected} />
  {#if confirmData}<div class="modal-overlay" onclick={cancelConfirm}><div class="modal-card" onclick={(e) => e.stopPropagation()}>{#if choosingSlot}<div class="modal-title">Mahlzeit wählen</div><div class="slot-list">{#each sortedMeals as meal (meal.id ?? meal.meal_slot)}<button class="slot-btn" onclick={() => assignToSlot(meal.meal_slot)}><span>{meal.name || SLOT_NAMES[meal.meal_slot] || `Slot ${meal.meal_slot}`}</span><span class="slot-t">{meal.default_time ? meal.default_time.slice(0, 5) : ''}</span></button>{/each}</div><button class="modal-secondary" onclick={cancelConfirm}>Abbrechen</button>{:else}{@const d = confirmData}<div class="modal-title">{d.name}</div><p class="modal-hint">Zugewiesen zu <strong style="color:var(--green)">{SLOT_NAMES[d.slot] || `Slot ${d.slot}`}</strong></p><div class="modal-pills"><PillBadge value={Math.round(d.kcal)} unit="kcal" color="var(--amber)" /><PillBadge value={Math.round(d.protein_g)} unit="g P" color="var(--blue)" /><PillBadge value={Math.round(d.carbs_g)} unit="g KH" color="var(--purple)" /><PillBadge value={Math.round(d.fat_g)} unit="g F" color="var(--pink)" /></div><div class="modal-actions"><button class="modal-primary" onclick={() => assignToSlot(d.slot)}>Akzeptieren</button><button class="modal-secondary" onclick={() => (choosingSlot = true)}>Andere wählen</button></div>{/if}</div></div>{/if}
</section>

<style>
  .todo-list { max-height: 420px; overflow-y: auto; }
  .empty { text-align: center; padding: 20px; color: var(--text-faint); font-size: 14px; }
  .hdr-actions { display: flex; align-items: center; gap: 4px; }
  .photo-btn { width: 30px; height: 30px; border-radius: 6px; background: var(--card-2); border: 1px solid var(--border-2); color: var(--text-dim); cursor: pointer; display: flex; align-items: center; justify-content: center; }
  .photo-btn:active { background: #26272a; }
  .photo-btn:disabled { opacity: 0.5; }
  .filt-toggle { cursor: pointer; padding: 0 4px; font-size: 12px; color: var(--text-faint); }
  .filters { padding: 10px 14px; border-bottom: 1px solid var(--border); display: flex; flex-direction: column; gap: 8px; }
  .filt-row { display: flex; gap: 4px; flex-wrap: wrap; }
  .filt-pill { padding: 4px 12px; border-radius: 6px; background: var(--card-2); border: 1px solid var(--border-2); color: var(--text-dim); font-size: 12px; font-weight: 500; cursor: pointer; transition: background 0.15s; }
  .filt-pill.active { background: var(--text); color: var(--bg); border-color: var(--text); }
  .sort-sel { flex: 1; padding: 4px 8px; border-radius: 6px; background: var(--card-2); border: 1px solid var(--border-2); color: var(--text); font-size: 12px; cursor: pointer; }
  .quickadd { display: flex; gap: 8px; padding: 12px 14px; border-top: 1px solid var(--border); }
  .quickadd input { flex: 1; padding: 8px 12px; border-radius: 8px; background: var(--card-2); border: 1px solid var(--border-2); color: var(--text); font-size: 14px; }
  .quickadd input:focus { border-color: var(--blue); }
  .quickadd input::placeholder { color: var(--text-faint); }
  .quickadd button { width: 34px; height: 34px; border-radius: 8px; background: var(--green); color: #000; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: opacity 0.15s; }
  .quickadd button:disabled { opacity: 0.3; }
  .quickadd button:active { opacity: 0.7; }
  .train-inline { padding: 0 14px 8px; }
  .slot-list { display: flex; flex-direction: column; gap: 8px; }
  .slot-btn { display: flex; align-items: center; justify-content: space-between; padding: 12px; border-radius: 8px; background: var(--card-2); border: 1px solid var(--border-2); color: var(--text); cursor: pointer; font-size: 14px; font-weight: 500; }
  .slot-t { font-size: 12px; color: var(--text-faint); }
  .modal-hint { text-align: center; font-size: 14px; color: var(--text-dim); }
  .modal-pills { display: flex; flex-wrap: wrap; justify-content: center; gap: 4px; }
</style>