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
  <div class="hdr"><button class="back" onclick={goBack} aria-label="Zurück"><Icon name="chevron-left" size={20} /></button><div><p class="eyebrow">Rückblick</p><h1>Deine Woche</h1></div></div>
  {#if weekStats}
    <section class="section-card"><div class="section-header"><span>Gewicht</span><span class="avg">{weekStats.avg_weight ? Number(weekStats.avg_weight).toFixed(1) : '—'} kg Ø</span></div><div class="body"><div class="chart">{#if weightData.length > 0}<Sparkline data={weightData} color="var(--status-info)" height={90} width={300} fill={true} />{:else}<div class="no-data">Keine Daten</div>{/if}</div></div></section>
    <section class="section-card"><div class="section-header"><span>Kalorien</span><span class="avg">{weekStats.avg_kcal ? Math.round(Number(weekStats.avg_kcal)) : '—'} kcal Ø</span></div><div class="body"><div class="chart">{#if kcalData.length > 0}<Sparkline data={kcalData} color="var(--status-warning)" height={90} width={300} fill={true} />{:else}<div class="no-data">Keine Daten</div>{/if}</div></div></section>
    <section class="section-card"><div class="section-header"><span>Schritte</span><span class="avg">{weekStats.avg_steps ? Math.round(Number(weekStats.avg_steps)) : '—'} Ø</span></div><div class="body"><div class="chart">{#if stepsData.length > 0}<Sparkline data={stepsData} color="var(--status-success)" height={90} width={300} fill={true} />{:else}<div class="no-data">Keine Daten</div>{/if}</div></div></section>
    {#if weekStats.avg_protein != null || weekStats.avg_carbs != null || weekStats.avg_fat != null || weekStats.avg_fiber != null || weekStats.avg_sugar != null || weekStats.avg_free_sugar != null}
    <section class="section-card"><div class="section-header">Makros Ø</div><div class="body">
      <div class="stat-r"><span class="stat-l">Protein</span><span class="stat-v">{weekStats.avg_protein ? Math.round(Number(weekStats.avg_protein)) : '—'} g</span></div>
      <div class="stat-r"><span class="stat-l">Kohlenhydrate</span><span class="stat-v">{weekStats.avg_carbs ? Math.round(Number(weekStats.avg_carbs)) : '—'} g</span></div>
      <div class="stat-r"><span class="stat-l">Fett</span><span class="stat-v">{weekStats.avg_fat ? Math.round(Number(weekStats.avg_fat)) : '—'} g</span></div>
      <div class="stat-r"><span class="stat-l">Ballaststoffe</span><span class="stat-v">{weekStats.avg_fiber != null ? Math.round(Number(weekStats.avg_fiber)) : '—'} g</span></div>
      <div class="stat-r"><span class="stat-l">Freie Zucker</span><span class="stat-v">{weekStats.avg_free_sugar != null ? Math.round(Number(weekStats.avg_free_sugar)) : '—'} g</span></div>
      <div class="stat-r"><span class="stat-l">Zucker gesamt</span><span class="stat-v">{weekStats.avg_sugar != null ? Math.round(Number(weekStats.avg_sugar)) : '—'} g</span></div>
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
      {#if weekStats.todo_completion}<div class="comp"><ProgressBar current={Math.round(Number(weekStats.todo_completion))} target={100} label="Erledigungsrate" color="var(--status-success)" /></div>{/if}
    </div></section>
  {:else}
    <div class="loading"><div class="spinner"></div></div>
  {/if}
</div>

<style>
  .page { display: flex; flex-direction: column; gap: var(--space-3); padding-top:var(--space-2); }
  .hdr { display: flex; align-items: center; gap: var(--space-2); padding:8px 0 var(--space-2); }
  .back { width:var(--control-min); height:var(--control-min); border-radius:var(--radius-control); background:var(--surface-default); border:1px solid var(--border-subtle); color:var(--text-secondary); cursor:pointer; display:flex; align-items:center; justify-content:center; }
  .back:active { background:var(--surface-raised); }
  .eyebrow { color:var(--status-success); font-size:11px; font-weight:750; letter-spacing:.07em; text-transform:uppercase; }
  h1 { font-size:24px; letter-spacing:-.035em; font-weight:700; }
  .body { padding: 14px; }
  .avg { font-size:13px; font-weight:700; color:var(--text-primary); }
  .chart { width: 100%; overflow: hidden; display: flex; justify-content: center; }
  .chart :global(svg) { width: 100%; height: auto; }
  .no-data { padding: 20px; text-align: center; color: var(--text-tertiary); font-size: 14px; }
  .stat-r { display:flex; justify-content:space-between; align-items:center; padding:10px 0; border-bottom:1px solid var(--border-subtle); }
  .stat-r:last-of-type { border-bottom: none; }
  .stat-l { font-size: 14px; color: var(--text-secondary); }
  .stat-v { font-size: 15px; font-weight: 600; }
  .stat-m { font-size: 12px; color: var(--text-tertiary); font-weight: 400; }
  .comp { margin-top: 12px; }
  .loading { display: flex; justify-content: center; padding: 40px; }
  .spinner { width: 28px; height: 28px; border-radius: 50%; border: 2.5px solid var(--surface-raised); border-top-color: var(--text-secondary); animation: spin 0.8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
