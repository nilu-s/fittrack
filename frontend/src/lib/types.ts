// FitTrack TypeScript Types

export interface DayEntry {
  id?: number;
  date: string; // YYYY-MM-DD
  weight?: number | null;
  weight_done?: boolean;
  steps?: number | null;
  steps_done?: boolean;
  sleep_hours?: number | null;
  sleep_done?: boolean;
  cardio_minutes?: number | null;
  cardio_done?: boolean;
  training_type?: string | null;
  training_done?: boolean;
  creatine?: boolean;
  belly_circumference?: number | null;
  rotation_slot?: number;
  notes?: string;
  updated_at?: string;
}

export interface Meal {
  id?: string;
  user_id?: string;
  date: string; // YYYY-MM-DD
  meal_slot: number; // 1=breakfast, 2=lunch, 3=dinner, 4=snack
  name?: string;
  default_time?: string; // HH:MM:SS
  kcal?: string | number;
  protein_g?: string | number;
  carbs_g?: string | number;
  fat_g?: string | number;
  is_standard?: boolean;
  is_done?: boolean;
  photo_url?: string | null;
  updated_at?: string;
}

export interface Todo {
  id?: number;
  date: string; // YYYY-MM-DD
  title: string;
  description?: string;
  status: 'open' | 'done';
  priority: number; // 1=low, 2=medium, 3=high
  category?: string;
  due_date?: string | null;
  due_time?: string | null;
  source?: string; // manual, google_calendar
  external_id?: string | null;
  sort_order?: number;
  created_at?: string;
  updated_at?: string;
}

export interface Exercise {
  id?: number;
  training_type: string;
  exercise_name: string;
  description?: string;
  default_sets?: number;
  default_reps?: number;
  default_weight?: number;
}

export interface TrainingSet {
  id?: number;
  date: string;
  training_type: string;
  exercise_name: string;
  set_number: number;
  reps?: number;
  weight?: number;
  completed: boolean;
  updated_at?: string;
}

export interface TrainingRotation {
  id?: number;
  slot: number;
  training_type: string;
  description?: string;
}

export interface MealTemplate {
  id?: number;
  slot: string;
  name: string;
  default_kcal?: number;
  default_protein?: number;
  default_carbs?: number;
  default_fat?: number;
  default_time?: string;
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
  date: string;
  weight_avg?: number;
  weight_trend?: number[];
  kcal_avg?: number;
  kcal_trend?: number[];
  steps_avg?: number;
  steps_trend?: number[];
  sleep_avg?: number;
  training_completed?: number;
  training_total?: number;
  todo_open?: number;
  todo_done?: number;
  todo_completion_rate?: number;
}

export interface TrendData {
  metric: string;
  days: number;
  values: { date: string; value: number | null }[];
}

export interface SyncPayload {
  changes: SyncQueueEntry[];
  lastSync: number;
}

export interface SyncResponse {
  success: boolean;
  conflicts?: any[];
  merged?: any;
  serverTime?: number;
}

export interface DayData {
  dayEntry: DayEntry | null;
  meals: Meal[];
  todos: Todo[];
  training: TrainingSet[];
  nextTraining: TrainingRotation | null;
  weekStats?: WeekStats | null;
}