import Dexie, { type Table } from 'dexie';
import type { DayEntry, Meal, Todo, Exercise, TrainingSet, TrainingRotation, MealTemplate, SyncQueueEntry } from './types';

export interface DayEntryRecord extends DayEntry { localId?: number; serverId?: number; }
export interface MealRecord extends Meal { localId?: number; serverId?: number; }
export interface TodoRecord extends Todo { localId?: number; serverId?: number; }
export interface ExerciseRecord extends Exercise { localId?: number; serverId?: number; }
export interface TrainingSetRecord extends TrainingSet { localId?: number; serverId?: number; }
export interface TrainingRotationRecord extends TrainingRotation { localId?: number; serverId?: number; }
export interface MealTemplateRecord extends MealTemplate { localId?: number; serverId?: number; }
export interface PhotoRecord { localId?: number; serverId?: number; mealLocalId?: number; blob?: Blob; }

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
    this.version(1).stores({
      dayEntries: '++localId, serverId, date, rotationSlot, updatedAt',
      trainingRotation: '++localId, serverId, slot',
      trainingSets: '++localId, serverId, date, trainingType, exerciseName, setNumber, completed, updatedAt',
      exercises: '++localId, serverId, trainingType, exerciseName',
      meals: '++localId, serverId, date, mealSlot, isDone, defaultTime, updatedAt',
      todos: '++localId, serverId, status, priority, category, dueDate, dueTime, source, externalId, sortOrder, updatedAt',
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