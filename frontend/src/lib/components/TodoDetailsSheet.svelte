<script lang="ts">
  import { createEventDispatcher, tick } from 'svelte';
  import { api } from '$lib/api';
  import type { PlaceSuggestion, Space, Todo } from '$lib/types';

  export let todo: Todo | null = null;
  export let suggestedPlaceQuery = '';
  export let suggestedTravelMode: Todo['travel_mode'] = null;
  export let spaces: Space[] = [];
  const dispatch = createEventDispatcher<{ close: void; updated: Todo }>();
  let dialog: HTMLDialogElement;
  let title = '';
  let category = '';
  let priority = 2;
  let dueDate = '';
  let dueTime = '';
  let travelMode: Todo['travel_mode'] = null;
  let travelMonitoring = false;
  let spaceId = '';
  let assigneeId = '';
  let selectedSpace: Space | null = null;
  let placeQuery = '';
  let places: PlaceSuggestion[] = [];
  let selectedPlace: PlaceSuggestion | null = null;
  let placeLoading = false;
  let placeError = '';
  let saving = false;
  let error = '';
  let opener: HTMLElement | null = null;

  $: if (todo && dialog && !dialog.open) {
    opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    title = todo.title; category = todo.category ?? ''; priority = todo.priority ?? 2;
    dueDate = todo.due_date ?? ''; dueTime = todo.start_time ?? todo.due_time ?? '';
    travelMode = todo.travel_mode ?? suggestedTravelMode;
    travelMonitoring = Boolean(todo.travel_monitoring_enabled);
    spaceId = todo.space_id ?? ''; assigneeId = todo.assignee_id ?? '';
    placeQuery = todo.place_name ?? suggestedPlaceQuery;
    selectedPlace = todo.place_id && todo.place_name ? { place_id: todo.place_id, name: todo.place_name, address: todo.place_address ?? null } : null;
    places = []; placeError = '';
    error = ''; dialog.showModal();
    void tick().then(() => dialog.querySelector<HTMLInputElement>('#todo-detail-title')?.focus());
    if (!selectedPlace && placeQuery.trim().length >= 2) void findPlaces();
  }
  $: if (!todo && dialog?.open) dialog.close();

  function close() { dispatch('close'); }
  async function findPlaces() {
    if (placeQuery.trim().length < 2 || placeLoading) return;
    placeLoading = true; placeError = '';
    try { places = await api.searchTodoPlaces(placeQuery.trim()); }
    catch { places = []; placeError = 'Die Ortssuche ist gerade nicht verfügbar. Du kannst die Details später ergänzen.'; }
    finally { placeLoading = false; }
  }
  function changeSpace() {
    assigneeId = '';
    if (spaceId) { travelMonitoring = false; travelMode = null; }
  }
  $: selectedSpace = spaces.find((space) => space.id === spaceId) ?? null;
  async function save() {
    if (!todo?.id || !title.trim() || saving) return;
    saving = true; error = '';
    const canMonitorTravel = Boolean(selectedPlace && dueDate && dueTime && travelMode);
    const updated = await api.updateTodo(todo.id, {
      title: title.trim(), category: category.trim() || null, priority: Number(priority),
      due_date: dueDate || null, due_time: dueTime || null, start_time: dueTime || null,
      is_all_day: !dueTime, space_id: spaceId || null, project_id: null, assignee_id: assigneeId || null,
      travel_mode: spaceId ? null : travelMode,
      place_id: selectedPlace?.place_id ?? todo.place_id ?? null,
      place_name: selectedPlace?.name ?? todo.place_name ?? null,
      place_address: selectedPlace?.address ?? todo.place_address ?? null,
      travel_monitoring_enabled: !spaceId && canMonitorTravel && travelMonitoring,
    });
    saving = false;
    if (!updated) { error = 'Die Angaben konnten nicht gespeichert werden. Bitte versuche es erneut.'; return; }
    dispatch('updated', updated); close();
  }
</script>

<dialog bind:this={dialog} class="todo-details" aria-labelledby="todo-details-title" oncancel={(event) => { event.preventDefault(); close(); }} onclose={() => opener?.focus()}>
  <form onsubmit={(event) => { event.preventDefault(); save(); }}>
    <header><div><p>TO-DO</p><h2 id="todo-details-title">Details ergänzen</h2></div><button type="button" class="close" aria-label="Details schließen" onclick={close}>×</button></header>
    <p class="hint">Dein To-do ist angelegt. Ergänze bei Bedarf die Planung.</p>
    <label for="todo-detail-title">Titel<input id="todo-detail-title" bind:value={title} required></label>
    <div class="two"><label for="todo-detail-date">Datum<input id="todo-detail-date" type="date" bind:value={dueDate}></label><label for="todo-detail-time">Uhrzeit<input id="todo-detail-time" type="time" bind:value={dueTime}></label></div>
    <div class="two"><label for="todo-detail-category">Kategorie<input id="todo-detail-category" bind:value={category} placeholder="z. B. Haushalt"></label><label for="todo-detail-priority">Priorität<select id="todo-detail-priority" bind:value={priority}><option value={1}>Niedrig</option><option value={2}>Mittel</option><option value={3}>Hoch</option></select></label></div>
    <fieldset><legend>Gemeinsamer Space</legend><label for="todo-detail-space">Space<select id="todo-detail-space" bind:value={spaceId} onchange={changeSpace}><option value="">Privat</option>{#each spaces as space (space.id)}<option value={space.id}>{space.name}</option>{/each}</select></label>
      {#if selectedSpace}<label for="todo-detail-assignee">Zugewiesen an<select id="todo-detail-assignee" bind:value={assigneeId}><option value="">Nicht zugewiesen</option>{#each selectedSpace.members as member (member.member_id)}<option value={member.member_id}>{member.display_name ?? 'Mitglied'}</option>{/each}</select></label><p class="hint">Alle Mitglieder dieses Bereichs können die Aufgabe bearbeiten und erledigen.</p>{/if}
    </fieldset>
    {#if !spaceId}<fieldset><legend>Ort und Anreise</legend><div class="place-search"><label for="todo-detail-place">Ort suchen<input id="todo-detail-place" bind:value={placeQuery} placeholder="Ort oder Adresse"></label><button type="button" class="search" disabled={placeQuery.trim().length < 2 || placeLoading} onclick={findPlaces}>{placeLoading ? 'Suche…' : 'Suchen'}</button></div>
      {#if places.length}<ul class="places" aria-label="Ortsvorschläge">{#each places as place (place.place_id)}<li><button type="button" class:selected={selectedPlace?.place_id === place.place_id} aria-pressed={selectedPlace?.place_id === place.place_id} onclick={() => selectedPlace = place}><strong>{place.name}</strong>{#if place.address}<small>{place.address}</small>{/if}</button></li>{/each}</ul>{/if}
      {#if selectedPlace}<p class="confirmed">Ort bestätigt: {selectedPlace.name}</p>{/if}
      {#if placeError}<p class="error" role="status">{placeError}</p>{/if}
      <label for="todo-detail-travel">Anreiseart<select id="todo-detail-travel" bind:value={travelMode}><option value={undefined}>Keine Anreise</option><option value="drive">Auto</option><option value="bicycle">Fahrrad</option><option value="walk">Zu Fuß</option><option value="transit">ÖPNV</option></select></label>
      {#if selectedPlace && dueDate && dueTime && travelMode}
        <label class="monitor"><input type="checkbox" bind:checked={travelMonitoring}> Anreise in der geöffneten App alle fünf Minuten aktualisieren</label>
      {:else if travelMonitoring}
        <p class="hint">Für die Anreiseüberwachung fehlen noch ein bestätigter Ort, Datum, Uhrzeit oder Anreiseart.</p>
      {/if}
    </fieldset>{/if}
    {#if error}<p class="error" role="alert">{error}</p>{/if}
    <div class="actions"><button type="button" class="secondary" onclick={close}>Später</button><button class="primary" disabled={!title.trim() || saving}>{saving ? 'Speichere…' : 'Speichern'}</button></div>
  </form>
</dialog>

<style>
  .todo-details { width:min(calc(100% - 24px),480px); max-height:min(86dvh,620px); margin:auto; padding:0; border:1px solid var(--border-default); border-radius:var(--radius-modal); background:var(--surface-default); color:var(--text-primary); box-shadow:var(--shadow-modal); }
  .todo-details::backdrop { background:var(--overlay-backdrop); } form { display:grid; gap:var(--space-3); padding:var(--space-4); } header { display:flex; align-items:flex-start; justify-content:space-between; gap:var(--space-3); } header p { margin:0 0 3px; color:var(--text-tertiary); font-size:11px; font-weight:700; letter-spacing:.05em; } h2 { margin:0; font-size:18px; } label { display:grid; gap:5px; color:var(--text-secondary); font-size:12px; } input,select { width:100%; min-height:var(--control-min); padding:8px 10px; border:1px solid var(--border-default); border-radius:var(--radius-control); background:var(--surface-raised); color:var(--text-primary); font:inherit; } fieldset { display:grid; gap:var(--space-2); margin:0; padding:var(--space-3); border:1px solid var(--border-subtle); border-radius:var(--radius-control); } legend { padding:0 4px; color:var(--text-secondary); font-size:12px; } .two,.place-search { display:grid; grid-template-columns:1fr 1fr; gap:var(--space-2); } .place-search { grid-template-columns:minmax(0,1fr) auto; align-items:end; } .search { min-height:var(--control-min); padding:8px 10px; border:1px solid var(--border-default); border-radius:var(--radius-control); background:var(--surface-raised); color:var(--text-secondary); cursor:pointer; } .places { display:grid; gap:4px; max-height:150px; margin:0; padding:0; overflow:auto; list-style:none; } .places button { display:grid; gap:2px; width:100%; min-height:48px; padding:8px 10px; border:1px solid transparent; border-radius:var(--radius-control); background:var(--surface-default); color:var(--text-primary); text-align:left; cursor:pointer; } .places button.selected { border-color:var(--action-primary); background:var(--surface-accent); } .places small { color:var(--text-tertiary); font-size:11px; } .hint,.error,.confirmed { margin:0; font-size:12px; line-height:1.45; } .hint { color:var(--text-tertiary); } .error { color:var(--status-danger); } .confirmed { color:var(--status-success); } .close { display:grid; place-items:center; width:38px; min-height:38px; border:1px solid var(--border-default); border-radius:var(--radius-control); background:var(--surface-raised); color:var(--text-primary); font-size:22px; cursor:pointer; } .actions { display:flex; justify-content:flex-end; gap:var(--space-2); } .actions button { min-height:var(--control-min); padding:8px 13px; border-radius:var(--radius-control); cursor:pointer; font:inherit; } .primary { border:0; background:var(--action-primary); color:var(--text-on-accent); font-weight:700; } .secondary { border:1px solid var(--border-default); background:var(--surface-raised); color:var(--text-secondary); } button:focus-visible,input:focus-visible,select:focus-visible { outline:2px solid var(--status-info); outline-offset:2px; } @media(max-width:420px) { .todo-details { width:100%; max-height:100dvh; margin:auto 0 0; border-radius:var(--radius-modal) var(--radius-modal) 0 0; } .two,.place-search { grid-template-columns:1fr; } }
  .monitor { grid-template-columns:auto 1fr; align-items:center; gap:8px; color:var(--text-secondary); }
  .monitor input { width:18px; min-height:18px; accent-color:var(--action-primary); }
</style>
