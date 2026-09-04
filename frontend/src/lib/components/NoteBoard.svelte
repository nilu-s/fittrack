<script lang="ts">
  import { createEventDispatcher, tick } from 'svelte';
  import type { Note, Space, Todo } from '$lib/types';
  import { api } from '$lib/api';

  export let open = false;
  export let notes: Note[] = [];
  export let spaces: Space[] = [];
  export let loading = false;
  export let date = '';
  export let inline = false;
  const dispatch = createEventDispatcher<{ close: void; changed: Note; areachange: string | null }>();

  let selected: Note | null = null;
  let title = '';
  let body = '';
  let areaId = '';
  let planDate = '';
  let planTime = '';
  let draggedId = '';
  let draggedTodoId = '';
  let saving = false;
  let error = '';
  let boardMessage = '';
  let selectedAreaId = '';
  let selectedPlanNoteId = '';
  let selectedScheduledTodo: Todo | null = null;
  let planningDate = '';
  let planDuration = 60;
  let scheduledTodos: Todo[] = [];
  let scheduledLoading = false;
  let opener: HTMLElement | null = null;
  let detailDialog: HTMLDialogElement;
  let touchCandidate: { noteId: string; pointerId: number } | null = null;
  let touchDrag: { noteId: string; pointerId: number } | null = null;
  let touchDragTimer: ReturnType<typeof setTimeout> | null = null;
  let suppressDetailId = '';
  let resizing: { todoId: string; pointerId: number; startY: number; startDuration: number } | null = null;
  let resizeDuration = 0;

  $: privateNotes = notes.filter((note) => !note.space_id && note.status === 'active');
  $: plannedNotes = notes.filter((note) => note.status === 'planned');
  $: selectedArea = spaces.find((space) => space.id === selectedAreaId) ?? null;
  $: selectedAreaNotes = selectedAreaId ? notes.filter((note) => note.space_id === selectedAreaId && note.status === 'active') : [];
  $: selectedPlanNote = notes.find((note) => note.id === selectedPlanNoteId) ?? null;
  $: if (date && planningDate !== date) planningDate = date;
  $: timelineHours = Array.from({ length: 16 }, (_, index) => index + 6);

  function dateValue(value: Date) { return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`; }
  function dateLabel(value: Date) { return new Intl.DateTimeFormat('de-DE', { weekday: 'short', day: 'numeric', month: 'short' }).format(value); }
  function openDetails(note: Note, element?: HTMLElement) {
    opener = element ?? document.activeElement as HTMLElement;
    selected = note; title = note.title; body = note.body ?? ''; areaId = note.space_id ?? ''; planDate = ''; planTime = ''; error = '';
    void tick().then(() => { if (!detailDialog.open) detailDialog.showModal(); detailDialog.querySelector<HTMLInputElement>('#note-title')?.focus(); });
  }
  function closeDetails() { if (detailDialog?.open) detailDialog.close(); selected = null; error = ''; void tick().then(() => opener?.focus()); }
  async function save() {
    if (!selected || !title.trim() || saving) return;
    saving = true;
    const result = await api.updateNote(selected.id, { title: title.trim(), body: body.trim() || null });
    saving = false;
    if (!result) { error = 'Notiz konnte nicht gespeichert werden.'; return; }
    dispatch('changed', result); closeDetails();
  }
  async function move(note: Note, spaceId: string) {
    if (!spaceId || saving || note.space_id === spaceId) return;
    if (!window.confirm(`Die Notiz wird für alle Mitglieder von ${spaces.find((space) => space.id === spaceId)?.name ?? 'diesem Bereich'} sichtbar.`)) return;
    saving = true;
    const result = await api.moveNote(note.id, spaceId, true);
    saving = false;
    if (!result) { error = 'Bereich konnte nicht zugeordnet werden.'; return; }
    dispatch('changed', result);
  }
  function durationBetween(startTime?: string | null, endTime?: string | null) {
    if (!startTime || !endTime) return 60;
    const [startHours, startMinutes] = startTime.split(':').map(Number);
    const [endHours, endMinutes] = endTime.split(':').map(Number);
    return Math.max(5, (endHours * 60 + endMinutes) - (startHours * 60 + startMinutes));
  }
  function endTimeFor(startTime: string, duration: number) {
    const [hours, minutes] = startTime.split(':').map(Number);
    const total = Math.min(23 * 60 + 59, hours * 60 + minutes + duration);
    return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`;
  }
  function timelineStyle(todo: Todo) {
    const [hours, minutes] = (todo.start_time ?? '06:00').split(':').map(Number);
    const start = Math.max(0, hours * 60 + minutes - 6 * 60);
    const duration = resizing?.todoId === String(todo.id) ? resizeDuration : durationBetween(todo.start_time, todo.end_time);
    return `top:${start}px;height:${Math.max(36, duration)}px`;
  }
  function snapMinutes(value: number) { return Math.round(value / 15) * 15; }
  function timeForTimelineMinute(value: number) {
    const total = 6 * 60 + Math.max(0, Math.min(16 * 60 - 15, snapMinutes(value)));
    return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`;
  }
  function timelineMinuteForEvent(event: DragEvent) {
    const canvas = event.currentTarget as HTMLElement;
    return event.clientY - canvas.getBoundingClientRect().top;
  }
  async function loadScheduledTodos() {
    if (!selectedAreaId || !planningDate) { scheduledTodos = []; return; }
    scheduledLoading = true;
    const todos = await api.getTodos(planningDate);
    scheduledTodos = todos.filter((todo) => todo.space_id === selectedAreaId).sort((a, b) => (a.start_time ?? '99:99').localeCompare(b.start_time ?? '99:99') || a.title.localeCompare(b.title));
    scheduledLoading = false;
  }
  async function plan(note: Note, dueDate: string, startTime?: string, duration?: number, closeAfter = true) {
    if (!dueDate || saving) return;
    saving = true;
    const result = await api.planNote(note.id, dueDate, startTime || null);
    saving = false;
    if (!result) { error = 'Notiz konnte nicht geplant werden.'; return; }
    if (result.scheduled_todo_id && startTime && duration) await api.updateTodo(result.scheduled_todo_id, { end_time: endTimeFor(startTime, duration) });
    dispatch('changed', result);
    selectedPlanNoteId = '';
    boardMessage = `„${note.title}“ ist für ${dueDate}${startTime ? ` um ${startTime} Uhr` : ' ganztägig'} eingeplant.`;
    await loadScheduledTodos();
    if (closeAfter) closeDetails();
  }
  async function unschedule(note: Note) {
    if (saving) return;
    saving = true;
    const result = await api.unscheduleNote(note.id);
    saving = false;
    if (!result) { error = 'Planung konnte nicht aufgehoben werden.'; return; }
    dispatch('changed', result); closeDetails();
  }
  function dragStart(event: DragEvent, note: Note) { draggedId = note.id; draggedTodoId = ''; event.dataTransfer?.setData('text/plain', `note:${note.id}`); if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'; }
  function dragTodoStart(event: DragEvent, todo: Todo) { draggedTodoId = String(todo.id); draggedId = ''; event.dataTransfer?.setData('text/plain', `todo:${todo.id}`); if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'; }
  function droppedItem(event: DragEvent) { return event.dataTransfer?.getData('text/plain') || (draggedId ? `note:${draggedId}` : draggedTodoId ? `todo:${draggedTodoId}` : ''); }
  function allowDrop(event: DragEvent) { event.preventDefault(); if (event.dataTransfer) event.dataTransfer.dropEffect = 'move'; }
  async function dropArea(event: DragEvent, spaceId: string) { const item = droppedItem(event); const note = notes.find((value) => item === `note:${value.id}`); if (note) await move(note, spaceId); draggedId = ''; draggedTodoId = ''; }
  async function dropSlot(event: DragEvent, dueDate: string, time?: string) { const item = droppedItem(event); const note = notes.find((value) => item === `note:${value.id}`); if (note) await plan(note, dueDate, time, time ? 60 : undefined, false); draggedId = ''; draggedTodoId = ''; }
  async function dropTimeline(event: DragEvent) {
    const item = droppedItem(event); const startTime = timeForTimelineMinute(timelineMinuteForEvent(event));
    const note = notes.find((value) => item === `note:${value.id}`);
    const todo = scheduledTodos.find((value) => item === `todo:${value.id}`);
    if (note) await plan(note, planningDate, startTime, 60, false);
    else if (todo?.id) {
      const duration = durationBetween(todo.start_time, todo.end_time);
      const updated = await api.updateTodo(todo.id, { start_time: startTime, due_time: startTime, end_time: endTimeFor(startTime, duration), is_all_day: false });
      if (!updated) error = 'To-do konnte nicht verschoben werden.';
      else { boardMessage = `„${updated.title}“ ist um ${startTime} eingeplant.`; await loadScheduledTodos(); }
    }
    draggedId = ''; draggedTodoId = '';
  }
  async function dropUntimed(event: DragEvent) {
    const item = droppedItem(event); const note = notes.find((value) => item === `note:${value.id}`); const todo = scheduledTodos.find((value) => item === `todo:${value.id}`);
    if (note) await plan(note, planningDate, undefined, undefined, false);
    else if (todo?.id) {
      const updated = await api.updateTodo(todo.id, { start_time: null, due_time: null, end_time: null, is_all_day: true });
      if (!updated) error = 'To-do konnte nicht in die Zeile ohne Uhrzeit verschoben werden.';
      else { boardMessage = `„${updated.title}“ ist ohne Uhrzeit eingeplant.`; await loadScheduledTodos(); }
    }
    draggedId = ''; draggedTodoId = '';
  }
  function startResize(event: PointerEvent, todo: Todo) {
    if (!todo.id || !todo.start_time) return;
    event.preventDefault(); event.stopPropagation();
    resizing = { todoId: String(todo.id), pointerId: event.pointerId, startY: event.clientY, startDuration: durationBetween(todo.start_time, todo.end_time) };
    resizeDuration = resizing.startDuration;
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
  }
  function moveResize(event: PointerEvent) {
    if (!resizing || resizing.pointerId !== event.pointerId) return;
    const todo = scheduledTodos.find((value) => String(value.id) === resizing?.todoId);
    if (!todo?.start_time) return;
    const [hours, minutes] = todo.start_time.split(':').map(Number);
    const maxDuration = 22 * 60 - (hours * 60 + minutes);
    resizeDuration = Math.max(15, Math.min(maxDuration, snapMinutes(resizing.startDuration + event.clientY - resizing.startY)));
  }
  async function finishResize(event: PointerEvent) {
    if (!resizing || resizing.pointerId !== event.pointerId) return;
    const state = resizing; resizing = null;
    const todo = scheduledTodos.find((value) => String(value.id) === state.todoId);
    if (!todo?.id || !todo.start_time) return;
    const duration = resizeDuration; resizeDuration = 0;
    const updated = await api.updateTodo(todo.id, { end_time: endTimeFor(todo.start_time, duration), is_all_day: false });
    if (!updated) error = 'Dauer konnte nicht angepasst werden.';
    else { boardMessage = `„${updated.title}“ dauert jetzt ${duration} Minuten.`; await loadScheduledTodos(); }
  }
  function selectArea(spaceId: string) {
    selectedAreaId = spaceId;
    dispatch('areachange', spaceId);
    selectedPlanNoteId = '';
    selectedScheduledTodo = null;
    planTime = '09:00';
    planDuration = 60;
    boardMessage = `Zeitfenster für ${spaces.find((space) => space.id === spaceId)?.name ?? 'diesen Bereich'} geöffnet.`;
    void loadScheduledTodos();
  }
  function clearAreaSelection() { selectedAreaId = ''; dispatch('areachange', null); selectedPlanNoteId = ''; selectedScheduledTodo = null; scheduledTodos = []; boardMessage = ''; }
  function selectPlanNote(note: Note, element: HTMLElement) {
    selectedPlanNoteId = note.id;
    selectedScheduledTodo = null;
    opener = element;
    boardMessage = `„${note.title}“ auswählen: Startzeit und Dauer festlegen.`;
  }
  function selectScheduledTodo(todo: Todo) {
    selectedScheduledTodo = todo;
    selectedPlanNoteId = '';
    planTime = todo.start_time ?? '09:00';
    planDuration = durationBetween(todo.start_time, todo.end_time);
    boardMessage = `„${todo.title}“ bearbeiten: Startzeit oder Dauer anpassen.`;
  }
  function placeSelectedNote() {
    if (!selectedPlanNote || !planningDate || !planTime) { boardMessage = 'Wähle zuerst eine Notiz und gib eine Startzeit an.'; return; }
    void plan(selectedPlanNote, planningDate, planTime, planDuration, false);
  }
  async function saveScheduledTodo() {
    if (!selectedScheduledTodo || !planTime) return;
    saving = true;
    const updated = await api.updateTodo(selectedScheduledTodo.id!, { start_time: planTime, due_time: planTime, end_time: endTimeFor(planTime, planDuration), is_all_day: false });
    saving = false;
    if (!updated) { error = 'Zeitblock konnte nicht aktualisiert werden.'; return; }
    selectedScheduledTodo = updated;
    boardMessage = `„${updated.title}“ wurde im Tagesplan verschoben.`;
    await loadScheduledTodos();
  }
  function startTouchDrag(event: PointerEvent, note: Note) {
    if (event.pointerType === 'mouse') return;
    touchCandidate = { noteId: note.id, pointerId: event.pointerId };
    touchDragTimer = setTimeout(() => {
      if (touchCandidate?.noteId !== note.id) return;
      touchDrag = touchCandidate;
      boardMessage = `„${note.title}“ loslassen, sobald ein Bereich oder Kalender-Slot markiert ist.`;
    }, 280);
  }
  async function finishTouchDrag(event: PointerEvent) {
    if (touchCandidate?.pointerId === event.pointerId) touchCandidate = null;
    if (touchDragTimer) { clearTimeout(touchDragTimer); touchDragTimer = null; }
    if (!touchDrag || touchDrag.pointerId !== event.pointerId) return;
    const note = notes.find((item) => item.id === touchDrag?.noteId);
    const target = document.elementFromPoint(event.clientX, event.clientY)?.closest<HTMLElement>('[data-area-id],[data-slot-date],[data-timeline],[data-untimed]');
    touchDrag = null;
    if (!note || !target) { boardMessage = 'Keine Ablage gewählt. Die Notiz bleibt im Eingang.'; return; }
    suppressDetailId = note.id;
    setTimeout(() => suppressDetailId = '', 0);
    if (target.dataset.areaId) await move(note, target.dataset.areaId);
    else if (target.dataset.slotDate) await plan(note, target.dataset.slotDate, target.dataset.slotTime);
    else if (target.dataset.timeline) await plan(note, planningDate, timeForTimelineMinute(event.clientY - target.getBoundingClientRect().top), 60, false);
    else if (target.dataset.untimed) await plan(note, planningDate, undefined, undefined, false);
  }
  function openCard(note: Note, element: HTMLElement) { if (suppressDetailId === note.id) return; openDetails(note, element); }
  function closeBoard() { dispatch('close'); }
</script>

<svelte:window onpointerup={(event) => { void finishTouchDrag(event); void finishResize(event); }} onpointermove={moveResize} onpointercancel={finishTouchDrag} />

{#if open}
  <section id="note-board" class="board" class:inline aria-label="Notiz-Board">
    {#if loading}<p class="status" role="status">Notizen werden geladen…</p>
    {:else}
      {#if !selectedArea}
        <section aria-label="Privater Notiz-Eingang"><div class="grid">{#each privateNotes as note (note.id)}<button class:dragging={touchDrag?.noteId === note.id} class="note" type="button" draggable="true" ondragstart={(event) => dragStart(event, note)} onpointerdown={(event) => startTouchDrag(event, note)} onclick={(event) => openCard(note, event.currentTarget)}><strong>{note.title}</strong>{#if note.body}<small>{note.body}</small>{/if}</button>{:else}<p class="empty">Noch keine privaten Notizen.</p>{/each}</div></section>
        <section aria-labelledby="areas-title"><div class="section-title"><h3 id="areas-title">Bereiche</h3><span>Bereich wählen, um Zeitfenster zu öffnen</span></div><div class="areas">{#each spaces as space (space.id)}{@const areaNotes = notes.filter((note) => note.space_id === space.id && note.status === 'active')}<div class="area" data-area-id={space.id} role="group" aria-label={`Bereich ${space.name}; Notiz hier ablegen`} ondragover={allowDrop} ondrop={(event) => dropArea(event, space.id)}><button type="button" class="area-select" aria-label={`${space.name} öffnen`} onclick={() => selectArea(space.id)}><span><strong>{space.name}</strong><small>{space.members.length} Mitglieder · {areaNotes.length} offene Notizen</small></span><span aria-hidden="true">›</span></button>{#if areaNotes.length}<div class="area-notes" aria-label={`Offene Notizen in ${space.name}`}>{#each areaNotes as note (note.id)}<button class:dragging={touchDrag?.noteId === note.id} class="note" type="button" draggable="true" ondragstart={(event) => dragStart(event, note)} onpointerdown={(event) => startTouchDrag(event, note)} onclick={(event) => openCard(note, event.currentTarget)}><strong>{note.title}</strong>{#if note.body}<small>{note.body}</small>{/if}</button>{/each}</div>{:else}<p class="empty">Noch keine Notizen in diesem Bereich.</p>{/if}</div>{:else}<p class="empty">Lege unter Einstellungen einen Bereich an, um Notizen zu teilen.</p>{/each}</div></section>
      {:else}
        <section class="planning" aria-labelledby="calendar-title">
          <div class="section-title"><div><p class="eyebrow">BEREICH · {planningDate ? dateLabel(new Date(`${planningDate}T00:00:00`)) : 'Heute'}</p><h3 id="calendar-title">{selectedArea.name}</h3></div><button type="button" onclick={clearAreaSelection}>Alle Bereiche</button></div>
          <p class="hint">Notiz auf eine Uhrzeit ziehen oder über die Felder einplanen.</p>
          <div class="planning-notes" aria-label={`Offene Notizen in ${selectedArea.name}`}>{#each selectedAreaNotes as note (note.id)}<button class:chosen={selectedPlanNoteId === note.id} class:dragging={touchDrag?.noteId === note.id} class="note" type="button" draggable="true" aria-pressed={selectedPlanNoteId === note.id} ondragstart={(event) => dragStart(event, note)} onpointerdown={(event) => startTouchDrag(event, note)} onclick={(event) => selectPlanNote(note, event.currentTarget)}><strong>{note.title}</strong>{#if note.body}<small>{note.body}</small>{/if}</button>{:else}<p class="empty">In diesem Bereich sind keine offenen Notizen.</p>{/each}</div>
          {#if selectedPlanNote || selectedScheduledTodo}<div class="time-editor"><strong>{selectedPlanNote?.title ?? selectedScheduledTodo?.title}</strong><label>Startzeit<input type="time" bind:value={planTime} required></label><label>Dauer (Minuten)<input type="number" min="15" max="720" step="15" bind:value={planDuration} required></label><button class="primary" type="button" disabled={saving} onclick={() => selectedPlanNote ? placeSelectedNote() : void saveScheduledTodo()}>{saving ? 'Speichere…' : selectedPlanNote ? 'Im Tagesplan platzieren' : 'Zeitblock speichern'}</button>{#if selectedPlanNote}<button type="button" disabled={saving} onclick={() => void plan(selectedPlanNote!, planningDate, undefined, undefined, false)}>Ohne Uhrzeit</button>{/if}</div>{/if}
          <div class="untimed" role="region" data-untimed ondragover={allowDrop} ondrop={dropUntimed} aria-label="To-dos ohne Uhrzeit"><strong>Ohne Uhrzeit</strong><div>{#each scheduledTodos.filter((todo) => !todo.start_time && !todo.due_time) as todo (todo.id)}<button type="button" draggable="true" ondragstart={(event) => dragTodoStart(event, todo)} onclick={() => selectScheduledTodo(todo)}>{todo.title}</button>{:else}<span>Notiz hier ablegen</span>{/each}</div></div>
          <div class="timeline" aria-label={`Tagesplan für ${selectedArea.name} am ${planningDate}`}><div class="time-labels" aria-hidden="true">{#each timelineHours as hour}<span>{String(hour).padStart(2, '0')}:00</span>{/each}</div><div class="timeline-canvas" role="region" data-timeline ondragover={allowDrop} ondrop={dropTimeline} aria-label="Zeitleiste; Notiz oder To-do hier ablegen">{#each timelineHours as hour}<div class="timeline-hour" style={`top:${(hour - 6) * 60}px`}></div>{/each}{#if scheduledLoading}<p class="timeline-status" role="status">Tagesplan wird geladen…</p>{/if}{#each scheduledTodos.filter((todo) => todo.start_time) as todo (todo.id)}<div class:chosen={selectedScheduledTodo?.id === todo.id} class="timeline-block" style={timelineStyle(todo)}><button type="button" class="timeline-todo" draggable="true" ondragstart={(event) => dragTodoStart(event, todo)} onclick={() => selectScheduledTodo(todo)} aria-label={`${todo.title}, ${todo.start_time} bis ${todo.end_time ?? endTimeFor(todo.start_time!, 60)}`}><strong>{todo.title}</strong><span>{todo.start_time}–{todo.end_time ?? endTimeFor(todo.start_time!, 60)}</span></button><button class="resize-handle" type="button" aria-label={`Dauer von ${todo.title} anpassen`} onpointerdown={(event) => startResize(event, todo)}></button></div>{/each}</div></div>
        </section>
      {/if}
      {#if error}<p class="error" role="alert">{error}</p>{/if}{#if boardMessage}<p class="planned" role="status">{boardMessage}</p>{/if}{#if plannedNotes.length}<p class="planned">{plannedNotes.length} Notiz{plannedNotes.length === 1 ? '' : 'en'} sind im Kalender geplant.</p>{/if}
    {/if}
  </section>
{/if}

<dialog bind:this={detailDialog} class="details" aria-labelledby="note-details-title" oncancel={(event) => { event.preventDefault(); closeDetails(); }} onclose={() => { selected = null; void tick().then(() => opener?.focus()); }}>{#if selected}<form onsubmit={(event) => { event.preventDefault(); void save(); }}><header><div><p>NOTIZ</p><h2 id="note-details-title">Details</h2></div><button type="button" class="close" onclick={closeDetails} aria-label="Details schließen">×</button></header><label for="note-title">Titel<input id="note-title" bind:value={title} required></label><label for="note-body">Inhalt<textarea id="note-body" bind:value={body} rows="5"></textarea></label><label for="note-area">Bereich<select id="note-area" bind:value={areaId} onchange={() => { if (selected && areaId && areaId !== selected.space_id) void move(selected, areaId); }}><option value="">Privater Eingang</option>{#each spaces as space (space.id)}<option value={space.id}>{space.name}</option>{/each}</select></label>{#if selected.status === 'active'}<fieldset><legend>Im Kalender planen</legend><div class="plan"><label for="note-date">Datum<input id="note-date" type="date" bind:value={planDate} required></label><label for="note-time">Uhrzeit<input id="note-time" type="time" bind:value={planTime}></label></div><button type="button" class="primary" disabled={!planDate || saving} onclick={() => void plan(selected!, planDate, planTime)}>Einplanen</button></fieldset>{:else}<button type="button" onclick={() => void unschedule(selected!)}>Zurück ins Board</button>{/if}{#if error}<p class="error" role="alert">{error}</p>{/if}<footer><button type="button" onclick={closeDetails}>Abbrechen</button><button class="primary" type="submit" disabled={saving}>{saving ? 'Speichere…' : 'Speichern'}</button></footer></form>{/if}</dialog>

<style>
  .board{position:fixed;z-index:45;top:5dvh;bottom:5dvh;left:50%;transform:translateX(-50%);width:min(calc(100% - 20px),720px);overflow:auto;display:grid;gap:16px;padding:16px;border:1px solid var(--border-default);border-radius:var(--radius-modal);background:var(--surface-default);box-shadow:var(--shadow-modal)}header,.section-title{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}header p,.section-title span,.hint,.planned,.eyebrow{margin:0;color:var(--text-tertiary);font-size:12px}header p,.eyebrow{font-size:10px;font-weight:750;letter-spacing:.07em}h2,h3{margin:2px 0 0}h2{font-size:18px}h3{font-size:14px}.hint{line-height:1.45}.close,button{min-height:36px;padding:7px 10px;border:1px solid var(--border-default);border-radius:var(--radius-control);background:var(--surface-raised);color:var(--text-primary);font:inherit;cursor:pointer}.note-add{display:flex;gap:8px}.note-add input{flex:1;min-width:0;min-height:40px;padding:8px 10px;border:1px solid var(--border-default);border-radius:var(--radius-control);background:var(--surface-raised);color:var(--text-primary);font:inherit}.grid,.planning-notes{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.note{min-height:104px;display:grid;align-content:start;gap:5px;padding:12px;text-align:left;background:var(--surface-accent);cursor:grab;touch-action:none}.note.dragging{opacity:.56;transform:scale(.98);cursor:grabbing}.note.chosen,.timeline-block.chosen{border-color:var(--action-primary);box-shadow:inset 0 0 0 1px var(--action-primary)}.note strong,.note small{overflow:hidden;text-overflow:ellipsis}.note small{color:var(--text-secondary);font-size:12px;display:-webkit-box;-webkit-line-clamp:3;line-clamp:3;-webkit-box-orient:vertical}.note-action{margin-top:auto;color:var(--text-tertiary);font-size:11px}.areas{display:grid;gap:8px}.area{display:grid;gap:6px;padding:8px;border:1px dashed var(--border-strong);border-radius:var(--radius-control)}.area p{margin:0 2px 2px;color:var(--text-tertiary);font-size:11px}.area-select{display:flex;align-items:center;justify-content:space-between;width:100%;border:0;background:transparent;text-align:left}.area-select small{display:block;margin-top:3px;color:var(--text-tertiary);font-size:11px}.planning{display:grid;gap:12px}.time-editor{display:grid;grid-template-columns:minmax(0,1fr) 130px 130px auto;align-items:end;gap:8px;padding:10px;border:1px solid var(--border-subtle);border-radius:var(--radius-control);background:var(--surface-raised)}.time-editor strong{align-self:center}.timeline{display:grid;grid-template-columns:44px minmax(0,1fr);gap:8px;max-height:420px;overflow:auto;padding-right:2px}.time-labels{position:relative;height:960px}.time-labels span{position:absolute;right:0;transform:translateY(-.55em);color:var(--text-tertiary);font-size:11px}.time-labels span:nth-child(1){top:0}.time-labels span:nth-child(2){top:60px}.time-labels span:nth-child(3){top:120px}.time-labels span:nth-child(4){top:180px}.time-labels span:nth-child(5){top:240px}.time-labels span:nth-child(6){top:300px}.time-labels span:nth-child(7){top:360px}.time-labels span:nth-child(8){top:420px}.time-labels span:nth-child(9){top:480px}.time-labels span:nth-child(10){top:540px}.time-labels span:nth-child(11){top:600px}.time-labels span:nth-child(12){top:660px}.time-labels span:nth-child(13){top:720px}.time-labels span:nth-child(14){top:780px}.time-labels span:nth-child(15){top:840px}.time-labels span:nth-child(16){top:900px}.timeline-canvas{position:relative;height:960px;border:1px solid var(--border-subtle);border-radius:var(--radius-control);background:var(--surface-default)}.timeline-hour{position:absolute;right:0;left:0;border-top:1px solid var(--border-subtle)}.timeline-block{position:absolute;z-index:1;left:8px;right:8px;min-height:36px;display:grid;align-content:start;gap:2px;overflow:hidden;text-align:left;background:var(--surface-accent)}.timeline-block strong{font-size:12px}.timeline-block span{color:var(--text-secondary);font-size:11px}.timeline-status{position:absolute;top:8px;left:8px;margin:0;color:var(--text-tertiary);font-size:12px}.details{width:min(calc(100% - 24px),480px);margin:auto;padding:0;border:1px solid var(--border-default);border-radius:var(--radius-modal);background:var(--surface-default);color:var(--text-primary);box-shadow:var(--shadow-modal)}.details::backdrop{background:var(--overlay-backdrop)}form{display:grid;gap:12px;padding:16px}label{display:grid;gap:5px;color:var(--text-secondary);font-size:12px}input,textarea,select{width:100%;box-sizing:border-box;min-height:38px;padding:8px;border:1px solid var(--border-default);border-radius:var(--radius-control);background:var(--surface-raised);color:var(--text-primary);font:inherit}fieldset{display:grid;gap:8px;margin:0;padding:10px;border:1px solid var(--border-subtle);border-radius:var(--radius-control)}legend{font-size:12px}.plan{display:grid;grid-template-columns:1fr 1fr;gap:8px}footer{display:flex;justify-content:flex-end;gap:8px}.primary{background:var(--action-primary);border-color:var(--action-primary);color:var(--text-on-accent);font-weight:700}.error{margin:0;color:var(--status-danger);font-size:12px}button:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible{outline:2px solid var(--status-info);outline-offset:2px}@media(max-width:620px){.board{top:5dvh;bottom:5dvh;padding:12px}.grid,.planning-notes{grid-template-columns:repeat(2,minmax(0,1fr))}.note{min-height:92px}.time-editor{grid-template-columns:1fr 1fr}.time-editor strong,.time-editor button{grid-column:1/-1}.plan{grid-template-columns:1fr}.details{width:100%;margin:auto 0 0;border-radius:var(--radius-modal) var(--radius-modal) 0 0}}
  /* The board is a compact spatial index: every section keeps four equal cards in view. */
  .grid,.planning-notes{grid-template-columns:repeat(4,minmax(0,1fr))}
  .note{aspect-ratio:1;min-height:0;padding:8px;gap:4px}
  .area-notes{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
  .area-notes .note{min-width:0}
  .untimed{display:grid;gap:6px;padding:8px;border:1px dashed var(--border-strong);border-radius:var(--radius-control)}
  .untimed>strong{font-size:12px}.untimed>div{display:flex;flex-wrap:wrap;gap:6px}.untimed button{min-height:32px;padding:5px 8px;font-size:12px}.untimed span{color:var(--text-tertiary);font-size:12px;line-height:32px}
  .timeline-canvas{min-height:960px}.timeline-block{padding:0}.timeline-todo{width:100%;height:100%;min-height:36px;display:grid;align-content:start;gap:2px;padding:7px 10px 14px;border:0;border-radius:inherit;background:transparent;color:inherit;text-align:left}.resize-handle{position:absolute;right:20px;bottom:4px;left:20px;min-height:3px;height:3px;padding:0;border:0;border-radius:99px;background:var(--border-strong);cursor:ns-resize;touch-action:none}
  @media(max-width:620px){.grid,.planning-notes{grid-template-columns:repeat(4,minmax(0,1fr))}.note{min-height:0}}
  .board.inline{position:static;z-index:auto;top:auto;right:auto;bottom:auto;left:auto;width:auto;min-height:0;transform:none;overflow:visible;padding:0;border:0;border-radius:0;background:transparent;box-shadow:none}
</style>
