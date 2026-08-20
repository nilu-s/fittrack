<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { api } from '$lib/api';
  import type { Exercise, TrainingCompleteRequest } from '$lib/types';

  export let training_type: string;
  export let date: string;

  const dispatch = createEventDispatcher();

  let expanded = false;
  let exercises: Exercise[] = [];
  let loading = false;
  let currentIndex = 0;
  let error = '';

  // Per-exercise set data: { reps, weight_kg, rir, set_type }
  let setsByExercise: Record<string, { reps?: number | null; weight_kg?: number | null; rir?: number | null; set_type?: string }[]> = {};

  $: open = expanded;
  $: if (open && training_type) {
    loadExercises();
  }

  async function loadExercises() {
    loading = true;
    error = '';
    try {
      const res = await api.getExercises(training_type);
      exercises = (res ?? []).sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
      initSets();
    } catch (e) {
      error = 'Übungen konnten nicht geladen werden.';
    } finally {
      loading = false;
    }
  }

  function initSets() {
    setsByExercise = {};
    for (const ex of exercises) {
      const match = String(ex.target_sets ?? '1').match(/(\d+)/);
      const count = match ? parseInt(match[1], 10) : 1;
      setsByExercise[ex.exercise_name] = Array.from({ length: count }, (_, i) => ({
        reps: ex.target_reps_low ?? null,
        weight_kg: ex.target_weight_kg ?? null,
        rir: ex.target_rir ?? null,
        set_type: ex.is_topset && i === count - 1 ? 'top' : 'work',
      }));
    }
    currentIndex = 0;
  }

  function prev() {
    currentIndex = (currentIndex - 1 + exercises.length) % exercises.length;
  }

  function next() {
    currentIndex = (currentIndex + 1) % exercises.length;
  }

  function updateSet(exerciseName: string, idx: number, field: 'reps' | 'weight_kg' | 'rir', value: number | null) {
    if (!setsByExercise[exerciseName]) return;
    setsByExercise[exerciseName][idx] = { ...setsByExercise[exerciseName][idx], [field]: value };
    setsByExercise = { ...setsByExercise };
  }

  async function completeTraining() {
    error = '';
    const sets: TrainingCompleteRequest['sets'] = [];
    for (const ex of exercises) {
      const exerciseSets = setsByExercise[ex.exercise_name] ?? [];
      exerciseSets.forEach((set, i) => {
        sets.push({
          exercise_name: ex.exercise_name,
          set_number: i + 1,
          set_type: set.set_type || 'work',
          reps: set.reps ?? null,
          weight_kg: set.weight_kg ?? null,
          rir: set.rir ?? null,
        });
      });
    }

    try {
      const res = await api.completeTraining({ date, training_type, sets });
      if (res) {
        dispatch('complete', { date, training_type });
        expanded = false;
      } else {
        error = 'Training konnte nicht gespeichert werden.';
      }
    } catch (e) {
      error = 'Fehler beim Speichern.';
    }
  }

  function toggle() {
    expanded = !expanded;
    if (!expanded) {
      dispatch('close');
    }
  }

  function formatReps(ex: Exercise): string {
    if (ex.target_reps_low == null && ex.target_reps_high == null) return '—';
    if (ex.target_reps_high == null) return String(ex.target_reps_low);
    return `${ex.target_reps_low ?? ''}–${ex.target_reps_high}`;
  }
</script>

{#if open}
  <div class="training-detail slide-down">
    <div class="detail-header">
      <span class="detail-title">{training_type}</span>
      <button class="close-btn" onclick={toggle} aria-label="Schliessen">✕</button>
    </div>

    {#if loading}
      <div class="loading muted text-sm">Lädt Übungen…</div>
    {:else if exercises.length === 0}
      <div class="empty muted text-sm">Keine Übungen für {training_type}.</div>
    {:else}
      {@const ex = exercises[currentIndex]}
      {@const sets = setsByExercise[ex.exercise_name] ?? []}

      <div class="karussell">
        <button class="karussell-btn" onclick={prev} aria-label="Vorherige Übung">◄</button>
        <span class="counter">{currentIndex + 1} / {exercises.length}</span>
        <button class="karussell-btn" onclick={next} aria-label="Nächste Übung">►</button>
      </div>

      <div class="exercise-card">
        <div class="exercise-name">{ex.exercise_name}</div>
        <div class="target-row muted text-sm">
          <span>Sätze: <strong>{ex.target_sets}</strong></span>
          <span>Reps: <strong>{formatReps(ex)}</strong></span>
          <span>Gewicht: <strong>{ex.target_weight_kg != null ? ex.target_weight_kg + ' kg' : '—'}</strong></span>
          <span>RIR: <strong>{ex.target_rir ?? '—'}</strong></span>
        </div>

        <div class="sets-header text-xs muted">
          <span>Set</span>
          <span>Reps</span>
          <span>kg</span>
          <span>RIR</span>
        </div>

        {#each sets as set, idx (idx)}
          <div class="set-row">
            <span class="set-number text-sm muted">{idx + 1}{set.set_type === 'top' ? '*' : ''}</span>
            <input
              class="set-input"
              type="number"
              inputmode="decimal"
              placeholder="Reps"
              value={set.reps ?? ''}
              oninput={(e) => updateSet(ex.exercise_name, idx, 'reps', parseFloat((e.target as HTMLInputElement).value) || null)}
            />
            <input
              class="set-input"
              type="number"
              inputmode="decimal"
              placeholder="kg"
              value={set.weight_kg ?? ''}
              oninput={(e) => updateSet(ex.exercise_name, idx, 'weight_kg', parseFloat((e.target as HTMLInputElement).value) || null)}
            />
            <input
              class="set-input"
              type="number"
              inputmode="decimal"
              placeholder="RIR"
              value={set.rir ?? ''}
              oninput={(e) => updateSet(ex.exercise_name, idx, 'rir', parseFloat((e.target as HTMLInputElement).value) || null)}
            />
          </div>
        {/each}
        {#if ex.is_topset}
          <div class="topset-hint text-xs muted">* Top-Set: letzter Satz mit maximalem Gewicht</div>
        {/if}
      </div>

      {#if error}
        <div class="error text-sm">{error}</div>
      {/if}

      <button class="complete-btn" onclick={completeTraining}>Training abschliessen</button>
    {/if}
  </div>
{/if}

<style>
  .training-detail {
    background: #1f1f1f;
    border: 1px solid var(--card-border);
    border-radius: var(--radius-md);
    margin: 0.5rem 0;
    padding: 0.75rem;
  }

  .detail-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.75rem;
  }

  .detail-title {
    font-size: 0.875rem;
    font-weight: 600;
    color: var(--text-primary);
  }

  .close-btn {
    width: 28px;
    height: 28px;
    border-radius: 6px;
    background: #333;
    border: 1px solid var(--card-border);
    color: var(--text-primary);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.875rem;
  }

  .close-btn:active {
    background: #444;
  }

  .loading,
  .empty {
    padding: 1rem 0;
    text-align: center;
  }

  .karussell {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.75rem;
  }

  .karussell-btn {
    width: 32px;
    height: 32px;
    border-radius: 6px;
    background: #333;
    border: 1px solid var(--card-border);
    color: var(--text-primary);
    cursor: pointer;
    font-size: 0.875rem;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .karussell-btn:active {
    background: #444;
  }

  .counter {
    font-size: 0.8125rem;
    color: var(--text-secondary);
  }

  .exercise-card {
    background: #161616;
    border: 1px solid var(--card-border);
    border-radius: var(--radius-sm);
    padding: 0.625rem;
    margin-bottom: 0.75rem;
  }

  .exercise-name {
    font-size: 0.9375rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
    color: var(--text-primary);
  }

  .target-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }

  .target-row span {
    background: #252525;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
  }

  .sets-header,
  .set-row {
    display: grid;
    grid-template-columns: 30px 1fr 1fr 1fr;
    gap: 0.375rem;
    align-items: center;
  }

  .sets-header {
    margin-bottom: 0.25rem;
    padding-bottom: 0.25rem;
    border-bottom: 1px solid #333;
  }

  .set-row {
    margin-bottom: 0.375rem;
  }

  .set-number {
    text-align: center;
  }

  .set-input {
    width: 100%;
    padding: 0.375rem 0.25rem;
    border-radius: 4px;
    background: #1a1a1a;
    border: 1px solid var(--card-border);
    color: var(--text-primary);
    font-size: 0.8125rem;
    text-align: center;
  }

  .topset-hint {
    margin-top: 0.25rem;
  }

  .error {
    color: #ef4444;
    text-align: center;
    margin-bottom: 0.5rem;
  }

  .complete-btn {
    width: 100%;
    padding: 0.625rem;
    border-radius: var(--radius-sm);
    background: var(--accent-done);
    color: #0f0f0f;
    border: none;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
  }

  .complete-btn:active {
    filter: brightness(1.1);
  }
</style>
