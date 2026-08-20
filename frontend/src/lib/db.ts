import Dexie, { type Table } from 'dexie';
import type { DayEntry, Meal, Todo, Exercise, TrainingSet, TrainingRotation, MealTemplate, SyncQueueEntry } from './types';

export interface DayEntryRecord extends DayEntry { localId?: number; serverId?: string; }
export interface MealRecord extends Meal { localId?: number; serverId?: string; }
export interface TodoRecord extends Todo { localId?: number; serverId?: string; }
export interface ExerciseRecord extends Exercise { localId?: number; serverId?: string; }
export interface TrainingSetRecord extends TrainingSet { localId?: number; serverId?: string; }
export interface TrainingRotationRecord extends TrainingRotation { localId?: number; serverId?: string; }
export interface MealTemplateRecord extends MealTemplate { localId?: number; serverId?: string; }
export interface PhotoRecord { localId?: number; serverId?: string; mealLocalId?: number; blob?: Blob; }

export class FitTrackDB extends Dexie {
  dayEntries!: Table<DayEntryRecord, number>;
  trainingRotation!: Table<TrainingRotationRecord, number>;
  trainingSets!: Table<TrainingSetRecord, number>;
  exercises!: Table<ExerciseRecord, number>;
  meals!: Table<MealRecord, number>;
  todos!: Table<TodoRecord, number>;
  mealTemplates!: Table<MealTemplateRecord, number>;
  syncQueue!: Table<SyncQueueEntry, number>;
  photos!: Table<PhotoRecord, number>;

  constructor() {
    super('fittrack');
    this.version(2).stores({
      dayEntries: '++localId, serverId, date, rotation_slot, updated_at',
      trainingRotation: '++localId, serverId, slot',
      trainingSets: '++localId, serverId, date, training_type, exercise_name, set_number, completed, updated_at',
      exercises: '++localId, serverId, training_type, exercise_name',
      meals: '++localId, serverId, date, meal_slot, is_done, default_time, updated_at',
      todos: '++localId, serverId, status, priority, category, due_date, due_time, source, external_id, sort_order, updated_at',
      mealTemplates: '++localId, serverId, slot',
      syncQueue: '++id, entityType, entityLocalId, action, clientTimestamp, synced',
      photos: '++localId, serverId, mealLocalId, blob',
    });
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