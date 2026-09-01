import Dexie, { type Table } from 'dexie';
import type { DayEntry, Todo, Exercise, TrainingSet, TrainingRotation, SyncQueueEntry } from './types';

export interface DayEntryRecord extends DayEntry { localId?: number; serverId?: string; }
export interface TodoRecord extends Todo { localId?: number; serverId?: string; }
export interface ExerciseRecord extends Exercise { localId?: number; serverId?: string; }
export interface TrainingSetRecord extends TrainingSet { localId?: number; serverId?: string; }
export interface TrainingRotationRecord extends TrainingRotation { localId?: number; serverId?: string; }
export interface PhotoRecord { localId?: number; serverId?: string; mealLocalId?: number; blob?: Blob; }

export class FitTrackDB extends Dexie {
  dayEntries!: Table<DayEntryRecord, number>;
  trainingRotation!: Table<TrainingRotationRecord, number>;
  trainingSets!: Table<TrainingSetRecord, number>;
  exercises!: Table<ExerciseRecord, number>;
  todos!: Table<TodoRecord, number>;
  syncQueue!: Table<SyncQueueEntry, number>;
  photos!: Table<PhotoRecord, number>;

  constructor() {
    super('fittrack');
    this.version(2).stores({
      dayEntries: '++localId, serverId, date, rotation_slot, updated_at',
      trainingRotation: '++localId, serverId, slot',
      trainingSets: '++localId, serverId, date, training_type, exercise_name, set_number, completed, updated_at',
      exercises: '++localId, serverId, training_type, exercise_name',
      todos: '++localId, serverId, status, priority, category, due_date, due_time, source, external_id, sort_order, updated_at',
      syncQueue: '++id, entityType, entityLocalId, action, clientTimestamp, synced',
      photos: '++localId, serverId, mealLocalId, blob',
    });
    // Legacy Meal/Dish/MealTemplate APIs were removed in the account-private
    // meal-entry cutover. Delete their unreachable local stores on upgrade so
    // an account switch cannot leave misleading stale records behind.
    this.version(3).stores({ meals: null, mealTemplates: null });
  }
}

export const db = new FitTrackDB();

// Helper: queue a sync change
export async function queueSync(entityType: string, entityLocalId: number, action: 'create' | 'update' | 'delete') {
  await db.syncQueue.add({
    entityType,
    entityLocalId,
    action,
    clientTimestamp: Date.now(),
    synced: false,
  });
}

// Helper: clear synced queue items
export async function clearSyncQueue() {
  await db.syncQueue.where('synced').equals(1 as any).delete();
  await db.syncQueue.where('synced').equals(true as any).delete();
}

/** Clear private offline records before switching browser accounts. */
export async function clearAccountData() {
  await db.transaction(
    'rw',
    [
      db.dayEntries, db.trainingRotation, db.trainingSets, db.exercises,
      db.todos, db.syncQueue, db.photos,
    ],
    async () => {
      await Promise.all([
        db.dayEntries.clear(), db.trainingRotation.clear(), db.trainingSets.clear(),
        db.exercises.clear(), db.todos.clear(), db.syncQueue.clear(), db.photos.clear(),
      ]);
    },
  );
}
