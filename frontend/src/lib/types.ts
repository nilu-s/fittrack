// FitTrack TypeScript Types — aligned with backend schemas (snake_case)

export interface DayEntry {
  id?: string;
  date: string; // YYYY-MM-DD
  weight_kg?: number | null;
  weight_source?: string | null; // 'scale_esp' | 'manual' | 'google_fit' | null
  bmi?: number | null;
  steps?: number | null;
  steps_done?: boolean;
  steps_confirmed?: boolean;
  steps_source?: string | null; // 'google_fit' | 'manual' | null
  sleep_hours?: number | null;
  sleep_deep_hours?: number | null;
  sleep_rem_hours?: number | null;
  sleep_light_hours?: number | null;
  sleep_awake_hours?: number | null;
  sleep_efficiency?: number | null; // 0-100
  sleep_quality?: number | null; // 0-5 (0 = no data)
  sleep_done?: boolean;
  cardio_minutes?: number | null;
  training_type?: string | null;
  training_done?: boolean;
  rotation_slot?: number | null;
  cardio_done?: boolean;
  creatine_done?: boolean;
  belly_cm?: number | null;
  notes?: string | null;
  updated_at?: string;
}

export interface Meal {
  id?: string;
  date: string; // YYYY-MM-DD
  meal_slot: number;
  name?: string;
  default_time?: string; // HH:MM:SS
  kcal?: number | string | null;
  protein_g?: number | string | null;
  carbs_g?: number | string | null;
  fat_g?: number | string | null;
  fiber_g?: number | string | null;
  sugar_g?: number | string | null;
  free_sugar_g?: number | string | null;
  is_standard?: boolean;
  is_done?: boolean;
  replaced_by?: string | null;
  photo_url?: string | null;
  photo_analysis?: any;
  assigned_via_photo?: boolean;
  deleted?: boolean;
  portion_factor?: number;
  dish_id?: string | null;
  updated_at?: string;
  /** True when this row is backed by the account-scoped MealEntry API. */
  meal_entry?: boolean;
  meal_entry_status?: 'planned' | 'consumed' | 'skipped';
  category_name?: string;
}

export interface Todo {
  id?: string;
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
  deleted?: boolean;
  updated_at?: string;
}

export interface Exercise {
  id?: string;
  training_type: string;
  exercise_name: string;
  target_sets: string;
  base_reps_low?: number | null;
  base_reps_high?: number | null;
  target_reps_low?: number | null;
  target_reps_high?: number | null;
  target_weight_kg?: number | null;
  progression_strategy?: string;
  progression_increment_weight?: number;
  is_topset?: boolean;
  top_set_count?: number;
  backoff_set_count?: number;
  backoff_reps_low?: number | null;
  backoff_reps_high?: number | null;
  backoff_weight_percent?: number | null;
  target_rir?: number | null;
  sort_order?: number;
}

export interface TrainingSet {
  id?: string;
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
  slot: number;
  training_type: string;
  weekday?: number | null;
  frequency_weeks?: number;
  week_offset?: number;
  start_date?: string | null;
}

export interface TrainingUnit {
  id?: string;
  name: string;
  description?: string | null;
  unit_type?: 'gym' | 'cardio' | string;
  cardio_minutes?: number | null;
  is_active?: boolean;
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
  top_set_count?: number;
  backoff_set_count?: number;
  backoff_reps_low?: number | null;
  backoff_reps_high?: number | null;
  backoff_weight_percent?: number | null;
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
  cardio_minutes?: number | null;
}

export interface ExerciseProgress {
  id: string;
  exercise_id: string;
  date: string;
  training_type: string;
  exercise_name: string;
  topset_reps?: number | null;
  topset_weight_kg?: number | null;
  topset_rir?: number | null;
  total_volume_kg?: number | null;
  progression_action: string;
  new_target_weight_kg?: number | null;
  new_target_reps_low?: number | null;
}

export interface TrainingCompleteResponse {
  saved: number;
  progressed_exercises: Exercise[];
  next_training: TrainingSuggestion | null;
}

export interface MealTemplate {
  id?: string;
  slot: number;
  name: string;
  kcal?: number | null;
  protein_g?: number | null;
  carbs_g?: number | null;
  fat_g?: number | null;
  fiber_g?: number | null;
  sugar_g?: number | null;
  free_sugar_g?: number | null;
}

/** Target v1 meal domain.  These types intentionally have no account/user fields. */
export interface MealCategory {
  id: string;
  name: string;
  sort_order: number;
  is_active: boolean;
  default_time?: string | null;
  updated_at?: string;
}

export interface Food {
  id: string;
  name: string;
  /** API values are per 100 g. */
  kcal?: number | null;
  protein_g?: number | null;
  carbs_g?: number | null;
  fat_g?: number | null;
  fiber_g?: number | null;
  sugar_g?: number | null;
  free_sugar_g?: number | null;
  source?: 'manual' | 'photo' | 'import';
  confidence?: 'verified' | 'estimated' | 'unknown';
  is_archived?: boolean;
  tags?: string[];
  updated_at?: string;
}

export interface RecipeIngredient {
  id?: string;
  food_id?: string | null;
  nested_recipe_id?: string | null;
  name?: string;
  quantity: number;
  unit: 'g' | 'ml' | 'serving';
  sort_order?: number;
}

export interface Recipe {
  id: string;
  name: string;
  status: 'draft' | 'active' | 'archived';
  servings: number;
  ingredients: RecipeIngredient[];
  notes?: string | null;
  /** Ordered cooking steps, kept separately from free-form notes. */
  instructions?: string[];
  nutrition?: Nutrition;
  updated_at?: string;
  expected_updated_at?: string;
}

export interface MealPlanItem {
  id?: string;
  category_id: string;
  weekdays?: number[] | null;
  planned_time?: string | null;
  recipe_id?: string | null;
  name?: string | null;
  portion?: number;
  sort_order?: number;
}

export interface MealPlan {
  id: string;
  name: string;
  is_active: boolean;
  version?: number;
  items: MealPlanItem[];
  updated_at?: string;
  expected_updated_at?: string;
}

export interface MealEntry {
  id: string;
  date: string;
  category_id: string;
  status: 'planned' | 'consumed' | 'skipped';
  consumed_at?: string | null;
  name?: string | null;
  source: 'manual' | 'plan' | 'photo';
  nutrition?: Nutrition;
  items?: MealEntryItem[];
  updated_at?: string;
  /** Optimistic-locking value accepted by the update command. */
  expected_updated_at?: string;
}

export interface Nutrition {
  kcal?: number | null;
  protein_g?: number | null;
  carbs_g?: number | null;
  fat_g?: number | null;
  fiber_g?: number | null;
  sugar_g?: number | null;
  free_sugar_g?: number | null;
}

export interface MealEntryItem {
  id?: string;
  food_id?: string | null;
  recipe_id?: string | null;
  quantity: number;
  unit: 'g' | 'ml' | 'serving';
  nutrition_snapshot?: Nutrition;
  source_snapshot?: Record<string, unknown>;
}

/** A photo analysis remains a proposal until the user explicitly applies items. */
export interface MealPhotoAnalysis {
  id: string;
  meal_entry_id: string;
  state: 'pending' | 'accepted' | 'rejected' | 'failed';
  analysis?: Record<string, unknown> | null;
  error_code?: string | null;
  created_at: string;
}

export interface Dish {
  id?: string;
  slot?: number | null;
  name: string;
  kcal?: number | null;
  protein_g?: number | null;
  carbs_g?: number | null;
  fat_g?: number | null;
  fiber_g?: number | null;
  sugar_g?: number | null;
  free_sugar_g?: number | null;
  photo_url?: string | null;
  is_default?: boolean;
  usage_count?: number;
  source?: string;
  portion_label?: string | null;
  portion_grams?: number | null;
  is_scalable?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface DishMatchResult {
  matched: boolean;
  dish?: Dish | null;
  similarity: number;
}

export interface DishRecommendResult {
  default: Dish | null;
  alternatives: Dish[];
}

export interface PhotoAnalysisItem {
  name: string;
  kcal: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g?: number;
  sugar_g?: number;
  free_sugar_g?: number;
  portion_label?: string | null;
  portion_grams?: number | null;
  is_scalable?: boolean;
}

export interface PhotoAnalysis {
  items: PhotoAnalysisItem[];
  total: { kcal: number; protein_g: number; carbs_g: number; fat_g: number; fiber_g?: number; sugar_g?: number; free_sugar_g?: number };
}

export interface PhotoAnalysisResponse {
  photo_id: string;
  file_path: string;
  analysis: PhotoAnalysis | null;
  error: string | null;
  dish_match: DishMatchResult | null;
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
  avg_protein?: number | null;
  avg_carbs?: number | null;
  avg_fat?: number | null;
  avg_fiber?: number | null;
  avg_sugar?: number | null;
  avg_free_sugar?: number | null;
  avg_sleep_hours?: number | null;
  avg_sleep_quality?: number | null;
  total_cardio_minutes?: number | null;
  creatine_compliance?: number | null;
  training_days: number;
  training_completion: number;
  training_streak?: number | null;
  step_goal_streak?: number | null;
  todo_total: number;
  todo_done: number;
  todo_completion: number;
  goals?: Goals | null;
}

export interface Goals {
  kcal?: number | null;
  protein?: number | null;
  carbs?: number | null;
  fat?: number | null;
  fiber_g?: number | null;
  free_sugar_g?: number | null;
  free_sugar_limit_g?: number | null;
  steps?: number | null;
  sleep_hours?: number | null;
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
  nextTraining: TrainingSuggestion | null;
  weekStats?: WeekStats | null;
}
