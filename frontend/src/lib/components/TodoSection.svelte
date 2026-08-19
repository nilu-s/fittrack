<script lang="ts">
  import TodoItem from './TodoItem.svelte';
  import { api } from '$lib/api';
  import type { Todo } from '$lib/types';

  export let todos: Todo[];
  export let currentDate: string;

  type FilterMode = 'all' | 'open' | 'done' | 'today';
  type SortMode = 'time' | 'priority' | 'due';

  let filter: FilterMode = 'open';
  let sort: SortMode = 'time';
  let categoryFilter: string = '';
  let quickAdd = '';
  let showFilters = false;

  $: categories = [...new Set((todos ?? []).map((t) => t.category).filter(Boolean))] as string[];
  $: openCount = (todos ?? []).filter((t) => t.status === 'open').length;

  $: filteredTodos = getFilteredSorted(todos ?? [], filter, sort, categoryFilter, currentDate);

  function getFilteredSorted(todos: Todo[], filter: FilterMode, sort: SortMode, catFilter: string, date: string): Todo[] {
    let result = [...todos];

    // Filter
    if (filter === 'open') result = result.filter((t) => t.status === 'open');
    else if (filter === 'done') result = result.filter((t) => t.status === 'done');
    else if (filter === 'today') result = result.filter((t) => t.due_date === date || t.date === date);

    if (catFilter) result = result.filter((t) => t.category === catFilter);

    // Sort
    if (sort === 'priority') {
      result.sort((a, b) => (b.priority ?? 2) - (a.priority ?? 2));
    } else if (sort === 'due') {
      result.sort((a, b) => {
        const ad = a.due_date ?? '9999';
        const bd = b.due_date ?? '9999';
        return ad.localeCompare(bd);
      });
    } else {
      // time sort - by due_time then sort_order
      result.sort((a, b) => {
        const at = a.due_time ?? '99:99';
        const bt = b.due_time ?? '99:99';
        return at.localeCompare(bt);
      });
    }

    return result;
  }

  async function markDone(id: number) {
    if (!id) return;
    try {
      await api.markTodoDone(id);
      todos = todos.map((t) => (t.id === id ? { ...t, status: t.status === 'open' ? 'done' : 'open' } : t));
    } catch {
      // graceful
    }
  }

  async function updateTodo(event: CustomEvent) {
    const { id, data } = event.detail;
    if (!id) return;
    try {
      await api.updateTodo(id, data);
      todos = todos.map((t) => (t.id === id ? { ...t, ...data } : t));
    } catch {
      // graceful
    }
  }

  async function deleteTodo(id: number) {
    if (!id) return;
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
      });
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
    {#each filteredTodos as todo (todo.id)}
      <TodoItem {todo} ondon={(e) => markDone(e.detail)} onupdate={updateTodo} ondelete={(e) => deleteTodo(e.detail)} />
    {:else}
      <div class="no-todos muted text-sm">Keine To-Dos</div>
    {/each}
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