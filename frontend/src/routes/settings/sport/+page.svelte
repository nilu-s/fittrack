<script lang="ts">
  import { onMount } from 'svelte';
  import SettingsHeader from '$lib/components/SettingsHeader.svelte';
  import Icon from '$lib/components/Icon.svelte';
  import { api } from '$lib/api';
  import type { Exercise, TrainingRotation, TrainingUnit } from '$lib/types';

  type RotationDraft = { training_type: string; weekday: string; frequency_weeks: string; week_offset: string; start_date: string };
  type ExerciseDraft = { exercise_name: string; target_sets: string; target_reps_low: string; target_reps_high: string; progression_strategy: string; progression_increment_weight: string; target_rir: string };
  const WEEKDAYS = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag'];
  let rotation: TrainingRotation[] = [];
  let units: TrainingUnit[] = [];
  let exercises: Record<string, Exercise[]> = {};
  let selectedUnitName = '';
  let showAdvanced: Record<string, boolean> = {};
  let newUnitName = '';
  let newUnitType: 'gym' | 'cardio' = 'gym';
  let newUnitCardioMinutes = '';
  let unitError = '';
  let newExercises: Record<string, ExerciseDraft> = {};
  let savingExercise = '';
  let unitLoading = true;
  let drafts: Record<number, RotationDraft> = {};
  let loading = true;
  let saving: number | null = null;
  let savedSlot: number | null = null;
  let error = '';
  let selectedSlot: TrainingRotation | null = null;
  let modalDraft: RotationDraft | null = null;
  let addingPlanner = false;

  function makeDraft(entry: TrainingRotation): RotationDraft { return { training_type: entry.training_type, weekday: entry.weekday == null ? '' : String(entry.weekday), frequency_weeks: String(entry.frequency_weeks ?? 1), week_offset: String(entry.week_offset ?? 0), start_date: entry.start_date ?? '' }; }
  function isCardioUnit(unit: TrainingUnit): boolean {
    const text = `${unit.name} ${unit.description ?? ''}`.toLowerCase();
    return unit.unit_type?.toLowerCase() === 'cardio' || /cardio|laufen|spaziergang|rad|bike|run/.test(text);
  }
  function blankExercise(): ExerciseDraft { return { exercise_name: '', target_sets: '3', target_reps_low: '8', target_reps_high: '12', progression_strategy: 'double_progression', progression_increment_weight: '2.5', target_rir: '2' }; }
  function setCount(targetSets?: string): number {
    const text = String(targetSets ?? '').trim();
    const parts = [...text.matchAll(/(\d+)\s*[×x]/gi)].map((match) => Number(match[1]));
    return parts.length ? parts.reduce((sum, count) => sum + count, 0) : Math.max(1, Number(text) || 1);
  }
  function updateSetCount(exercise: Exercise, value: string): void {
    exercise.target_sets = String(Math.max(1, Math.min(99, Number(value) || 1)));
  }
  function progressionSummary(strategy?: string, increment?: number | string | null): string {
    if (strategy === 'weight_increase') return `Bei Ziel: +${increment ?? 2.5} kg`;
    if (strategy === 'reps_only') return 'Erst Wiederholungen steigern';
    return `Erst Wiederholungen, dann +${increment ?? 2.5} kg`;
  }
  async function loadUnits() {
    unitLoading = true;
    units = await api.getTrainingUnits();
    const loaded = await Promise.all(units.map(async (unit) => [unit.name, await api.getExercises(unit.name)] as const));
    exercises = Object.fromEntries(loaded);
    newExercises = Object.fromEntries(units.map((unit) => [unit.name, blankExercise()]));
    selectedUnitName = selectedUnitName && units.some((unit) => unit.name === selectedUnitName) ? selectedUnitName : (units[0]?.name ?? '');
    unitLoading = false;
  }
  function selectUnit(name: string): void {
    selectedUnitName = selectedUnitName === name ? '' : name;
  }
  function toggleAdvanced(exercise: Exercise): void {
    if (!exercise.id) return;
    showAdvanced = { ...showAdvanced, [exercise.id]: !showAdvanced[exercise.id] };
  }
  async function addUnit() {
    const name = newUnitName.trim(); if (!name) return;
    unitError = '';
    const unit = await api.createTrainingUnit({ name, description: newUnitType === 'cardio' ? 'Cardio-Trainingseinheit' : 'Gym-Trainingseinheit', unit_type: newUnitType, cardio_minutes: newUnitType === 'cardio' && newUnitCardioMinutes.trim() ? Math.max(0, Number(newUnitCardioMinutes)) : null });
    if (!unit) { unitError = 'Trainingseinheit konnte nicht erstellt werden.'; return; }
    newUnitName = ''; newUnitCardioMinutes = ''; units = [...units, unit]; exercises = { ...exercises, [unit.name]: [] }; newExercises = { ...newExercises, [unit.name]: blankExercise() }; selectedUnitName = unit.name;
  }
  async function saveUnit(unit: TrainingUnit) {
    if (!unit.id) return;
    const updated = await api.updateTrainingUnit(unit.id, { unit_type: unit.unit_type === 'cardio' ? 'cardio' : 'gym', cardio_minutes: unit.unit_type === 'cardio' && unit.cardio_minutes != null ? Math.max(0, Number(unit.cardio_minutes)) : null });
    if (updated) units = units.map((item) => item.id === updated.id ? updated : item);
  }
  async function addExercise(unitName: string) {
    const draft = newExercises[unitName]; if (!draft?.exercise_name.trim()) return;
    savingExercise = `${unitName}:new`;
    const created = await api.createExercise({ training_type: unitName, exercise_name: draft.exercise_name.trim(), target_sets: draft.target_sets, target_reps_low: Number(draft.target_reps_low), target_reps_high: Number(draft.target_reps_high), base_reps_low: Number(draft.target_reps_low), base_reps_high: Number(draft.target_reps_high), progression_strategy: draft.progression_strategy, progression_increment_weight: Number(draft.progression_increment_weight), target_rir: Number(draft.target_rir), sort_order: (exercises[unitName]?.length ?? 0) });
    if (created) { exercises = { ...exercises, [unitName]: [...(exercises[unitName] ?? []), created] }; newExercises = { ...newExercises, [unitName]: blankExercise() }; }
    savingExercise = '';
  }
  function exercisePlanError(exercise: Exercise): string | null {
    const low = Number(exercise.target_reps_low); const high = Number(exercise.target_reps_high);
    if (!Number.isInteger(low) || !Number.isInteger(high) || low < 1 || high < low) return 'Wiederholungen müssen einen gültigen Bereich bilden.';
    if (!exercise.is_topset) return null;
    const top = Number(exercise.top_set_count ?? 0); const backoff = Number(exercise.backoff_set_count ?? 0);
    if (!Number.isInteger(top) || top < 1 || !Number.isInteger(backoff) || backoff < 0) return 'Top- und Back-off-Sätze müssen gültige ganze Zahlen sein.';
    if (backoff > 0 && (!exercise.backoff_reps_low || !exercise.backoff_reps_high || Number(exercise.backoff_reps_low) > Number(exercise.backoff_reps_high) || Number(exercise.backoff_weight_percent) < 50 || Number(exercise.backoff_weight_percent) > 99)) return 'Back-off benötigt einen gültigen Wiederholungsbereich und 50–99 % Gewicht.';
    return null;
  }
  function toggleTopset(exercise: Exercise, enabled: boolean): void {
    exercise.is_topset = enabled;
    if (enabled) { exercise.top_set_count = exercise.top_set_count || 1; exercise.backoff_set_count = exercise.backoff_set_count || Math.max(0, setCount(exercise.target_sets) - 1); exercise.backoff_reps_low ??= exercise.target_reps_low; exercise.backoff_reps_high ??= exercise.target_reps_high; exercise.backoff_weight_percent ??= 90; }
    else { exercise.top_set_count = 0; exercise.backoff_set_count = 0; exercise.backoff_reps_low = null; exercise.backoff_reps_high = null; exercise.backoff_weight_percent = null; }
    exercises = { ...exercises };
  }
  async function saveExercise(exercise: Exercise) {
    if (!exercise.id) return;
    const validationError = exercisePlanError(exercise);
    if (validationError) { error = validationError; return; }
    error = '';
    savingExercise = exercise.id;
    if (exercise.is_topset) exercise.target_sets = String((exercise.top_set_count ?? 1) + (exercise.backoff_set_count ?? 0));
    const updated = await api.updateExercise(exercise.id, { exercise_name: exercise.exercise_name, target_sets: exercise.target_sets, target_reps_low: exercise.target_reps_low, target_reps_high: exercise.target_reps_high, progression_strategy: exercise.progression_strategy, progression_increment_weight: exercise.progression_increment_weight, is_topset: exercise.is_topset, top_set_count: exercise.is_topset ? exercise.top_set_count ?? 1 : 0, backoff_set_count: exercise.is_topset ? exercise.backoff_set_count ?? 0 : 0, backoff_reps_low: exercise.is_topset ? exercise.backoff_reps_low : null, backoff_reps_high: exercise.is_topset ? exercise.backoff_reps_high : null, backoff_weight_percent: exercise.is_topset ? exercise.backoff_weight_percent : null, target_rir: exercise.target_rir });
    if (updated) exercises = { ...exercises, [updated.training_type]: (exercises[updated.training_type] ?? []).map((item) => item.id === updated.id ? updated : item) };
    savingExercise = '';
  }
  async function removeExercise(unitName: string, exercise: Exercise) {
    if (!exercise.id || !confirm(`„${exercise.exercise_name}“ wirklich entfernen?`)) return;
    if (await api.deleteExercise(exercise.id)) exercises = { ...exercises, [unitName]: (exercises[unitName] ?? []).filter((item) => item.id !== exercise.id) };
  }
  async function moveExercise(unitName: string, index: number, delta: number) {
    const current = [...(exercises[unitName] ?? [])]; const target = index + delta;
    if (target < 0 || target >= current.length) return;
    [current[index], current[target]] = [current[target], current[index]];
    const ordered = await api.reorderExercises(unitName, current.map((item) => item.id!).filter(Boolean));
    if (ordered.length) exercises = { ...exercises, [unitName]: ordered };
  }
  async function archiveUnit(unit: TrainingUnit) {
    if (!unit.id || !confirm(`„${unit.name}“ archivieren? Die Planung wird entfernt, Historie bleibt erhalten.`)) return;
    if (await api.deleteTrainingUnit(unit.id)) { units = units.map((item) => item.id === unit.id ? { ...item, is_active: false } : item); if (selectedUnitName === unit.name) selectedUnitName = ''; await loadRotation(); }
  }
  async function loadRotation() {
    loading = true; error = '';
    try {
      rotation = await api.getRotation();
      drafts = Object.fromEntries(rotation.map((entry) => [entry.slot, makeDraft(entry)]));
    } catch { error = 'Sportprogramm konnte nicht geladen werden.'; }
    finally { loading = false; }
  }
  function entriesForDay(day: number): TrainingRotation[] { return rotation.filter((entry) => entry.weekday === day); }
  function openPlanner(entry: TrainingRotation, day?: number) { selectedSlot = entry; modalDraft = { ...makeDraft(entry), weekday: day == null ? makeDraft(entry).weekday : String(day) }; }
  async function openNewPlanner(day: number) {
    if (addingPlanner) return;
    addingPlanner = true; error = '';
    const created = await api.createRotation({ training_type: units[0]?.name ?? 'Cardio', weekday: day, frequency_weeks: 1, start_date: null });
    if (created) {
      await loadRotation();
      const fresh = rotation.find((item) => item.slot === created.slot) ?? created;
      openPlanner(fresh, day);
    } else error = 'Neue Einheit konnte nicht angelegt werden.';
    addingPlanner = false;
  }
  function firstPlannedDate(draft: RotationDraft): string {
    if (!draft.start_date || draft.weekday === '') return 'Wochentag und Datum auswählen';
    const start = new Date(`${draft.start_date}T12:00:00`);
    const target = Number(draft.weekday);
    const currentWeekday = (start.getDay() + 6) % 7;
    const delta = (target - currentWeekday + 7) % 7;
    start.setDate(start.getDate() + delta);
    return start.toLocaleDateString('de-DE', { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric' });
  }
  async function savePlanner() {
    if (!selectedSlot || !modalDraft) return;
    saving = selectedSlot.slot; error = '';
    const frequency_weeks = Math.max(1, Math.min(52, Number(modalDraft.frequency_weeks) || 1));
    const week_offset = Math.max(0, Math.min(51, Number(modalDraft.week_offset) || 0));
    const result = await api.updateRotation(selectedSlot.slot, { training_type: modalDraft.training_type.trim() || selectedSlot.training_type, weekday: modalDraft.weekday === '' ? null : Number(modalDraft.weekday), frequency_weeks, week_offset, start_date: modalDraft.start_date || null });
    if (result) {
      await loadRotation();
      selectedSlot = null;
      modalDraft = null;
    } else error = `Slot ${selectedSlot.slot} konnte nicht gespeichert werden.`;
    saving = null;
  }
  async function removePlanner() { if (!selectedSlot || !confirm('Geplante Einheit wirklich entfernen?')) return; if (await api.deleteRotation(selectedSlot.slot)) { await loadRotation(); closePlanner(); } }
  function closePlanner() { selectedSlot = null; modalDraft = null; }
  onMount(() => { loadUnits(); loadRotation(); });
</script>

<svelte:head><title>FitTrack - Sportprogramm</title></svelte:head>
<div class="page">
  <SettingsHeader title="Sportprogramm" subtitle="Gym und Cardio eigenständig steuern" />
  <section class="intro"><div class="intro-icon"><Icon name="training" size={24} /></div><div><strong>Dein Trainingsprogramm</strong><p>Lege wiederverwendbare Gym- und Cardio-Einheiten an, plane sie in der Woche und führe sie am Trainingstag aus.</p></div></section>

  <section class="section-card"><div class="section-header"><span>Trainingseinheiten</span><span class="muted">Vorlagen für Planung und Durchführung</span></div><div class="body">
    <div class="section-intro"><strong>Einheit erstellen</strong><span>Lege zuerst eine wiederverwendbare Gym- oder Cardio-Einheit an.</span></div>
    <div class="add-unit"><input aria-label="Name der neuen Trainingseinheit" placeholder="Name, z. B. Push A" bind:value={newUnitName} onkeydown={(event) => event.key === 'Enter' && addUnit()} /><select bind:value={newUnitType} aria-label="Typ der neuen Trainingseinheit"><option value="gym">Gym</option><option value="cardio">Cardio</option></select>{#if newUnitType === 'cardio'}<input class="cardio-input" type="number" min="0" aria-label="Cardio-Ziel in Minuten" placeholder="Ziel-Minuten" bind:value={newUnitCardioMinutes} />{/if}<button class="primary" onclick={addUnit}>+ Einheit erstellen</button></div>
    {#if unitError}<div class="error">{unitError}</div>{/if}
    {#if unitLoading}<div class="empty">Lade Trainingseinheiten…</div>
    {:else if units.filter((unit) => unit.is_active !== false).length === 0}<div class="empty">Noch keine Trainingseinheiten angelegt.</div>
    {:else}
      <div class="unit-overview">
        {#each units.filter((unit) => unit.is_active !== false) as unit (unit.id)}
          <button class="unit-summary" class:selected={selectedUnitName === unit.name} onclick={() => selectUnit(unit.name)}>
            <span class="unit-summary-main"><strong>{unit.name}</strong><small>{isCardioUnit(unit) ? `Cardio · ${unit.cardio_minutes ? `${unit.cardio_minutes} Minuten Ziel` : 'Ziel noch offen'}` : `Gym · ${exercises[unit.name]?.length ?? 0} Übungen`}</small></span>
            <span class="unit-summary-action">{selectedUnitName === unit.name ? 'Schließen' : 'Bearbeiten'} ›</span>
          </button>
        {/each}
      </div>
      {#each units.filter((item) => item.is_active !== false && item.name === selectedUnitName) as unit (unit.id)}
        <div class="unit-editor">
          <div class="editor-heading"><div><strong>{unit.name}</strong><small>{isCardioUnit(unit) ? 'Cardio-Ziel' : 'Übungsplan'}</small></div><button class="secondary" onclick={() => saveUnit(unit)}>Einheit speichern</button></div>
          <div class="unit-settings"><label>Typ<select bind:value={unit.unit_type}><option value="gym">Gym</option><option value="cardio">Cardio</option></select></label>{#if isCardioUnit(unit)}<label>Ziel-Dauer<input type="number" min="0" aria-label="Cardio-Ziel in Minuten" bind:value={unit.cardio_minutes} /></label>{/if}<button class="secondary danger" onclick={() => archiveUnit(unit)}>Archivieren</button></div>
          {#if !isCardioUnit(unit)}
            <div class="exercise-list">
              {#each exercises[unit.name] ?? [] as exercise, exerciseIndex (exercise.id)}
                <div class="exercise-row">
                  <div class="exercise-main-fields">
                    <label class="exercise-title">Übung<input class="exercise-name" bind:value={exercise.exercise_name} /></label>
                    <label>Sätze<input type="number" min="1" max="20" value={setCount(exercise.target_sets)} oninput={(event) => updateSetCount(exercise, (event.target as HTMLInputElement).value)} /></label>
                    <label>Wiederholungen ab<input type="number" min="1" bind:value={exercise.target_reps_low} /></label>
                    <label>Wiederholungen bis<input type="number" min="1" bind:value={exercise.target_reps_high} /></label>
                    <label>RIR-Ziel<input type="number" min="0" max="5" bind:value={exercise.target_rir} /></label>
                  </div>
                  <div class="exercise-toolbar"><button class="text-button" onclick={() => toggleAdvanced(exercise)}>{showAdvanced[exercise.id!] ? 'Weniger Einstellungen' : 'Weitere Einstellungen'}</button><div class="exercise-actions"><button class="save" onclick={() => moveExercise(unit.name, exerciseIndex, -1)} aria-label="Übung nach oben">↑</button><button class="save" onclick={() => moveExercise(unit.name, exerciseIndex, 1)} aria-label="Übung nach unten">↓</button><button class="save" onclick={() => saveExercise(exercise)} disabled={savingExercise === exercise.id} aria-label="Übung speichern">{savingExercise === exercise.id ? '…' : '✓'}</button><button class="save danger" onclick={() => removeExercise(unit.name, exercise)} aria-label="Übung entfernen">×</button></div></div>
                  {#if showAdvanced[exercise.id!]}
                    <div class="advanced-fields"><label>Progression<select bind:value={exercise.progression_strategy}><option value="double_progression">Erst Wiederholungen, dann Gewicht</option><option value="weight_increase">Gewicht direkt steigern</option><option value="reps_only">Nur Wiederholungen steigern</option></select></label><label>Gewichtsschritt<input type="number" step="0.25" min="0" bind:value={exercise.progression_increment_weight} /></label><span class="progression-explanation">{progressionSummary(exercise.progression_strategy, exercise.progression_increment_weight)}</span><label class="topset-toggle"><input type="checkbox" checked={exercise.is_topset} onchange={(event) => toggleTopset(exercise, (event.target as HTMLInputElement).checked)} /> Top-Satz mit Back-off-Sätzen</label>{#if exercise.is_topset}<div class="backoff-fields"><div class="locked-field"><strong>1 Top-Satz</strong><small>steuert die Progression</small></div><label>Back-off-Sätze<select bind:value={exercise.backoff_set_count}>{#each [0, 1, 2, 3, 4, 5] as count}<option value={count}>{count}</option>{/each}</select></label><label>Back-off-Wiederholungen ab<input type="number" min="1" bind:value={exercise.backoff_reps_low} /></label><label>Back-off-Wiederholungen bis<input type="number" min="1" bind:value={exercise.backoff_reps_high} /></label><label>Back-off-Gewicht in %<input type="number" min="50" max="99" bind:value={exercise.backoff_weight_percent} /></label></div>{/if}<span class="advanced-hint">{progressionSummary(exercise.progression_strategy, exercise.progression_increment_weight)}. RIR beschreibt, wie viele Wiederholungen noch möglich gewesen wären.</span></div>
                  {/if}
                </div>
              {/each}
              <div class="exercise-add"><label class="exercise-title">Neue Übung<input class="exercise-name" placeholder="z. B. Bankdrücken" bind:value={newExercises[unit.name].exercise_name} /></label><label>Sätze<input type="number" min="1" max="20" bind:value={newExercises[unit.name].target_sets} /></label><label>Wiederholungen ab<input type="number" min="1" bind:value={newExercises[unit.name].target_reps_low} /></label><label>Wiederholungen bis<input type="number" min="1" bind:value={newExercises[unit.name].target_reps_high} /></label><label>RIR-Ziel<input type="number" min="0" max="5" bind:value={newExercises[unit.name].target_rir} /></label><label>Progression<select bind:value={newExercises[unit.name].progression_strategy}><option value="double_progression">Wiederholungen, dann Gewicht</option><option value="weight_increase">Gewicht direkt steigern</option><option value="reps_only">Nur Wiederholungen steigern</option></select></label><button class="primary" onclick={() => addExercise(unit.name)} disabled={savingExercise === `${unit.name}:new`}>+ Übung hinzufügen</button></div>
              <p class="hint">Die Grundwerte definieren das Ziel. Weitere Einstellungen sind nur nötig, wenn du Progression oder Top-/Back-off-Sätze individuell steuern möchtest.</p>
            </div>
          {:else}
            <div class="cardio-info"><strong>Cardio flexibel durchführen</strong><span>Die Dauer ist ein Mindestziel. Sportart und tatsächliche Dauer wählst du am Trainingstag.</span></div>
          {/if}
        </div>
      {/each}
    {/if}
  </div></section>

  <section class="section-card"><div class="section-header"><span>Wochenplanung</span><span class="muted">Einheit einem Tag zuweisen</span></div><div class="planner-list">
    {#if loading}<div class="empty">Lade Wochenplan…</div>
    {:else}{#each WEEKDAYS as day, index}
      <div class="day-row">
        <div class="day-name">{day}</div>
        <div class="day-entries">
          {#each entriesForDay(index) as entry (entry.slot)}
            <button class="planned-entry" onclick={() => openPlanner(entry, index)}><strong>{entry.training_type}</strong>{#if entry.frequency_weeks && entry.frequency_weeks > 1}<small>alle {entry.frequency_weeks} Wochen</small>{/if}<small>Antippen zum Bearbeiten</small></button>
          {/each}
          <button class="add-entry" onclick={() => openNewPlanner(index)} disabled={addingPlanner}>{addingPlanner ? '…' : '+ Einheit'}</button>
        </div>
      </div>
    {/each}{/if}
  </div></section>

  {#if selectedSlot && modalDraft}
    <div class="planner-overlay" role="presentation" onclick={(event) => event.target === event.currentTarget && closePlanner()}>
      <div class="planner-modal" role="dialog" aria-modal="true" aria-label="Rotation bearbeiten">
        <div class="modal-top"><div><strong>{selectedSlot.training_type}</strong><small>Wochenplanung bearbeiten</small></div><button class="close" onclick={closePlanner} aria-label="Planung schließen">×</button></div>
        <label>Trainingseinheit<select bind:value={modalDraft.training_type}>{#each units.filter((unit) => unit.is_active !== false) as unit}<option value={unit.name}>{unit.name}</option>{/each}</select></label>
        <label>Wochentag<select bind:value={modalDraft.weekday}><option value="">Nicht geplant</option>{#each WEEKDAYS as day, index}<option value={String(index)}>{day}</option>{/each}</select></label>
        <label>Plan gültig ab<input type="date" bind:value={modalDraft.start_date} /></label>
        <div class="plan-hint">Nächster Termin: <strong>{firstPlannedDate(modalDraft)}</strong></div>
        <label>Wiederholung<input type="number" min="1" max="52" bind:value={modalDraft.frequency_weeks} /><small class="field-help">Nach wie vielen Wochen sich diese Einheit wiederholt.</small></label><label>Startversatz in Wochen<input type="number" min="0" max="51" bind:value={modalDraft.week_offset} /></label>
        <div class="modal-actions"><button class="secondary danger" onclick={removePlanner}>Entfernen</button><button class="secondary" onclick={closePlanner}>Abbrechen</button><button class="primary" onclick={savePlanner} disabled={saving === selectedSlot.slot}>{saving === selectedSlot.slot ? 'Speichern…' : 'Speichern'}</button></div>
      </div>
    </div>
  {/if}

  <section class="section-card"><div class="section-header">Cardio flexibel halten</div><div class="body info"><p>Die Minuten sind eine Vorgabe für das Sport-To-do, keine feste Aktivität. Im Cardio-Eintrag kann später die konkrete Sportart und tatsächliche Dauer gewählt werden.</p><div class="chips"><span>Aktivität frei wählbar</span><span>Mindestziel über Minuten</span><span>Im To-do abschließen</span></div></div></section>
  {#if error}<div class="error">{error}</div>{/if}
</div>

<style>
  .page { display: flex; flex-direction: column; gap: 10px; }
  .intro { display: flex; gap: 12px; padding: 14px; border-radius: 14px; background: linear-gradient(135deg, var(--card), var(--card-2)); border: 1px solid var(--border); }
  .intro-icon { width: 42px; height: 42px; border-radius: 11px; background: var(--blue); color: white; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .intro strong { display: block; margin-bottom: 4px; font-size: 15px; }
  p { color: var(--text-dim); font-size: 13px; line-height: 1.4; }
  .muted { color: var(--text-faint); font-size: 11px; font-weight: 400; }
  .body { padding: 10px 12px; }
  .empty { padding: 18px 0; color: var(--text-faint); font-size: 14px; text-align: center; }
  .planner-list { padding: 0 12px; }
  .day-row { display: grid; grid-template-columns: 92px 1fr; gap: 10px; min-height: 52px; padding: 8px 0; border-bottom: 1px solid var(--border); }
  .day-row:last-child { border-bottom: none; }
  .day-name { padding-top: 9px; color: var(--text-dim); font-size: 13px; font-weight: 600; }
  .day-entries { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
  .planned-entry { display: flex; flex-direction: column; align-items: flex-start; gap: 2px; padding: 7px 9px; border: 1px solid var(--border-2); border-radius: 8px; background: var(--card-2); color: var(--text); cursor: pointer; text-align: left; }
  .planned-entry small { color: var(--text-faint); font-size: 10px; }
  .add-entry { padding: 7px 9px; border: 1px dashed var(--border-2); border-radius: 8px; background: transparent; color: var(--text-faint); font-size: 12px; cursor: pointer; }
  .planner-overlay { position: fixed; inset: 0; z-index: 20; display: flex; align-items: flex-end; justify-content: center; padding: 14px; background: rgba(0,0,0,.58); }
  .planner-modal { width: min(100%, 420px); display: flex; flex-direction: column; gap: 12px; padding: 16px; border: 1px solid var(--border); border-radius: 16px 16px 10px 10px; background: var(--card); box-shadow: 0 14px 50px rgba(0,0,0,.35); }
  .modal-top { display: flex; align-items: flex-start; justify-content: space-between; }
  .modal-top div { display: flex; flex-direction: column; gap: 3px; }
  .modal-top small { color: var(--text-faint); font-size: 11px; }
  .close { border: none; background: transparent; color: var(--text-faint); font-size: 24px; line-height: 1; cursor: pointer; }
  .plan-hint { padding: 8px 10px; border-radius: 7px; background: var(--card-2); color: var(--text-faint); font-size: 12px; }
  .plan-hint strong { color: var(--text-dim); font-weight: 600; }
  .modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 4px; }
  .secondary { border: 1px solid var(--border-2); border-radius: 7px; padding: 8px 10px; background: transparent; color: var(--text-dim); font-size: 12px; cursor: pointer; }
  .rotation-row, .slot-number, .slot-fields { display: none; }
  .cardio-info { display: flex; flex-direction: column; gap: 3px; padding: 4px 0 12px; color: var(--text-dim); font-size: 13px; }
  .cardio-info span { color: var(--text-faint); font-size: 12px; }
  .unit-settings { display: flex; align-items: flex-end; gap: 8px; padding: 0 0 10px; }
  .unit-settings label { flex: 0 0 130px; }
  .unit-settings .secondary { margin-bottom: 0; }
  .add-unit, .exercise-add { display: flex; gap: 7px; align-items: center; margin-bottom: 10px; }
  .primary { border: none; border-radius: 7px; padding: 8px 10px; background: var(--blue); color: white; font-size: 12px; cursor: pointer; white-space: nowrap; }
  .unit-card { border-top: 1px solid var(--border); }
  .unit-header { width: 100%; display: flex; justify-content: space-between; align-items: center; padding: 11px 0; border: none; background: none; color: var(--text); text-align: left; cursor: pointer; }
  .unit-header span:first-child { display: flex; flex-direction: column; gap: 2px; }
  .unit-header small { color: var(--text-faint); font-size: 11px; font-weight: 400; }
  .exercise-list { display: flex; flex-direction: column; gap: 6px; padding: 0 0 10px; }
  .exercise-row { display: grid; grid-template-columns: minmax(180px, 1fr) minmax(260px, 1.2fr) minmax(250px, 1.4fr) auto; gap: 8px; align-items: end; padding: 10px; border: 1px solid var(--border); border-radius: 9px; background: var(--card-2); }
  .normal-fields { display: grid; grid-template-columns: repeat(4, minmax(56px, 1fr)); gap: 6px; }
  .progression-row { display: grid; grid-template-columns: 1.5fr .7fr; gap: 6px; }
  .progression-row span { grid-column: 1 / -1; color: var(--text-faint); font-size: 11px; }
  .topset-toggle { display: flex; align-items: center; gap: 6px; color: var(--text-dim); font-size: 12px; text-transform: none; letter-spacing: normal; }
  .topset-toggle input { width: auto; margin: 0; }
  .backoff-fields { grid-column: 1 / -2; display: grid; grid-template-columns: repeat(5, minmax(70px, 1fr)); gap: 6px; }
  .locked-field { display: flex; flex-direction: column; justify-content: center; padding: 7px 8px; border-radius: 7px; background: var(--bg); color: var(--text-dim); font-size: 12px; }
  .locked-field small { color: var(--text-faint); font-size: 10px; }
  .exercise-actions { display: flex; gap: 4px; align-items: flex-end; }
  .exercise-add { display: grid; grid-template-columns: minmax(120px, 1fr) 62px 45px 10px 45px 145px 55px 45px auto; gap: 5px; }
  .plan-summary, .progress-summary, .exercise-main, .exercise-advanced, .advanced-grid { display: none; }
  .exercise-name, .small, .strategy { min-width: 0; }
  .dash { color: var(--text-faint); text-align: center; align-self: center; }
  .hint { color: var(--text-faint); font-size: 11px; margin: 3px 0 0; }
  .save { border: 1px solid var(--border-2); border-radius: 7px; background: var(--card-2); color: var(--green); cursor: pointer; }
  .save:disabled { opacity: .5; }
  label { color: var(--text-faint); font-size: 10px; text-transform: uppercase; letter-spacing: .03em; }
  input, select { display: block; width: 100%; box-sizing: border-box; margin-top: 3px; padding: 7px 8px; border-radius: 7px; background: var(--card-2); border: 1px solid var(--border-2); color: var(--text); font-size: 13px; }
  select { appearance: auto; }
  input:focus, select:focus { border-color: var(--blue); outline: none; }
  .save { width: 30px; height: 30px; border-radius: 7px; background: var(--card-2); color: var(--text-dim); border: 1px solid var(--border-2); display: flex; align-items: center; justify-content: center; cursor: pointer; flex-shrink: 0; }
  .save:disabled { opacity: .45; }
  .info { padding-top: 12px; }
  .chips { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 10px; }
  .chips span { padding: 5px 8px; border-radius: 6px; background: var(--card-2); color: var(--text-dim); font-size: 11px; }
  .error { padding: 10px 12px; border-radius: 8px; background: rgba(220, 70, 70, .12); color: var(--red); font-size: 13px; }
  .danger { color: var(--red); }
  .section-intro { display: flex; flex-direction: column; gap: 3px; padding: 4px 0 12px; }
  .section-intro strong { color: var(--text); font-size: 14px; }
  .section-intro span, .field-help { color: var(--text-faint); font-size: 11px; text-transform: none; letter-spacing: normal; }
  .unit-overview { display: grid; gap: 6px; margin: 4px 0 10px; }
  .unit-summary { width: 100%; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px; border: 1px solid var(--border); border-radius: 10px; background: var(--card-2); color: var(--text); text-align: left; cursor: pointer; }
  .unit-summary.selected { border-color: var(--blue); box-shadow: 0 0 0 1px rgba(70, 140, 255, .18); }
  .unit-summary-main { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
  .unit-summary-main strong { font-size: 14px; }
  .unit-summary-main small, .unit-summary-action { color: var(--text-faint); font-size: 11px; }
  .unit-summary-action { white-space: nowrap; color: var(--blue); }
  .unit-editor { padding: 14px 0 4px; border-top: 1px solid var(--border); }
  .editor-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; margin-bottom: 12px; }
  .editor-heading > div { display: flex; flex-direction: column; gap: 3px; }
  .editor-heading strong { font-size: 16px; }
  .editor-heading small { color: var(--text-faint); font-size: 11px; }
  .exercise-main-fields { display: grid; grid-template-columns: minmax(160px, 1.8fr) repeat(4, minmax(70px, 1fr)); gap: 7px; align-items: end; }
  .exercise-title { min-width: 150px; }
  .exercise-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 8px; }
  .text-button { border: 0; background: transparent; color: var(--blue); padding: 4px 0; font-size: 11px; cursor: pointer; }
  .advanced-fields { display: grid; grid-template-columns: 1.5fr .7fr; gap: 7px; margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border); }
  .progression-explanation, .advanced-hint { grid-column: 1 / -1; color: var(--text-faint); font-size: 11px; }
  .advanced-hint { line-height: 1.4; }
  .advanced-fields .topset-toggle { grid-column: 1 / -1; }
  .exercise-add { display: grid; grid-template-columns: minmax(150px, 1.5fr) repeat(4, minmax(70px, .7fr)) minmax(180px, 1.5fr) auto; align-items: end; padding: 10px; border: 1px dashed var(--border-2); border-radius: 9px; }
  .exercise-add .primary { min-height: 34px; }
  .field-help { display: block; margin-top: 4px; }
  .planner-modal label { text-transform: none; letter-spacing: normal; font-size: 11px; }
  @media (max-width: 640px) {
    .editor-heading { align-items: stretch; flex-direction: column; }
    .editor-heading .secondary { align-self: flex-start; }
    .exercise-main-fields { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .exercise-title { grid-column: 1 / -1; }
    .advanced-fields { grid-template-columns: 1fr 1fr; }
    .exercise-add { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .exercise-add .exercise-title { grid-column: 1 / -1; }
    .exercise-add label:nth-of-type(6) { grid-column: 1 / -1; }
    .exercise-add .primary { grid-column: 1 / -1; }
  }
  @media (max-width: 420px) {
    .exercise-main-fields { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .advanced-fields { grid-template-columns: 1fr; }
    .advanced-fields .progression-explanation, .advanced-fields .advanced-hint, .advanced-fields .topset-toggle { grid-column: 1; }
    .backoff-fields { grid-template-columns: 1fr 1fr; }
  }
  @media (max-width: 640px) {
    .add-unit, .unit-settings { align-items: stretch; flex-wrap: wrap; }
    .add-unit > input:first-child { flex: 1 1 100%; }
    .exercise-row { grid-template-columns: 1fr auto; align-items: start; }
    .normal-fields, .progression-row, .backoff-fields { grid-column: 1 / -1; }
    .normal-fields { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .progression-row { grid-template-columns: 1fr 1fr; }
    .backoff-fields { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .exercise-add { grid-template-columns: repeat(4, minmax(0, 1fr)); padding: 10px; border: 1px solid var(--border); border-radius: 9px; }
    .exercise-name { grid-column: 1 / -1; }
    .strategy { grid-column: span 2; }
    .exercise-row .save, .exercise-add .primary { min-height: 34px; }
    .dash { display: none; }
  }
</style>
