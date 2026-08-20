<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import { currentDate } from '$lib/stores';
  import Sparkline from '$lib/components/Sparkline.svelte';
  import ProgressBar from '$lib/components/ProgressBar.svelte';
  import Icon from '$lib/components/Icon.svelte';
  import type { WeekStats } from '$lib/types';

  let weekStats: WeekStats | null = null;
  let weightData: number[] = [];
  let kcalData: number[] = [];
  let stepsData: number[] = [];

  function goBack() { if (typeof window !== 'undefined') window.history.back(); }

  onMount(async () => {
    try {
      weekStats = await api.getStatsWeek($currentDate);
      const [wt, kt, st] = await Promise.all([api.getStatsTrend('weight', 7), api.getStatsTrend('kcal', 7), api.getStatsTrend('steps', 7)]);
      weightData = (wt?.points ?? []).map((p) => p.value ?? 0).filter((v) => v !== null && v > 0);
      kcalData = (kt?.points ?? []).map((p) => p.value ?? 0).filter((v) => v !== null && v > 0);
      stepsData = (st?.points ?? []).map((p) => p.value ?? 0).filter((v) => v !== null && v > 0);
    } catch {}
  });
</script>

<svelte:head><title>FitTrack - Woche</title></svelte:head>

<div class="page">
  <div class="hdr"><button class="back" onclick={goBack} aria-label="Zurück"><Icon name="chevron-left" size={20} /></button><h1>Wochenübersicht</h1></div>
  {#if weekStats}
    <section class="section-card"><div class="section-header"><span>Gewicht</span><span class="avg">{weekStats.avg_weight ? Number(weekStats.avg_weight).toFixed(1) : '—'} kg Ø</span></div><div class="body"><div class="chart">{#if weightData.length > 0}<Sparkline data={weightData} color="var(--blue)" height={90} width={300} fill={true} />{:else}<div class="no-data">Keine Daten</div>{/if}</div></div></section>
    <section class="section-card"><div class="section-header"><span>Kalorien</span><span class="avg">{weekStats.avg_kcal ? Math.round(Number(weekStats.avg_kcal)) : '—'} kcal Ø</span></div><div class="body"><div class="chart">{#if kcalData.length > 0}<Sparkline data={kcalData} color="var(--amber)" height={90} width={300} fill={true} />{:else}<div class="no-data">Keine Daten</div>{/if}</div></div></section>
    <section class="section-card"><div class="section-header"><span>Schritte</span><span class="avg">{weekStats.avg_steps ? Math.round(Number(weekStats.avg_steps)) : '—'} Ø</span></div><div class="body"><div class="chart">{#if stepsData.length > 0}<Sparkline data={stepsData} color="var(--green)" height={90} width={300} fill={true} />{:else}<div class="no-data">Keine Daten</div>{/if}</div></div></section>
    {#if weekStats.avg_protein != null || weekStats.avg_carbs != null || weekStats.avg_fat != null}
    <section class="section-card"><div class="section-header">Makros Ø</div><div class="body">
      <div class="stat-r"><span class="stat-l">Protein</span><span class="stat-v">{weekStats.avg_protein ? Math.round(Number(weekStats.avg_protein)) : '—'} g</span></div>
      <div class="stat-r"><span class="stat-l">Kohlenhydrate</span><span class="stat-v">{weekStats.avg_carbs ? Math.round(Number(weekStats.avg_carbs)) : '—'} g</span></div>
      <div class="stat-r"><span class="stat-l">Fett</span><span class="stat-v">{weekStats.avg_fat ? Math.round(Number(weekStats.avg_fat)) : '—'} g</span></div>
    </div></section>
    {/if}
    {#if weekStats.avg_sleep_hours != null || weekStats.total_cardio_minutes != null}
    <section class="section-card"><div class="section-header">Schlaf &amp; Cardio</div><div class="body">
      <div class="stat-r"><span class="stat-l">Schlaf Ø</span><span class="stat-v">{weekStats.avg_sleep_hours ? Number(weekStats.avg_sleep_hours).toFixed(1) : '—'} h</span></div>
      <div class="stat-r"><span class="stat-l">Schlafqualität Ø</span><span class="stat-v">{weekStats.avg_sleep_quality ? `${Number(weekStats.avg_sleep_quality).toFixed(1)}/5 ★` : '—'}</span></div>
      <div class="stat-r"><span class="stat-l">Cardio gesamt</span><span class="stat-v">{weekStats.total_cardio_minutes ? Math.round(Number(weekStats.total_cardio_minutes)) : '—'} min</span></div>
    </div></section>
    {/if}
    {#if weekStats.training_streak != null || weekStats.step_goal_streak != null || weekStats.creatine_compliance != null}
    <section class="section-card"><div class="section-header">Streaks</div><div class="body">
      <div class="stat-r"><span class="stat-l">Training</span><span class="stat-v">{weekStats.training_streak ?? '—'} Tage</span></div>
      <div class="stat-r"><span class="stat-l">Schritte-Ziel</span><span class="stat-v">{weekStats.step_goal_streak ?? '—'} Tage</span></div>
      <div class="stat-r"><span class="stat-l">Kreatin</span><span class="stat-v">{weekStats.creatine_compliance ? Math.round(Number(weekStats.creatine_compliance) * 100) : '—'} %</span></div>
    </div></section>
    {/if}
    <section class="section-card"><div class="section-header">Abschluss</div><div class="body">
      <div class="stat-r"><span class="stat-l">Trainingstage</span><span class="stat-v">{weekStats.training_days}<span class="stat-m">/7</span></span></div>
      <div class="stat-r"><span class="stat-l">To-Dos erledigt</span><span class="stat-v">{weekStats.todo_done}<span class="stat-m">/{weekStats.todo_total}</span></span></div>
      {#if weekStats.todo_completion}<div class="comp"><ProgressBar current={Math.round(Number(weekStats.todo_completion))} target={100} label="Erledigungsrate" color="var(--green)" /></div>{/if}
    </div></section>
  {:else}
    <div class="loading"><div class="spinner"></div></div>
  {/if}
</div>

<style>
  .page { display: flex; flex-direction: column; gap: 10px; }
  .hdr { display: flex; align-items: center; gap: 8px; padding: 8px 0; }
  .back { width: 34px; height: 34px; border-radius: 8px; background: var(--card); border: 1px solid var(--border); color: var(--text-dim); cursor: pointer; display: flex; align-items: center; justify-content: center; }
  .back:active { background: var(--card-2); }
  h1 { font-size: 18px; font-weight: 600; }
  .body { padding: 14px; }
  .avg { font-size: 14px; font-weight: 600; color: var(--text); }
  .chart { width: 100%; overflow: hidden; display: flex; justify-content: center; }
  .chart :global(svg) { width: 100%; height: auto; }
  .no-data { padding: 20px; text-align: center; color: var(--text-faint); font-size: 14px; }
  .stat-r { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--border); }
  .stat-r:last-of-type { border-bottom: none; }
  .stat-l { font-size: 14px; color: var(--text-dim); }
  .stat-v { font-size: 15px; font-weight: 600; }
  .stat-m { font-size: 12px; color: var(--text-faint); font-weight: 400; }
  .comp { margin-top: 12px; }
  .loading { display: flex; justify-content: center; padding: 40px; }
  .spinner { width: 28px; height: 28px; border-radius: 50%; border: 2.5px solid var(--card-2); border-top-color: var(--text-dim); animation: spin 0.8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>