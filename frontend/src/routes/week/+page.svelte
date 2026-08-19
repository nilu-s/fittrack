<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { currentDate } from '$lib/stores';
  import Sparkline from '$lib/components/Sparkline.svelte';
  import ProgressBar from '$lib/components/ProgressBar.svelte';
  import type { WeekStats } from '$lib/types';

  let weekStats: WeekStats | null = null;
  let weightData: number[] = [];
  let kcalData: number[] = [];
  let stepsData: number[] = [];

  function goBack() {
    if (typeof window !== 'undefined') {
      window.history.back();
    }
  }

  onMount(async () => {
    try {
      weekStats = await api.getStatsWeek($currentDate);
      if (weekStats?.weight_trend) weightData = weekStats.weight_trend;
      if (weekStats?.kcal_trend) kcalData = weekStats.kcal_trend;
      if (weekStats?.steps_trend) stepsData = weekStats.steps_trend;
    } catch {
      // graceful
    }
  });
</script>

<svelte:head>
  <title>FitTrack - Woche</title>
</svelte:head>

<div class="week-page">
  <div class="week-header">
    <button class="back-btn" onclick={goBack}>‹ Zurück</button>
    <h1>Wochenübersicht</h1>
  </div>

  {#if weekStats}
    <!-- Weight trend -->
    <section class="section-card">
      <div class="section-header">
        <span>⚖️ Gewicht</span>
        <span class="text-sm muted">{weekStats.weight_avg?.toFixed(1) ?? '—'} kg Ø</span>
      </div>
      <div class="card-body">
        <div class="chart-area">
          {#if weightData.length > 0}
            <Sparkline data={weightData} color="#3b82f6" height={80} width={300} fill={true} />
          {:else}
            <div class="muted text-sm" style="padding:1rem;text-align:center">Keine Daten</div>
          {/if}
        </div>
      </div>
    </section>

    <!-- Kcal average -->
    <section class="section-card">
      <div class="section-header">
        <span>🔥 Kalorien</span>
        <span class="text-sm muted">{weekStats.kcal_avg?.toFixed(0) ?? '—'} kcal Ø</span>
      </div>
      <div class="card-body">
        <div class="chart-area">
          {#if kcalData.length > 0}
            <Sparkline data={kcalData} color="#f59e0b" height={80} width={300} fill={true} />
          {:else}
            <div class="muted text-sm" style="padding:1rem;text-align:center">Keine Daten</div>
          {/if}
        </div>
      </div>
    </section>

    <!-- Steps average -->
    <section class="section-card">
      <div class="section-header">
        <span>👣 Schritte</span>
        <span class="text-sm muted">{weekStats.steps_avg?.toFixed(0) ?? '—'} Ø</span>
      </div>
      <div class="card-body">
        <div class="chart-area">
          {#if stepsData.length > 0}
            <Sparkline data={stepsData} color="#22c55e" height={80} width={300} fill={true} />
          {:else}
            <div class="muted text-sm" style="padding:1rem;text-align:center">Keine Daten</div>
          {/if}
        </div>
      </div>
    </section>

    <!-- Training & Todo completion -->
    <section class="section-card">
      <div class="section-header">📊 Abschluss</div>
      <div class="card-body">
        <div class="stat-row">
          <span class="stat-label">Training</span>
          <span class="stat-value">{weekStats.training_completed ?? 0}/{weekStats.training_total ?? 0}</span>
        </div>
        <div class="stat-row">
          <span class="stat-label">To-Dos erledigt</span>
          <span class="stat-value">{weekStats.todo_done ?? 0}/{(weekStats.todo_done ?? 0) + (weekStats.todo_open ?? 0)}</span>
        </div>
        {#if weekStats.todo_completion_rate != null}
          <div style="margin-top:0.5rem">
            <ProgressBar
              current={Math.round((weekStats.todo_completion_rate ?? 0) * 100)}
              target={100}
              label="Erledigungsrate"
              color="#22c55e"
            />
          </div>
        {/if}
      </div>
    </section>
  {:else}
    <div class="loading">
      <span>lade Daten…</span>
    </div>
  {/if}
</div>

<style>
  .week-page {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .week-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0;
  }

  .back-btn {
    padding: 4px 12px;
    border-radius: 8px;
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    color: var(--text-primary);
    cursor: pointer;
    font-size: 0.8125rem;
  }

  h1 {
    font-size: 1.1rem;
    font-weight: 600;
  }

  .card-body {
    padding: 0.75rem;
  }

  .chart-area {
    width: 100%;
    overflow: hidden;
  }

  .chart-area :global(.sparkline) {
    width: 100%;
    height: auto;
  }

  .stat-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.375rem 0;
    border-bottom: 1px solid #333;
  }

  .stat-row:last-child {
    border-bottom: none;
  }

  .stat-label {
    font-size: 0.8125rem;
    color: var(--text-secondary);
  }

  .stat-value {
    font-size: 0.875rem;
    font-weight: 500;
  }

  .loading {
    display: flex;
    justify-content: center;
    padding: 3rem;
    color: var(--text-secondary);
    font-size: 0.875rem;
  }
</style>