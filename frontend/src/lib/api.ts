import type {
  DayEntry,
  Todo,
  Exercise,
  TrainingSet,
  TrainingRotation,
  TrainingUnit,
  TrainingSuggestion,
  TrainingCompleteRequest,
  ExerciseProgress,
  WeekStats,
  TrendData,
  SyncPayload,
  SyncResponse,
  Goals,
  MealCategory,
  Food,
  Recipe,
  MealPlan,
  MealEntry,
  MealPhotoAnalysis,
  BodyProfile,
  ScaleMeasurement,
  TodoRoutine,
  TodoDraft,
  PlaceSuggestion,
  TravelEstimate,
  ShoppingItem,
  ShoppingList,
  ShoppingMealPreview,
  Space,
  SpaceInvitation,
  SpaceProject,
  Note,
} from "./types";
import { db, queueSync, type DayEntryRecord, type TodoRecord } from "./db";

function getBaseUrl(): string {
  if (typeof window !== "undefined") {
    const host = window.location?.hostname ?? "";
    if (host === "localhost" || host === "127.0.0.1") {
      return "http://localhost:8000/api";
    }
  }
  return "/api";
}

export const BASE_URL = getBaseUrl();

class NetworkError extends Error {
  constructor(
    message: string,
    public original?: unknown,
  ) {
    super(message);
    this.name = "NetworkError";
  }
}

function isNetworkError(err: unknown): err is NetworkError {
  return err instanceof NetworkError;
}

function looksLikeServerId(id?: string | number | null): boolean {
  if (!id) return false;
  const str = String(id);
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
    str,
  );
}

/** Translate the UI's explicit per-100g names to the compact API command. */
function foodPayload(data: Partial<Food>): Record<string, unknown> {
  return { ...data };
}

function recipePayload(data: Partial<Recipe>): Record<string, unknown> {
  return {
    ...data,
    ingredients: data.ingredients?.map(
      ({ nested_recipe_id, unit, ...ingredient }) => ({
        ...ingredient,
        nested_recipe_id,
        unit,
      }),
    ),
  };
}

function planPayload(data: Partial<MealPlan>): Record<string, unknown> {
  return {
    ...data,
    items: data.items?.map(({ weekdays, portion, id: _id, ...item }) => ({
      ...item,
      weekdays,
      portion: portion ?? 1,
    })),
  };
}

async function findLocalByServerId<
  T extends { localId?: number; serverId?: string },
>(
  table: any,
  serverId: string,
): Promise<(T & { localId: number }) | undefined> {
  const existing = await table.where("serverId").equals(serverId).first();
  if (existing?.localId) return existing;
  return undefined;
}

async function saveLocalEntity<T extends Record<string, any>>(
  entityType: string,
  table: any,
  data: Partial<T>,
  action: "create" | "update" | "delete",
  serverId?: string,
): Promise<number | undefined> {
  const timestamp = new Date().toISOString();

  if (action === "delete") {
    if (serverId) {
      const existing = await findLocalByServerId(table, serverId);
      if (existing?.localId) {
        await table.update(existing.localId, {
          deleted: true,
          updated_at: timestamp,
        });
        await queueSync(entityType, existing.localId, "delete");
        return existing.localId;
      }
    }
    // No local record to delete; create a tombstone so sync can still propagate
    const localId = await table.add({
      serverId,
      deleted: true,
      updated_at: timestamp,
    } as unknown as T);
    await queueSync(entityType, localId, "delete");
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

  private async request<T>(
    path: string,
    options?: RequestInit,
  ): Promise<T | null> {
    try {
      const url = `${this.baseUrl}${path}`;
      const response = await fetch(url, {
        ...options,
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...options?.headers,
        },
      });

      if (!response.ok) {
        console.warn(
          `API error: ${response.status} ${response.statusText} for ${path}`,
        );
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

  /** Commands returning HTTP 204 need an explicit success channel. */
  private async requestOk(
    path: string,
    options?: RequestInit,
  ): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}${path}`, {
        ...options,
        credentials: "include",
        headers: { "Content-Type": "application/json", ...options?.headers },
      });
      return response.ok;
    } catch (err) {
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
        method: "PUT",
        body: JSON.stringify(data),
      });
      if (result) {
        // Cache the server result locally
        await saveLocalEntity(
          "dayEntry",
          db.dayEntries,
          result,
          "update",
          result.id,
        );
      }
      return result;
    } catch (err) {
      if (isNetworkError(err)) {
        const localId = await saveLocalEntity(
          "dayEntry",
          db.dayEntries,
          data,
          serverId ? "update" : "create",
          serverId,
        );
        return (await db.dayEntries.get(localId as number)) ?? null;
      }
      return null;
    }
  }

  // Notes are deliberately online-first: moving a private card into a shared
  // area must be authorized by the server before the UI presents it as shared.
  async getNotes(): Promise<Note[]> {
    return (await this.request<Note[]>(`/notes`)) ?? [];
  }

  async createNote(data: Pick<Note, 'title'> & Partial<Pick<Note, 'body' | 'space_id'>>): Promise<Note | null> {
    return await this.request<Note>(`/notes`, { method: 'POST', body: JSON.stringify(data) });
  }

  async updateNote(id: string, data: Partial<Pick<Note, 'title' | 'body' | 'sort_order'>>): Promise<Note | null> {
    return await this.request<Note>(`/notes/${id}`, { method: 'PUT', body: JSON.stringify(data) });
  }

  async moveNote(id: string, space_id: string, confirm_share = false): Promise<Note | null> {
    return await this.request<Note>(`/notes/${id}/move`, { method: 'POST', body: JSON.stringify({ space_id, confirm_share }) });
  }

  async planNote(id: string, due_date: string, start_time?: string | null): Promise<Note | null> {
    return await this.request<Note>(`/notes/${id}/plan`, { method: 'POST', body: JSON.stringify({ due_date, start_time: start_time || null }) });
  }

  async unscheduleNote(id: string): Promise<Note | null> {
    return await this.request<Note>(`/notes/${id}/unschedule`, { method: 'POST' });
  }

  // Todos
  async getTodos(
    date?: string,
    filters?: Record<string, string>,
  ): Promise<Todo[]> {
    const params = new URLSearchParams();
    if (date) params.set("date", date);
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
        method: "POST",
        body: JSON.stringify(data),
      });
      if (result) {
        await saveLocalEntity("todo", db.todos, result, "update", result.id);
      }
      return result;
    } catch (err) {
      if (isNetworkError(err)) {
        const localId = await saveLocalEntity("todo", db.todos, data, "create");
        return (await db.todos.get(localId as number)) ?? null;
      }
      return null;
    }
  }

  async updateTodo(
    id: string | number,
    data: Partial<Todo>,
  ): Promise<Todo | null> {
    const serverId = looksLikeServerId(id) ? String(id) : undefined;
    try {
      const result = await this.request<Todo>(`/todos/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      });
      if (result) {
        await saveLocalEntity("todo", db.todos, result, "update", result.id);
      }
      return result;
    } catch (err) {
      if (isNetworkError(err)) {
        const merged = { ...data, id: serverId ?? id };
        const localId = await saveLocalEntity(
          "todo",
          db.todos,
          merged,
          "update",
          serverId,
        );
        return (await db.todos.get(localId as number)) ?? null;
      }
      return null;
    }
  }

  async deleteTodo(id: string | number): Promise<boolean> {
    const serverId = looksLikeServerId(id) ? String(id) : undefined;
    try {
      await this.request(`/todos/${id}`, { method: "DELETE" });
      if (serverId) {
        await saveLocalEntity("todo", db.todos, {}, "delete", serverId);
      }
      return true;
    } catch (err) {
      if (isNetworkError(err)) {
        await saveLocalEntity(
          "todo",
          db.todos,
          {},
          "delete",
          serverId ?? String(id),
        );
        return true;
      }
      return false;
    }
  }

  async markTodoDone(id: string | number): Promise<Todo | null> {
    const serverId = looksLikeServerId(id) ? String(id) : undefined;
    try {
      const result = await this.request<Todo>(`/todos/${id}/done`, {
        method: "POST",
      });
      if (result) {
        await saveLocalEntity("todo", db.todos, result, "update", result.id);
      }
      return result;
    } catch (err) {
      if (isNetworkError(err)) {
        const existing = serverId
          ? await findLocalByServerId<TodoRecord>(db.todos, serverId)
          : undefined;
        const newStatus = existing?.status === "done" ? "open" : "done";
        const updated: Partial<Todo> = existing
          ? {
              ...existing,
              status: newStatus,
              updated_at: new Date().toISOString(),
            }
          : {
              id: serverId ?? String(id),
              status: "done",
              updated_at: new Date().toISOString(),
            };
        const localId = await saveLocalEntity(
          "todo",
          db.todos,
          updated,
          "update",
          serverId ?? String(id),
        );
        return (await db.todos.get(localId as number)) ?? null;
      }
      return null;
    }
  }

  // Shared spaces are online-only: membership changes must be verified before
  // a browser can show or mutate shared household content.
  async getSpaces(): Promise<Space[]> { return (await this.request<Space[]>('/spaces')) ?? []; }
  async createSpace(name: string): Promise<Space | null> { return this.request<Space>('/spaces', { method: 'POST', body: JSON.stringify({ name }) }); }
  async inviteToSpace(spaceId: string, contactId: string): Promise<boolean> { return Boolean(await this.request(`/spaces/${spaceId}/invitations`, { method: 'POST', body: JSON.stringify({ contact_id: contactId }) })); }
  async removeSpaceMember(spaceId: string, accountId: string): Promise<boolean> { return this.requestOk(`/spaces/${spaceId}/members/${accountId}`, { method: 'DELETE' }); }
  async getSpaceProjects(spaceId: string): Promise<SpaceProject[]> { return (await this.request<SpaceProject[]>(`/spaces/${spaceId}/projects`)) ?? []; }
  async createSpaceProject(spaceId: string, name: string, description?: string): Promise<SpaceProject | null> { return this.request<SpaceProject>(`/spaces/${spaceId}/projects`, { method: 'POST', body: JSON.stringify({ name, description: description || null }) }); }
  async getSpaceInvitations(): Promise<SpaceInvitation[]> { return (await this.request<SpaceInvitation[]>('/space-invitations')) ?? []; }
  async acceptSpaceInvitation(id: string): Promise<Space | null> { return this.request<Space>(`/space-invitations/${id}/accept`, { method: 'POST' }); }
  async declineSpaceInvitation(id: string): Promise<boolean> { return this.requestOk(`/space-invitations/${id}/decline`, { method: 'POST' }); }
  async getContacts(): Promise<import('./types').Contact[]> { return (await this.request<import('./types').Contact[]>('/contacts')) ?? []; }
  async searchContacts(query: string): Promise<import('./types').ContactSearchResult[]> { return (await this.request<import('./types').ContactSearchResult[]>(`/contacts/search?query=${encodeURIComponent(query)}`)) ?? []; }
  async inviteContact(alias: string): Promise<boolean> { return Boolean(await this.request('/contacts/invitations', { method: 'POST', body: JSON.stringify({ alias }) })); }
  async removeContact(id: string): Promise<boolean> { return this.requestOk(`/contacts/entries/${id}`, { method: 'DELETE' }); }
  async getContactInvitations(): Promise<import('./types').ContactInvitation[]> { return (await this.request<import('./types').ContactInvitation[]>('/contact-invitations')) ?? []; }
  async getOutgoingContactInvitations(): Promise<import('./types').ContactOutgoingInvitation[]> { return (await this.request<import('./types').ContactOutgoingInvitation[]>('/contacts/outgoing-invitations')) ?? []; }
  async acceptContactInvitation(id: string): Promise<boolean> { return this.requestOk(`/contact-invitations/${id}/accept`, { method: 'POST' }); }
  async declineContactInvitation(id: string): Promise<boolean> { return this.requestOk(`/contact-invitations/${id}/decline`, { method: 'POST' }); }
  async setAccountAlias(alias: string): Promise<boolean> { return this.requestOk('/auth/alias', { method: 'POST', body: JSON.stringify({ alias }) }); }

  async draftTodo(text: string, date: string): Promise<TodoDraft | null> {
    return this.request<TodoDraft>("/todo-planning/draft", {
      method: "POST", body: JSON.stringify({ text, date }),
    });
  }

  async askAssistant(text: string, date: string): Promise<string | null> {
    const response = await this.request<{ message: string }>("/todo-planning/assistant", { method: "POST", body: JSON.stringify({ text, date }) });
    return response?.message ?? null;
  }

  async searchTodoPlaces(query: string): Promise<PlaceSuggestion[]> {
    return (await this.request<PlaceSuggestion[]>(`/todo-planning/places?query=${encodeURIComponent(query)}`)) ?? [];
  }

  async estimateTodoTravel(id: string, latitude: number, longitude: number): Promise<TravelEstimate | null> {
    return this.request<TravelEstimate>(`/todo-planning/${id}/estimate`, {
      method: "POST", body: JSON.stringify({ origin_latitude: latitude, origin_longitude: longitude }),
    });
  }

  // Recurring todos are deliberately online-only: they configure server-side
  // schedule rules and must not be replayed as offline todo mutations.
  async getTodoRoutines(): Promise<TodoRoutine[]> {
    return (await this.request<TodoRoutine[]>("/todo-routines")) ?? [];
  }

  async createTodoRoutine(
    data: Omit<TodoRoutine, "id" | "created_at" | "updated_at">,
  ): Promise<TodoRoutine | null> {
    return this.request<TodoRoutine>("/todo-routines", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updateTodoRoutine(
    id: string,
    data: Partial<TodoRoutine>,
  ): Promise<TodoRoutine | null> {
    return this.request<TodoRoutine>(`/todo-routines/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async deleteTodoRoutine(id: string): Promise<boolean> {
    try {
      await this.request(`/todo-routines/${id}`, { method: "DELETE" });
      return true;
    } catch {
      return false;
    }
  }

  // Shopping stays online-first: a meal import is an explicit, account-scoped
  // command and must never be replayed through the legacy todo sync queue.
  async getShoppingList(spaceId?: string): Promise<ShoppingList | null> {
    return this.request<ShoppingList>(`/shopping${spaceId ? `?space_id=${encodeURIComponent(spaceId)}` : ""}`);
  }

  async createShoppingItem(data: Partial<ShoppingItem>, spaceId?: string): Promise<ShoppingItem | null> {
    return this.request<ShoppingItem>(`/shopping/items${spaceId ? `?space_id=${encodeURIComponent(spaceId)}` : ""}`, { method: "POST", body: JSON.stringify(data) });
  }

  async updateShoppingItem(id: string, data: Partial<ShoppingItem>): Promise<ShoppingItem | null> {
    return this.request<ShoppingItem>(`/shopping/items/${id}`, { method: "PUT", body: JSON.stringify(data) });
  }

  async toggleShoppingItem(id: string): Promise<ShoppingItem | null> {
    return this.request<ShoppingItem>(`/shopping/items/${id}/toggle`, { method: "POST" });
  }

  async deleteShoppingItem(id: string): Promise<boolean> {
    return this.requestOk(`/shopping/items/${id}`, { method: "DELETE" });
  }

  async getShoppingMealPreview(from: string, to: string): Promise<ShoppingMealPreview | null> {
    return this.request<ShoppingMealPreview>(`/shopping/meal-preview?from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`);
  }

  async importShoppingMealPlan(from_date: string, to_date: string): Promise<ShoppingList | null> {
    return this.request<ShoppingList>("/shopping/meal-import", { method: "POST", body: JSON.stringify({ from_date, to_date }) });
  }

  // Training
  async getTraining(date: string): Promise<TrainingSuggestion | null> {
    return this.request<TrainingSuggestion>(`/training?date=${date}`);
  }

  async getNextTraining(
    trainingType: string,
    date?: string,
  ): Promise<TrainingSuggestion | null> {
    const params = new URLSearchParams({ training_type: trainingType });
    if (date) params.set("date", date);
    return this.request<TrainingSuggestion>(`/training/next?${params}`);
  }

  async getExerciseProgress(exerciseName: string): Promise<ExerciseProgress[]> {
    return (
      (await this.request<ExerciseProgress[]>(
        `/training/progress?exercise_name=${encodeURIComponent(exerciseName)}&limit=5`,
      )) ?? []
    );
  }

  async completeTraining(data: TrainingCompleteRequest): Promise<any> {
    try {
      return await this.request<any>(`/training/complete`, {
        method: "POST",
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
    return (
      (await this.request<Exercise[]>(
        `/exercises?training_type=${encodeURIComponent(trainingType)}`,
      )) ?? []
    );
  }

  async createExercise(data: Partial<Exercise>): Promise<Exercise | null> {
    return this.request<Exercise>("/exercises", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updateExercise(
    id: string,
    data: Partial<Exercise>,
  ): Promise<Exercise | null> {
    return this.request<Exercise>(`/exercises/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async deleteExercise(id: string): Promise<boolean> {
    const response = await fetch(`${this.baseUrl}/exercises/${id}`, {
      method: "DELETE",
      credentials: "include",
    });
    return response.ok;
  }

  async reorderExercises(
    trainingType: string,
    ids: string[],
  ): Promise<Exercise[]> {
    return (
      (await this.request<Exercise[]>(
        `/exercises/reorder/all?training_type=${encodeURIComponent(trainingType)}`,
        { method: "PUT", body: JSON.stringify(ids) },
      )) ?? []
    );
  }

  async getTrainingUnits(): Promise<TrainingUnit[]> {
    return (await this.request<TrainingUnit[]>("/training-units")) ?? [];
  }

  async createTrainingUnit(
    data: Partial<TrainingUnit>,
  ): Promise<TrainingUnit | null> {
    return this.request<TrainingUnit>("/training-units", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updateTrainingUnit(
    id: string,
    data: Partial<TrainingUnit>,
  ): Promise<TrainingUnit | null> {
    return this.request<TrainingUnit>(`/training-units/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async deleteTrainingUnit(id: string): Promise<boolean> {
    const response = await fetch(`${this.baseUrl}/training-units/${id}`, {
      method: "DELETE",
      credentials: "include",
    });
    return response.ok;
  }

  async getRotation(): Promise<TrainingRotation[]> {
    return (
      (await this.request<TrainingRotation[]>(`/templates/rotation`)) ?? []
    );
  }

  async createRotation(
    data: Partial<TrainingRotation>,
  ): Promise<TrainingRotation | null> {
    return this.request<TrainingRotation>("/templates/rotation", {
      method: "POST",
      body: JSON.stringify({ slot: 0, training_type: "Cardio", ...data }),
    });
  }

  async updateRotation(
    slot: number,
    data: Partial<TrainingRotation>,
  ): Promise<TrainingRotation | null> {
    return this.request<TrainingRotation>(`/templates/rotation/${slot}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async deleteRotation(slot: number): Promise<boolean> {
    const response = await fetch(`${this.baseUrl}/templates/rotation/${slot}`, {
      method: "DELETE",
      credentials: "include",
    });
    return response.ok;
  }

  // Stats
  async getStatsWeek(date: string, rollingDays?: number): Promise<WeekStats | null> {
    const rollingDaysQuery = rollingDays ? `&rolling_days=${rollingDays}` : "";
    return this.request<WeekStats>(`/stats/week?date=${date}${rollingDaysQuery}`);
  }

  async getStatsTrend(metric: string, days: number, endDate?: string): Promise<TrendData | null> {
    const endDateQuery = endDate ? `&end_date=${encodeURIComponent(endDate)}` : "";
    return this.request<TrendData>(
      `/stats/trend?metric=${encodeURIComponent(metric)}&days=${days}${endDateQuery}`,
    );
  }

  // Google Auth
  async getGoogleStatus(): Promise<any | null> {
    return this.request<any>(`/auth/google/status`);
  }

  async applyDevelopmentPreset(): Promise<{ preset: string; days: number; todos: number; foods: number; recipes: number; meal_entries: number } | null> {
    return this.request(`/auth/development-preset`, { method: "POST" });
  }

  // Google Fit sync — fetches steps + sleep details from Google Fit, updates DayEntry in DB
  async syncGoogleFit(date: string): Promise<any> {
    try {
      return await this.request<any>(`/google-fit/sync?date=${date}`, {
        method: "POST",
      });
    } catch (err) {
      if (isNetworkError(err)) return null;
      return null;
    }
  }

  async getScaleMeasurements(
    from?: string,
    to?: string,
  ): Promise<ScaleMeasurement[] | null> {
    const params = new URLSearchParams();
    if (from) params.set("from", from);
    if (to) params.set("to", to);
    return this.request(
      `/scale-measurements${params.size ? `?${params}` : ""}`,
    );
  }

  async removeScaleMeasurement(
    id: string,
  ): Promise<{ id: string; status: "rejected" } | null> {
    return this.request(`/scale-measurements/${id}/reject`, { method: "POST" });
  }

  async getBodyProfile(): Promise<BodyProfile | null> {
    return this.request<BodyProfile>("/account/body-profile");
  }

  async updateBodyProfile(
    profile: Omit<BodyProfile, "id">,
  ): Promise<BodyProfile | null> {
    return this.request<BodyProfile>("/account/body-profile", {
      method: "PUT",
      body: JSON.stringify(profile),
    });
  }

  // Goals
  async getGoals(): Promise<Goals | null> {
    return this.request<Goals>(`/goals`);
  }

  async updateGoals(goals: Partial<Goals>): Promise<Goals | null> {
    return this.request<Goals>(`/goals`, {
      method: "PUT",
      body: JSON.stringify({ goals }),
    });
  }

  // Sync
  async syncChanges(payload: SyncPayload): Promise<SyncResponse | null> {
    return this.request<SyncResponse>(`/sync`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  // Configurable meals v1.  Server derives the account from the session; callers
  // never send an owner identifier.  These calls deliberately do not use the
  // legacy offline queue: v1 mutations require revision-aware conflict handling.
  async getMealCategories(includeInactive = false): Promise<MealCategory[]> {
    const query = includeInactive ? "?include_inactive=true" : "";
    return (
      (await this.request<MealCategory[]>(`/meal-categories${query}`)) ?? []
    );
  }
  async createMealCategory(
    data: Pick<MealCategory, "name"> & Partial<MealCategory>,
  ): Promise<MealCategory | null> {
    return this.request("/meal-categories", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }
  async updateMealCategory(
    id: string,
    data: Partial<MealCategory>,
  ): Promise<MealCategory | null> {
    const { updated_at, id: _id, default_time: _time, ...payload } = data;
    return this.request(`/meal-categories/${id}`, {
      method: "PUT",
      body: JSON.stringify({ ...payload, expected_updated_at: updated_at }),
    });
  }
  async deleteMealCategory(id: string): Promise<boolean> {
    return this.requestOk(`/meal-categories/${id}`, { method: "DELETE" });
  }
  async reorderMealCategories(ids: string[]): Promise<MealCategory[]> {
    return (
      (await this.request("/meal-categories/reorder", {
        method: "PUT",
        body: JSON.stringify({ ids }),
      })) ?? []
    );
  }
  async getMealCategoryRecipePresets(categoryId: string): Promise<Recipe[]> {
    return (
      (await this.request<Recipe[]>(
        `/meal-categories/${categoryId}/recipe-presets`,
      )) ?? []
    );
  }
  async updateMealCategoryRecipePresets(
    categoryId: string,
    recipeIds: string[],
  ): Promise<Recipe[]> {
    return (
      (await this.request<Recipe[]>(
        `/meal-categories/${categoryId}/recipe-presets`,
        { method: "PUT", body: JSON.stringify({ recipe_ids: recipeIds }) },
      )) ?? []
    );
  }
  async getFoods(q?: string): Promise<Food[]> {
    const query = q ? `?q=${encodeURIComponent(q)}` : "";
    return (await this.request<Food[]>(`/foods${query}`)) ?? [];
  }
  async createFood(data: Omit<Food, "id">): Promise<Food | null> {
    return this.request("/foods", {
      method: "POST",
      body: JSON.stringify(foodPayload(data)),
    });
  }
  async updateFood(id: string, data: Partial<Food>): Promise<Food | null> {
    const { updated_at, id: _id, ...rest } = data;
    return this.request(`/foods/${id}`, {
      method: "PUT",
      body: JSON.stringify({
        ...foodPayload(rest),
        expected_updated_at: updated_at,
      }),
    });
  }
  async deleteFood(id: string): Promise<boolean> {
    return this.requestOk(`/foods/${id}`, { method: "DELETE" });
  }
  async getRecipes(): Promise<Recipe[]> {
    return (await this.request<Recipe[]>("/recipes")) ?? [];
  }
  async createRecipe(data: Omit<Recipe, "id">): Promise<Recipe | null> {
    return this.request("/recipes", {
      method: "POST",
      body: JSON.stringify(recipePayload(data)),
    });
  }
  async updateRecipe(
    id: string,
    data: Partial<Recipe>,
  ): Promise<Recipe | null> {
    const { updated_at, id: _id, ...rest } = data;
    return this.request(`/recipes/${id}`, {
      method: "PUT",
      body: JSON.stringify({
        ...recipePayload(rest),
        expected_updated_at: updated_at,
      }),
    });
  }
  async deleteRecipe(id: string): Promise<boolean> {
    return this.requestOk(`/recipes/${id}`, { method: "DELETE" });
  }
  async getMealPlans(): Promise<MealPlan[]> {
    return (await this.request<MealPlan[]>("/meal-plans")) ?? [];
  }
  async createMealPlan(data: Omit<MealPlan, "id">): Promise<MealPlan | null> {
    return this.request("/meal-plans", {
      method: "POST",
      body: JSON.stringify(planPayload(data)),
    });
  }
  async updateMealPlan(
    id: string,
    data: Partial<MealPlan>,
  ): Promise<MealPlan | null> {
    const { updated_at, id: _id, ...rest } = data;
    return this.request(`/meal-plans/${id}`, {
      method: "PUT",
      body: JSON.stringify({
        ...planPayload(rest),
        expected_updated_at: updated_at,
      }),
    });
  }
  async deleteMealPlan(id: string): Promise<boolean> {
    return this.requestOk(`/meal-plans/${id}`, { method: "DELETE" });
  }
  async getMealEntries(from: string, to = from): Promise<MealEntry[]> {
    const params = new URLSearchParams({ from, to });
    return (await this.request<MealEntry[]>(`/meal-entries?${params}`)) ?? [];
  }
  async enrichHistoricalMealNutrients(): Promise<{ updated_item_count: number } | null> {
    return this.request('/meal-entries/enrich-historical-nutrients', { method: 'POST' });
  }
  async instantiateMealEntries(date: string): Promise<MealEntry[]> {
    return (
      (await this.request<MealEntry[]>(
        `/meal-entries/instantiate?date=${encodeURIComponent(date)}`,
        { method: "POST" },
      )) ?? []
    );
  }
  async createMealEntry(
    data: Omit<MealEntry, "id">,
  ): Promise<MealEntry | null> {
    return this.request("/meal-entries", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }
  async updateMealEntry(
    id: string,
    data: Partial<MealEntry>,
  ): Promise<MealEntry | null> {
    return this.request(`/meal-entries/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }
  async setMealEntryStatus(
    id: string,
    status: "planned" | "consumed" | "skipped",
    expectedUpdatedAt?: string,
  ): Promise<MealEntry | null> {
    if (status === "planned") {
      return this.request(`/meal-entries/${id}`, {
        method: "PUT",
        body: JSON.stringify({
          status,
          expected_updated_at: expectedUpdatedAt,
        }),
      });
    }
    return this.request(
      `/meal-entries/${id}/${status === "consumed" ? "consume" : "skip"}`,
      {
        method: "POST",
        body: expectedUpdatedAt
          ? JSON.stringify({ expected_updated_at: expectedUpdatedAt })
          : undefined,
      },
    );
  }
  async deleteMealEntry(id: string): Promise<boolean> {
    return this.requestOk(`/meal-entries/${id}`, { method: "DELETE" });
  }
  async uploadMealEntryPhoto(
    id: string,
    file: File,
  ): Promise<MealPhotoAnalysis | null> {
    const form = new FormData();
    form.append("file", file);
    try {
      const response = await fetch(
        `${this.baseUrl}/meal-entries/${id}/photo-analyses`,
        { method: "POST", body: form, credentials: "include" },
      );
      if (!response.ok) return null;
      return (await response.json()) as MealPhotoAnalysis;
    } catch (err) {
      throw new NetworkError(
        `Network request failed for meal photo ${id}`,
        err,
      );
    }
  }
  async acceptMealEntryPhoto(
    id: string,
    analysisId: string,
    data: {
      name?: string;
      status?: "planned" | "consumed" | "skipped";
      items: Array<{
        food_id?: string;
        recipe_id?: string;
        quantity: number;
        unit: "g" | "ml" | "serving";
      }>;
    },
  ): Promise<MealEntry | null> {
    return this.request(
      `/meal-entries/${id}/photo-analyses/${analysisId}/accept`,
      { method: "POST", body: JSON.stringify(data) },
    );
  }
  async rejectMealEntryPhoto(
    id: string,
    analysisId: string,
  ): Promise<MealPhotoAnalysis | null> {
    return this.request(
      `/meal-entries/${id}/photo-analyses/${analysisId}/reject`,
      { method: "POST" },
    );
  }
}

export const api = new ApiClient();
export { ApiClient };
