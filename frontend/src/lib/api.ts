import type {
  DayEntry, Meal, Todo, Exercise, TrainingSet, TrainingRotation,
  TrainingSuggestion, TrainingCompleteRequest,
  MealTemplate, WeekStats, TrendData, SyncPayload, SyncResponse, Goals,
  Dish, DishMatchResult, DishRecommendResult, PhotoAnalysisResponse,
} from './types';
import { db, queueSync, type DayEntryRecord, type MealRecord, type TodoRecord } from './db';

function getBaseUrl(): string {
  if (typeof window !== 'undefined') {
    const host = window.location?.hostname ?? '';
    if (host === 'localhost' || host === '127.0.0.1') {
      return 'http://localhost:8000/api';
    }
  }
  return '/api';
}

export const BASE_URL = getBaseUrl();

class NetworkError extends Error {
  constructor(message: string, public original?: unknown) {
    super(message);
    this.name = 'NetworkError';
  }
}

function isNetworkError(err: unknown): err is NetworkError {
  return err instanceof NetworkError;
}

function looksLikeServerId(id?: string | number | null): boolean {
  if (!id) return false;
  const str = String(id);
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(str);
}

async function findLocalByServerId<T extends { localId?: number; serverId?: string }>(
  table: any,
  serverId: string
): Promise<(T & { localId: number }) | undefined> {
  const existing = await table.where('serverId').equals(serverId).first();
  if (existing?.localId) return existing;
  return undefined;
}

async function saveLocalEntity<T extends Record<string, any>>(
  entityType: string,
  table: any,
  data: Partial<T>,
  action: 'create' | 'update' | 'delete',
  serverId?: string
): Promise<number | undefined> {
  const timestamp = new Date().toISOString();

  if (action === 'delete') {
    if (serverId) {
      const existing = await findLocalByServerId(table, serverId);
      if (existing?.localId) {
        await table.update(existing.localId, { deleted: true, updated_at: timestamp });
        await queueSync(entityType, existing.localId, 'delete');
        return existing.localId;
      }
    }
    // No local record to delete; create a tombstone so sync can still propagate
    const localId = await table.add({ serverId, deleted: true, updated_at: timestamp } as unknown as T);
    await queueSync(entityType, localId, 'delete');
    return localId;
  }

  let localId: number | undefined;
  let merged: Partial<T> = { ...data };

  if (serverId) {
    const existing = await findLocalByServerId(table, serverId);
    if (existing?.localId) {
      localId = existing.localId;
      merged = { ...existing, ...data, serverId, updated_at: timestamp };
      await table.update(localId, merged);
    }
  }

  if (localId === undefined) {
    merged = { ...data, serverId, updated_at: timestamp };
    localId = await table.add(merged as unknown as T);
  }

  await queueSync(entityType, localId as number, action);
  return localId as number;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl ?? BASE_URL;
  }

  private async request<T>(path: string, options?: RequestInit): Promise<T | null> {
    try {
      const url = `${this.baseUrl}${path}`;
      const response = await fetch(url, {
        ...options,
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
      });

      if (!response.ok) {
        console.warn(`API error: ${response.status} ${response.statusText} for ${path}`);
        return null;
      }

      const text = await response.text();
      if (!text) return null;
      return JSON.parse(text) as T;
    } catch (err) {
      console.warn(`API request failed for ${path}:`, err);
      throw new NetworkError(`Network request failed for ${path}`, err);
    }
  }

  // Day Entry
  async getDayEntry(date: string): Promise<DayEntry | null> {
    return this.request<DayEntry>(`/day-entries?date=${date}`);
  }

  async upsertDayEntry(data: Partial<DayEntry>): Promise<DayEntry | null> {
    const serverId = looksLikeServerId(data.id) ? data.id : undefined;
    try {
      const result = await this.request<DayEntry>(`/day-entries`, {
        method: 'PUT',
        body: JSON.stringify(data),
      });
      if (result) {
        // Cache the server result locally
        await saveLocalEntity('dayEntry', db.dayEntries, result, 'update', result.id);
      }
      return result;
    } catch (err) {
      if (isNetworkError(err)) {
        const localId = await saveLocalEntity('dayEntry', db.dayEntries, data, serverId ? 'update' : 'create', serverId);
        return (await db.dayEntries.get(localId as number)) ?? null;
      }
      return null;
    }
  }

  // Meals
  async getMeals(date: string): Promise<Meal[]> {
    return (await this.request<Meal[]>(`/meals?date=${date}`)) ?? [];
  }

  async createMeal(data: Partial<Meal>): Promise<Meal | null> {
    try {
      const result = await this.request<Meal>(`/meals`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
      if (result) {
        await saveLocalEntity('meal', db.meals, result, 'update', result.id);
      }
      return result;
    } catch (err) {
      if (isNetworkError(err)) {
        const localId = await saveLocalEntity('meal', db.meals, data, 'create');
        return (await db.meals.get(localId as number)) ?? null;
      }
      return null;
    }
  }

  async updateMeal(id: string | number, data: Partial<Meal>): Promise<Meal | null> {
    const serverId = looksLikeServerId(id) ? String(id) : undefined;
    try {
      const result = await this.request<Meal>(`/meals/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      });
      if (result) {
        await saveLocalEntity('meal', db.meals, result, 'update', result.id);
      }
      return result;
    } catch (err) {
      if (isNetworkError(err)) {
        const merged = { ...data, id: serverId ?? id };
        const localId = await saveLocalEntity('meal', db.meals, merged, 'update', serverId);
        return (await db.meals.get(localId as number)) ?? null;
      }
      return null;
    }
  }

  async deleteMeal(id: string | number): Promise<boolean> {
    const serverId = looksLikeServerId(id) ? String(id) : undefined;
    try {
      await this.request(`/meals/${id}`, { method: 'DELETE' });
      if (serverId) {
        await saveLocalEntity('meal', db.meals, {}, 'delete', serverId);
      }
      return true;
    } catch (err) {
      if (isNetworkError(err)) {
        await saveLocalEntity('meal', db.meals, {}, 'delete', serverId ?? String(id));
        return true;
      }
      return false;
    }
  }

  async markMealDone(id: string | number): Promise<Meal | null> {
    const serverId = looksLikeServerId(id) ? String(id) : undefined;
    try {
      const result = await this.request<Meal>(`/meals/${id}/done`, { method: 'POST' });
      if (result) {
        await saveLocalEntity('meal', db.meals, result, 'update', result.id);
      }
      return result;
    } catch (err) {
      if (isNetworkError(err)) {
        const existing = serverId ? await findLocalByServerId<MealRecord>(db.meals, serverId) : undefined;
        const updated: Partial<Meal> = existing
          ? { ...existing, is_done: !existing.is_done, updated_at: new Date().toISOString() }
          : { id: serverId ?? String(id), is_done: true, updated_at: new Date().toISOString() };
        const localId = await saveLocalEntity('meal', db.meals, updated, 'update', serverId ?? String(id));
        return (await db.meals.get(localId as number)) ?? null;
      }
      return null;
    }
  }

  async getMealTemplates(): Promise<MealTemplate[]> {
    return (await this.request<MealTemplate[]>(`/meal-templates`)) ?? [];
  }

  // Todos
  async getTodos(date: string, filters?: Record<string, string>): Promise<Todo[]> {
    const params = new URLSearchParams({ date });
    if (filters) {
      for (const [key, val] of Object.entries(filters)) {
        params.append(key, val);
      }
    }
    return (await this.request<Todo[]>(`/todos?${params.toString()}`)) ?? [];
  }

  async createTodo(data: Partial<Todo>): Promise<Todo | null> {
    try {
      const result = await this.request<Todo>(`/todos`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
      if (result) {
        await saveLocalEntity('todo', db.todos, result, 'update', result.id);
      }
      return result;
    } catch (err) {
      if (isNetworkError(err)) {
        const localId = await saveLocalEntity('todo', db.todos, data, 'create');
        return (await db.todos.get(localId as number)) ?? null;
      }
      return null;
    }
  }

  async updateTodo(id: string | number, data: Partial<Todo>): Promise<Todo | null> {
    const serverId = looksLikeServerId(id) ? String(id) : undefined;
    try {
      const result = await this.request<Todo>(`/todos/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      });
      if (result) {
        await saveLocalEntity('todo', db.todos, result, 'update', result.id);
      }
      return result;
    } catch (err) {
      if (isNetworkError(err)) {
        const merged = { ...data, id: serverId ?? id };
        const localId = await saveLocalEntity('todo', db.todos, merged, 'update', serverId);
        return (await db.todos.get(localId as number)) ?? null;
      }
      return null;
    }
  }

  async deleteTodo(id: string | number): Promise<boolean> {
    const serverId = looksLikeServerId(id) ? String(id) : undefined;
    try {
      await this.request(`/todos/${id}`, { method: 'DELETE' });
      if (serverId) {
        await saveLocalEntity('todo', db.todos, {}, 'delete', serverId);
      }
      return true;
    } catch (err) {
      if (isNetworkError(err)) {
        await saveLocalEntity('todo', db.todos, {}, 'delete', serverId ?? String(id));
        return true;
      }
      return false;
    }
  }

  async markTodoDone(id: string | number): Promise<Todo | null> {
    const serverId = looksLikeServerId(id) ? String(id) : undefined;
    try {
      const result = await this.request<Todo>(`/todos/${id}/done`, { method: 'POST' });
      if (result) {
        await saveLocalEntity('todo', db.todos, result, 'update', result.id);
      }
      return result;
    } catch (err) {
      if (isNetworkError(err)) {
        const existing = serverId ? await findLocalByServerId<TodoRecord>(db.todos, serverId) : undefined;
        const newStatus = existing?.status === 'done' ? 'open' : 'done';
        const updated: Partial<Todo> = existing
          ? { ...existing, status: newStatus, updated_at: new Date().toISOString() }
          : { id: serverId ?? String(id), status: 'done', updated_at: new Date().toISOString() };
        const localId = await saveLocalEntity('todo', db.todos, updated, 'update', serverId ?? String(id));
        return (await db.todos.get(localId as number)) ?? null;
      }
      return null;
    }
  }

  // Training
  async getTraining(date: string): Promise<TrainingSuggestion | null> {
    return this.request<TrainingSuggestion>(`/training?date=${date}`);
  }

  async getNextTraining(trainingType: string): Promise<TrainingRotation | null> {
    return this.request<TrainingRotation>(`/training/next?training_type=${encodeURIComponent(trainingType)}`);
  }

  async completeTraining(data: TrainingCompleteRequest): Promise<any> {
    try {
      return await this.request<any>(`/training/complete`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
    } catch (err) {
      if (isNetworkError(err)) {
        // Training completion is not queued for sync in this phase.
        // Future enhancement: store training sets locally and queue them.
        return null;
      }
      return null;
    }
  }

  async getExercises(trainingType: string): Promise<Exercise[]> {
    return (await this.request<Exercise[]>(`/exercises?training_type=${encodeURIComponent(trainingType)}`)) ?? [];
  }

  async getRotation(): Promise<TrainingRotation[]> {
    return (await this.request<TrainingRotation[]>(`/templates/rotation`)) ?? [];
  }

  // Stats
  async getStatsWeek(date: string): Promise<WeekStats | null> {
    return this.request<WeekStats>(`/stats/week?date=${date}`);
  }

  async getStatsTrend(metric: string, days: number): Promise<TrendData | null> {
    return this.request<TrendData>(`/stats/trend?metric=${encodeURIComponent(metric)}&days=${days}`);
  }

  // Photos
  async analyzePhoto(file: File, mealId?: string): Promise<PhotoAnalysisResponse | null> {
    const formData = new FormData();
    formData.append('file', file);
    if (mealId) {
      formData.append('meal_id', mealId);
    }
    try {
      const url = `${this.baseUrl}/photos/analyze`;
      const response = await fetch(url, {
        method: 'POST',
        body: formData,
        credentials: 'include',
      });
      if (!response.ok) {
        console.warn(`API error: ${response.status} ${response.statusText} for /photos/analyze`);
        return null;
      }
      const text = await response.text();
      if (!text) return null;
      return JSON.parse(text);
    } catch (err) {
      console.warn('API request failed for /photos/analyze:', err);
      return null;
    }
  }

  // Google Auth
  async getGoogleStatus(): Promise<any | null> {
    return this.request<any>(`/auth/google/status`);
  }

  // Google Fit sync — fetches steps + sleep details from Google Fit, updates DayEntry in DB
  async syncGoogleFit(date: string): Promise<any> {
    try {
      return await this.request<any>(`/google-fit/sync?date=${date}`, { method: 'POST' });
    } catch (err) {
      if (isNetworkError(err)) return null;
      return null;
    }
  }

  // Scale sync (ESP32 posts to /api/scale-sync directly; this is for manual trigger/testing)
  async scaleSync(data: { weight_kg: number; date?: string; impedance?: number; height_cm?: number; age?: number; gender?: string }): Promise<DayEntry | null> {
    try {
      return await this.request<DayEntry>(`/scale-sync`, {
        method: 'POST',
        body: JSON.stringify(data),
      });
    } catch (err) {
      if (isNetworkError(err)) return null;
      return null;
    }
  }

  // Goals
  async getGoals(): Promise<Goals | null> {
    return this.request<Goals>(`/goals`);
  }

  async updateGoals(goals: Partial<Goals>): Promise<Goals | null> {
    return this.request<Goals>(`/goals`, {
      method: 'PUT',
      body: JSON.stringify({ goals }),
    });
  }

  // Sync
  async syncChanges(payload: SyncPayload): Promise<SyncResponse | null> {
    return this.request<SyncResponse>(`/sync`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  // Dishes
  async getDishes(slot?: number, q?: string): Promise<Dish[]> {
    const params = new URLSearchParams();
    if (slot !== undefined) params.set('slot', String(slot));
    if (q) params.set('q', q);
    const query = params.toString() ? `?${params}` : '';
    return (await this.request<Dish[]>(`/dishes${query}`)) ?? [];
  }

  async getDishRecommend(slot: number): Promise<DishRecommendResult | null> {
    return this.request<DishRecommendResult>(`/dishes/recommend?slot=${slot}`);
  }

  async createDish(data: Partial<Dish> & { name: string }): Promise<Dish | null> {
    return this.request<Dish>(`/dishes`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateDish(id: string, data: Partial<Dish>): Promise<Dish | null> {
    return this.request<Dish>(`/dishes/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteDish(id: string): Promise<boolean> {
    try {
      await this.request(`/dishes/${id}`, { method: 'DELETE' });
      return true;
    } catch { return false; }
  }

  async matchDish(name: string): Promise<DishMatchResult | null> {
    return this.request<DishMatchResult>(`/dishes/match?name=${encodeURIComponent(name)}`);
  }

  async incrementDishUsage(id: string): Promise<Dish | null> {
    return this.request<Dish>(`/dishes/${id}/use`, { method: 'POST' });
  }
}

export const api = new ApiClient();
export { ApiClient };
