<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import MetricRow from './MetricRow.svelte';
  import ProgressBar from './ProgressBar.svelte';
  import Sparkline from './Sparkline.svelte';
  import PillBadge from './PillBadge.svelte';
  import TrainingDetail from './TrainingDetail.svelte';
  import Icon from './Icon.svelte';
  import { api } from '$lib/api';
  import { dailyGoals } from '$lib/stores';
  import type { DayEntry, Meal, Todo, TrainingSuggestion, DayData } from '$lib/types';

  export let dayData: DayData;
  export let currentDate: string;
  const dispatch = createEventDispatcher();
  const SLOT_NAMES: Record<number, string> = { 1: 'Frühstück', 2: 'Mittag', 3: 'Snack', 4: 'Abend' };

  let entry: DayEntry | null = dayData.dayEntry ?? null;
  let meals: Meal[] = dayData.meals ?? [];
  let todos: Todo[] = dayData.todos ?? [];
  let trainingSuggestion: TrainingSuggestion | null = dayData.trainingSuggestion ?? null;
  $: entry = dayData.dayEntry ?? null;
  $: meals = dayData.meals ?? [];
  $: todos = dayData.todos ?? [];
  $: trainingSuggestion = dayData.trainingSuggestion ?? null;

  let weightTrend: number[] = [];
  $: if (currentDate) loadWeightTrend();
  async function loadWeightTrend() { try { const wt = await api.getStatsTrend('weight', 7); weightTrend = (wt?.points ?? []).map((v: any) => v.value ?? 0).filter((v: number) => v !== null && v > 0); } catch {} }

  $: goals = $dailyGoals;
  $: doneMeals = meals.filter((m) => m.is_done);
  $: totalKcal = Math.round(doneMeals.reduce((s, m) => s + (Number(m.kcal) || 0), 0));
  $: totalP = Math.round(doneMeals.reduce((s, m) => s + (Number(m.protein_g) || 0), 0));
  $: totalKH = Math.round(doneMeals.reduce((s, m) => s + (Number(m.carbs_g) || 0), 0));
  $: totalF = Math.round(doneMeals.reduce((s, m) => s + (Number(m.fat_g) || 0), 0));

  let expandedTraining = false;
  let quickAdd = '';
  let photoInput: HTMLInputElement;
  let photoLoading = false;
  let confirmData: { slot: number; name: string; kcal: number; protein_g: number; carbs_g: number; fat_g: number } | null = null;
  let choosingSlot = false;

  type UnifiedItem = { id: string; type: 'metric' | 'meal' | 'training' | 'cardio' | 'todo'; icon: string; title: string; done: boolean; sortKey: string; metricField?: string; metricValue?: string | number | null; metricUnit?: string; metricEditable?: boolean; metricCheckable?: boolean; metricDoneField?: string; hasProgress?: boolean; progressCurrent?: number; progressTarget?: number; kcal?: number | null; protein?: number | null; mealTime?: string | null; todoData?: Todo; };

  $: unifiedItems = buildUnifiedItems(entry, meals, todos, trainingSuggestion);

  function buildUnifiedItems(entry: DayEntry | null, mealList: Meal[], todoList: Todo[], suggestion: TrainingSuggestion | null): UnifiedItem[] {
    const items: UnifiedItem[] = [];
    if (!entry) return items;
    items.push({ id: 'metric-weight', type: 'metric', icon: 'weight', title: 'Gewicht', done: false, sortKey: '00-00', metricField: 'weight_kg', metricValue: entry.weight_kg ?? null, metricUnit: 'kg', metricEditable: true });
    items.push({ id: 'metric-steps', type: 'metric', icon: 'steps', title: 'Schritte', done: entry.steps_done ?? false, sortKey: '00-01', metricField: 'steps', metricValue: entry.steps ?? null, hasProgress: true, progressCurrent: entry.steps ?? 0, progressTarget: goals.steps });
    items.push({ id: 'metric-sleep', type: 'metric', icon: 'sleep', title: 'Schlaf', done: entry.sleep_done ?? false, sortKey: '00-02', metricField: 'sleep_hours', metricValue: entry.sleep_hours ?? null, metricUnit: 'h', hasProgress: true, progressCurrent: entry.sleep_hours ?? 0, progressTarget: goals.sleepHours });
    items.push({ id: 'metric-creatine', type: 'metric', icon: 'creatine', title: 'Kreatin', done: entry.creatine_done ?? false, sortKey: '00-03', metricField: 'creatine_done', metricValue: entry.creatine_done ? 'Eingenommen' : 'Ausstehend', metricCheckable: true, metricDoneField: 'creatine_done', metricEditable: false });
    items.push({ id: 'metric-belly', type: 'metric', icon: 'belly', title: 'Bauchumfang', done: false, sortKey: '00-04', metricField: 'belly_cm', metricValue: entry.belly_cm ?? null, metricUnit: 'cm', metricEditable: true });
    const sortedMeals = [...mealList].sort((a, b) => (a.meal_slot ?? 99) - (b.meal_slot ?? 99));
    for (const m of sortedMeals) { items.push({ id: `meal-${m.id ?? m.meal_slot}`, type: 'meal', icon: 'meal', title: m.name || SLOT_NAMES[m.meal_slot] || 'Mahlzeit', done: m.is_done ?? false, sortKey: `01-${String(m.meal_slot).padStart(2,'0')}`, kcal: Number(m.kcal) || null, protein: Number(m.protein_g) || null, mealTime: m.default_time ? m.default_time.slice(0, 5) : null }); }
    const trainingType = suggestion?.training_type ?? entry.training_type ?? 'Training';
    items.push({ id: 'training', type: 'training', icon: 'training', title: trainingType, done: entry.training_done ?? false, sortKey: '02-00' });
    const cardioMin = entry.cardio_minutes ?? suggestion?.cardio_minutes ?? 0;
    items.push({ id: 'cardio', type: 'cardio', icon: 'cardio', title: cardioMin > 0 ? `Cardio ${cardioMin}min` : 'Cardio', done: (entry as any).cardio_done ?? false, sortKey: '02-01' });
    for (const t of todoList) { items.push({ id: `todo-${t.id}`, type: 'todo', icon: 'todo', title: t.title, done: t.status === 'done', sortKey: `03-${t.due_time ?? '99:99'}`, todoData: t }); }
    return items.sort((a, b) => a.sortKey.localeCompare(b.sortKey));
  }

  let lastTap: Record<string, number> = {};
  let longPressTimer: ReturnType<typeof setTimeout> | null = null;
  let longPressTriggered = false;
  let actionSheetItem: UnifiedItem | null = null;
  let editingTodo: Todo | null = null;
  let editTitle = ''; let editCategory = ''; let editPriority = 2; let editDueDate = ''; let editDueTime = '';

  function handleTouchStart(item: UnifiedItem, e: TouchEvent) {
    longPressTriggered = false;
    if (item.type !== 'todo') return;
    longPressTimer = setTimeout(() => {
      longPressTriggered = true;
      if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(50);
      actionSheetItem = item;
    }, 500);
  }
  function handleTouchEnd() { if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null; } }
  function handleTouchMove() { if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null; } }
  function handleContextMenu(item: UnifiedItem, e: MouseEvent) { if (item.type !== 'todo') return; e.preventDefault(); actionSheetItem = item; }

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
    const now = Date.now(); const id = item.id;
    if (lastTap[id] && now - lastTap[id] < 300) { lastTap[id] = 0; const canToggle = (item.type === 'metric' && item.metricCheckable) || item.type === 'meal' || item.type === 'training' || item.type === 'cardio' || item.type === 'todo'; if (!canToggle) return; if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(50); toggleDone(item); return; }
    lastTap[id] = now;
    if (item.type === 'training') { expandedTraining = !expandedTraining; return; }
  }

  async function toggleDone(item: UnifiedItem) {
    if (item.type === 'metric' && item.metricDoneField) { const newVal = !(entry as any)[item.metricDoneField]; try { await api.upsertDayEntry({ ...entry, [item.metricDoneField]: newVal, date: currentDate }); entry = { ...entry, [item.metricDoneField]: newVal }; dispatch('update', { field: item.metricDoneField, value: newVal }); } catch {} return; }
    if (item.type === 'meal') { const mealId = item.id.replace('meal-', ''); const meal = meals.find((m) => String(m.id) === mealId || `meal-${m.meal_slot}` === item.id); if (!meal?.id) return; try { await api.markMealDone(meal.id); meals = meals.map((m) => m.id === meal.id ? { ...m, is_done: !m.is_done } : m); dispatch('mealtoggle', { id: meal.id, is_done: !meal.is_done }); } catch {} return; }
    if (item.type === 'training' && entry) { const newVal = !entry.training_done; try { await api.upsertDayEntry({ ...entry, training_done: newVal, date: currentDate }); entry = { ...entry, training_done: newVal }; dispatch('trainingtoggle', newVal); } catch {} return; }
    if (item.type === 'cardio' && entry) { const newVal = !(entry as any).cardio_done; try { await api.upsertDayEntry({ ...entry, cardio_done: newVal, date: currentDate } as any); entry = { ...entry, cardio_done: newVal } as any; dispatch('cardiotoggle', newVal); } catch {} return; }
    if (item.type === 'todo') { const todoId = item.id.replace('todo-', ''); try { await api.markTodoDone(todoId); todos = todos.map((t) => String(t.id) === todoId ? { ...t, status: t.status === 'open' ? 'done' : 'open' } : t); dispatch('todotoggle', { id: todoId }); } catch {} return; }
  }

  async function updateMetric(field: string, value: any) { if (!entry) return; entry = { ...entry, [field]: value }; try { await api.upsertDayEntry({ ...entry, date: currentDate }); dispatch('update', { field, value }); } catch {} }
  function handleTrainingComplete() { expandedTraining = false; if (entry) { entry = { ...entry, training_done: true }; dispatch('trainingtoggle', true); } }

  async function addQuick() { const title = quickAdd.trim(); if (!title) return; try { const n = await api.createTodo({ due_date: currentDate, title, status: 'open', priority: 2, source: 'manual' } as any); if (n) { todos = [...todos, n]; dispatch('todoadd', n); } quickAdd = ''; } catch {} }
  function handleKey(e: KeyboardEvent) { if (e.key === 'Enter') { e.preventDefault(); addQuick(); } }

  function getCurrentSlot(): number { const now = new Date(); const t = now.getHours() * 60 + now.getMinutes(); if (t >= 240 && t < 630) return 1; if (t >= 630 && t < 840) return 2; if (t >= 840 && t < 1050) return 3; if (t >= 1050 && t < 1320) return 4; return 1; }
  function parseVisionResult(result: any) { if (!result?.analysis?.total) return null; const total = result.analysis.total; const firstItem = result.analysis.items?.[0]; return { name: firstItem?.name ?? 'Erkanntes Gericht', kcal: Number(total.kcal) || 0, protein_g: Number(total.protein_g) || 0, carbs_g: Number(total.carbs_g) || 0, fat_g: Number(total.fat_g) || 0 }; }
  function triggerPhoto() { photoInput?.click(); }
  async function onPhotoSelected(e: Event) { const input = e.target as HTMLInputElement; const file = input.files?.[0]; if (!file) return; photoLoading = true; try { const result = await api.analyzePhoto(file); const parsed = parseVisionResult(result); if (parsed) { confirmData = { slot: getCurrentSlot(), ...parsed }; choosingSlot = false; } } catch {} finally { photoLoading = false; input.value = ''; } }
  async function assignToSlot(slot: number) { if (!confirmData) return; const meal = meals.find((m) => m.meal_slot === slot); if (!meal?.id) { confirmData = null; choosingSlot = false; return; } try { await api.updateMeal(meal.id, { name: confirmData.name, kcal: confirmData.kcal, protein_g: confirmData.protein_g, carbs_g: confirmData.carbs_g, fat_g: confirmData.fat_g }); await api.markMealDone(meal.id); meals = meals.map((m) => m.id === meal.id ? { ...m, name: confirmData.name, kcal: String(confirmData.kcal), protein_g: String(confirmData.protein_g), carbs_g: String(confirmData.carbs_g), fat_g: String(confirmData.fat_g), is_done: true } : m); dispatch('mealtoggle', { id: meal.id, is_done: true }); } catch {} confirmData = null; choosingSlot = false; }
  function cancelConfirm() { confirmData = null; choosingSlot = false; }

  $: openCount = unifiedItems.filter((i) => !i.done).length;
</script>

<!-- Macro stats -->
<div class="macros">
  <div class="macro"><span class="macro-l" style="color:var(--amber)">kcal</span><span class="macro-v">{totalKcal}/{goals.kcal}</span><ProgressBar current={totalKcal} target={goals.kcal} color="var(--amber)" /></div>
  <div class="macro"><span class="macro-l" style="color:var(--blue)">P</span><span class="macro-v">{totalP}/{goals.protein}g</span><ProgressBar current={totalP} target={goals.protein} color="var(--blue)" /></div>
  <div class="macro"><span class="macro-l" style="color:var(--purple)">KH</span><span class="macro-v">{totalKH}/{goals.carbs}g</span><ProgressBar current={totalKH} target={goals.carbs} color="var(--purple)" /></div>
  <div class="macro"><span class="macro-l" style="color:var(--pink)">F</span><span class="macro-v">{totalF}/{goals.fat}g</span><ProgressBar current={totalF} target={goals.fat} color="var(--pink)" /></div>
</div>

<!-- Day list -->
<div class="daylist">
  <div class="daylist-hdr">
    <span>{openCount} offen</span>
    <button class="photo-btn" onclick={triggerPhoto} disabled={photoLoading} aria-label="Foto">
      {#if photoLoading}<Icon name="refresh" size={16} />{:else}<Icon name="camera" size={16} />{/if}
    </button>
  </div>

  {#each unifiedItems as item (item.id)}
    <div class="item tap-area" class:done={item.done}
      onclick={(e) => handleTap(item, e)}
      oncontextmenu={(e) => handleContextMenu(item, e)}
      ontouchstart={(e) => handleTouchStart(item, e)}
      ontouchend={handleTouchEnd}
      ontouchmove={handleTouchMove}
      ontouchcancel={handleTouchEnd}
      role="button" tabindex="0">
      <div class="item-check" class:done={item.done}>{#if item.done}<Icon name="check" size={14} />{/if}</div>
      <Icon name={item.icon} size={18} />
      <div class="item-body">
        <span class="item-title" class:strike={item.done}>{item.title}</span>
        <div class="item-badges">
          {#if item.type === 'meal' && item.kcal}<PillBadge value={Math.round(item.kcal)} unit="kcal" color="var(--amber)" />{/if}
          {#if item.type === 'meal' && item.protein}<PillBadge value={Math.round(item.protein)} unit="g P" color="var(--blue)" />{/if}
          {#if item.mealTime}<span class="item-time">{item.mealTime}</span>{/if}
        </div>
      </div>
      {#if item.type === 'metric'}
        <MetricRow icon="" label="" value={item.metricValue} unit={item.metricUnit ?? ''} editable={item.metricEditable ?? false} checkable={false} on:change={(e) => updateMetric(item.metricField!, e.detail)} />
      {/if}
      {#if item.hasProgress}<div class="item-prog"><ProgressBar current={item.progressCurrent ?? 0} target={item.progressTarget ?? 1} color="var(--text-dim)" /></div>{/if}
    </div>

    {#if item.id === 'metric-weight' && weightTrend.length > 0}
      <div class="spark-row"><Sparkline data={weightTrend} color="var(--blue)" height={24} width={90} fill={true} /></div>
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

<style>
  .macros { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; padding: 12px 14px; background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); }
  .macro { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
  .macro-l { font-size: 11px; text-transform: uppercase; font-weight: 600; }
  .macro-v { font-size: 13px; font-weight: 600; color: var(--text); white-space: nowrap; }

  .daylist { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; }
  .daylist-hdr { display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; border-bottom: 1px solid var(--border); font-size: 13px; color: var(--text-dim); font-weight: 500; }
  .photo-btn { width: 30px; height: 30px; border-radius: 6px; background: var(--card-2); border: 1px solid var(--border-2); color: var(--text-dim); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background 0.15s; }
  .photo-btn:active { background: #26272a; }
  .photo-btn:disabled { opacity: 0.5; }

  .item { display: flex; align-items: center; gap: 10px; padding: 12px 14px; border-bottom: 1px solid var(--border); cursor: pointer; transition: opacity 0.15s; min-height: 48px; -webkit-user-select: none; user-select: none; }
  .item:last-of-type { border-bottom: none; }
  .item.done { opacity: 0.35; }
  .item:active { background: var(--card-2); }

  .item-check { width: 20px; height: 20px; border-radius: 50%; border: 1.5px solid var(--border-2); flex-shrink: 0; display: flex; align-items: center; justify-content: center; transition: all 0.2s; color: transparent; }
  .item-check.done { background: var(--green); border-color: var(--green); color: #000; }

  .item-body { flex: 1; display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .item-title { font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: 500; color: var(--text); }
  .item-title.strike { text-decoration: line-through; }
  .item-badges { display: flex; align-items: center; gap: 4px; }
  .item-time { font-size: 11px; color: var(--text-faint); font-weight: 500; }
  .item-prog { flex: 0 0 70px; }
  .spark-row { padding: 0 14px 8px; }
  .train-inline { padding: 0 14px 8px; }

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
</style>