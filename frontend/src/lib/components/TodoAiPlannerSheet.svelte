<script lang="ts">
  import { createEventDispatcher, tick } from 'svelte';
  import { api } from '$lib/api';
  import type { PlaceSuggestion, TodoDraft } from '$lib/types';

  export let open = false;
  export let date: string;
  const dispatch = createEventDispatcher<{ close: void; todoadd: any }>();

  let dialog: HTMLDialogElement;
  let prompt = '';
  let draft: TodoDraft | null = null;
  let places: PlaceSuggestion[] = [];
  let selectedPlace: PlaceSuggestion | null = null;
  let loading = false;
  let placeLoading = false;
  let error = '';
  let closeTrigger: HTMLElement | null = null;

  $: if (open && dialog && !dialog.open) {
    closeTrigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialog.showModal();
    void tick().then(() => dialog.querySelector<HTMLTextAreaElement>('textarea')?.focus());
  }
  $: if (!open && dialog?.open) dialog.close();

  function close() {
    draft = null; places = []; selectedPlace = null; error = ''; prompt = '';
    dispatch('close');
  }

  async function createDraft() {
    if (!prompt.trim() || loading) return;
    loading = true; error = '';
    try {
      draft = await api.draftTodo(prompt.trim(), date);
      if (!draft) throw new Error();
      if (draft.place_query) await findPlaces(draft.place_query);
    } catch {
      error = 'Der Entwurf konnte nicht erstellt werden. Bitte versuche es erneut.';
    } finally { loading = false; }
  }

  async function findPlaces(query: string) {
    if (query.trim().length < 2) { places = []; return; }
    placeLoading = true;
    try { places = await api.searchTodoPlaces(query.trim()); }
    catch { places = []; error = 'Die Ortssuche ist gerade nicht verfügbar. Du kannst das To-do trotzdem ohne Ort anlegen.'; }
    finally { placeLoading = false; }
  }

  async function createTodo() {
    if (!draft || loading) return;
    loading = true; error = '';
    try {
      const canMonitor = Boolean(selectedPlace && draft.start_time && draft.travel_mode);
      const todo = await api.createTodo({
        title: draft.title, due_date: draft.due_date, start_time: draft.start_time || null,
        is_all_day: !draft.start_time, status: 'open', priority: 2, source: 'manual',
        place_id: selectedPlace?.place_id ?? null, place_name: selectedPlace?.name ?? null,
        place_address: selectedPlace?.address ?? null, travel_mode: draft.travel_mode ?? null,
        travel_buffer_minutes: 10, travel_monitoring_enabled: canMonitor,
      });
      if (!todo) throw new Error();
      dispatch('todoadd', todo); close();
    } catch { error = 'Das To-do konnte nicht angelegt werden.'; }
    finally { loading = false; }
  }
</script>

<dialog bind:this={dialog} class="planner" aria-labelledby="ai-planner-title" oncancel={(event) => { event.preventDefault(); close(); }} onclose={() => closeTrigger?.focus()}>
  <form method="dialog" onsubmit={(event) => event.preventDefault()}>
    <header><div><p>TO-DO</p><h2 id="ai-planner-title">Mit KI planen</h2></div><button type="button" class="close" aria-label="KI-Planung schließen" onclick={close}>×</button></header>
    {#if !draft}
      <label>Was möchtest du erledigen?
        <textarea bind:value={prompt} placeholder="z. B. Donnerstag 17:30 Physiotherapie Müller in Neukölln, mit dem Auto"></textarea>
      </label>
      <p class="hint">Die KI erstellt einen Entwurf. Erst nach deiner Prüfung wird etwas angelegt.</p>
      <div class="actions"><button type="button" class="secondary" onclick={close}>Abbrechen</button><button type="button" class="primary" disabled={!prompt.trim() || loading} onclick={createDraft}>{loading ? 'Erstelle…' : 'Entwurf erstellen'}</button></div>
    {:else}
      <section class="draft" aria-live="polite"><p>VORSCHLAG · BITTE PRÜFEN</p><label>Titel<input bind:value={draft.title}></label><div class="two"><label>Datum<input type="date" bind:value={draft.due_date}></label><label>Beginn<input type="time" bind:value={draft.start_time}></label></div>
        <label>Anreiseart<select bind:value={draft.travel_mode}><option value={undefined}>Keine Anreise</option><option value="drive">Auto</option><option value="bicycle">Fahrrad</option><option value="walk">Zu Fuß</option><option value="transit">ÖPNV</option></select></label>
        <label>Ort suchen<input value={draft.place_query ?? ''} oninput={(event) => findPlaces(event.currentTarget.value)} placeholder="Ort oder Adresse"></label>
        {#if placeLoading}<p class="hint">Suche Orte…</p>{/if}
        {#if places.length}<div class="places" role="listbox" aria-label="Ortsvorschläge">{#each places as place (place.place_id)}<button type="button" class:selected={selectedPlace?.place_id === place.place_id} onclick={() => selectedPlace = place}><strong>{place.name}</strong>{#if place.address}<small>{place.address}</small>{/if}</button>{/each}</div>{/if}
        {#if selectedPlace}<p class="confirmed">Ort bestätigt: {selectedPlace.name}</p>{/if}
        {#if draft.needs_review.length}<p class="hint">Noch prüfen: {draft.needs_review.join(' · ')}</p>{/if}
      </section>
      <div class="actions"><button type="button" class="secondary" onclick={() => draft = null}>Zurück</button><button type="button" class="primary" disabled={loading} onclick={createTodo}>{loading ? 'Lege an…' : 'Anlegen'}</button></div>
    {/if}
    {#if error}<p class="error" role="alert">{error}</p>{/if}
  </form>
</dialog>

<style>
  .planner { width:min(calc(100% - 24px),500px); max-height:min(86dvh,640px); margin:auto; padding:0; border:1px solid var(--border-default); border-radius:var(--radius-modal); background:var(--surface-default); color:var(--text-primary); box-shadow:var(--shadow-modal); }
  .planner::backdrop { background:var(--overlay-backdrop); } form { display:grid; gap:var(--space-3); padding:var(--space-4); } header { display:flex; align-items:flex-start; justify-content:space-between; gap:var(--space-3); } header p,.draft > p { margin:0 0 3px; color:var(--text-tertiary); font-size:11px; font-weight:700; letter-spacing:.05em; } h2 { margin:0; font-size:18px; } label { display:grid; gap:5px; color:var(--text-secondary); font-size:12px; } input,textarea,select { width:100%; min-height:var(--control-min); padding:8px 10px; border:1px solid var(--border-default); border-radius:var(--radius-control); background:var(--surface-raised); color:var(--text-primary); font:inherit; } textarea { min-height:88px; resize:vertical; } .close { display:grid; place-items:center; width:38px; min-height:38px; border:1px solid var(--border-default); border-radius:var(--radius-control); background:var(--surface-raised); color:var(--text-primary); font-size:22px; cursor:pointer; } .two { display:grid; grid-template-columns:1fr 1fr; gap:var(--space-2); } .draft { display:grid; gap:var(--space-2); padding:var(--space-3); border:1px solid var(--border-subtle); border-radius:var(--radius-control); background:var(--surface-raised); } .places { display:grid; gap:4px; max-height:180px; overflow:auto; } .places button { display:grid; gap:2px; width:100%; min-height:48px; padding:8px 10px; border:1px solid transparent; border-radius:var(--radius-control); background:var(--surface-default); color:var(--text-primary); text-align:left; cursor:pointer; } .places button.selected { border-color:var(--action-primary); background:var(--surface-accent); } .places small { color:var(--text-tertiary); font-size:11px; } .hint,.confirmed,.error { margin:0; font-size:12px; line-height:1.45; } .hint { color:var(--text-tertiary); } .confirmed { color:var(--status-success); } .error { color:var(--status-danger); } .actions { display:flex; justify-content:flex-end; gap:var(--space-2); } .actions button { min-height:var(--control-min); padding:8px 13px; border-radius:var(--radius-control); cursor:pointer; font:inherit; } .primary { border:0; background:var(--action-primary); color:var(--text-on-accent); font-weight:700; } .secondary { border:1px solid var(--border-default); background:var(--surface-raised); color:var(--text-secondary); } button:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible { outline:2px solid var(--status-info); outline-offset:2px; } @media(max-width:420px) { .planner { width:100%; max-height:100dvh; margin:auto 0 0; border-radius:var(--radius-modal) var(--radius-modal) 0 0; } .two { grid-template-columns:1fr; } }
</style>
