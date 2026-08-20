<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import TodoItem from './TodoItem.svelte';
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

  // --- Virtual todos from meals + training (daily routine) ---
  const SLOT_NAMES: Record<number, string> = { 1: 'Frühstück', 2: 'Mittag', 3: 'Abend', 4: 'Snack' };

  $: virtualTodos = buildRoutineTodos(dayEntry, meals);

  function buildRoutineTodos(entry: DayEntry | null, mealList: Meal[]): Todo[] {
    const items: Todo[] = [];

    // Meals as routine todos
    for (const m of mealList ?? []) {
      items.push({
        id: `routine-meal-${m.id ?? m.meal_slot}`,
        title: m.name || SLOT_NAMES[m.meal_slot] || 'Mahlzeit',
        status: m.is_done ? 'done' : 'open',
        due_time: m.default_time ? m.default_time.slice(0, 5) : null,
        due_date: currentDate,
        priority: 2,
        source: 'meal_routine',
        sort_order: m.meal_slot,
      });
    }

    // Training as routine todo — use dayEntry.training_type, fallback to rotation suggestion
    if (entry) {
      const trainingType = entry.training_type ?? trainingSuggestion?.training_type ?? 'Training';
      items.push({
        id: 'routine-training',
        title: trainingType,
        status: entry.training_done ? 'done' : 'open',
        due_time: null,
        due_date: currentDate,
        priority: 2,
        source: 'training',
        sort_order: 99,
      });
    }

    return items;
  }

  $: categories = [...new Set((todos ?? []).map((t) => t.category).filter(Boolean))] as string[];
  $: allTodos = [...virtualTodos, ...(todos ?? [])];
  $: openCount = allTodos.filter((t) => t.status === 'open').length;

  $: filteredTodos = getFilteredSorted(allTodos, filter, sort, categoryFilter, currentDate);

  function getFilteredSorted(todos: Todo[], filter: FilterMode, sort: SortMode, catFilter: string, date: string): Todo[] {
    let result = [...todos];

    // Filter
    if (filter === 'open') result = result.filter((t) => t.status === 'open');
    else if (filter === 'done') result = result.filter((t) => t.status === 'done');
    else if (filter === 'today') result = result.filter((t) => t.due_date === date);

    if (catFilter) result = result.filter((t) => t.category === catFilter);

    // Sort: routine items first (by sort_order), then by selected sort mode
    if (sort === 'priority') {
      result.sort((a, b) => (b.priority ?? 2) - (a.priority ?? 2));
    } else if (sort === 'due') {
      result.sort((a, b) => {
        const ad = a.due_date ?? '9999';
        const bd = b.due_date ?? '9999';
        return ad.localeCompare(bd);
      });
    } else {
      // time sort — routine items by sort_order first, then manual by time
      result.sort((a, b) => {
        const aRoutine = a.source === 'meal_routine' || a.source === 'training';
        const bRoutine = b.source === 'meal_routine' || b.source === 'training';
        if (aRoutine && bRoutine) {
          return (a.sort_order ?? 99) - (b.sort_order ?? 99);
        }
        if (aRoutine) return -1;
        if (bRoutine) return 1;
        const at = a.due_time ?? '99:99';
        const bt = b.due_time ?? '99:99';
        return at.localeCompare(bt);
      });
    }

    return result;
  }

  function isRoutineTodo(id?: string): boolean {
    return id?.startsWith('routine-') ?? false;
  }

  async function markDone(id: string | number) {
    if (!id) return;
    const idStr = String(id);

    // Handle routine todos
    if (isRoutineTodo(idStr)) {
      await toggleRoutineTodo(idStr);
      return;
    }

    // Regular todo
    try {
      await api.markTodoDone(id);
      todos = todos.map((t) => (t.id === id ? { ...t, status: t.status === 'open' ? 'done' : 'open' } : t));
    } catch {
      // graceful
    }
  }

  async function toggleRoutineTodo(id: string) {
    // Training
    if (id === 'routine-training' && dayEntry) {
      const newVal = !dayEntry.training_done;
      try {
        await api.upsertDayEntry({ ...dayEntry, training_done: newVal, date: currentDate });
        dispatch('trainingtoggle', newVal);
      } catch {
        // graceful
      }
      return;
    }

    // Meal
    if (id.startsWith('routine-meal-')) {
      const mealId = id.replace('routine-meal-', '');
      const meal = meals.find((m) => String(m.id) === mealId);
      if (!meal) return;
      try {
        await api.markMealDone(mealId);
        dispatch('mealtoggle', { id: mealId, is_done: !meal.is_done });
      } catch {
        // graceful
      }
      return;
    }
  }

  async function updateTodo(event: CustomEvent) {
    const { id, data } = event.detail;
    if (!id || isRoutineTodo(String(id))) return; // routine todos aren't editable here
    try {
      await api.updateTodo(id, data);
      todos = todos.map((t) => (t.id === id ? { ...t, ...data } : t));
    } catch {
      // graceful
    }
  }

  async function deleteTodo(id: string | number) {
    if (!id || isRoutineTodo(String(id))) return; // routine todos can't be deleted
    try {
      await api.deleteTodo(id);
      todos = todos.filter((t) => t.id !== id);
    } catch {
      // graceful
    }
  }

  async function addQuick() {
    const title = quickAdd.trim();
    if (!title) return;
    try {
      const newTodo = await api.createTodo({
        due_date: currentDate,
        title,
        status: 'open',
        priority: 2,
        source: 'manual',
      } as any);
      if (newTodo) {
        todos = [...todos, newTodo];
      }
      quickAdd = '';
    } catch {
      // graceful
    }
  }

  function handleKey(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      e.preventDefault();
      addQuick();
    }
  }
</script>

<section class="section-card todo-card">
  <div class="section-header" onclick={() => (showFilters = !showFilters)}>
    <span>📋 To-Dos ({openCount} offen)</span>
    <span class="filter-toggle">{showFilters ? '▲' : '▼'}</span>
  </div>

  {#if showFilters}
    <div class="filters slide-down">
      <div class="filter-row">
        <button class="filter-btn" class:active={filter === 'all'} onclick={() => (filter = 'all')}>Alle</button>
        <button class="filter-btn" class:active={filter === 'open'} onclick={() => (filter = 'open')}>Offen</button>
        <button class="filter-btn" class:active={filter === 'done'} onclick={() => (filter = 'done')}>Erledigt</button>
        <button class="filter-btn" class:active={filter === 'today'} onclick={() => (filter = 'today')}>Heute</button>
      </div>
      <div class="filter-row">
        <select class="sort-select" bind:value={sort}>
          <option value="time">Sort: Zeit</option>
          <option value="priority">Sort: Priorität</option>
          <option value="due">Sort: Fälligkeit</option>
        </select>
        {#if categories.length > 0}
          <select class="sort-select" bind:value={categoryFilter}>
            <option value="">Alle Kategorien</option>
            {#each categories as cat}
              <option value={cat}>{cat}</option>
            {/each}
          </select>
        {/if}
      </div>
    </div>
  {/if}

  <div class="todo-list">
    {#if filteredTodos.length > 0}
      <!-- Routine section label (only if there are routine items in the filtered list) -->
      {#if filteredTodos.some((t) => t.source === 'meal_routine' || t.source === 'training')}
        <div class="routine-label">📋 Tagesroutine</div>
      {/if}
      {#each filteredTodos as todo (todo.id)}
        <TodoItem {todo} ondon={(e) => markDone(e.detail)} onupdate={updateTodo} ondelete={(e) => deleteTodo(e.detail)} />
      {/each}
    {:else}
      <div class="no-todos muted text-sm">Keine To-Dos</div>
    {/if}
  </div>

  <div class="quick-add">
    <input
      class="quick-add-input"
      placeholder="+ To-Do hinzufügen…"
      bind:value={quickAdd}
      onkeydown={handleKey}
    />
    <button class="add-btn" onclick={addQuick} disabled={!quickAdd.trim()}>+</button>
  </div>
</section>

<style>
  .todo-list {
    max-height: 400px;
    overflow-y: auto;
  }

  .no-todos {
    text-align: center;
    padding: 1.25rem;
  }

  .routine-label {
    font-size: 0.6875rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-secondary);
    padding: 0.5rem 0.625rem 0.25rem;
    font-weight: 600;
  }

  .filters {
    padding: 0.5rem 0.625rem;
    border-bottom: 1px solid var(--card-border);
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .filter-row {
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
  }

  .filter-btn {
    padding: 3px 10px;
    border-radius: 14px;
    background: #1f1f1f;
    border: 1px solid var(--card-border);
    color: var(--text-secondary);
    font-size: 0.6875rem;
    cursor: pointer;
    transition: all 0.15s;
  }

  .filter-btn.active {
    background: #444;
    color: var(--text-primary);
    border-color: #555;
  }

  .sort-select {
    flex: 1;
    padding: 4px 8px;
    border-radius: 6px;
    background: #1f1f1f;
    border: 1px solid var(--card-border);
    color: var(--text-primary);
    font-size: 0.6875rem;
    cursor: pointer;
  }

  .quick-add {
    display: flex;
    gap: 6px;
    padding: 0.625rem;
    border-top: 1px solid var(--card-border);
  }

  .quick-add-input {
    flex: 1;
    padding: 6px 10px;
    border-radius: 8px;
    background: #1f1f1f;
    border: 1px solid var(--card-border);
    color: var(--text-primary);
    font-size: 0.8125rem;
  }

  .add-btn {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: var(--accent-done);
    color: #0f0f0f;
    font-size: 1.1rem;
    font-weight: 700;
    cursor: pointer;
    border: none;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: opacity 0.15s;
  }

  .add-btn:disabled {
    opacity: 0.4;
  }

  .add-btn:active {
    transform: scale(0.95);
  }

  .filter-toggle {
    cursor: pointer;
    padding: 0 4px;
    font-size: 0.75rem;
    color: var(--text-secondary);
  }
</style>