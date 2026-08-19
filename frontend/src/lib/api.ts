import type {
  DayEntry, Meal, Todo, Exercise, TrainingSet, TrainingRotation,
  MealTemplate, WeekStats, TrendData, SyncPayload, SyncResponse
} from './types';

const PROD_URL = 'https://fittrack.49.12.225.84.sslip.io/api';
const DEV_URL = 'http://localhost:8000/api';

function getBaseUrl(): string {
  if (typeof window !== 'undefined') {
    const host = window.location?.hostname ?? '';
    if (host === 'localhost' || host === '127.0.0.1' || host.startsWith('192.168.') || host.startsWith('10.')) {
      return DEV_URL;
    }
  }
  return PROD_URL;
}

export const BASE_URL = getBaseUrl();

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
      return null;
    }
  }

  // Day Entry
  async getDayEntry(date: string): Promise<DayEntry | null> {
    return this.request<DayEntry>(`/day-entries/${date}`);
  }

  async upsertDayEntry(data: Partial<DayEntry>): Promise<DayEntry | null> {
    return this.request<DayEntry>(`/day-entries`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Meals
  async getMeals(date: string): Promise<Meal[]> {
    return (await this.request<Meal[]>(`/meals?date=${date}`)) ?? [];
  }

  async createMeal(data: Partial<Meal>): Promise<Meal | null> {
    return this.request<Meal>(`/meals`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateMeal(id: number, data: Partial<Meal>): Promise<Meal | null> {
    return this.request<Meal>(`/meals/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteMeal(id: number): Promise<boolean> {
    await this.request(`/meals/${id}`, { method: 'DELETE' });
    return true;
  }

  async markMealDone(id: number): Promise<Meal | null> {
    return this.request<Meal>(`/meals/${id}/done`, { method: 'PATCH' });
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
    return this.request<Todo>(`/todos`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateTodo(id: number, data: Partial<Todo>): Promise<Todo | null> {
    return this.request<Todo>(`/todos/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteTodo(id: number): Promise<boolean> {
    await this.request(`/todos/${id}`, { method: 'DELETE' });
    return true;
  }

  async markTodoDone(id: number): Promise<Todo | null> {
    return this.request<Todo>(`/todos/${id}/done`, { method: 'PATCH' });
  }

  // Training
  async getTraining(date: string): Promise<TrainingSet[]> {
    return (await this.request<TrainingSet[]>(`/training?date=${date}`)) ?? [];
  }

  async getNextTraining(trainingType: string): Promise<TrainingRotation | null> {
    return this.request<TrainingRotation>(`/training/next/${encodeURIComponent(trainingType)}`);
  }

  async completeTraining(data: Partial<TrainingSet>): Promise<TrainingSet | null> {
    return this.request<TrainingSet>(`/training/complete`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getExercises(trainingType: string): Promise<Exercise[]> {
    return (await this.request<Exercise[]>(`/exercises?trainingType=${encodeURIComponent(trainingType)}`)) ?? [];
  }

  async getRotation(): Promise<TrainingRotation[]> {
    return (await this.request<TrainingRotation[]>(`/training/rotation`)) ?? [];
  }

  // Stats
  async getStatsWeek(date: string): Promise<WeekStats | null> {
    return this.request<WeekStats>(`/stats/week?date=${date}`);
  }

  async getStatsTrend(metric: string, days: number): Promise<TrendData | null> {
    return this.request<TrendData>(`/stats/trend?metric=${encodeURIComponent(metric)}&days=${days}`);
  }

  // Sync
  async syncChanges(payload: SyncPayload): Promise<SyncResponse | null> {
    return this.request<SyncResponse>(`/sync`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }
}

export const api = new ApiClient();
export { ApiClient };