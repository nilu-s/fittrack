<script lang="ts">
  import { onMount } from 'svelte';
  import { dailyGoals } from '$lib/stores';
  import { api } from '$lib/api';
  import { db } from '$lib/db';
  import { isAuthenticated, authEmail, logout, disconnectGoogle } from '$lib/auth';
  import { goto } from '$app/navigation';
  import Icon from '$lib/components/Icon.svelte';
  import type { Goals } from '$lib/types';

  let goals = { kcal: 2480, protein: 194, carbs: 258, fat: 78, steps: 10000, sleepHours: 8 };
  let templates: any[] = [];
  $: goals = $dailyGoals;

  function goBack() { if (typeof window !== 'undefined') window.history.back(); }
  async function handleDisconnectGoogle() { await disconnectGoogle(); window.location.reload(); }
  async function handleLogout() { await logout(); goto('/login'); }
  async function saveGoals() {
    dailyGoals.set(goals);
    if (typeof localStorage !== 'undefined') localStorage.setItem('fittrack-goals', JSON.stringify(goals));
    try {
      const payload: Partial<Goals> = {
        kcal: goals.kcal,
        protein: goals.protein,
        carbs: goals.carbs,
        fat: goals.fat,
        steps: goals.steps,
        sleep_hours: goals.sleepHours,
      };
      await api.updateGoals(payload);
    } catch {
      // offline / silent fail — store already updated locally
    }
  }
  function exportData(format: 'csv' | 'json') { const data = { goals, templates, exportedAt: new Date().toISOString() }; const content = format === 'json' ? JSON.stringify(data, null, 2) : toCSV(data); const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/csv' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `fittrack-export.${format}`; a.click(); URL.revokeObjectURL(url); }
  function toCSV(data: any): string { const rows = ['key,value']; for (const [k, v] of Object.entries(data.goals)) rows.push(`${k},${v}`); return rows.join('\n'); }

  onMount(async () => {
    if (typeof localStorage !== 'undefined') { const saved = localStorage.getItem('fittrack-goals'); if (saved) { try { const parsed = JSON.parse(saved); goals = { ...goals, ...parsed }; dailyGoals.set(goals); } catch {} } }
    try {
      const serverGoals = await api.getGoals();
      if (serverGoals) {
        goals = {
          ...goals,
          kcal: serverGoals.kcal ?? goals.kcal,
          protein: serverGoals.protein ?? goals.protein,
          carbs: serverGoals.carbs ?? goals.carbs,
          fat: serverGoals.fat ?? goals.fat,
          steps: serverGoals.steps ?? goals.steps,
          sleepHours: serverGoals.sleep_hours ?? goals.sleepHours,
        };
        dailyGoals.set(goals);
        if (typeof localStorage !== 'undefined') localStorage.setItem('fittrack-goals', JSON.stringify(goals));
      }
    } catch {}
    try { templates = await api.getMealTemplates(); } catch {}
  });
</script>

<svelte:head><title>FitTrack - Einstellungen</title></svelte:head>

<div class="page">
  <div class="hdr"><button class="back" onclick={goBack} aria-label="Zurück"><Icon name="chevron-left" size={20} /></button><h1>Einstellungen</h1></div>
  <section class="section-card"><div class="section-header">Tagesziele</div><div class="body">
    <div class="row"><span class="row-l">Kalorien</span><input type="number" bind:value={goals.kcal} onchange={saveGoals} /><span class="row-u">kcal</span></div>
    <div class="row"><span class="row-l">Protein</span><input type="number" bind:value={goals.protein} onchange={saveGoals} /><span class="row-u">g</span></div>
    <div class="row"><span class="row-l">Kohlenhydrate</span><input type="number" bind:value={goals.carbs} onchange={saveGoals} /><span class="row-u">g</span></div>
    <div class="row"><span class="row-l">Fett</span><input type="number" bind:value={goals.fat} onchange={saveGoals} /><span class="row-u">g</span></div>
    <div class="row"><span class="row-l">Schritte</span><input type="number" bind:value={goals.steps} onchange={saveGoals} /><span class="row-u">steps</span></div>
    <div class="row"><span class="row-l">Schlaf</span><input type="number" bind:value={goals.sleepHours} onchange={saveGoals} /><span class="row-u">h</span></div>
  </div></section>
  <section class="section-card"><div class="section-header">Mahlzeit-Vorlagen</div><div class="body">
    {#if templates.length > 0}{#each templates as t}<div class="row"><span class="row-l slot">Slot {t.slot}</span><span class="row-name">{t.name}</span><span class="row-kcal">{t.kcal ?? 0} kcal</span></div>{/each}{:else}<div class="empty">Keine Vorlagen</div>{/if}
  </div></section>
  <section class="section-card"><div class="section-header">Google-Konto</div><div class="body">
    {#if $isAuthenticated}<div class="g-row"><div><span class="g-name">Verbunden als</span><span class="g-status connected">{$authEmail}</span></div><button class="btn" onclick={handleDisconnectGoogle}>Trennen</button></div>{:else}<div class="empty">Nicht verbunden</div>{/if}
  </div></section>
  <section class="section-card"><div class="section-header">Daten exportieren</div><div class="body"><div class="exp"><button class="btn" onclick={() => exportData('json')}>JSON</button><button class="btn" onclick={() => exportData('csv')}>CSV</button></div></div></section>
</div>

<style>
  .page { display: flex; flex-direction: column; gap: 10px; }
  .hdr { display: flex; align-items: center; gap: 8px; padding: 8px 0; }
  .back { width: 34px; height: 34px; border-radius: 8px; background: var(--card); border: 1px solid var(--border); color: var(--text-dim); cursor: pointer; display: flex; align-items: center; justify-content: center; }
  .back:active { background: var(--card-2); }
  h1 { font-size: 18px; font-weight: 600; }
  .body { padding: 12px; }
  .row { display: flex; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 1px solid var(--border); }
  .row:last-child { border-bottom: none; }
  .row-l { flex: 1; font-size: 14px; color: var(--text-dim); }
  .row-l.slot { font-size: 12px; width: 56px; flex: 0 0 auto; }
  .row-name { flex: 1; font-size: 14px; font-weight: 500; }
  .row-kcal { font-size: 12px; color: var(--text-faint); }
  input { width: 76px; padding: 6px 10px; border-radius: 6px; background: var(--card-2); border: 1px solid var(--border-2); color: var(--text); font-size: 14px; text-align: right; }
  input:focus { border-color: var(--blue); }
  .row-u { font-size: 12px; color: var(--text-faint); width: 40px; }
  .g-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 8px 0; }
  .g-name { font-size: 14px; color: var(--text-dim); display: block; }
  .g-status { font-size: 12px; color: var(--text-faint); display: block; }
  .g-status.connected { color: var(--green); }
  .exp { display: flex; gap: 8px; }
  .exp .btn { flex: 1; }
  .empty { padding: 12px 0; color: var(--text-faint); font-size: 14px; }
</style>