<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { api } from '$lib/api';
  import Icon from './Icon.svelte';
  import type { Todo } from '$lib/types';

  export let spaceName: string;
  export let date: string;
  export let todos: Todo[] = [];
  const dispatch = createEventDispatcher<{ updated: Todo; edit: Todo }>();
  let savingId = '';
  $: ordered = [...todos].sort((a, b) => (a.status === 'done' ? 1 : 0) - (b.status === 'done' ? 1 : 0) || (a.start_time ?? a.due_time ?? '').localeCompare(b.start_time ?? b.due_time ?? ''));
  async function toggle(todo: Todo) { if (!todo.id || savingId) return; savingId = todo.id; const updated = await api.markTodoDone(todo.id); savingId = ''; if (updated) dispatch('updated', updated); }
</script>

<section class="space-day" aria-labelledby="space-day-title">
  <header><div><p>GEMEINSAMER BEREICH</p><h1 id="space-day-title">{spaceName}</h1><span>{new Date(`${date}T00:00:00`).toLocaleDateString('de-DE', { weekday: 'long', day: 'numeric', month: 'long' })}</span></div><div class="count">{todos.filter((todo) => todo.status === 'open').length} offen</div></header>
  {#if ordered.length}<ul>{#each ordered as todo (todo.id)}<li class:done={todo.status === 'done'}><button class="check" type="button" aria-label={todo.status === 'done' ? `${todo.title} erneut öffnen` : `${todo.title} erledigen`} disabled={savingId === todo.id} onclick={() => toggle(todo)}>{#if todo.status === 'done'}<Icon name="check" size={15}/>{/if}</button><button class="details" type="button" onclick={() => dispatch('edit', todo)}><strong>{todo.title}</strong><span>{#if todo.assignee_display_name}{todo.assignee_display_name}{/if}{#if todo.start_time || todo.due_time}{todo.assignee_display_name ? ' · ' : ''}{todo.start_time ?? todo.due_time}{/if}</span></button></li>{/each}</ul>{:else}<p class="empty">Für diesen Bereich sind heute keine To-dos geplant.</p>{/if}
</section>

<style>
  .space-day { display:grid; gap:var(--space-3); padding:var(--space-4); border:1px solid var(--border-subtle); border-radius:var(--radius-surface); background:var(--surface-default); } header { display:flex; justify-content:space-between; gap:var(--space-3); } header p,header span { display:block; margin:0; color:var(--text-tertiary); font-size:11px; font-weight:700; letter-spacing:.06em; } h1 { margin:2px 0; font-size:22px; letter-spacing:-.03em; } .count { align-self:flex-start; padding:5px 8px; border-radius:var(--radius-full); background:var(--surface-accent); color:var(--action-primary); font-size:12px; font-weight:700; white-space:nowrap; } ul { display:grid; gap:6px; margin:0; padding:0; list-style:none; } li { display:grid; grid-template-columns:38px minmax(0,1fr); align-items:center; min-height:56px; border:1px solid var(--border-subtle); border-radius:var(--radius-control); background:var(--surface-raised); } button { font:inherit; cursor:pointer; } .check { display:grid; place-items:center; align-self:stretch; border:0; border-right:1px solid var(--border-subtle); border-radius:var(--radius-control) 0 0 var(--radius-control); background:transparent; color:var(--status-success); } .details { display:grid; gap:3px; min-width:0; padding:8px 10px; border:0; border-radius:0 var(--radius-control) var(--radius-control) 0; background:transparent; color:var(--text-primary); text-align:left; } strong { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:13px; } .details span { color:var(--text-tertiary); font-size:11px; } li.done strong { color:var(--text-tertiary); text-decoration:line-through; } .empty { margin:0; padding:var(--space-4); color:var(--text-tertiary); text-align:center; font-size:13px; } button:focus-visible { outline:2px solid var(--status-info); outline-offset:2px; }
</style>
