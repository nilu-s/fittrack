import { writable } from 'svelte/store';
import { db } from './db';
import { api } from './api';
import { onlineStatus } from './stores';
import type { SyncPayload, SyncResponse, SyncQueueEntry, DayEntry, Meal, Todo } from './types';

export type SyncStatus = 'synced' | 'syncing' | 'offline' | 'error';

export const syncStatus = writable<SyncStatus>('synced');
export const lastSync = writable<number | null>(null);

let isSyncing = false;
let retryCount = 0;
const MAX_RETRIES = 5;
const AUTO_SYNC_INTERVAL_MS = 15 * 60 * 1000; // 15 minutes

function generateUUID(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function looksLikeServerId(id?: string | number | null): boolean {
  if (!id) return false;
  const str = String(id);
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(str);
}

function stripLocalOnlyFields(payload: Record<string, any>): Record<string, any> {
  const { localId, serverId, synced, deleted, ...rest } = payload;
  return rest;
}

const ENTITY_TYPE_MAP: Record<string, string> = {
  dayEntry: 'day_entry',
  meal: 'meal',
  todo: 'todo',
  trainingSet: 'training_set',
  exercise: 'exercise',
  mealTemplate: 'meal_template',
};

async function buildSyncPayload(pending: SyncQueueEntry[]): Promise<SyncPayload> {
  const changes: SyncPayload['changes'] = [];

  for (const entry of pending) {
    const entityType = ENTITY_TYPE_MAP[entry.entityType] ?? entry.entityType;
    let record: Record<string, any> | undefined;
    let serverId: string | undefined;

    try {
      if (entry.entityType === 'dayEntry') {
        record = (await db.dayEntries.get(entry.entityLocalId)) as Record<string, any> | undefined;
      } else if (entry.entityType === 'meal') {
        record = (await db.meals.get(entry.entityLocalId)) as Record<string, any> | undefined;
      } else if (entry.entityType === 'todo') {
        record = (await db.todos.get(entry.entityLocalId)) as Record<string, any> | undefined;
      } else if (entry.entityType === 'trainingSet') {
        record = (await db.trainingSets.get(entry.entityLocalId)) as Record<string, any> | undefined;
      } else if (entry.entityType === 'exercise') {
        record = (await db.exercises.get(entry.entityLocalId)) as Record<string, any> | undefined;
      } else if (entry.entityType === 'mealTemplate') {
        record = (await db.mealTemplates.get(entry.entityLocalId)) as Record<string, any> | undefined;
      }
    } catch (e) {
      console.warn('Failed to load queued entity from IndexedDB:', e);
    }

    if (record) {
      serverId = record.serverId || record.id;
    }

    if (!serverId) {
      serverId = generateUUID();
      // Persist generated server id on the local record for future syncs
      if (record && entry.action !== 'delete') {
        try {
          if (entry.entityType === 'dayEntry') {
            await db.dayEntries.update(entry.entityLocalId, { serverId });
          } else if (entry.entityType === 'meal') {
            await db.meals.update(entry.entityLocalId, { serverId });
          } else if (entry.entityType === 'todo') {
            await db.todos.update(entry.entityLocalId, { serverId });
          } else if (entry.entityType === 'trainingSet') {
            await db.trainingSets.update(entry.entityLocalId, { serverId });
          } else if (entry.entityType === 'exercise') {
            await db.exercises.update(entry.entityLocalId, { serverId });
          } else if (entry.entityType === 'mealTemplate') {
            await db.mealTemplates.update(entry.entityLocalId, { serverId });
          }
        } catch (e) {
          console.warn('Failed to persist generated server id:', e);
        }
      }
    }

    let payload: Record<string, any> = {};
    if (record) {
      payload = stripLocalOnlyFields(record);
    }

    changes.push({
      entity_type: entityType,
      entity_id: serverId,
      action: entry.action,
      payload,
      client_timestamp: entry.clientTimestamp,
    });
  }

  return {
    changes,
    lastSync: Date.now(),
  };
}

async function processSyncQueue(): Promise<boolean> {
  const pending = await db.syncQueue.where('synced').equals(0 as any).toArray();
  if (pending.length === 0) {
    syncStatus.set('synced');
    lastSync.set(Date.now());
    return true;
  }

  syncStatus.set('syncing');

  const payload = await buildSyncPayload(pending);

  const response: SyncResponse | null = await api.syncChanges(payload);

  if (response === null) {
    retryCount++;
    if (retryCount >= MAX_RETRIES) {
      syncStatus.set('error');
      return false;
    }
    const backoff = Math.min(1000 * Math.pow(2, retryCount), 30000);
    await new Promise((r) => setTimeout(r, backoff));
    return processSyncQueue();
  }

  // Mark all as synced
  for (const entry of pending) {
    if (entry.id) {
      await db.syncQueue.update(entry.id, { synced: true });
    }
  }
  await db.syncQueue.where('synced').equals(1 as any).delete();
  await db.syncQueue.where('synced').equals(true as any).delete();

  retryCount = 0;
  syncStatus.set('synced');
  lastSync.set(Date.now());
  return true;
}

export async function triggerSync() {
  if (isSyncing) return;
  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    syncStatus.set('offline');
    return;
  }
  isSyncing = true;
  try {
    await processSyncQueue();
  } catch (e) {
    console.warn('Sync failed:', e);
    syncStatus.set('error');
  } finally {
    isSyncing = false;
  }
}

export function initSync() {
  if (typeof window === 'undefined') return;

  window.addEventListener('online', () => {
    onlineStatus.set(true);
    syncStatus.set('syncing');
    triggerSync();
  });

  window.addEventListener('offline', () => {
    onlineStatus.set(false);
    syncStatus.set('offline');
  });

  // Initial sync attempt
  if (navigator.onLine) {
    triggerSync();
  } else {
    onlineStatus.set(false);
    syncStatus.set('offline');
  }

  // Auto-sync every 15 minutes when online
  setInterval(() => {
    if (navigator.onLine) {
      triggerSync();
    }
  }, AUTO_SYNC_INTERVAL_MS);

  // Periodic retry on error
  setInterval(() => {
    syncStatus.update((status) => {
      if (status === 'error' && navigator.onLine) {
        triggerSync();
      }
      return status;
    });
  }, 60000);
}
