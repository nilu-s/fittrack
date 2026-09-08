import { writable } from 'svelte/store';
import { apiFetch, isNative, nativeBridge } from './native';

export interface TravelState {
  id: string; todo_id: string; active: boolean; timezone: string; lead_minutes: number;
  live_active: boolean; origin_status: 'live' | 'stale' | 'fixed' | 'none';
  location_checked_at: string | null; checked_at: string | null; depart_at: string | null;
  arrival_at: string | null; duration_seconds: number | null; expires_at: string;
  error: string | null; push_available: boolean; starts_at: string | null;
  departure_change_minutes: number | null; departure_changed_at: string | null;
}
export const travelStates = writable<Record<string, TravelState>>({});
export const travelLoadError = writable('');
export const pendingTravelTodo = writable<{ id: string; date: string } | null>(null);
let generation = 0;
export function clearTravel(preservePending = false) { generation++; travelStates.set({}); travelLoadError.set(''); if (!preservePending) pendingTravelTodo.set(null); }

export async function travelRequest(path = '', method = 'GET', body?: unknown): Promise<any> {
  const response = await apiFetch(`/api/travel${path}`, { method, headers: { 'Content-Type': 'application/json' }, ...(body !== undefined ? { body: JSON.stringify(body) } : {}) });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(typeof detail.detail === 'string' ? detail.detail : 'Anreise konnte nicht aktualisiert werden.');
  }
  return response.status === 204 ? null : response.json();
}

export async function refreshTravel() {
  const requestGeneration = generation;
  try {
    const states: TravelState[] = await travelRequest();
    if (requestGeneration !== generation) return;
    travelStates.set(Object.fromEntries(states.map((state) => [state.todo_id, state])));
    travelLoadError.set('');
    if (isNative()) {
      const local = await nativeBridge.locationState();
      if (local.active && !states.some((state) => state.todo_id === local.todoId && state.live_active)) await nativeBridge.stopLocation();
    }
  } catch { if (requestGeneration === generation) travelLoadError.set('Anreisestatus nicht aktualisiert. Letzte Angaben prüfen.'); }
}

export async function currentPosition(): Promise<{ latitude: number; longitude: number }> {
  if (isNative()) {
    const { Geolocation } = await import('@capacitor/geolocation');
    await Geolocation.requestPermissions();
    const fix = await Geolocation.getCurrentPosition({ enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 });
    if (fix.coords.accuracy > 200) throw new Error('Standort zu ungenau. Bitte einen Startort auswählen.');
    return { latitude: fix.coords.latitude, longitude: fix.coords.longitude };
  }
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) { reject(new Error('Standort nicht verfügbar. Bitte einen Startort auswählen.')); return; }
    navigator.geolocation.getCurrentPosition((fix) => {
      if (fix.coords.accuracy > 200) reject(new Error('Standort zu ungenau. Bitte einen Startort auswählen.'));
      else resolve({ latitude: fix.coords.latitude, longitude: fix.coords.longitude });
    }, () => reject(new Error('Standortzugriff nicht möglich. Bitte einen Startort auswählen.')), { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 });
  });
}

export function travelTime(value: string | null, zone = 'Europe/Berlin') {
  return value ? new Date(value).toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', timeZone: zone }) : '–';
}

export function travelHeadline(state: TravelState, now: number): string {
  if (!state.active || new Date(state.expires_at).getTime() <= now) return 'Anreiseüberwachung beendet';
  if (state.error || !state.checked_at || now - Date.parse(state.checked_at) > 10 * 60000 || state.origin_status === 'stale') return 'Abfahrtsprognose prüfen';
  if (!state.depart_at) return 'Abfahrt wird berechnet';
  return Date.parse(state.depart_at) <= now ? 'Jetzt los · Abfahrt prüfen' : `Um ${travelTime(state.depart_at, state.timezone)} losfahren`;
}
