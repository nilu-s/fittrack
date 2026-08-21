<script lang="ts">
  import { onMount } from 'svelte';
  import SettingsHeader from '$lib/components/SettingsHeader.svelte';
  import Icon from '$lib/components/Icon.svelte';
  import ProgressionHelp from '$lib/components/ProgressionHelp.svelte';
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
  let isNewPlanner = false;
  let activeView: 'week' | 'units' = 'week';
  let showUnitCreator = false;

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

  async function loadUnits() {
    unitLoading = true;
    units = await api.getTrainingUnits();
    const loaded = await Promise.all(units.map(async (unit) => [unit.name, await api.getExercises(unit.name)] as const));
    exercises = Object.fromEntries(loaded);
    newExercises = Object.fromEntries(units.map((unit) => [unit.name, blankExercise()]));
    selectedUnitName = selectedUnitName && units.some((unit) => unit.name === selectedUnitName) ? selectedUnitName : '';
    unitLoading = false;
  }
  function selectUnit(name: string): void {
    selectedUnitName = name;
    activeView = 'units';
  }
  function closeUnit(): void { selectedUnitName = ''; }
  function plannedDays(name: string): string {
    const days = rotation.filter((entry) => entry.training_type === name && entry.weekday != null).map((entry) => WEEKDAYS[entry.weekday!].slice(0, 2));
    return days.length ? days.join(', ') : 'Noch nicht geplant';
  }
  function openUnitFromPlanner(): void {
    if (!modalDraft) return;
    const name = modalDraft.training_type;
    closePlanner();
    selectUnit(name);
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
    newUnitName = ''; newUnitCardioMinutes = ''; units = [...units, unit]; exercises = { ...exercises, [unit.name]: [] }; newExercises = { ...newExercises, [unit.name]: blankExercise() }; showUnitCreator = false; selectUnit(unit.name);
  }
  async function saveUnit(unit: TrainingUnit): Promise<boolean> {
    if (!unit.id) return false;
    const updated = await api.updateTrainingUnit(unit.id, { unit_type: unit.unit_type === 'cardio' ? 'cardio' : 'gym', cardio_minutes: unit.unit_type === 'cardio' && unit.cardio_minutes != null ? Math.max(0, Number(unit.cardio_minutes)) : null });
    if (updated) units = units.map((item) => item.id === updated.id ? updated : item);
    return Boolean(updated);
  }
  async function finishUnit(unit: TrainingUnit): Promise<void> { if (await saveUnit(unit)) closeUnit(); }
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
  function openPlanner(entry: TrainingRotation, day?: number) { isNewPlanner = false; selectedSlot = entry; modalDraft = { ...makeDraft(entry), weekday: day == null ? makeDraft(entry).weekday : String(day) }; }
  function openNewPlanner(day: number) {
    const firstUnit = units.find((unit) => unit.is_active !== false);
    if (!firstUnit) { error = 'Lege zuerst eine Trainingseinheit an.'; activeView = 'units'; return; }
    error = '';
    isNewPlanner = true;
    selectedSlot = { slot: 0, training_type: firstUnit.name, weekday: day, frequency_weeks: 1, week_offset: 0, start_date: null };
    modalDraft = makeDraft(selectedSlot);
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
    const payload = { training_type: modalDraft.training_type.trim() || selectedSlot.training_type, weekday: modalDraft.weekday === '' ? null : Number(modalDraft.weekday), frequency_weeks, week_offset, start_date: modalDraft.start_date || null };
    const result = isNewPlanner ? await api.createRotation(payload) : await api.updateRotation(selectedSlot.slot, payload);
    if (result) {
      await loadRotation();
      closePlanner();
    } else error = isNewPlanner ? 'Der Termin konnte nicht gespeichert werden. Prüfe, ob diese Planung bereits existiert.' : `Slot ${selectedSlot.slot} konnte nicht gespeichert werden.`;
    saving = null;
  }
  async function removePlanner() { if (!selectedSlot) return; if (isNewPlanner) { closePlanner(); return; } if (!confirm('Geplante Einheit wirklich entfernen?')) return; if (await api.deleteRotation(selectedSlot.slot)) { await loadRotation(); closePlanner(); } }
  function closePlanner() { selectedSlot = null; modalDraft = null; isNewPlanner = false; }
  onMount(() => { loadUnits(); loadRotation(); });
</script>

<svelte:head><title>FitTrack - Sportprogramm</title></svelte:head>
<div class="page">
  <SettingsHeader title="Sportprogramm" subtitle="Planen, aufbauen, trainieren" />

  <section class="sport-hero">
    <div class="hero-copy"><span class="eyebrow">Dein Programm</span><strong>{units.filter((unit) => unit.is_active !== false).length} Einheiten · {rotation.filter((entry) => entry.weekday != null).length} Termine</strong><p>Wochenrhythmus und Trainingsinhalte greifen hier direkt ineinander.</p></div>
    <div class="hero-mark"><Icon name="training" size={26} /></div>
  </section>

  <div class="view-tabs" role="tablist" aria-label="Sportprogramm Bereiche">
    <button class:active={activeView === 'week'} role="tab" aria-selected={activeView === 'week'} onclick={() => (activeView = 'week')}><Icon name="calendar" size={17} /><span>Wochenplan</span></button>
    <button class:active={activeView === 'units'} role="tab" aria-selected={activeView === 'units'} onclick={() => (activeView = 'units')}><Icon name="training" size={17} /><span>Einheiten</span><small>{units.filter((unit) => unit.is_active !== false).length}</small></button>
  </div>

  <section class="program-shell">
    {#if activeView === 'week'}
      <div class="workspace-head"><div><span class="eyebrow">Rhythmus</span><h2>Deine Trainingswoche</h2><p>Tippe auf einen Termin zum Anpassen oder plane direkt eine Einheit ein.</p></div></div>
      <div class="week-grid">
        {#if loading}<div class="empty">Lade Wochenplan…</div>
        {:else}{#each WEEKDAYS as day, index}
          <div class="day-card" class:planned={entriesForDay(index).length > 0}>
            <div class="day-heading"><span>{day.slice(0, 2)}</span><strong>{day}</strong></div>
            <div class="day-content">
              {#each entriesForDay(index) as entry (entry.slot)}
                <button class="planned-entry" onclick={() => openPlanner(entry, index)}>
                  <span class="entry-icon"><Icon name="training" size={16} /></span>
                  <span class="entry-copy"><strong>{entry.training_type}</strong><small>{entry.frequency_weeks && entry.frequency_weeks > 1 ? `Alle ${entry.frequency_weeks} Wochen` : 'Wöchentlich'}</small></span>
                  <span class="chevron">›</span>
                </button>
              {/each}
              <button class="add-entry" onclick={() => openNewPlanner(index)}><span>+</span>Training planen</button>
            </div>
          </div>
        {/each}{/if}
      </div>
    {:else}
      <div class="workspace-head units-head"><div><span class="eyebrow">Bibliothek</span><h2>Trainingseinheiten</h2><p>Eine Einheit enthält alles, was du am Trainingstag brauchst.</p></div><button class="primary create-button" onclick={() => (showUnitCreator = true)}>+ Neue Einheit</button></div>
      {#if unitError}<div class="error">{unitError}</div>{/if}
      {#if unitLoading}<div class="empty">Lade Trainingseinheiten…</div>
      {:else if units.filter((unit) => unit.is_active !== false).length === 0}<div class="empty-state"><div class="empty-icon"><Icon name="training" size={24} /></div><strong>Noch keine Einheit</strong><span>Erstelle deine erste Gym- oder Cardio-Vorlage.</span><button class="primary" onclick={() => (showUnitCreator = true)}>Einheit erstellen</button></div>
      {:else}
        <div class="unit-grid">
          {#each units.filter((unit) => unit.is_active !== false) as unit (unit.id)}
            <button class="unit-tile" onclick={() => selectUnit(unit.name)}>
              <span class="unit-icon" class:cardio={isCardioUnit(unit)}><Icon name={isCardioUnit(unit) ? 'cardio' : 'training'} size={20} /></span>
              <span class="unit-copy"><strong>{unit.name}</strong><small>{isCardioUnit(unit) ? `${unit.cardio_minutes || '—'} Min. Ziel` : `${exercises[unit.name]?.length ?? 0} Übungen`}</small><span class="schedule"><Icon name="calendar" size={12} /> {plannedDays(unit.name)}</span></span>
              <span class="chevron">›</span>
            </button>
          {/each}
        </div>
      {/if}
    {/if}
  </section>

  {#if selectedUnitName}
    {#each units.filter((item) => item.is_active !== false && item.name === selectedUnitName) as unit (unit.id)}
      <div class="unit-workspace-overlay" role="presentation">
        <div class="unit-workspace" role="dialog" aria-modal="true" aria-label={`${unit.name} bearbeiten`}>
          <header class="unit-workspace-header">
            <button class="back-button" onclick={closeUnit} aria-label="Zurück zu Einheiten">‹</button>
            <div class="workspace-title"><span class="unit-icon" class:cardio={isCardioUnit(unit)}><Icon name={isCardioUnit(unit) ? 'cardio' : 'training'} size={18} /></span><div><strong>{unit.name}</strong><small>{isCardioUnit(unit) ? 'Cardio-Einheit' : `${exercises[unit.name]?.length ?? 0} Übungen · ${plannedDays(unit.name)}`}</small></div></div>
            <button class="header-save" onclick={() => finishUnit(unit)}>Fertig</button>
          </header>
          <div class="unit-workspace-body">
            <section class="editor-section compact-settings">
              <div class="editor-section-title"><div><span class="eyebrow">Grundlagen</span><h3>Einheit konfigurieren</h3></div></div>
              <div class="unit-settings"><label>Typ<select bind:value={unit.unit_type}><option value="gym">Gym</option><option value="cardio">Cardio</option></select></label>{#if isCardioUnit(unit)}<label>Ziel-Dauer<input type="number" min="0" aria-label="Cardio-Ziel in Minuten" bind:value={unit.cardio_minutes} /><small>Minuten</small></label>{/if}</div>
            </section>
            {#if !isCardioUnit(unit)}
              <section class="editor-section">
                <div class="editor-section-title"><div><span class="eyebrow">Ablauf</span><h3>Übungen</h3></div><span class="count-badge">{exercises[unit.name]?.length ?? 0}</span></div>
                <div class="exercise-list">
                  {#each exercises[unit.name] ?? [] as exercise, exerciseIndex (exercise.id)}
                    <article class="exercise-row">
                      <div class="exercise-index">{exerciseIndex + 1}</div>
                      <div class="exercise-main-fields">
                        <label class="exercise-title">Übung<input class="exercise-name" bind:value={exercise.exercise_name} /></label>
                        <label>Sätze<input type="number" min="1" max="20" value={setCount(exercise.target_sets)} oninput={(event) => updateSetCount(exercise, (event.target as HTMLInputElement).value)} /></label>
                        <label>Wdh. von<input type="number" min="1" bind:value={exercise.target_reps_low} /></label>
                        <label>Wdh. bis<input type="number" min="1" bind:value={exercise.target_reps_high} /></label>
                        <label>RIR<input type="number" min="0" max="5" bind:value={exercise.target_rir} /></label>
                      </div>
                      <div class="exercise-toolbar"><button class="text-button" onclick={() => toggleAdvanced(exercise)}>{showAdvanced[exercise.id!] ? 'Details schließen' : 'Progression & Details'}</button><div class="exercise-actions"><button class="icon-button" onclick={() => moveExercise(unit.name, exerciseIndex, -1)} aria-label="Übung nach oben">↑</button><button class="icon-button" onclick={() => moveExercise(unit.name, exerciseIndex, 1)} aria-label="Übung nach unten">↓</button><button class="icon-button success" onclick={() => saveExercise(exercise)} disabled={savingExercise === exercise.id} aria-label="Übung speichern">{savingExercise === exercise.id ? '…' : '✓'}</button><button class="icon-button danger" onclick={() => removeExercise(unit.name, exercise)} aria-label="Übung entfernen">×</button></div></div>
                      {#if showAdvanced[exercise.id!]}
                        <div class="advanced-fields"><label>Progression<select bind:value={exercise.progression_strategy}><option value="double_progression">Erst Wiederholungen, dann Gewicht</option><option value="weight_increase">Gewicht direkt steigern</option><option value="reps_only">Nur Wiederholungen steigern</option></select></label><label>Gewichtsschritt<input type="number" step="0.25" min="0" bind:value={exercise.progression_increment_weight} /></label><ProgressionHelp strategy={exercise.progression_strategy} repsLow={exercise.target_reps_low} repsHigh={exercise.target_reps_high} increment={exercise.progression_increment_weight} targetRir={exercise.target_rir} /><label class="topset-toggle"><input type="checkbox" checked={exercise.is_topset} onchange={(event) => toggleTopset(exercise, (event.target as HTMLInputElement).checked)} /> Top-Satz mit Back-off-Sätzen</label>{#if exercise.is_topset}<div class="backoff-fields"><div class="locked-field"><strong>1 Top-Satz</strong><small>steuert die Progression</small></div><label>Back-off-Sätze<select bind:value={exercise.backoff_set_count}>{#each [0, 1, 2, 3, 4, 5] as count}<option value={count}>{count}</option>{/each}</select></label><label>Wdh. ab<input type="number" min="1" bind:value={exercise.backoff_reps_low} /></label><label>Wdh. bis<input type="number" min="1" bind:value={exercise.backoff_reps_high} /></label><label>Gewicht %<input type="number" min="50" max="99" bind:value={exercise.backoff_weight_percent} /></label></div>{/if}</div>
                      {/if}
                    </article>
                  {/each}
                </div>
              </section>
              <section class="editor-section add-exercise-section">
                <div class="editor-section-title"><div><span class="eyebrow">Erweitern</span><h3>Übung hinzufügen</h3></div></div>
                <div class="exercise-add"><label class="exercise-title">Name<input class="exercise-name" placeholder="z. B. Bankdrücken" bind:value={newExercises[unit.name].exercise_name} /></label><div class="compact-grid"><label>Sätze<input type="number" min="1" max="20" bind:value={newExercises[unit.name].target_sets} /></label><label>Wdh. von<input type="number" min="1" bind:value={newExercises[unit.name].target_reps_low} /></label><label>Wdh. bis<input type="number" min="1" bind:value={newExercises[unit.name].target_reps_high} /></label><label>RIR<input type="number" min="0" max="5" bind:value={newExercises[unit.name].target_rir} /></label></div><label>Progression<select bind:value={newExercises[unit.name].progression_strategy}><option value="double_progression">Wiederholungen, dann Gewicht</option><option value="weight_increase">Gewicht direkt steigern</option><option value="reps_only">Nur Wiederholungen steigern</option></select></label><ProgressionHelp strategy={newExercises[unit.name].progression_strategy} repsLow={newExercises[unit.name].target_reps_low} repsHigh={newExercises[unit.name].target_reps_high} increment={newExercises[unit.name].progression_increment_weight} targetRir={newExercises[unit.name].target_rir} /><button class="primary wide" onclick={() => addExercise(unit.name)} disabled={savingExercise === `${unit.name}:new`}>{savingExercise === `${unit.name}:new` ? 'Wird hinzugefügt…' : '+ Übung hinzufügen'}</button></div>
              </section>
            {:else}
              <section class="editor-section cardio-panel"><div class="cardio-visual"><Icon name="cardio" size={26} /></div><div><h3>Flexibles Cardio</h3><p>Die Dauer ist dein Mindestziel. Aktivität und tatsächliche Zeit wählst du am Trainingstag.</p></div></section>
            {/if}
            <button class="archive-button" onclick={() => archiveUnit(unit)}>Einheit archivieren</button>
          </div>
        </div>
      </div>
    {/each}
  {/if}

  {#if showUnitCreator}
    <div class="planner-overlay" role="presentation" onclick={(event) => event.target === event.currentTarget && (showUnitCreator = false)}>
      <div class="planner-modal" role="dialog" aria-modal="true" aria-label="Trainingseinheit erstellen">
        <div class="modal-top"><div><span class="eyebrow">Neue Vorlage</span><strong>Trainingseinheit erstellen</strong><small>Du kannst Inhalte und Planung danach direkt ergänzen.</small></div><button class="close" onclick={() => (showUnitCreator = false)} aria-label="Schließen">×</button></div>
        <label>Name<input aria-label="Name der neuen Trainingseinheit" placeholder="z. B. Push A" bind:value={newUnitName} onkeydown={(event) => event.key === 'Enter' && addUnit()} /></label>
        <label>Typ<select bind:value={newUnitType} aria-label="Typ der neuen Trainingseinheit"><option value="gym">Gym</option><option value="cardio">Cardio</option></select></label>
        {#if newUnitType === 'cardio'}<label>Ziel-Dauer<input type="number" min="0" aria-label="Cardio-Ziel in Minuten" placeholder="z. B. 30" bind:value={newUnitCardioMinutes} /><small class="field-help">Kann am Trainingstag überschritten werden.</small></label>{/if}
        <div class="modal-actions"><button class="secondary" onclick={() => (showUnitCreator = false)}>Abbrechen</button><button class="primary" onclick={addUnit}>Einheit erstellen</button></div>
      </div>
    </div>
  {/if}

  {#if selectedSlot && modalDraft}
    <div class="planner-overlay" role="presentation" onclick={(event) => event.target === event.currentTarget && closePlanner()}>
      <div class="planner-modal" role="dialog" aria-modal="true" aria-label="Rotation bearbeiten">
        <div class="modal-top"><div><span class="eyebrow">Wochenplan</span><strong>{selectedSlot.training_type}</strong><small>Termin und Wiederholung anpassen</small></div><button class="close" onclick={closePlanner} aria-label="Planung schließen">×</button></div>
        <label>Trainingseinheit<select bind:value={modalDraft.training_type}>{#each units.filter((unit) => unit.is_active !== false) as unit}<option value={unit.name}>{unit.name}</option>{/each}</select></label>
        <button class="linked-unit" onclick={openUnitFromPlanner}><span><small>Trainingsinhalt</small><strong>{modalDraft.training_type} bearbeiten</strong></span><span>›</span></button>
        <div class="two-fields"><label>Wochentag<select bind:value={modalDraft.weekday}><option value="">Nicht geplant</option>{#each WEEKDAYS as day, index}<option value={String(index)}>{day}</option>{/each}</select></label><label>Gültig ab<input type="date" bind:value={modalDraft.start_date} /></label></div>
        <div class="plan-hint"><span>Nächster Termin</span><strong>{firstPlannedDate(modalDraft)}</strong></div>
        <div class="two-fields"><label>Alle<input type="number" min="1" max="52" bind:value={modalDraft.frequency_weeks} /><small class="field-help">Wochen</small></label><label>Startversatz<input type="number" min="0" max="51" bind:value={modalDraft.week_offset} /><small class="field-help">Wochen</small></label></div>
        <div class="modal-actions split"><button class="secondary danger" onclick={removePlanner}>{isNewPlanner ? 'Verwerfen' : 'Termin entfernen'}</button><span></span><button class="secondary" onclick={closePlanner}>Abbrechen</button><button class="primary" onclick={savePlanner} disabled={saving === selectedSlot.slot}>{saving === selectedSlot.slot ? 'Speichern…' : 'Speichern'}</button></div>
      </div>
    </div>
  {/if}

  {#if error}<div class="error">{error}</div>{/if}
</div>
<style>
  :global(body:has(.unit-workspace-overlay)), :global(body:has(.planner-overlay)) { overflow: hidden; }
  .page { display: flex; flex-direction: column; gap: 12px; padding-bottom: 24px; }
  .sport-hero { display: flex; justify-content: space-between; gap: var(--space-4); min-height: 96px; padding: var(--space-4); border: 1px solid var(--border); border-radius: var(--radius); background: var(--card); }
  .hero-copy { display: flex; flex-direction: column; gap: 5px; }
  .hero-copy strong { max-width: 300px; font-size: 19px; line-height: 1.2; letter-spacing: -.02em; }
  .hero-copy p, .workspace-head p, .cardio-panel p { margin: 0; color: var(--text-dim); font-size: 12px; line-height: 1.45; }
  .eyebrow { color: var(--text-dim); font-size: 10px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
  .hero-mark { width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; border-radius: var(--radius-sm); background: var(--card-2); color: var(--text-dim); }

  .view-tabs { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; padding: 4px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--card); }
  .view-tabs button { min-height: 48px; display: flex; align-items: center; justify-content: center; gap: 8px; border: 0; border-radius: 10px; background: transparent; color: var(--text-dim); font-size: 13px; font-weight: 650; cursor: pointer; }
  .view-tabs button.active { background: var(--card-2); color: var(--text); box-shadow: inset 0 0 0 1px var(--border); }
  .view-tabs small { min-width: 18px; height: 18px; padding: 0 5px; display: inline-flex; align-items: center; justify-content: center; border-radius: 9px; background: rgba(255,255,255,.07); color: var(--text-dim); font-size: 10px; }
  .view-tabs button.active small { background: var(--card); color: var(--text-dim); }

  .program-shell { min-height: 220px; padding: 14px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--card); }
  .workspace-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 16px; padding: 0 2px; }
  .workspace-head h2 { margin: 3px 0 4px; color: var(--text); font-size: 18px; letter-spacing: -.02em; }
  .workspace-head p { max-width: 320px; }
  .units-head { align-items: center; }
  .create-button { flex-shrink: 0; }

  .week-grid { display: flex; flex-direction: column; gap: 7px; }
  .day-card { display: grid; grid-template-columns: 54px minmax(0,1fr); min-height: 62px; padding: 7px; border: 1px solid transparent; border-radius: 13px; background: rgba(255,255,255,.018); }
  .day-card.planned { border-color: var(--border); background: var(--card-2); }
  .day-heading { display: flex; flex-direction: column; justify-content: center; align-items: center; gap: 1px; border-right: 1px solid var(--border); }
  .day-heading span { display: none; }
  .day-heading strong { color: var(--text-dim); font-size: 11px; font-weight: 700; }
  .day-card.planned .day-heading strong { color: var(--text); }
  .day-content { display: flex; flex-direction: column; justify-content: center; gap: 5px; padding-left: 8px; }
  .planned-entry, .unit-tile, .linked-unit { width: 100%; min-height: 52px; display: flex; align-items: center; gap: 10px; padding: 7px 9px; border: 0; border-radius: 10px; background: rgba(255,255,255,.03); color: var(--text); text-align: left; cursor: pointer; }
  .planned-entry:active, .unit-tile:active, .linked-unit:active { background: rgba(255,255,255,.08); }
  .entry-icon, .unit-icon { width: 36px; height: 36px; display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0; border-radius: 10px; background: rgba(10,132,255,.14); color: #65afff; }
  .unit-icon.cardio { background: rgba(255,159,10,.14); color: var(--amber); }
  .entry-copy, .unit-copy { min-width: 0; flex: 1; display: flex; flex-direction: column; gap: 2px; }
  .entry-copy strong, .unit-copy strong { overflow: hidden; color: var(--text); font-size: 13px; white-space: nowrap; text-overflow: ellipsis; }
  .entry-copy small, .unit-copy small { color: var(--text-faint); font-size: 10px; }
  .chevron { flex-shrink: 0; color: var(--text-faint); font-size: 23px; font-weight: 300; }
  .add-entry { min-height: 42px; display: flex; align-items: center; justify-content: center; gap: 6px; border: 1px dashed var(--border-2); border-radius: 10px; background: transparent; color: var(--text-faint); font-size: 11px; cursor: pointer; }
  .add-entry span { font-size: 16px; }
  .day-card.planned .add-entry { min-height: 34px; justify-content: flex-start; padding-left: 12px; border-color: transparent; }

  .unit-grid { display: grid; gap: 8px; }
  .unit-tile { min-height: 76px; padding: 12px; border: 1px solid var(--border); background: var(--card-2); }
  .unit-tile .unit-icon { width: 44px; height: 44px; border-radius: 13px; }
  .schedule { display: flex; align-items: center; gap: 4px; margin-top: 3px; color: var(--text-dim); font-size: 10px; }
  .empty, .empty-state { padding: 30px 12px; color: var(--text-faint); font-size: 13px; text-align: center; }
  .empty-state { display: flex; flex-direction: column; align-items: center; gap: 8px; }
  .empty-state strong { color: var(--text); font-size: 15px; }
  .empty-icon { width: 52px; height: 52px; display: flex; align-items: center; justify-content: center; margin-bottom: 4px; border-radius: 16px; background: var(--card-2); color: var(--blue); }

  .unit-workspace-overlay { position: fixed; inset: 0; z-index: 70; display: flex; justify-content: center; background: var(--bg); }
  .unit-workspace { width: min(100%, 560px); height: 100dvh; display: flex; flex-direction: column; background: var(--bg); }
  .unit-workspace-header { min-height: 64px; display: grid; grid-template-columns: 44px minmax(0,1fr) auto; align-items: center; gap: 8px; padding: max(8px, env(safe-area-inset-top, 0px)) 12px 8px; border-bottom: 1px solid var(--border); background: var(--bg); }
  .back-button, .header-save { min-width: 44px; min-height: 44px; border: 0; border-radius: 10px; cursor: pointer; }
  .back-button { background: var(--card-2); color: var(--text); font-size: 30px; font-weight: 250; }
  .header-save { padding: 0 12px; background: rgba(10,132,255,.14); color: #75b8ff; font-size: 12px; font-weight: 700; }
  .workspace-title { min-width: 0; display: flex; align-items: center; gap: 9px; }
  .workspace-title .unit-icon { width: 38px; height: 38px; }
  .workspace-title > div { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
  .workspace-title strong { overflow: hidden; font-size: 15px; white-space: nowrap; text-overflow: ellipsis; }
  .workspace-title small { overflow: hidden; color: var(--text-faint); font-size: 10px; white-space: nowrap; text-overflow: ellipsis; }
  .unit-workspace-body { flex: 1; overflow-y: auto; overscroll-behavior: contain; padding: 14px 12px calc(28px + env(safe-area-inset-bottom, 0px)); }
  .editor-section { margin-bottom: 12px; padding: 14px; border: 1px solid var(--border); border-radius: 16px; background: var(--card); }
  .editor-section-title { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 13px; }
  .editor-section-title h3, .cardio-panel h3 { margin: 2px 0 0; font-size: 16px; letter-spacing: -.015em; }
  .count-badge { min-width: 28px; height: 28px; display: inline-flex; align-items: center; justify-content: center; border-radius: 9px; background: var(--card-2); color: var(--text-dim); font-size: 11px; font-weight: 700; }
  .unit-settings { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }

  .exercise-list { display: flex; flex-direction: column; gap: 9px; }
  .exercise-row { position: relative; padding: 13px 11px 11px; border: 1px solid var(--border); border-radius: 13px; background: var(--card-2); }
  .exercise-index { position: absolute; top: -7px; left: 10px; min-width: 20px; height: 16px; display: flex; align-items: center; justify-content: center; padding: 0 4px; border-radius: 6px; background: #2b2d33; color: var(--text-dim); font-size: 9px; font-weight: 800; }
  .exercise-main-fields { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 7px; }
  .exercise-title { grid-column: 1 / -1; }
  .exercise-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 9px; }
  .exercise-actions { display: flex; gap: 5px; }
  .text-button { min-height: 36px; padding: 0 4px; border: 0; background: transparent; color: var(--blue); font-size: 11px; cursor: pointer; }
  .icon-button { width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; border: 1px solid var(--border-2); border-radius: 10px; background: #202126; color: var(--text-dim); cursor: pointer; }
  .icon-button.success { color: var(--green); }
  .icon-button.danger, .danger { color: var(--red); }
  .advanced-fields { display: grid; grid-template-columns: 1.5fr .8fr; gap: 8px; margin-top: 10px; padding-top: 11px; border-top: 1px solid var(--border); }
  .topset-toggle { grid-column: 1 / -1; min-height: 42px; display: flex; align-items: center; gap: 8px; color: var(--text-dim); font-size: 11px; text-transform: none; letter-spacing: normal; }
  .topset-toggle input { width: 20px; height: 20px; margin: 0; }
  .backoff-fields { grid-column: 1 / -1; display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 7px; }
  .locked-field { display: flex; flex-direction: column; justify-content: center; min-height: 55px; padding: 6px 9px; border-radius: 9px; background: var(--bg); color: var(--text-dim); font-size: 11px; }
  .locked-field small { color: var(--text-faint); font-size: 9px; }
  .exercise-add { display: flex; flex-direction: column; gap: 9px; }
  .compact-grid { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 7px; }
  .wide { width: 100%; min-height: 46px; }
  .cardio-panel { display: flex; align-items: center; gap: 12px; }
  .cardio-visual { width: 52px; height: 52px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; border-radius: 16px; background: rgba(255,159,10,.13); color: var(--amber); }
  .archive-button { width: 100%; min-height: 46px; border: 1px solid rgba(255,69,58,.17); border-radius: 12px; background: transparent; color: var(--red); font-size: 12px; cursor: pointer; }

  .planner-overlay { position: fixed; inset: 0; z-index: 80; display: flex; align-items: flex-end; justify-content: center; padding: 12px; padding-bottom: max(12px, env(safe-area-inset-bottom, 0px)); background: rgba(0,0,0,.66); }
  .planner-modal { width: min(100%, 460px); max-height: min(88dvh, 720px); overflow-y: auto; display: flex; flex-direction: column; gap: 12px; padding: 18px; border: 1px solid var(--border-2); border-radius: 20px; background: #18191d; box-shadow: 0 24px 70px rgba(0,0,0,.55); }
  .modal-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
  .modal-top > div { display: flex; flex-direction: column; gap: 3px; }
  .modal-top strong { font-size: 17px; }
  .modal-top small { color: var(--text-faint); font-size: 10px; }
  .close { width: 44px; height: 44px; flex-shrink: 0; border: 0; border-radius: 11px; background: var(--card-2); color: var(--text-dim); font-size: 24px; cursor: pointer; }
  .linked-unit { min-height: 58px; justify-content: space-between; border: 1px solid rgba(10,132,255,.18); background: rgba(10,132,255,.08); color: #78baff; }
  .linked-unit span:first-child { display: flex; flex-direction: column; gap: 2px; }
  .linked-unit small { color: var(--text-faint); font-size: 9px; text-transform: uppercase; letter-spacing: .06em; }
  .two-fields { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .plan-hint { display: flex; flex-direction: column; gap: 3px; padding: 11px; border-radius: 11px; background: var(--card-2); color: var(--text-faint); font-size: 10px; }
  .plan-hint strong { color: var(--text); font-size: 12px; }
  .modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 2px; }
  .modal-actions.split { display: grid; grid-template-columns: auto 1fr auto auto; }

  label { position: relative; color: var(--text-faint); font-size: 9px; font-weight: 650; letter-spacing: .045em; text-transform: uppercase; }
  input, select { width: 100%; min-height: 44px; box-sizing: border-box; display: block; margin-top: 5px; padding: 9px 10px; border: 1px solid var(--border-2); border-radius: 10px; background: #202126; color: var(--text); font-size: 13px; text-transform: none; }
  input:focus, select:focus { border-color: var(--blue); outline: 2px solid rgba(10,132,255,.13); }
  label > small:not(.field-help) { position: absolute; right: 9px; bottom: 14px; color: var(--text-faint); font-size: 9px; }
  .field-help { display: block; margin-top: 4px; color: var(--text-faint); font-size: 9px; font-weight: 400; letter-spacing: 0; text-transform: none; }
  .primary, .secondary { min-height: 44px; padding: 0 14px; border-radius: 10px; font-size: 12px; font-weight: 650; cursor: pointer; }
  .primary { border: 0; background: var(--blue); color: white; }
  .secondary { border: 1px solid var(--border-2); background: transparent; color: var(--text-dim); }
  button:disabled { opacity: .48; cursor: default; }
  .error { padding: 11px 12px; border-radius: 11px; background: rgba(255,69,58,.1); color: var(--red); font-size: 12px; }

  @media (max-width: 390px) {
    .sport-hero { padding: 17px; }
    .hero-copy strong { font-size: 19px; }
    .hero-mark { width: 44px; height: 44px; }
    .program-shell { padding: 16px 10px 10px; }
    .units-head { align-items: flex-start; }
    .create-button { min-width: 44px; width: 44px; padding: 0; overflow: hidden; font-size: 0; }
    .create-button::before { content: '+'; font-size: 22px; }
    .exercise-main-fields, .compact-grid { grid-template-columns: repeat(2, minmax(0,1fr)); }
    .exercise-title { grid-column: 1 / -1; }
    .exercise-toolbar { align-items: flex-start; flex-direction: column; }
    .exercise-actions { width: 100%; justify-content: flex-end; }
    .advanced-fields, .two-fields { grid-template-columns: 1fr; }
    .advanced-fields > * { grid-column: 1; }
    .modal-actions.split { grid-template-columns: 1fr 1fr; }
    .modal-actions.split span { display: none; }
    .modal-actions.split .danger { grid-column: 1 / -1; }
  }
</style>
