<script lang="ts">
  import { travelHeadline, travelTime, type TravelState } from '$lib/travel';
  export let state: TravelState;
  export let now = Date.now();
  export let buffer = 10;
</script>

<div class="travel-status">
  <strong>{travelHeadline(state, now)}</strong>
  {#if state.departure_change_minutes && state.departure_changed_at && now - Date.parse(state.departure_changed_at) < 30 * 60000}
    <span>Abfahrt angepasst: {Math.abs(state.departure_change_minutes)} Min. {state.departure_change_minutes < 0 ? 'früher' : 'später'}</span>
  {/if}
  {#if state.duration_seconds != null}
    <span>{Math.ceil(state.duration_seconds / 60)} Min. Anreise + {buffer} Min. Puffer · Ankunft {travelTime(state.arrival_at, state.timezone)}</span>
  {/if}
  <span>{state.origin_status === 'live' ? 'Aktueller Gerätestandort' : state.origin_status === 'stale' ? 'Kein frischer Gerätestandort · Prognose ab bestätigtem Startort' : state.origin_status === 'fixed' ? 'Ab bestätigtem Startort' : 'Begleitung beendet'}</span>
  {#if state.checked_at}<small>Google Routes · geprüft {travelTime(state.checked_at, state.timezone)}</small>{/if}
  {#if state.location_checked_at}<small>Standort gemessen {travelTime(state.location_checked_at, state.timezone)}</small>{/if}
  {#if state.error}<span>{state.error}</span>{/if}
</div>

<style>
  .travel-status { display:flex; flex-direction:column; gap:var(--space-1); }
  strong { color:var(--text-primary); font-size:14px; }
  span,small { color:var(--text-secondary); font-size:12px; line-height:1.5; }
</style>
