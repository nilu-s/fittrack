<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { isNative, nativeBridge, registerNativePush } from '$lib/native';
  import { currentPosition, refreshTravel, travelRequest, travelStates, travelTime } from '$lib/travel';
  import type { Todo, PlaceSuggestion } from '$lib/types';
  import TravelStatus from './TravelStatus.svelte';
  export let todo: Todo;
  export let now = Date.now();
  let busy = false;
  let error = '';
  let message = '';
  let lead = 60;
  let originMode = 'current';
  let query = '';
  let places: PlaceSuggestion[] = [];
  let selected: PlaceSuggestion | null = null;
  onMount(() => {
    const failed = () => error = 'Push konnte nicht eingerichtet werden. Die Verkehrsprüfung läuft weiter; prüfe die Anreise in der App.';
    const ready = () => { void refreshTravel(); };
    window.addEventListener('native-push-error', failed);
    window.addEventListener('native-push-ready', ready);
    return () => { window.removeEventListener('native-push-error', failed); window.removeEventListener('native-push-ready', ready); };
  });
  $: state = todo.id ? $travelStates[todo.id] : undefined;
  $: canStart = Boolean(state?.active && state.starts_at && Date.parse(state.starts_at) <= now && Date.parse(state.expires_at) > now);

  async function perform(action: () => Promise<void>) {
    if (busy) return;
    busy = true; error = ''; message = '';
    try { await action(); await refreshTravel(); }
    catch (err) { error = err instanceof Error ? err.message : 'Anreise konnte nicht aktualisiert werden.'; }
    finally { busy = false; }
  }
  async function setup() {
    await perform(async () => {
      // Provider setup/notification permission must never prevent fixed-origin
      // traffic monitoring. Push can be enabled separately after confirmation.
      const origin = originMode === 'place' ? { origin_place_id: selected?.place_id } : await currentPosition();
      await travelRequest(`/${todo.id}`, 'PUT', { ...origin, lead_minutes: Number(lead), timezone: 'Europe/Berlin' });
      message = 'Überwachung eingerichtet. Die erste Prognose wird berechnet.';
    });
  }
  async function start() {
    await perform(async () => {
      const previous = await nativeBridge.locationState();
      if (previous.active && previous.todoId !== todo.id) {
        await travelRequest(`/${previous.todoId}/pause`, 'POST');
        await nativeBridge.stopLocation();
      }
      const current = await travelRequest(`/${todo.id}/start`, 'POST');
      try { await nativeBridge.startLocation({ todoId: todo.id!, expiresAt: current.expires_at }); }
      catch (err) { await travelRequest(`/${todo.id}/pause`, 'POST'); throw err; }
      message = 'Begleitung gestartet. Sie endet automatisch nach der Anreisezeit.';
    });
  }
  async function pause(remove = false) {
    await perform(async () => {
      if (isNative()) {
        const local = await nativeBridge.locationState();
        if (local.todoId === todo.id) await nativeBridge.stopLocation();
      }
      await travelRequest(`/${todo.id}${remove ? '' : '/pause'}`, remove ? 'DELETE' : 'POST');
    });
  }
  async function findPlaces() {
    await perform(async () => { places = await api.searchTodoPlaces(query); if (!places.length) message = 'Keine Orte gefunden. Suche bitte genauer.'; });
  }
</script>

{#if !todo.space_id && todo.status === 'open'}
<section class="companion ui-dialog__section" aria-label="Anreisebegleitung">
  <h3>Anreisebegleitung</h3>
  {#if state?.active}
    <TravelStatus {state} {now} buffer={todo.travel_buffer_minutes ?? 10} />
    <p>{state.lead_minutes} Min. Vorlauf{#if state.starts_at} · ab {travelTime(state.starts_at, state.timezone)}{/if}</p>
    <p>{state.push_available ? 'Benachrichtigungen für dieses Begleitgerät eingerichtet.' : 'Push nicht eingerichtet. Aktualisierungen sind in der App sichtbar.'}</p>
    {#if isNative()}
      <p>Während der gestarteten Begleitung aktualisiert dieses Gerät deinen Standort auch bei gesperrtem Bildschirm. Es wird kein Bewegungsverlauf gespeichert.</p>
      <div class="actions">
        {#if state.live_active}<button type="button" class="ui-button" disabled={busy} onclick={() => pause()}>Standortbegleitung pausieren</button>
        {:else}<button type="button" class="ui-button" disabled={busy || !canStart} onclick={start}>Standortbegleitung starten</button>{/if}
        <button type="button" class="ui-button" disabled={busy} onclick={() => perform(async () => { const granted = await registerNativePush(); message = granted ? 'Benachrichtigungen angefordert.' : 'Benachrichtigungen sind in den Systemeinstellungen deaktiviert.'; })}>Benachrichtigungen erlauben</button>
      </div>
      {#if !canStart && !state.live_active}<p>Die Standortbegleitung kannst du im Vorlauf vor der Abfahrt starten.</p>{/if}
    {:else}<p>Die Verkehrsprüfung läuft ab dem bestätigten Startort weiter. Für aktuelle Standorte im Hintergrund verwende die iPhone-/Android-App.</p>{/if}
    <button type="button" class="ui-button" disabled={busy} onclick={() => pause(true)}>Überwachung beenden</button>
  {:else}
    <p>Der Verkehr wird rund um deine Abfahrt automatisch geprüft. Der bestätigte Startort bleibt bis zum Ende dieser Überwachung gespeichert.</p>
    <label>Vorlauf vor Abfahrt <input type="number" min="15" max="180" step="1" bind:value={lead} /></label>
    <label>Startort <select bind:value={originMode}><option value="current">Aktuellen Standort bestätigen</option><option value="place">Ort auswählen</option></select></label>
    {#if originMode === 'place'}
      <label>Startort suchen <input bind:value={query} oninput={() => { selected = null; places = []; }} placeholder="Adresse oder Ort" /></label>
      <button type="button" class="ui-button" disabled={busy || query.trim().length < 2} onclick={findPlaces}>Orte suchen</button>
      <ul>{#each places as place}<li><button type="button" class="ui-button" aria-pressed={selected?.place_id === place.place_id} onclick={() => selected = place}>{place.name} · {place.address ?? ''}</button></li>{/each}</ul>
      {#if selected}<p>Bestätigter Startort: {selected.name}</p>{/if}
    {/if}
    <button type="button" class="ui-button" disabled={busy || !Number.isInteger(lead) || lead < 15 || lead > 180 || (originMode === 'place' && !selected)} onclick={setup}>{busy ? 'Wird eingerichtet …' : 'Startort bestätigen und überwachen'}</button>
  {/if}
  {#if message}<p role="status">{message}</p>{/if}
  {#if error}<p role="alert">{error}</p>{/if}
</section>
{/if}

<style>
  .companion { display:flex; flex-direction:column; gap:var(--space-3); }
  h3 { margin:0; color:var(--text-primary); font-size:16px; }
  p { margin:0; color:var(--text-secondary); font-size:12px; line-height:1.5; }
  label { display:flex; flex-direction:column; gap:var(--space-1); color:var(--text-secondary); font-size:12px; }
  .actions { display:flex; flex-wrap:wrap; gap:var(--space-2); }
  input,select,button { min-height:44px; }
  ul { display:flex; flex-direction:column; gap:var(--space-2); padding:0; list-style:none; }
</style>
