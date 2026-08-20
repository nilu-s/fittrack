// FitTrack TypeScript Types — aligned with backend schemas (snake_case)

export interface DayEntry {
  id?: string;
  user_id?: string;
  date: string; // YYYY-MM-DD
  weight_kg?: number | null;
  steps?: number | null;
  steps_done?: boolean;
  sleep_hours?: number | null;
  sleep_done?: boolean;
  cardio_minutes?: number | null;
  training_type?: string | null;
  training_done?: boolean;
  rotation_slot?: number | null;
  creatine_done?: boolean;
  belly_cm?: number | null;
  notes?: string | null;
  updated_at?: string;
}

export interface Meal {
  id?: string;
  user_id?: string;
  date: string; // YYYY-MM-DD
  meal_slot: number;
  name?: string;
  default_time?: string; // HH:MM:SS
  kcal?: number | string | null;
  protein_g?: number | string | null;
  carbs_g?: number | string | null;
  fat_g?: number | string | null;
  is_standard?: boolean;
  is_done?: boolean;
  replaced_by?: string | null;
  photo_url?: string | null;
  photo_analysis?: any;
  assigned_via_photo?: boolean;
  updated_at?: string;
}

export interface Todo {
  id?: string;
  user_id?: string;
  title: string;
  category?: string | null;
  priority: number; // 1=low, 2=medium, 3=high
  status: 'open' | 'done';
  due_date?: string | null;
  due_time?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  is_all_day?: boolean;
  source?: string;
  external_id?: string | null;
  sort_order?: number;
  completed_at?: string | null;
  updated_at?: string;
}

export interface Exercise {
  id?: string;
  user_id?: string;
  training_type: string;
  exercise_name: string;
  target_sets: string;
  target_reps_low?: number | null;
  target_reps_high?: number | null;
  target_weight_kg?: number | null;
  progression_strategy?: string;
  progression_increment_weight?: number;
  is_topset?: boolean;
  target_rir?: number | null;
  sort_order?: number;
}

export interface TrainingSet {
  id?: string;
  user_id?: string;
  date: string;
  training_type: string;
  exercise_name: string;
  set_number: number;
  set_type?: string;
  reps?: number | null;
  weight_kg?: number | null;
  rir?: number | null;
  completed?: boolean;
  updated_at?: string;
}

export interface TrainingRotation {
  id?: string;
  user_id?: string;
  slot: number;
  training_type: string;
  cardio_minutes?: number | null;
}

export interface TrainingSuggestion {
  date: string;
  training_type: string;
  rotation_slot?: number | null;
  cardio_minutes?: number | null;
  exercises: TrainingSuggestionExercise[];
}

export interface TrainingSuggestionExercise {
  exercise_name: string;
  target_sets: string;
  target_reps_low?: number | null;
  target_reps_high?: number | null;
  target_weight_kg?: number | null;
  is_topset?: boolean;
  target_rir?: number | null;
  sort_order?: number;
}

export interface TrainingCompleteRequest {
  date: string;
  training_type: string;
  sets: {
    exercise_name: string;
    set_number: number;
    set_type?: string;
    reps?: number | null;
    weight_kg?: number | null;
    rir?: number | null;
  }[];
}

export interface TrainingCompleteResponse {
  saved: number;
  progressed_exercises: Exercise[];
  next_training: TrainingSuggestion | null;
}

export interface MealTemplate {
  id?: string;
  user_id?: string;
  slot: number;
  name: string;
  kcal?: number | null;
  protein_g?: number | null;
  carbs_g?: number | null;
  fat_g?: number | null;
}

export interface SyncQueueEntry {
  id?: number;
  entityType: string;
  entityLocalId: number;
  action: 'create' | 'update' | 'delete';
  clientTimestamp: number;
  synced: boolean;
}

export interface WeekStats {
  week_start: string;
  week_end: string;
  avg_weight?: number | null;
  avg_kcal?: number | null;
  avg_steps?: number | null;
  training_days: number;
  training_completion: number;
  todo_total: number;
  todo_done: number;
  todo_completion: number;
}

export interface TrendPoint {
  date: string;
  value: number | null;
}

export interface TrendData {
  metric: string;
  points: TrendPoint[];
}

export interface SyncChangeItem {
  entity_type: string;
  entity_id: string;
  action: string;
  payload: Record<string, any>;
  client_timestamp: number;
}

export interface SyncPayload {
  changes: SyncChangeItem[];
  lastSync: number;
}

export interface SyncResponse {
  server_changes: any[];
  conflicts: any[];
  sync_token: string;
}

export interface DayData {
  dayEntry: DayEntry | null;
  meals: Meal[];
  todos: Todo[];
  trainingSuggestion: TrainingSuggestion | null;
  nextTraining: TrainingRotation | null;
  weekStats?: WeekStats | null;
}