<script lang="ts">
  import MetricRow from './MetricRow.svelte';
  import Sparkline from './Sparkline.svelte';
  import ProgressBar from './ProgressBar.svelte';
  import TrainingDetail from './TrainingDetail.svelte';
  import { api } from '$lib/api';
  import { dailyGoals } from '$lib/stores';
  import type { DayData } from '$lib/types';

  export let dayData: DayData;
  export let currentDate: string;

  let entry = dayData.dayEntry;
  let weightTrend: number[] = [];
  let kcalTrend: number[] = [];

  $: entry = dayData.dayEntry ?? { date: currentDate };
  $: totalKcal = (dayData.meals ?? []).reduce((s, m) => s + (Number(m.kcal) ?? 0), 0);

  // Fetch sparkline data
  $: if (currentDate) {
    loadTrends();
  }

  async function loadTrends() {
    try {
      const [wt, kt] = await Promise.all([
        api.getStatsTrend('weight', 7),
        api.getStatsTrend('kcal', 7),
      ]);
      weightTrend = (wt?.points ?? []).map((v) => v.value ?? 0).filter((v) => v !== null && v > 0);
      kcalTrend = (kt?.points ?? []).map((v) => v.value ?? 0).filter((v) => v !== null && v > 0);
    } catch {
      // graceful
    }
  }

  async function updateField(field: string, value: any) {
    entry = { ...entry, [field]: value };
    try {
      await api.upsertDayEntry({ ...entry, date: currentDate });
    } catch {
      // graceful
    }
  }

  async function toggleCheck(field: string) {
    const doneField = field + '_done';
    const newVal = !(entry as any)[doneField];
    entry = { ...entry, [doneField]: newVal };
    if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(30);
    try {
      await api.upsertDayEntry({ ...entry, date: currentDate });
    } catch {
      // graceful
    }
  }

  // Training karussell
  let rotationIdx = 0;
  let showDetail = false;
  let lastTrainingTap = 0;
  $: rotationTypes = dayData.nextTraining
    ? [dayData.nextTraining.training_type]
    : ['Oberkörper A', 'Oberkörper B', 'Unterkörper A', 'Unterkörper B'];

  function prevTraining() {
    rotationIdx = (rotationIdx - 1 + rotationTypes.length) % rotationTypes.length;
  }

  function nextTraining() {
    rotationIdx = (rotationIdx + 1) % rotationTypes.length;
  }

  function onTrainingComplete() {
    entry = {
      ...(entry || { date: currentDate }),
      training_done: true,
      training_type: currentTrainingType === '—' ? null : currentTrainingType,
    };
    showDetail = false;
  }

  function handleTrainingRowClick(e: MouseEvent | TouchEvent) {
    const target = e.target as HTMLElement;
    if (target.closest('button, input')) return;
    const now = Date.now();
    if (now - lastTrainingTap < 300) {
      lastTrainingTap = 0;
      toggleCheck('training');
      return;
    }
    lastTrainingTap = now;
    setTimeout(() => {
      if (lastTrainingTap && Date.now() - lastTrainingTap >= 300) {
        showDetail = !showDetail;
        lastTrainingTap = 0;
      }
    }, 320);
  }

  $: currentTrainingType = rotationTypes[rotationIdx] ?? entry?.training_type ?? '—';
  $: goals = $dailyGoals;
</script>

<section class="section-card fitness-card">
  <div class="section-header">
    <span>💪 Fitness</span>
    <a href="/week" class="header-link">7T ›</a>
  </div>

  <div class="card-body">
    <!-- Weight with sparkline -->
    <div class="metric-with-spark">
      <MetricRow
        icon="⚖️"
        label="Gewicht"
        value={entry?.weight_kg ?? null}
        unit="kg"
        editable
        onchange={(e) => updateField('weight_kg', e.detail)}
      />
      <div class="spark-wrap">
        <Sparkline data={weightTrend} color="#3b82f6" height={24} width={70} fill={true} />
      </div>
    </div>

    <!-- Steps with progress bar -->
    <div class="metric-with-progress">
      <MetricRow
        icon="👣"
        label="Schritte"
        value={entry?.steps ?? null}
        checkable
        checked={entry?.steps_done ?? false}
        onchange={(e) => updateField('steps', e.detail)}
        oncheck={() => toggleCheck('steps')}
      />
      <ProgressBar current={entry?.steps ?? 0} target={goals.steps} color="#666" />
    </div>

    <!-- Sleep with progress bar -->
    <div class="metric-with-progress">
      <MetricRow
        icon="😴"
        label="Schlaf"
        value={entry?.sleep_hours ?? null}
        unit="h"
        checkable
        checked={entry?.sleep_done ?? false}
        onchange={(e) => updateField('sleep_hours', e.detail)}
        oncheck={() => toggleCheck('sleep')}
      />
      <ProgressBar current={entry?.sleep_hours ?? 0} target={goals.sleepHours} color="#666" />
    </div>

    <!-- Cardio -->
    <MetricRow
      icon="🏃"
      label="Cardio"
      value={entry?.cardio_minutes ?? null}
      unit="min"
      checkable
      checked={entry?.cardio_minutes ? (entry as any).cardio_done : false}
      onchange={(e) => updateField('cardio_minutes', e.detail)}
      oncheck={() => toggleCheck('cardio')}
    />

    <!-- Training with karussell -->
    <div class="training-row tap-area" onclick={handleTrainingRowClick}>
      <MetricRow
        icon="🏋️"
        label="Training"
        value={currentTrainingType}
        checkable
        checked={entry?.training_done ?? false}
        oncheck={() => toggleCheck('training')}
      />
      <div class="karussell" onclick={(e) => e.stopPropagation()}>
        <button class="karussell-btn" onclick={prevTraining}>◄</button>
        <button class="karussell-btn" onclick={nextTraining}>►</button>
      </div>
    </div>

    {#if showDetail}
      <TrainingDetail
        training_type={currentTrainingType}
        date={currentDate}
        on:complete={onTrainingComplete}
        on:close={() => (showDetail = false)}
      />
    {/if}

    <!-- Creatine -->
    <div class="metric-row-custom">
      <span class="metric-icon">💊</span>
      <span class="metric-label">Kreatin</span>
      <button class="toggle-btn" class:active={entry?.creatine_done ?? false} onclick={() => updateField('creatine_done', !entry?.creatine_done)}>
        {entry?.creatine_done ? '✓ Eingenommen' : '○ Ausstehend'}
      </button>
    </div>

    <!-- Belly circumference -->
    <MetricRow
      icon="📏"
      label="Bauchumfang"
      value={entry?.belly_cm ?? null}
      unit="cm"
      editable
      onchange={(e) => updateField('belly_cm', e.detail)}
    />

    <!-- Kcal sparkline -->
    <div class="kcal-spark-row">
      <span class="text-sm muted">kcal 7T</span>
      <Sparkline data={kcalTrend} color="#f59e0b" height={24} width={100} fill={true} />
    </div>
  </div>
</section>

<style>
  .header-link {
    font-size: 0.75rem;
    color: var(--text-secondary);
    text-decoration: none;
  }

  .card-body {
    padding: 0 0.75rem 0.5rem;
  }

  .metric-with-spark {
    display: flex;
    align-items: center;
  }

  .metric-with-spark :global(.metric-row) {
    flex: 1;
  }

  .spark-wrap {
    flex-shrink: 0;
    padding-left: 0.5rem;
  }

  .metric-with-progress {
    padding-bottom: 0.25rem;
  }

  .training-row {
    display: flex;
    align-items: center;
  }

  .training-row :global(.metric-row) {
    flex: 1;
  }

  .karussell {
    display: flex;
    gap: 4px;
    flex-shrink: 0;
  }

  .karussell-btn {
    width: 28px;
    height: 28px;
    border-radius: 6px;
    background: #333;
    border: 1px solid var(--card-border);
    color: var(--text-primary);
    cursor: pointer;
    font-size: 0.75rem;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .karussell-btn:active {
    background: #444;
  }

  .metric-row-custom {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid #333;
  }

  .metric-icon {
    width: 24px;
    text-align: center;
    flex-shrink: 0;
  }

  .metric-label {
    flex: 1;
    font-size: 0.8125rem;
    color: var(--text-secondary);
  }

  .toggle-btn {
    padding: 4px 10px;
    border-radius: 6px;
    background: #333;
    color: var(--text-secondary);
    font-size: 0.75rem;
    cursor: pointer;
    border: 1px solid var(--card-border);
    transition: all 0.2s;
  }

  .toggle-btn.active {
    background: var(--accent-done);
    color: #0f0f0f;
    border-color: var(--accent-done);
    font-weight: 600;
  }

  .kcal-spark-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 0 0;
  }
</style>