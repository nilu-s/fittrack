import { writable } from 'svelte/store';
import { syncStatus, lastSync } from './sync';
import type { DayData } from './types';

function todayStr(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export const currentDate = writable<string>(todayStr());
export { syncStatus, lastSync };
export const dayData = writable<DayData | null>(null);

export const onlineStatus = writable<boolean>(
  typeof navigator !== 'undefined' ? navigator.onLine : true
);

// Daily goals (can be overridden in settings)
export const dailyGoals = writable({
  kcal: 2480,
  protein: 194,
  carbs: 258,
  fat: 78,
  steps: 10000,
  sleepHours: 8,
});