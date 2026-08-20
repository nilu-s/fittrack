<script lang="ts">
  import Icon from './Icon.svelte';
  import { api } from '$lib/api';
  import type { Exercise, TrainingCompleteRequest } from '$lib/types';

  export let training_type: string;
  export let date: string;
  export let oncomplete: (data: { date: string; training_type: string }) => void = () => {};
  export let onclose: () => void = () => {};

  let exercises: Exercise[] = [];
  let loading = true;
  let currentIndex = 0;
  let error = '';
  let setsByExercise: Record<string, { reps?: number | null; weight_kg?: number | null; rir?: number | null; set_type?: string }[]> = {};

  $: if (training_type) loadExercises();
  async function loadExercises() { loading = true; error = ''; try { const res = await api.getExercises(training_type); exercises = (res ?? []).sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0)); initSets(); } catch (e) { error = 'Übungen konnten nicht geladen werden.'; } finally { loading = false; } }
  function initSets() { setsByExercise = {}; for (const ex of exercises) { const match = String(ex.target_sets ?? '1').match(/(\d+)/); const count = match ? parseInt(match[1], 10) : 1; setsByExercise[ex.exercise_name] = Array.from({ length: count }, (_, i) => ({ reps: ex.target_reps_low ?? null, weight_kg: ex.target_weight_kg ?? null, rir: ex.target_rir ?? null, set_type: ex.is_topset && i === count - 1 ? 'top' : 'work' })); } currentIndex = 0; }
  function prev() { currentIndex = (currentIndex - 1 + exercises.length) % exercises.length; }
  function next() { currentIndex = (currentIndex + 1) % exercises.length; }
  function updateSet(exerciseName: string, idx: number, field: 'reps' | 'weight_kg' | 'rir', value: number | null) { if (!setsByExercise[exerciseName]) return; setsByExercise[exerciseName][idx] = { ...setsByExercise[exerciseName][idx], [field]: value }; setsByExercise = { ...setsByExercise }; }
  async function completeTraining() { error = ''; const sets: TrainingCompleteRequest['sets'] = []; for (const ex of exercises) { const exerciseSets = setsByExercise[ex.exercise_name] ?? []; exerciseSets.forEach((set, i) => { sets.push({ exercise_name: ex.exercise_name, set_number: i + 1, set_type: set.set_type || 'work', reps: set.reps ?? null, weight_kg: set.weight_kg ?? null, rir: set.rir ?? null }); }); } try { const res = await api.completeTraining({ date, training_type, sets }); if (res) oncomplete({ date, training_type }); else error = 'Training konnte nicht gespeichert werden.'; } catch (e) { error = 'Fehler beim Speichern.'; } }
  function formatReps(ex: Exercise): string { if (ex.target_reps_low == null && ex.target_reps_high == null) return '—'; if (ex.target_reps_high == null) return String(ex.target_reps_low); return `${ex.target_reps_low ?? ''}–${ex.target_reps_high}`; }
</script>

<div class="td slide-down">
  <div class="td-hdr"><span class="td-title">{training_type}</span><button class="td-close" onclick={onclose} aria-label="Schliessen"><Icon name="x" size={16} /></button></div>
  {#if loading}<div class="td-loading"><div class="spinner"></div><span>Lädt…</span></div>
  {:else if exercises.length === 0}<div class="td-empty">Keine Übungen für {training_type}.</div>
  {:else}
    {@const ex = exercises[currentIndex]}
    {@const sets = setsByExercise[ex.exercise_name] ?? []}
    <div class="carousel">
      <button class="car-btn" onclick={prev} aria-label="Zurück"><Icon name="chevron-left" size={16} /></button>
      <div class="car-mid"><span class="car-count">{currentIndex + 1} / {exercises.length}</span><div class="car-dots">{#each exercises as _, i}<span class="dot" class:active={i === currentIndex}></span>{/each}</div></div>
      <button class="car-btn" onclick={next} aria-label="Weiter"><Icon name="chevron-right" size={16} /></button>
    </div>
    <div class="ex-card">
      <div class="ex-name">{ex.exercise_name}</div>
      <div class="ex-targets">
        <div class="tchip"><span class="tchip-l">Sätze</span><span class="tchip-v">{ex.target_sets}</span></div>
        <div class="tchip"><span class="tchip-l">Reps</span><span class="tchip-v">{formatReps(ex)}</span></div>
        <div class="tchip"><span class="tchip-l">kg</span><span class="tchip-v">{ex.target_weight_kg != null ? ex.target_weight_kg : '—'}</span></div>
        <div class="tchip"><span class="tchip-l">RIR</span><span class="tchip-v">{ex.target_rir ?? '—'}</span></div>
      </div>
      <div class="set-hdr"><span>Set</span><span>Reps</span><span>kg</span><span>RIR</span></div>
      {#each sets as set, idx (idx)}<div class="set-row"><span class="set-n">{idx + 1}{set.set_type === 'top' ? '★' : ''}</span><input type="number" placeholder="—" value={set.reps ?? ''} oninput={(e) => updateSet(ex.exercise_name, idx, 'reps', parseFloat((e.target as HTMLInputElement).value) || null)} /><input type="number" placeholder="—" value={set.weight_kg ?? ''} oninput={(e) => updateSet(ex.exercise_name, idx, 'weight_kg', parseFloat((e.target as HTMLInputElement).value) || null)} /><input type="number" placeholder="—" value={set.rir ?? ''} oninput={(e) => updateSet(ex.exercise_name, idx, 'rir', parseFloat((e.target as HTMLInputElement).value) || null)} /></div>{/each}
      {#if ex.is_topset}<div class="top-hint">★ Top-Set</div>{/if}
    </div>
    {#if error}<div class="td-error">{error}</div>{/if}
    <button class="td-complete" onclick={completeTraining}><Icon name="check" size={16} /> Training abschliessen</button>
  {/if}
</div>

<style>
  .td { background: var(--card-2); border: 1px solid var(--border-2); border-radius: var(--radius); margin: 6px 0; padding: 14px; }
  .td-hdr { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
  .td-title { font-size: 15px; font-weight: 600; }
  .td-close { width: 28px; height: 28px; border-radius: 6px; background: var(--card); border: 1px solid var(--border-2); color: var(--text-dim); cursor: pointer; display: flex; align-items: center; justify-content: center; }
  .td-close:active { background: #26272a; }
  .td-loading, .td-empty { padding: 20px 0; text-align: center; color: var(--text-faint); font-size: 14px; display: flex; flex-direction: column; align-items: center; gap: 8px; }
  .spinner { width: 22px; height: 22px; border-radius: 50%; border: 2.5px solid var(--card); border-top-color: var(--text-dim); animation: spin 0.8s linear infinite; }
  .carousel { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
  .car-btn { width: 32px; height: 32px; border-radius: 6px; background: var(--card); border: 1px solid var(--border-2); color: var(--text-dim); cursor: pointer; display: flex; align-items: center; justify-content: center; }
  .car-btn:active { background: #26272a; }
  .car-mid { display: flex; flex-direction: column; align-items: center; gap: 4px; }
  .car-count { font-size: 13px; color: var(--text-dim); }
  .car-dots { display: flex; gap: 4px; }
  .dot { width: 4px; height: 4px; border-radius: 50%; background: var(--border-2); }
  .dot.active { background: var(--text); width: 14px; border-radius: 2px; }
  .ex-card { background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 12px; margin-bottom: 12px; }
  .ex-name { font-size: 15px; font-weight: 600; margin-bottom: 8px; }
  .ex-targets { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
  .tchip { display: flex; flex-direction: column; align-items: center; padding: 4px 8px; border-radius: 6px; background: var(--card-2); min-width: 48px; }
  .tchip-l { font-size: 10px; color: var(--text-faint); text-transform: uppercase; }
  .tchip-v { font-size: 14px; font-weight: 600; }
  .set-hdr, .set-row { display: grid; grid-template-columns: 28px 1fr 1fr 1fr; gap: 8px; align-items: center; }
  .set-hdr { margin-bottom: 4px; padding-bottom: 4px; border-bottom: 1px solid var(--border); font-size: 11px; color: var(--text-faint); font-weight: 600; text-transform: uppercase; }
  .set-row { margin-bottom: 6px; }
  .set-n { text-align: center; font-size: 13px; color: var(--text-dim); }
  .set-row input { width: 100%; padding: 8px 4px; border-radius: 6px; background: var(--card-2); border: 1px solid var(--border-2); color: var(--text); font-size: 14px; text-align: center; font-weight: 500; }
  .set-row input:focus { border-color: var(--blue); }
  .top-hint { margin-top: 4px; font-size: 11px; color: var(--amber); }
  .td-error { color: var(--red); text-align: center; margin-bottom: 8px; font-size: 14px; }
  .td-complete { width: 100%; padding: 10px 14px; border-radius: 8px; background: var(--green); color: #000; border: none; font-size: 14px; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; transition: opacity 0.15s; }
  .td-complete:active { opacity: 0.8; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>