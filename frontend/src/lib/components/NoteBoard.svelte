<script lang="ts">
  import { createEventDispatcher, tick } from 'svelte';
  import type { Note, Space } from '$lib/types';
  import { api } from '$lib/api';

  export let open = false;
  export let notes: Note[] = [];
  export let spaces: Space[] = [];
  export let loading = false;
  const dispatch = createEventDispatcher<{ close: void; changed: void }>();

  let selected: Note | null = null;
  let title = '';
  let body = '';
  let areaId = '';
  let planDate = '';
  let planTime = '';
  let draggedId = '';
  let saving = false;
  let error = '';
  let boardMessage = '';
  let opener: HTMLElement | null = null;
  let detailDialog: HTMLDialogElement;
  let touchCandidate: { noteId: string; pointerId: number } | null = null;
  let touchDrag: { noteId: string; pointerId: number } | null = null;
  let touchDragTimer: ReturnType<typeof setTimeout> | null = null;
  let suppressDetailId = '';

  $: privateNotes = notes.filter((note) => !note.space_id && note.status === 'active');
  $: plannedNotes = notes.filter((note) => note.status === 'planned');
  $: days = Array.from({ length: 7 }, (_, index) => { const value = new Date(); value.setHours(0, 0, 0, 0); value.setDate(value.getDate() + index); return value; });

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
    dispatch('changed'); closeDetails();
  }
  async function move(note: Note, spaceId: string) {
    if (!spaceId || saving || note.space_id === spaceId) return;
    if (!window.confirm(`Die Notiz wird für alle Mitglieder von ${spaces.find((space) => space.id === spaceId)?.name ?? 'diesem Bereich'} sichtbar.`)) return;
    saving = true;
    const result = await api.moveNote(note.id, spaceId, true);
    saving = false;
    if (!result) { error = 'Bereich konnte nicht zugeordnet werden.'; return; }
    dispatch('changed');
  }
  async function plan(note: Note, dueDate: string, startTime?: string) {
    if (!dueDate || saving) return;
    saving = true;
    const result = await api.planNote(note.id, dueDate, startTime || null);
    saving = false;
    if (!result) { error = 'Notiz konnte nicht geplant werden.'; return; }
    dispatch('changed'); closeDetails();
  }
  async function unschedule(note: Note) {
    if (saving) return;
    saving = true;
    const result = await api.unscheduleNote(note.id);
    saving = false;
    if (!result) { error = 'Planung konnte nicht aufgehoben werden.'; return; }
    dispatch('changed'); closeDetails();
  }
  function dragStart(event: DragEvent, note: Note) { draggedId = note.id; event.dataTransfer?.setData('text/plain', note.id); if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'; }
  function droppedNote(event: DragEvent) { return event.dataTransfer?.getData('text/plain') || draggedId; }
  function allowDrop(event: DragEvent) { event.preventDefault(); if (event.dataTransfer) event.dataTransfer.dropEffect = 'move'; }
  async function dropArea(event: DragEvent, spaceId: string) { const id = droppedNote(event); const note = notes.find((item) => item.id === id); if (note) await move(note, spaceId); draggedId = ''; }
  async function dropSlot(event: DragEvent, dueDate: string, time?: string) { const id = droppedNote(event); const note = notes.find((item) => item.id === id); if (note) await plan(note, dueDate, time); draggedId = ''; }
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
    const target = document.elementFromPoint(event.clientX, event.clientY)?.closest<HTMLElement>('[data-area-id],[data-slot-date]');
    touchDrag = null;
    if (!note || !target) { boardMessage = 'Keine Ablage gewählt. Die Notiz bleibt im Eingang.'; return; }
    suppressDetailId = note.id;
    setTimeout(() => suppressDetailId = '', 0);
    if (target.dataset.areaId) await move(note, target.dataset.areaId);
    else if (target.dataset.slotDate) await plan(note, target.dataset.slotDate, target.dataset.slotTime);
  }
  function openCard(note: Note, element: HTMLElement) { if (suppressDetailId === note.id) return; openDetails(note, element); }
  function closeBoard() { dispatch('close'); }
</script>

<svelte:window onpointerup={finishTouchDrag} onpointercancel={finishTouchDrag} />

{#if open}
  <section id="note-board" class="board" aria-label="Notiz-Board">
    <header><div><p>NOTIZ-BOARD</p><h2>Privater Eingang</h2></div><button type="button" class="close" onclick={closeBoard}>Schließen</button></header>
    <p class="hint">Neue Notizen sind nur für dich sichtbar. Ziehe sie in einen Bereich, um sie bewusst zu teilen, oder lege sie im Kalender ab.</p>
    {#if loading}<p class="status" role="status">Notizen werden geladen…</p>
    {:else}<section aria-labelledby="inbox-title"><div class="section-title"><h3 id="inbox-title">Eingang</h3><span>{privateNotes.length} privat</span></div><div class="grid">{#each privateNotes.slice(0, 9) as note (note.id)}<button class:dragging={touchDrag?.noteId === note.id} class="note" type="button" draggable="true" ondragstart={(event) => dragStart(event, note)} onpointerdown={(event) => startTouchDrag(event, note)} onclick={(event) => openCard(note, event.currentTarget)}><strong>{note.title}</strong>{#if note.body}<small>{note.body}</small>{/if}</button>{:else}<p class="empty">Noch keine privaten Notizen.</p>{/each}</div></section>
    <section aria-labelledby="areas-title"><div class="section-title"><h3 id="areas-title">Bereiche</h3><span>Ablage und Zugriff</span></div><div class="areas">{#each spaces as space (space.id)}<div class="area" data-area-id={space.id} role="group" aria-label={`Bereich ${space.name}; Notiz hier ablegen`} ondragover={allowDrop} ondrop={(event) => dropArea(event, space.id)}><div><strong>{space.name}</strong><small>{space.members.length} Mitglieder</small></div><div class="area-notes">{#each notes.filter((note) => note.space_id === space.id && note.status === 'active') as note (note.id)}<button class:dragging={touchDrag?.noteId === note.id} class="note compact" type="button" draggable="true" ondragstart={(event) => dragStart(event, note)} onpointerdown={(event) => startTouchDrag(event, note)} onclick={(event) => openCard(note, event.currentTarget)}>{note.title}</button>{:else}<span>Notiz hier ablegen oder eine Kachel öffnen und den Bereich wählen.</span>{/each}</div></div>{:else}<p class="empty">Lege unter Einstellungen einen Bereich an, um Notizen zu teilen.</p>{/each}</div></section>
    <section aria-labelledby="calendar-title"><div class="section-title"><h3 id="calendar-title">Planen</h3><span>Tag oder Uhrzeit ablegen</span></div><div class="calendar">{#each days as day (dateValue(day))}<div class="day"><strong>{dateLabel(day)}</strong><button data-slot-date={dateValue(day)} type="button" class="all-day" ondragover={allowDrop} ondrop={(event) => dropSlot(event, dateValue(day))} onclick={() => boardMessage = 'Für Tastatur und Touch: Öffne eine Kachel und wähle dort Datum und Uhrzeit.'}>Ganztägig</button>{#each ['09:00', '13:00', '17:00'] as time}<button data-slot-date={dateValue(day)} data-slot-time={time} type="button" class="slot" ondragover={allowDrop} ondrop={(event) => dropSlot(event, dateValue(day), time)} onclick={() => boardMessage = 'Für Tastatur und Touch: Öffne eine Kachel und wähle dort Datum und Uhrzeit.'}>{time}</button>{/each}</div>{/each}</div></section>
    {#if boardMessage}<p class="planned" role="status">{boardMessage}</p>{/if}{#if plannedNotes.length}<p class="planned">{plannedNotes.length} Notiz{plannedNotes.length === 1 ? '' : 'en'} sind im Kalender geplant.</p>{/if}{/if}
  </section>
{/if}

<dialog bind:this={detailDialog} class="details" aria-labelledby="note-details-title" oncancel={(event) => { event.preventDefault(); closeDetails(); }} onclose={() => { selected = null; void tick().then(() => opener?.focus()); }}>{#if selected}<form onsubmit={(event) => { event.preventDefault(); void save(); }}><header><div><p>NOTIZ</p><h2 id="note-details-title">Details</h2></div><button type="button" class="close" onclick={closeDetails} aria-label="Details schließen">×</button></header><label for="note-title">Titel<input id="note-title" bind:value={title} required></label><label for="note-body">Inhalt<textarea id="note-body" bind:value={body} rows="5"></textarea></label><label for="note-area">Bereich<select id="note-area" bind:value={areaId} onchange={() => { if (selected && areaId && areaId !== selected.space_id) void move(selected, areaId); }}><option value="">Privater Eingang</option>{#each spaces as space (space.id)}<option value={space.id}>{space.name}</option>{/each}</select></label>{#if selected.status === 'active'}<fieldset><legend>Im Kalender planen</legend><div class="plan"><label for="note-date">Datum<input id="note-date" type="date" bind:value={planDate} required></label><label for="note-time">Uhrzeit<input id="note-time" type="time" bind:value={planTime}></label></div><button type="button" class="primary" disabled={!planDate || saving} onclick={() => void plan(selected!, planDate, planTime)}>Einplanen</button></fieldset>{:else}<button type="button" onclick={() => void unschedule(selected!)}>Zurück ins Board</button>{/if}{#if error}<p class="error" role="alert">{error}</p>{/if}<footer><button type="button" onclick={closeDetails}>Abbrechen</button><button class="primary" type="submit" disabled={saving}>{saving ? 'Speichere…' : 'Speichern'}</button></footer></form>{/if}</dialog>

<style>
  .board{position:fixed;z-index:45;left:50%;bottom:78px;transform:translateX(-50%);width:min(calc(100% - 20px),680px);max-height:calc(100dvh - 98px);overflow:auto;display:grid;gap:16px;padding:16px;border:1px solid var(--border-default);border-radius:var(--radius-modal);background:var(--surface-default);box-shadow:var(--shadow-modal)}header,.section-title{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}header p,.section-title span,.hint,.planned{margin:0;color:var(--text-tertiary);font-size:12px}header p{font-size:10px;font-weight:750;letter-spacing:.07em}h2,h3{margin:2px 0 0}h2{font-size:18px}h3{font-size:14px}.hint{line-height:1.45}.close,button{min-height:36px;padding:7px 10px;border:1px solid var(--border-default);border-radius:var(--radius-control);background:var(--surface-raised);color:var(--text-primary);font:inherit;cursor:pointer}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.note{min-height:90px;display:grid;align-content:start;gap:5px;padding:10px;text-align:left;background:var(--surface-accent);cursor:grab;touch-action:none}.note.dragging{opacity:.56;transform:scale(.98);cursor:grabbing}.note strong,.note small{overflow:hidden;text-overflow:ellipsis}.note small{color:var(--text-secondary);font-size:12px;display:-webkit-box;-webkit-line-clamp:3;line-clamp:3;-webkit-box-orient:vertical}.areas{display:grid;gap:8px}.area{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;padding:10px;border:1px dashed var(--border-strong);border-radius:var(--radius-control)}.area small{display:block;color:var(--text-tertiary);font-size:11px}.area-notes{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:5px}.note.compact{min-height:34px;padding:6px 8px;font-size:12px}.area-notes span,.empty{color:var(--text-tertiary);font-size:12px}.calendar{display:grid;grid-template-columns:repeat(7,minmax(104px,1fr));gap:6px;overflow:auto}.day{display:grid;gap:5px;min-width:104px}.day strong{font-size:11px}.all-day,.slot{font-size:11px;text-align:left}.all-day{background:var(--surface-accent)}.slot{border-style:dashed}.details{width:min(calc(100% - 24px),480px);margin:auto;padding:0;border:1px solid var(--border-default);border-radius:var(--radius-modal);background:var(--surface-default);color:var(--text-primary);box-shadow:var(--shadow-modal)}.details::backdrop{background:var(--overlay-backdrop)}form{display:grid;gap:12px;padding:16px}label{display:grid;gap:5px;color:var(--text-secondary);font-size:12px}input,textarea,select{width:100%;box-sizing:border-box;min-height:38px;padding:8px;border:1px solid var(--border-default);border-radius:var(--radius-control);background:var(--surface-raised);color:var(--text-primary);font:inherit}fieldset{display:grid;gap:8px;margin:0;padding:10px;border:1px solid var(--border-subtle);border-radius:var(--radius-control)}legend{font-size:12px}.plan{display:grid;grid-template-columns:1fr 1fr;gap:8px}footer{display:flex;justify-content:flex-end;gap:8px}.primary{background:var(--action-primary);border-color:var(--action-primary);color:var(--text-on-accent);font-weight:700}.error{margin:0;color:var(--status-danger);font-size:12px}button:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible{outline:2px solid var(--status-info);outline-offset:2px}@media(max-width:520px){.board{bottom:70px;padding:12px}.grid{grid-template-columns:repeat(3,minmax(84px,1fr))}.note{min-height:78px}.plan{grid-template-columns:1fr}.details{width:100%;margin:auto 0 0;border-radius:var(--radius-modal) var(--radius-modal) 0 0}}
</style>
