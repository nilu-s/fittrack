<script lang="ts">
  import { onMount } from 'svelte';
  import SettingsHeader from '$lib/components/SettingsHeader.svelte';
  import { dailyGoals } from '$lib/stores';
  import { api } from '$lib/api';
  import type { Goals } from '$lib/types';

  let goals = { kcal: 2480, protein: 194, carbs: 258, fat: 78, fiber: 36, freeSugar: 31, freeSugarLimit: 62, steps: 10000, sleepHours: 8 };
  $: goals = $dailyGoals;

  async function saveGoals() {
    dailyGoals.set(goals);
    localStorage.setItem('fittrack-goals', JSON.stringify(goals));
    const payload: Partial<Goals> = { kcal: goals.kcal, protein: goals.protein, carbs: goals.carbs, fat: goals.fat, fiber_g: goals.fiber, free_sugar_g: goals.freeSugar, free_sugar_limit_g: goals.freeSugarLimit, steps: goals.steps, sleep_hours: goals.sleepHours };
    try { await api.updateGoals(payload); } catch { /* local store remains available offline */ }
  }

  onMount(async () => {
    const saved = localStorage.getItem('fittrack-goals');
    if (saved) { try { goals = { ...goals, ...JSON.parse(saved) }; dailyGoals.set(goals); } catch {} }
    try {
      const server = await api.getGoals();
      if (server) { goals = { ...goals, kcal: server.kcal ?? goals.kcal, protein: server.protein ?? goals.protein, carbs: server.carbs ?? goals.carbs, fat: server.fat ?? goals.fat, fiber: server.fiber_g ?? goals.fiber, freeSugar: server.free_sugar_g ?? goals.freeSugar, freeSugarLimit: server.free_sugar_limit_g ?? goals.freeSugarLimit, steps: server.steps ?? goals.steps, sleepHours: server.sleep_hours ?? goals.sleepHours }; dailyGoals.set(goals); localStorage.setItem('fittrack-goals', JSON.stringify(goals)); }
    } catch {}
  });
</script>

<svelte:head><title>FitTrack - Tagesziele</title></svelte:head>
<div class="page">
  <SettingsHeader title="Tagesziele" subtitle="Ernährung, Schritte und Schlaf" />
  <section class="section-card"><div class="section-header">Ziele</div><div class="body">
    <div class="row"><span>Kalorien</span><input type="number" bind:value={goals.kcal} onchange={saveGoals} /><em>kcal</em></div>
    <div class="row"><span>Protein</span><input type="number" bind:value={goals.protein} onchange={saveGoals} /><em>g</em></div>
    <div class="row"><span>Kohlenhydrate</span><input type="number" bind:value={goals.carbs} onchange={saveGoals} /><em>g</em></div>
    <div class="row"><span>Fett</span><input type="number" bind:value={goals.fat} onchange={saveGoals} /><em>g</em></div>
    <div class="row"><span>Ballaststoffe (min.)</span><input type="number" bind:value={goals.fiber} onchange={saveGoals} /><em>g</em></div>
    <div class="row"><span>Freie Zucker (Ziel)</span><input type="number" bind:value={goals.freeSugar} onchange={saveGoals} /><em>g</em></div>
    <div class="row"><span>Freie Zucker (Obergrenze)</span><input type="number" bind:value={goals.freeSugarLimit} onchange={saveGoals} /><em>g</em></div>
    <div class="row"><span>Schritte</span><input type="number" bind:value={goals.steps} onchange={saveGoals} /><em>steps</em></div>
    <div class="row"><span>Schlaf</span><input type="number" bind:value={goals.sleepHours} onchange={saveGoals} /><em>h</em></div>
  </div></section>
</div>

<style>
  .page { display: flex; flex-direction: column; gap: 10px; }
  .body { padding: 12px; }
  .row { display: flex; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 1px solid var(--border); }
  .row:last-child { border-bottom: none; }
  .row span { flex: 1; color: var(--text-dim); font-size: 14px; }
  input { width: 76px; padding: 6px 10px; border-radius: 6px; background: var(--card-2); border: 1px solid var(--border-2); color: var(--text); font-size: 14px; text-align: right; }
  em { width: 42px; color: var(--text-faint); font-size: 12px; font-style: normal; }
</style>
