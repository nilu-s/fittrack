import { writable } from 'svelte/store';
import { db } from './db';
import { api } from './api';
import type { SyncPayload, SyncResponse } from './types';

export type SyncStatus = 'synced' | 'syncing' | 'offline' | 'error';

export const syncStatus = writable<SyncStatus>('synced');

let isSyncing = false;
let retryCount = 0;
const MAX_RETRIES = 5;

async function processSyncQueue(): Promise<boolean> {
  const pending = await db.syncQueue.where('synced').equals(0 as any).toArray();
  if (pending.length === 0) {
    syncStatus.set('synced');
    return true;
  }

  syncStatus.set('syncing');

  const payload: SyncPayload = {
    changes: pending.map((p) => ({
      id: p.id,
      entityType: p.entityType,
      entityLocalId: p.entityLocalId,
      action: p.action,
      clientTimestamp: p.clientTimestamp,
      synced: false,
    })),
    lastSync: Date.now(),
  };

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
    syncStatus.set('syncing');
    triggerSync();
  });

  window.addEventListener('offline', () => {
    syncStatus.set('offline');
  });

  // Initial sync attempt
  if (navigator.onLine) {
    triggerSync();
  } else {
    syncStatus.set('offline');
  }

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