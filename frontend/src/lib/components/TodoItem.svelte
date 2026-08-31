<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import PillBadge from './PillBadge.svelte';
  import Icon from './Icon.svelte';
  import type { Todo } from '$lib/types';

  export let todo: Todo;
  export let kcal: number | null = null;
  export let protein: number | null = null;
  export let fiber: number | null = null;
  export let sugar: number | null = null;
  const dispatch = createEventDispatcher();
  let expanded = false;
  let lastTap = 0;
  let editTitle = ''; let editCategory = ''; let editPriority = 2; let editDueDate = ''; let editDueTime = '';
  let showActionSheet = false;

  const PRIORITY_COLORS: Record<number, string> = { 1: 'var(--text-faint)', 2: 'var(--amber)', 3: 'var(--red)' };
  $: priorityColor = PRIORITY_COLORS[todo.priority] ?? 'var(--text-faint)';
  $: isRoutine = todo.source === 'meal_routine' || todo.source === 'cardio';
  $: isMealRoutine = todo.source === 'meal_routine';
  $: canEdit = !isRoutine && todo.source !== 'training';
  $: canLongPress = canEdit || isMealRoutine;  // meals can be long-pressed to swap dish

  let longPressTimer: ReturnType<typeof setTimeout> | null = null;
  let longPressTriggered = false;

  function handleTouchStart() {
    longPressTriggered = false;
    if (!canLongPress) return;
    longPressTimer = setTimeout(() => {
      longPressTriggered = true;
      if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(50);
      if (isMealRoutine) {
        dispatch('editmeal', todo.id);
      } else {
        showActionSheet = true;
      }
    }, 500);
  }

  function handleTouchEnd() {
    if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null; }
  }

  function handleTouchMove() {
    if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null; }
  }

  function handleContextMenu(e: MouseEvent) {
    if (!canLongPress) return;
    e.preventDefault();
    if (isMealRoutine) {
      dispatch('editmeal', todo.id);
    } else {
      showActionSheet = true;
    }
  }

  function handleTap() {
    if (longPressTriggered) { longPressTriggered = false; return; }
    // Meal details use the native dblclick event below. This keeps that
    // interaction distinct from the touch double-tap completion gesture.
    if (isMealRoutine) return;
    const now = Date.now();
    if (now - lastTap < 300) { if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(50); dispatch('done', todo.id); lastTap = 0; return; }
    lastTap = now;
    if (todo.source === 'training') { dispatch('expand', todo.id); return; }
  }

  function startEdit() {
    showActionSheet = false;
    expanded = true;
    editTitle = todo.title;
    editCategory = todo.category ?? '';
    editPriority = todo.priority;
    editDueDate = todo.due_date ?? '';
    editDueTime = todo.due_time ?? '';
  }

  function confirmDelete() {
    showActionSheet = false;
    dispatch('delete', todo.id);
  }

  function saveEdit() { dispatch('update', { id: todo.id, data: { title: editTitle, category: editCategory, priority: editPriority, due_date: editDueDate || null, due_time: editDueTime || null } }); expanded = false; }
  function deleteTodo() { dispatch('delete', todo.id); }
</script>

<div class="ti tap-area" class:done={todo.status === 'done'} class:expanded={expanded}
  onclick={handleTap}
  oncontextmenu={handleContextMenu}
  ontouchstart={handleTouchStart}
  ontouchend={handleTouchEnd}
  ontouchmove={handleTouchMove}
  ontouchcancel={handleTouchEnd}
  role="button" tabindex="0">
  <div class="ti-main">
    <div class="ti-check" class:done={todo.status === 'done'}>{#if todo.status === 'done'}<Icon name="check" size={14} />{/if}</div>
    {#if todo.priority === 3}<span class="ti-prio" style="background:{priorityColor}"></span>{/if}
    <span class="ti-title">{todo.title}</span>
    {#if kcal != null && kcal > 0}<PillBadge value={Math.round(kcal)} unit="kcal" color="var(--amber)" />{/if}
    {#if protein != null && protein > 0}<PillBadge value={Math.round(protein)} unit="g P" color="var(--blue)" />{/if}
    {#if fiber != null && fiber > 0}<PillBadge value={Math.round(fiber)} unit="g Ballaststoffe" color="var(--green)" />{/if}
    {#if sugar != null && sugar > 0}<PillBadge value={Math.round(sugar)} unit="g Zucker" color="var(--amber)" />{/if}
    {#if todo.category}<span class="ti-badge">{todo.category}</span>{/if}
    {#if todo.due_time}<span class="ti-time">{todo.due_time}</span>{/if}
    {#if todo.source === 'google_calendar'}<Icon name="calendar" size={14} />{/if}
    {#if isMealRoutine}<span class="ti-recipe-marker">Rezeptdetails</span>{/if}
  </div>
  {#if expanded}
    <div class="ti-edit slide-down" onclick={(e) => e.stopPropagation()}>
      <input placeholder="Titel" bind:value={editTitle} />
      <div class="ti-row"><input placeholder="Kategorie" bind:value={editCategory} /><select bind:value={editPriority}><option value={1}>Niedrig</option><option value={2}>Mittel</option><option value={3}>Hoch</option></select></div>
      <div class="ti-row"><input type="date" bind:value={editDueDate} /><input type="time" bind:value={editDueTime} /></div>
      <div class="ti-actions"><button class="btn" onclick={saveEdit}>Speichern</button><button class="btn btn-del" onclick={deleteTodo}>Löschen</button></div>
    </div>
  {/if}
</div>

{#if showActionSheet}
  <div class="action-overlay" onclick={() => (showActionSheet = false)} ontouchstart={(e) => { e.preventDefault(); showActionSheet = false; }}>
    <div class="action-sheet" onclick={(e) => e.stopPropagation()} ontouchstart={(e) => e.stopPropagation()}>
      <div class="action-handle"></div>
      <div class="action-title">{todo.title}</div>
      <button class="action-btn" onclick={startEdit}>
        <Icon name="edit" size={18} />
        <span>Bearbeiten</span>
      </button>
      <button class="action-btn action-del" onclick={confirmDelete}>
        <Icon name="trash" size={18} />
        <span>Löschen</span>
      </button>
      <button class="action-cancel" onclick={() => (showActionSheet = false)}>Abbrechen</button>
    </div>
  </div>
{/if}

<style>
  .ti { display: flex; flex-direction: column; padding: 12px 14px; border-bottom: 1px solid var(--border); cursor: pointer; transition: opacity 0.15s; -webkit-user-select: none; user-select: none; }
  .ti:last-child { border-bottom: none; }
  .ti.done { opacity: 0.35; }
  .ti.done .ti-title { text-decoration: line-through; }
  .ti:active { background: var(--card-2); }
  .ti-main { display: flex; align-items: center; gap: 8px; min-height: 34px; }
  .ti-check { width: 20px; height: 20px; border-radius: 50%; border: 1.5px solid var(--border-2); flex-shrink: 0; display: flex; align-items: center; justify-content: center; color: transparent; transition: all 0.2s; }
  .ti-check.done { background: var(--green); border-color: var(--green); color: #000; }
  .ti-prio { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
  .ti-title { flex: 1; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: 500; }
  .ti-badge { font-size: 11px; padding: 2px 8px; border-radius: 6px; background: var(--card-2); color: var(--text-dim); white-space: nowrap; }
  .ti-time { font-size: 11px; color: var(--text-faint); font-weight: 500; }
  .ti-recipe-marker { font-size: 10px; color: var(--green); border: 1px solid color-mix(in srgb, var(--green) 55%, var(--border-2)); border-radius: 999px; padding: 2px 6px; white-space: nowrap; }
  .ti-edit { display: flex; flex-direction: column; gap: 8px; margin-top: 8px; }
  .ti-edit input, .ti-edit select { flex: 1; padding: 8px 10px; border-radius: 6px; background: var(--bg); border: 1px solid var(--border-2); color: var(--text); font-size: 14px; }
  .ti-edit input:focus, .ti-edit select:focus { border-color: var(--blue); }
  .ti-row { display: flex; gap: 8px; }
  .ti-actions { display: flex; gap: 8px; }
  .ti-actions .btn { flex: 1; }
  .btn-del { background: rgba(255,69,58,0.1); border-color: var(--red); color: var(--red); }
  .btn-del:active { background: rgba(255,69,58,0.2); }

  .action-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 1000; display: flex; align-items: flex-end; justify-content: center; animation: fadeIn 0.15s; }
  .action-sheet { background: var(--card); border-radius: 16px 16px 0 0; width: 100%; max-width: 420px; padding: 8px 0 20px; box-shadow: 0 -4px 24px rgba(0,0,0,0.4); animation: slideUp 0.2s; }
  .action-handle { width: 36px; height: 4px; border-radius: 2px; background: var(--border-2); margin: 8px auto 12px; }
  .action-title { text-align: center; font-size: 14px; font-weight: 600; color: var(--text-dim); padding: 0 16px 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .action-btn { display: flex; align-items: center; gap: 12px; width: calc(100% - 16px); margin: 0 8px; padding: 14px 16px; border: none; border-radius: 10px; background: var(--card-2); color: var(--text); font-size: 15px; font-weight: 500; cursor: pointer; transition: background 0.15s; }
  .action-btn:active { background: var(--bg); }
  .action-del { color: var(--red); }
  .action-cancel { display: block; width: calc(100% - 16px); margin: 12px 8px 0; padding: 14px 16px; border: none; border-radius: 10px; background: var(--card-2); color: var(--text-dim); font-size: 15px; font-weight: 500; cursor: pointer; }
  .action-cancel:active { background: var(--bg); }

  @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
  @keyframes slideUp { from { transform: translateY(100%); } to { transform: translateY(0); } }
</style>
