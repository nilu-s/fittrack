<script lang="ts">
  import { onDestroy } from 'svelte';
  import Icon from './Icon.svelte';
  import { api } from '$lib/api';
  import type { ExerciseProgress, TrainingCompleteRequest, TrainingSuggestionExercise } from '$lib/types';

  export let training_type: string;
  export let date: string;
  export let oncomplete: (data: { date: string; training_type: string }) => void = () => {};
  export let onclose: () => void = () => {};

  let exercises: TrainingSuggestionExercise[] = [];
  let loading = true;
  let currentIndex = 0;
  let error = '';
  let cardioMinutes: number | null = null;
  let restSeconds = 0;
  let restTimer: ReturnType<typeof setInterval> | undefined;
  let progressHistory: ExerciseProgress[] = [];
  let historyFor = '';
  let selectedExerciseName = '';
  let setsByExercise: Record<string, { reps?: number | null; weight_kg?: number | null; rir?: number | null; set_type?: string }[]> = {};

  $: if (training_type) loadExercises();
  $: selectedExerciseName = exercises[currentIndex]?.exercise_name ?? '';
  $: if (selectedExerciseName && selectedExerciseName !== historyFor) loadHistory(selectedExerciseName);
  async function loadHistory(exerciseName: string) { historyFor = exerciseName; const history = await api.getExerciseProgress(exerciseName).catch(() => []); if (historyFor === exerciseName) progressHistory = history; }
  async function loadExercises() { loading = true; error = ''; try { const plan = await api.getNextTraining(training_type, date); exercises = [...(plan?.exercises ?? [])].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0)); cardioMinutes = plan?.cardio_minutes ?? null; initSets(); } catch { error = 'Übungen konnten nicht geladen werden.'; } finally { loading = false; } }
  function initSets() { setsByExercise = {}; for (const ex of exercises) { const topCount = ex.is_topset ? Math.max(1, ex.top_set_count ?? 1) : 0; const backoffCount = ex.is_topset ? Math.max(0, ex.backoff_set_count ?? 0) : 0; const workCount = ex.is_topset ? 0 : Math.max(1, Number(ex.target_sets) || 1); const topSets = Array.from({ length: topCount }, () => ({ reps: ex.target_reps_low ?? null, weight_kg: ex.target_weight_kg ?? null, rir: ex.target_rir ?? null, set_type: 'top' })); const backoffWeight = ex.target_weight_kg != null && ex.backoff_weight_percent != null ? Math.round(Number(ex.target_weight_kg) * Number(ex.backoff_weight_percent) / 100 * 100) / 100 : ex.target_weight_kg ?? null; const backoffSets = Array.from({ length: backoffCount }, () => ({ reps: ex.backoff_reps_low ?? ex.target_reps_low ?? null, weight_kg: backoffWeight, rir: ex.target_rir ?? null, set_type: 'backoff' })); const workSets = Array.from({ length: workCount }, () => ({ reps: ex.target_reps_low ?? null, weight_kg: ex.target_weight_kg ?? null, rir: ex.target_rir ?? null, set_type: 'work' })); setsByExercise[ex.exercise_name] = [...topSets, ...backoffSets, ...workSets]; } currentIndex = 0; }
  function prev() { currentIndex = (currentIndex - 1 + exercises.length) % exercises.length; }
  function next() { currentIndex = (currentIndex + 1) % exercises.length; }
  type SetType = 'warmup' | 'work' | 'top' | 'backoff' | 'drop';
  function updateSet(exerciseName: string, idx: number, field: 'reps' | 'weight_kg' | 'rir' | 'set_type', value: number | SetType | null) { if (!setsByExercise[exerciseName]) return; setsByExercise[exerciseName][idx] = { ...setsByExercise[exerciseName][idx], [field]: value }; setsByExercise = { ...setsByExercise }; }
  function addSet(exerciseName: string) { const current = setsByExercise[exerciseName] ?? []; const last = current.at(-1); setsByExercise = { ...setsByExercise, [exerciseName]: [...current, { reps: last?.reps ?? null, weight_kg: last?.weight_kg ?? null, rir: last?.rir ?? null, set_type: 'work' }] }; }
  function removeSet(exerciseName: string, idx: number) { const current = setsByExercise[exerciseName] ?? []; if (current.length <= 1) return; setsByExercise = { ...setsByExercise, [exerciseName]: current.filter((_, index) => index !== idx) }; }
  function startRest(seconds: number) { if (restTimer) clearInterval(restTimer); restSeconds = seconds; restTimer = setInterval(() => { restSeconds -= 1; if (restSeconds <= 0) { restSeconds = 0; if (restTimer) clearInterval(restTimer); restTimer = undefined; navigator.vibrate?.([120, 80, 120]); } }, 1000); }
  function formatRest() { return `${Math.floor(restSeconds / 60)}:${String(restSeconds % 60).padStart(2, '0')}`; }
  onDestroy(() => { if (restTimer) clearInterval(restTimer); });
  async function completeTraining() { error = ''; const sets: TrainingCompleteRequest['sets'] = []; for (const ex of exercises) { const exerciseSets = setsByExercise[ex.exercise_name] ?? []; exerciseSets.forEach((set, i) => { sets.push({ exercise_name: ex.exercise_name, set_number: i + 1, set_type: set.set_type || 'work', reps: set.reps ?? null, weight_kg: set.weight_kg ?? null, rir: set.rir ?? null }); }); } try { const res = await api.completeTraining({ date, training_type, sets, cardio_minutes: cardioMinutes }); if (res) oncomplete({ date, training_type }); else error = 'Training konnte nicht gespeichert werden.'; } catch { error = 'Fehler beim Speichern.'; } }
  function formatReps(ex: TrainingSuggestionExercise): string { if (ex.target_reps_low == null && ex.target_reps_high == null) return '—'; if (ex.target_reps_high == null) return String(ex.target_reps_low); return `${ex.target_reps_low ?? ''}–${ex.target_reps_high}`; }
</script>

<div class="td slide-down">
  <div class="td-hdr"><span class="td-title">{training_type}</span><button class="td-close" onclick={onclose} aria-label="Schliessen"><Icon name="x" size={16} /></button></div>
  {#if loading}<div class="td-loading"><div class="spinner"></div><span>Lädt…</span></div>
  {:else if exercises.length === 0 && cardioMinutes == null}<div class="td-empty">Keine Übungen für {training_type}.</div>
  {:else if exercises.length === 0}
    <div class="cardio-card"><div class="ex-name">{training_type}</div><p>Geplant: <strong>{cardioMinutes} Minuten</strong></p><label for="cardio-minutes">Tatsächliche Dauer (Minuten)</label><input id="cardio-minutes" type="number" min="0" bind:value={cardioMinutes} /></div>{#if error}<div class="td-error">{error}</div>{/if}<button class="td-complete" onclick={completeTraining}><Icon name="check" size={16} /> Cardio abschliessen</button>
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
        <div class="tchip"><span class="tchip-l">Sätze</span><span class="tchip-v">{ex.is_topset ? `${ex.top_set_count ?? 1} Top + ${ex.backoff_set_count ?? 0} Back-off` : ex.target_sets}</span></div>
        <div class="tchip"><span class="tchip-l">Reps</span><span class="tchip-v">{formatReps(ex)}</span></div>
        <div class="tchip"><span class="tchip-l">kg</span><span class="tchip-v">{ex.target_weight_kg != null ? ex.target_weight_kg : '—'}</span></div>
        <div class="tchip"><span class="tchip-l">RIR</span><span class="tchip-v">{ex.target_rir ?? '—'}</span></div>
      </div>
      {#if progressHistory[0]}<div class="progress-hint">Zuletzt: {progressHistory[0].topset_weight_kg ?? '—'} kg × {progressHistory[0].topset_reps ?? '—'} · {progressHistory[0].date} · {progressHistory[0].progression_action}</div>{/if}
      <div class="set-hdr"><span>Set</span><span>Typ</span><span>Reps</span><span>kg</span><span>RIR</span><span></span></div>
      {#each sets as set, idx (idx)}<div class="set-row"><span class="set-n">{idx + 1}</span><select aria-label={`Satztyp ${idx + 1}`} value={set.set_type ?? 'work'} onchange={(e) => updateSet(ex.exercise_name, idx, 'set_type', (e.target as HTMLSelectElement).value as SetType)}><option value="warmup">W</option><option value="work">A</option><option value="top">★</option><option value="backoff">B</option><option value="drop">D</option></select><input type="number" placeholder="—" value={set.reps ?? ''} oninput={(e) => updateSet(ex.exercise_name, idx, 'reps', parseFloat((e.target as HTMLInputElement).value) || null)} /><input type="number" placeholder="—" value={set.weight_kg ?? ''} oninput={(e) => updateSet(ex.exercise_name, idx, 'weight_kg', parseFloat((e.target as HTMLInputElement).value) || null)} /><input type="number" placeholder="—" value={set.rir ?? ''} oninput={(e) => updateSet(ex.exercise_name, idx, 'rir', parseFloat((e.target as HTMLInputElement).value) || null)} /><button class="set-remove" onclick={() => removeSet(ex.exercise_name, idx)} disabled={sets.length <= 1} aria-label={`Satz ${idx + 1} entfernen`}>×</button></div>{/each}
      <button class="set-add" onclick={() => addSet(ex.exercise_name)}>+ Satz hinzufügen</button>
      <div class="rest-timer"><span>Pause {restSeconds ? formatRest() : 'bereit'}</span><button onclick={() => startRest(60)}>1 min</button><button onclick={() => startRest(120)}>2 min</button><button onclick={() => startRest(180)}>3 min</button></div>
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
  .ex-card, .cardio-card { background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 12px; margin-bottom: 12px; }
  .cardio-card p { color: var(--text-dim); margin: 8px 0 12px; }
  .cardio-card label { display: block; color: var(--text-dim); font-size: 12px; margin-bottom: 5px; }
  .cardio-card input { box-sizing: border-box; width: 100%; padding: 10px; background: var(--card-2); color: var(--text); border: 1px solid var(--border-2); border-radius: 6px; font-size: 16px; }
  .ex-name { font-size: 15px; font-weight: 600; margin-bottom: 8px; }
  .ex-targets { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
  .tchip { display: flex; flex-direction: column; align-items: center; padding: 4px 8px; border-radius: 6px; background: var(--card-2); min-width: 48px; }
  .tchip-l { font-size: 10px; color: var(--text-faint); text-transform: uppercase; }
  .tchip-v { font-size: 14px; font-weight: 600; }
  .progress-hint { margin: -5px 0 10px; color: var(--text-faint); font-size: 11px; }
  .set-hdr, .set-row { display: grid; grid-template-columns: 24px 42px 1fr 1fr 1fr 28px; gap: 6px; align-items: center; }
  .set-hdr { margin-bottom: 4px; padding-bottom: 4px; border-bottom: 1px solid var(--border); font-size: 10px; color: var(--text-faint); font-weight: 600; text-transform: uppercase; }
  .set-row { margin-bottom: 6px; }
  .set-n { text-align: center; font-size: 13px; color: var(--text-dim); }
  .set-row input, .set-row select { min-width: 0; width: 100%; padding: 8px 4px; border-radius: 6px; background: var(--card-2); border: 1px solid var(--border-2); color: var(--text); font-size: 14px; text-align: center; font-weight: 500; }
  .set-row input:focus, .set-row select:focus { border-color: var(--blue); }
  .set-remove { height: 32px; border: 0; border-radius: 6px; background: transparent; color: var(--red); cursor: pointer; font-size: 18px; }
  .set-remove:disabled { color: var(--text-faint); cursor: not-allowed; }
  .set-add { margin-top: 3px; border: 1px dashed var(--border-2); background: transparent; color: var(--text-dim); border-radius: 6px; padding: 7px; width: 100%; cursor: pointer; font-size: 12px; }
  .rest-timer { display: flex; align-items: center; gap: 6px; margin-top: 10px; color: var(--text-dim); font-size: 12px; }
  .rest-timer span { margin-right: auto; font-variant-numeric: tabular-nums; }
  .rest-timer button { border: 1px solid var(--border-2); border-radius: 5px; background: var(--card-2); color: var(--text-dim); padding: 5px 7px; cursor: pointer; }
  .top-hint { margin-top: 4px; font-size: 11px; color: var(--amber); }
  .td-error { color: var(--red); text-align: center; margin-bottom: 8px; font-size: 14px; }
  .td-complete { width: 100%; padding: 10px 14px; border-radius: 8px; background: var(--green); color: #000; border: none; font-size: 14px; font-weight: 600; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; transition: opacity 0.15s; }
  .td-complete:active { opacity: 0.8; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>