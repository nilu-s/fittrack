<script lang="ts">
  import MetricRow from './MetricRow.svelte';
  import Sparkline from './Sparkline.svelte';
  import ProgressBar from './ProgressBar.svelte';
  import { api } from '$lib/api';
  import { dailyGoals } from '$lib/stores';
  import type { DayData, DayEntry } from '$lib/types';

  export let dayData: DayData;
  export let currentDate: string;

  let entry: DayEntry = dayData.dayEntry ?? { date: currentDate };
  let weightTrend: number[] = [];

  $: entry = dayData.dayEntry ?? { date: currentDate };

  // Fetch weight sparkline data
  $: if (currentDate) {
    loadWeightTrend();
  }

  async function loadWeightTrend() {
    try {
      const wt = await api.getStatsTrend('weight', 7);
      weightTrend = (wt?.points ?? []).map((v) => v.value ?? 0).filter((v) => v !== null && v > 0);
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

  $: goals = $dailyGoals;
</script>

<section class="section-card fitness-card">
  <div class="section-header">
    <span>💪 Fitness</span>
    <a href="/week" class="header-link">7T ›</a>
  </div>

  <div class="card-body">
    <!-- Weight with sparkline -->
    <div class="metric-card">
      <div class="metric-with-spark">
        <MetricRow
          icon="⚖️"
          label="Gewicht"
          value={entry?.weight_kg ?? null}
          unit="kg"
          editable
          on:change={(e) => updateField('weight_kg', e.detail)}
        />
        <div class="spark-wrap">
          <Sparkline data={weightTrend} color="#3b82f6" height={24} width={70} fill={true} />
        </div>
      </div>
    </div>

    <!-- Steps with progress bar -->
    <div class="metric-card">
      <MetricRow
        icon="👣"
        label="Schritte"
        value={entry?.steps ?? null}
        checkable
        checked={entry?.steps_done ?? false}
        on:change={(e) => updateField('steps', e.detail)}
        on:check={() => toggleCheck('steps')}
      />
      <ProgressBar current={entry?.steps ?? 0} target={goals.steps} color="#666" />
    </div>

    <!-- Sleep with progress bar -->
    <div class="metric-card">
      <MetricRow
        icon="😴"
        label="Schlaf"
        value={entry?.sleep_hours ?? null}
        unit="h"
        checkable
        checked={entry?.sleep_done ?? false}
        on:change={(e) => updateField('sleep_hours', e.detail)}
        on:check={() => toggleCheck('sleep')}
      />
      <ProgressBar current={entry?.sleep_hours ?? 0} target={goals.sleepHours} color="#666" />
    </div>

    <!-- Creatine as uniform MetricRow -->
    <div class="metric-card">
      <MetricRow
        icon="💊"
        label="Kreatin"
        value={entry?.creatine_done ? '✓ Eingenommen' : '○ Ausstehend'}
        checkable
        checked={entry?.creatine_done ?? false}
        editable={false}
        on:check={() => toggleCheck('creatine')}
      />
    </div>

    <!-- Belly circumference -->
    <div class="metric-card">
      <MetricRow
        icon="📏"
        label="Bauchumfang"
        value={entry?.belly_cm ?? null}
        unit="cm"
        editable
        on:change={(e) => updateField('belly_cm', e.detail)}
      />
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
    padding: 0.5rem 0.75rem;
  }

  .metric-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: var(--radius-md);
    padding: 0.5rem 0.625rem;
    margin-bottom: 0.5rem;
  }

  .metric-card:last-child {
    margin-bottom: 0;
  }

  .metric-card :global(.metric-row) {
    border-bottom: none;
    padding: 0;
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
</style>