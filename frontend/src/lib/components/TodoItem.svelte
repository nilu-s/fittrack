<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import type { Todo } from '$lib/types';

  export let todo: Todo;

  const dispatch = createEventDispatcher();

  let expanded = false;
  let lastTap = 0;
  let editTitle = '';
  let editCategory = '';
  let editPriority = 'medium';
  let editDueDate = '';
  let editDueTime = '';

  $: priorityColor = { low: '#666', medium: '#f59e0b', high: '#ef4444' }[todo.priority] ?? '#666';

  function handleTap() {
    const now = Date.now();
    if (now - lastTap < 300) {
      // Doppel-tap = mark done
      if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(50);
      dispatch('done', todo.id);
      lastTap = 0;
    } else {
      lastTap = now;
      setTimeout(() => {
        if (Date.now() - lastTap >= 300) {
          expanded = !expanded;
          if (expanded) {
            editTitle = todo.title;
            editCategory = todo.category ?? '';
            editPriority = todo.priority;
            editDueDate = todo.due_date ?? '';
            editDueTime = todo.due_time ?? '';
          }
        }
      }, 320);
    }
  }

  function saveEdit() {
    dispatch('update', {
      id: todo.id,
      data: {
        title: editTitle,
        category: editCategory,
        priority: editPriority,
        due_date: editDueDate || null,
        due_time: editDueTime || null,
      },
    });
    expanded = false;
  }

  function deleteTodo() {
    dispatch('delete', todo.id);
  }
</script>

<div class="todo-item tap-area" class:done={todo.status === 'done'} class:expanded onclick={handleTap}>
  <div class="todo-main">
    {#if todo.status === 'done'}
      <span class="todo-check">✓</span>
    {:else}
      <span class="todo-check-empty">○</span>
    {/if}

    <span class="todo-title">{todo.title}</span>

    {#if todo.category}
      <span class="badge category-badge">{todo.category}</span>
    {/if}

    {#if todo.priority === 'high'}
      <span class="priority-dot" style="background:{priorityColor}"></span>
    {/if}

    {#if todo.due_time}
      <span class="badge time-badge">⏰ {todo.due_time}</span>
    {/if}

    {#if todo.source === 'google_calendar'}
      <span class="badge cal-badge">📅</span>
    {/if}
  </div>

  {#if expanded}
    <div class="todo-edit slide-down" onclick={(e) => e.stopPropagation()}>
      <input class="edit-input" placeholder="Titel" bind:value={editTitle} />
      <div class="edit-row">
        <input class="edit-input" placeholder="Kategorie" bind:value={editCategory} />
        <select class="edit-input" bind:value={editPriority}>
          <option value="low">Niedrig</option>
          <option value="medium">Mittel</option>
          <option value="high">Hoch</option>
        </select>
      </div>
      <div class="edit-row">
        <input class="edit-input" type="date" bind:value={editDueDate} />
        <input class="edit-input" type="time" bind:value={editDueTime} />
      </div>
      <div class="edit-actions">
        <button class="btn" onclick={saveEdit}>Speichern</button>
        <button class="btn btn-delete" onclick={deleteTodo}>Löschen</button>
      </div>
    </div>
  {/if}
</div>

<style>
  .todo-item {
    display: flex;
    flex-direction: column;
    padding: 0.5rem 0.625rem;
    border-bottom: 1px solid #333;
    cursor: pointer;
    transition: opacity 0.2s;
  }

  .todo-item:last-child {
    border-bottom: none;
  }

  .todo-item.done {
    opacity: 0.5;
  }

  .todo-item.done .todo-title {
    text-decoration: line-through;
  }

  .todo-main {
    display: flex;
    align-items: center;
    gap: 6px;
    min-height: 32px;
  }

  .todo-check {
    color: var(--accent-done);
    font-size: 0.875rem;
    flex-shrink: 0;
  }

  .todo-check-empty {
    color: var(--text-secondary);
    font-size: 0.875rem;
    flex-shrink: 0;
  }

  .todo-title {
    flex: 1;
    font-size: 0.8125rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .badge {
    font-size: 0.625rem;
    padding: 1px 6px;
    border-radius: 8px;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .category-badge {
    background: #333;
    color: var(--text-secondary);
  }

  .time-badge {
    background: #2a2a2a;
    color: var(--text-secondary);
  }

  .cal-badge {
    font-size: 0.75rem;
  }

  .priority-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .todo-edit {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-top: 0.5rem;
  }

  .edit-input {
    flex: 1;
    padding: 5px 8px;
    border-radius: 6px;
    background: #1a1a1a;
    border: 1px solid var(--card-border);
    color: var(--text-primary);
    font-size: 0.75rem;
  }

  .edit-row {
    display: flex;
    gap: 6px;
  }

  .edit-actions {
    display: flex;
    gap: 6px;
  }

  .edit-actions .btn {
    flex: 1;
  }

  .btn-delete {
    background: #5a2222;
    border-color: #7a3333;
  }

  .btn-delete:active {
    background: #6a2222;
  }
</style>