<script lang="ts">
  import { onMount } from 'svelte';
  import SettingsHeader from '$lib/components/SettingsHeader.svelte';
  import Icon from '$lib/components/Icon.svelte';
  import { api } from '$lib/api';
  import type { TodoRoutine } from '$lib/types';

  const WEEKDAYS = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];
  let routines: TodoRoutine[] = [];
  let title = '';
  let dueTime = '';
  let selectedDays = [0, 1, 2, 3, 4, 5, 6];
  let priority = 2;
  let loading = true;
  let saving = false;
  let error = '';

  onMount(async () => {
    try { routines = await api.getTodoRoutines(); }
    catch { error = 'Routinen konnten nicht geladen werden.'; }
    finally { loading = false; }
  });

  function toggleDay(day: number) {
    selectedDays = selectedDays.includes(day) ? selectedDays.filter((value) => value !== day) : [...selectedDays, day].sort();
  }
  function dayLabel(days: number[]) { return days.length === 7 ? 'Täglich' : days.map((day) => WEEKDAYS[day]).join(', '); }
  async function addRoutine() {
    if (!title.trim() || !selectedDays.length) { error = 'Bitte gib einen Namen und mindestens einen Wochentag an.'; return; }
    saving = true; error = '';
    const created = await api.createTodoRoutine({ title: title.trim(), weekdays: selectedDays, due_time: dueTime || null, priority, is_active: true });
    saving = false;
    if (!created) { error = 'Routine konnte nicht gespeichert werden.'; return; }
    routines = [...routines, created]; title = ''; dueTime = ''; selectedDays = [0, 1, 2, 3, 4, 5, 6]; priority = 2;
  }
  async function setActive(routine: TodoRoutine, is_active: boolean) {
    if (!routine.id) return;
    const updated = await api.updateTodoRoutine(routine.id, { is_active });
    if (updated) routines = routines.map((item) => item.id === updated.id ? updated : item);
    else error = 'Änderung konnte nicht gespeichert werden.';
  }
  async function remove(routine: TodoRoutine) {
    if (!routine.id || !confirm(`„${routine.title}“ wirklich entfernen? Bereits erzeugte To-dos bleiben erhalten.`)) return;
    if (await api.deleteTodoRoutine(routine.id)) routines = routines.filter((item) => item.id !== routine.id);
    else error = 'Routine konnte nicht entfernt werden.';
  }
</script>

<svelte:head><title>Chronickel – Wiederkehrende To-dos</title></svelte:head>

<div class="page">
  <SettingsHeader title="Wiederkehrende To-dos" subtitle="Lege fest, welche To-dos an bestimmten Tagen automatisch in deiner Tagesliste erscheinen." />

  <section class="surface" aria-labelledby="new-routine-title">
    <header><div><h2 id="new-routine-title">Neue Routine</h2><p>Eine Routine erzeugt höchstens ein To-do pro passendendem Tag.</p></div></header>
    <div class="form">
      <label>Bezeichnung<input bind:value={title} placeholder="z. B. Kreatin einnehmen" maxlength="200" /></label>
      <fieldset><legend>Wiederholen an</legend><div class="days">{#each WEEKDAYS as label, day}<button type="button" class:chosen={selectedDays.includes(day)} aria-pressed={selectedDays.includes(day)} onclick={() => toggleDay(day)}>{label}</button>{/each}</div></fieldset>
      <div class="options"><label>Uhrzeit <input type="time" bind:value={dueTime} /></label><label>Priorität <select bind:value={priority}><option value={1}>Niedrig</option><option value={2}>Mittel</option><option value={3}>Hoch</option></select></label></div>
      <button class="primary" type="button" onclick={addRoutine} disabled={saving}>{saving ? 'Speichere…' : 'Routine hinzufügen'}</button>
    </div>
  </section>

  {#if error}<p class="message error" role="alert">{error}</p>{/if}
  <section class="surface" aria-labelledby="routine-list-title">
    <header><div><h2 id="routine-list-title">Deine Routinen</h2><p>Deaktivierte Routinen erzeugen keine neuen To-dos.</p></div></header>
    {#if loading}<p class="empty">Lade Routinen…</p>
    {:else if !routines.length}<p class="empty">Noch keine wiederkehrenden To-dos eingerichtet.</p>
    {:else}<div class="list">{#each routines as routine (routine.id)}<article class:inactive={!routine.is_active}><div class="icon"><Icon name="todo" size={18} /></div><div class="body"><strong>{routine.title}</strong><small>{dayLabel(routine.weekdays)}{routine.due_time ? ` · ${routine.due_time.slice(0, 5)} Uhr` : ''}</small></div><label class="switch"><span class="sr-only">{routine.title} aktiv</span><input type="checkbox" checked={routine.is_active} onchange={(event) => setActive(routine, event.currentTarget.checked)} /><span aria-hidden="true"></span></label><button class="remove" type="button" onclick={() => remove(routine)} aria-label={`${routine.title} entfernen`}><Icon name="trash" size={17} /></button></article>{/each}</div>{/if}
  </section>
</div>

<style>
  .page { display:grid; gap:var(--space-3); padding-top:var(--space-3); } .surface { overflow:hidden; border:1px solid var(--border-subtle); border-radius:var(--radius-surface); background:var(--surface-default); } header { padding:var(--space-4); border-bottom:1px solid var(--border-subtle); } h2,p { margin:0; } h2 { font-size:16px; } header p,small,.empty { color:var(--text-tertiary); font-size:12px; line-height:1.45; } .form { display:grid; gap:var(--space-3); padding:var(--space-4); } label,fieldset { display:grid; gap:5px; color:var(--text-secondary); font-size:12px; } fieldset { border:0; padding:0; } legend { margin-bottom:5px; } input,select { width:100%; min-height:var(--control-min); border:1px solid var(--border-default); border-radius:var(--radius-control); background:var(--surface-raised); color:var(--text-primary); padding:8px 10px; font:inherit; } .days,.options { display:flex; gap:7px; flex-wrap:wrap; } .days button { min-width:42px; min-height:38px; border:1px solid var(--border-default); border-radius:var(--radius-full); background:var(--surface-default); color:var(--text-secondary); font:inherit; } .days button.chosen,.primary { border-color:var(--status-success); background:var(--status-success); color:var(--text-on-accent); font-weight:700; } .options label { flex:1 1 150px; } button { cursor:pointer; } button:focus-visible,input:focus-visible,select:focus-visible { outline:2px solid var(--status-info); outline-offset:2px; } .primary { min-height:var(--control-min); border-radius:var(--radius-control); padding:0 14px; } .primary:disabled { opacity:.6; cursor:wait; } .empty,.message { padding:var(--space-4); } .error { color:var(--status-danger); } .list { display:grid; } article { display:flex; align-items:center; gap:10px; padding:12px var(--space-4); border-top:1px solid var(--border-subtle); } .icon { color:var(--status-success); } .body { display:grid; flex:1; gap:3px; min-width:0; } strong { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:14px; } .inactive { opacity:.55; } .switch { display:block; position:relative; width:44px; height:26px; } .switch input { position:absolute; opacity:0; width:1px; height:1px; } .switch span { display:block; height:100%; border-radius:20px; background:var(--border-default); transition:background var(--motion-fast); } .switch span::after { content:''; display:block; width:20px; height:20px; margin:3px; border-radius:50%; background:var(--surface-default); transition:transform var(--motion-fast); } .switch input:checked + span { background:var(--status-success); } .switch input:checked + span::after { transform:translateX(18px); } .switch input:focus-visible + span { outline:2px solid var(--status-info); outline-offset:2px; } .remove { display:grid; place-items:center; width:36px; height:36px; border:0; border-radius:var(--radius-control); background:transparent; color:var(--status-danger); } .remove:active { background:var(--surface-raised); } .sr-only { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; }
</style>
