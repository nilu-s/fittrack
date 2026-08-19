<script lang="ts">
  import { onMount } from 'svelte';
  import { dailyGoals } from '$lib/stores';
  import { api } from '$lib/api';
  import { db } from '$lib/db';

  let goals = { kcal: 2480, protein: 194, carbs: 258, fat: 78, steps: 10000, sleepHours: 8 };
  let templates: any[] = [];
  let googleFitConnected = false;
  let googleCalConnected = false;

  $: goals = $dailyGoals;

  function goBack() {
    if (typeof window !== 'undefined') {
      window.history.back();
    }
  }

  async function saveGoals() {
    dailyGoals.set(goals);
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('fittrack-goals', JSON.stringify(goals));
    }
  }

  function exportData(format: 'csv' | 'json') {
    const data = { goals, templates, exportedAt: new Date().toISOString() };
    const content = format === 'json' ? JSON.stringify(data, null, 2) : toCSV(data);
    const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `fittrack-export.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function toCSV(data: any): string {
    const rows = ['key,value'];
    for (const [k, v] of Object.entries(data.goals)) {
      rows.push(`${k},${v}`);
    }
    return rows.join('\n');
  }

  onMount(async () => {
    if (typeof localStorage !== 'undefined') {
      const saved = localStorage.getItem('fittrack-goals');
      if (saved) {
        try {
          const parsed = JSON.parse(saved);
          goals = { ...goals, ...parsed };
          dailyGoals.set(goals);
        } catch {}
      }
    }

    try {
      templates = await api.getMealTemplates();
    } catch {
      // graceful
    }
  });
</script>

<svelte:head>
  <title>FitTrack - Einstellungen</title>
</svelte:head>

<div class="settings-page">
  <div class="settings-header">
    <button class="back-btn" onclick={goBack}>‹ Zurück</button>
    <h1>Einstellungen</h1>
  </div>

  <!-- Daily Goals -->
  <section class="section-card">
    <div class="section-header">🎯 Tagesziele</div>
    <div class="card-body">
      <div class="goal-row">
        <span class="goal-label">Kalorien</span>
        <input class="goal-input" type="number" bind:value={goals.kcal} onchange={saveGoals} />
        <span class="goal-unit">kcal</span>
      </div>
      <div class="goal-row">
        <span class="goal-label">Protein</span>
        <input class="goal-input" type="number" bind:value={goals.protein} onchange={saveGoals} />
        <span class="goal-unit">g</span>
      </div>
      <div class="goal-row">
        <span class="goal-label">Kohlenhydrate</span>
        <input class="goal-input" type="number" bind:value={goals.carbs} onchange={saveGoals} />
        <span class="goal-unit">g</span>
      </div>
      <div class="goal-row">
        <span class="goal-label">Fett</span>
        <input class="goal-input" type="number" bind:value={goals.fat} onchange={saveGoals} />
        <span class="goal-unit">g</span>
      </div>
      <div class="goal-row">
        <span class="goal-label">Schritte</span>
        <input class="goal-input" type="number" bind:value={goals.steps} onchange={saveGoals} />
        <span class="goal-unit">steps</span>
      </div>
      <div class="goal-row">
        <span class="goal-label">Schlaf</span>
        <input class="goal-input" type="number" bind:value={goals.sleepHours} onchange={saveGoals} />
        <span class="goal-unit">h</span>
      </div>
    </div>
  </section>

  <!-- Meal Templates -->
  <section class="section-card">
    <div class="section-header">🍽️ Mahlzeit-Vorlagen</div>
    <div class="card-body">
      {#if templates.length > 0}
        {#each templates as t}
          <div class="template-row">
            <span class="template-slot">{t.slot}</span>
            <span class="template-name">{t.name}</span>
            <span class="template-kcal muted">{t.default_kcal ?? 0} kcal</span>
          </div>
        {/each}
      {:else}
        <div class="muted text-sm" style="padding:0.75rem 0">Keine Vorlagen</div>
      {/if}
    </div>
  </section>

  <!-- Integrations -->
  <section class="section-card">
    <div class="section-header">🔌 Integrationen</div>
    <div class="card-body">
      <div class="integration-row">
        <span class="int-icon">🏃</span>
        <div class="int-info">
          <span class="int-name">Google Fit</span>
          <span class="int-status" class:connected={googleFitConnected}>
            {googleFitConnected ? '✓ Verbunden' : '○ Nicht verbunden'}
          </span>
        </div>
        <button class="btn">{googleFitConnected ? 'Trennen' : 'Verbinden'}</button>
      </div>
      <div class="integration-row">
        <span class="int-icon">📅</span>
        <div class="int-info">
          <span class="int-name">Google Calendar</span>
          <span class="int-status" class:connected={googleCalConnected}>
            {googleCalConnected ? '✓ Verbunden' : '○ Nicht verbunden'}
          </span>
        </div>
        <button class="btn">{googleCalConnected ? 'Trennen' : 'Verbinden'}</button>
      </div>
    </div>
  </section>

  <!-- Data Export -->
  <section class="section-card">
    <div class="section-header">💾 Daten exportieren</div>
    <div class="card-body">
      <div class="export-row">
        <button class="btn" onclick={() => exportData('json')}>JSON exportieren</button>
        <button class="btn" onclick={() => exportData('csv')}>CSV exportieren</button>
      </div>
    </div>
  </section>
</div>

<style>
  .settings-page {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .settings-header {
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
    padding: 0.625rem;
  }

  .goal-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.375rem 0;
    border-bottom: 1px solid #333;
  }

  .goal-row:last-child {
    border-bottom: none;
  }

  .goal-label {
    flex: 1;
    font-size: 0.8125rem;
    color: var(--text-secondary);
  }

  .goal-input {
    width: 70px;
    padding: 4px 8px;
    border-radius: 6px;
    background: #1a1a1a;
    border: 1px solid var(--card-border);
    color: var(--text-primary);
    font-size: 0.8125rem;
    text-align: right;
  }

  .goal-unit {
    font-size: 0.6875rem;
    color: var(--text-secondary);
    width: 40px;
  }

  .template-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.375rem 0;
    border-bottom: 1px solid #333;
  }

  .template-row:last-child {
    border-bottom: none;
  }

  .template-slot {
    font-size: 0.6875rem;
    color: var(--text-secondary);
    width: 60px;
  }

  .template-name {
    flex: 1;
    font-size: 0.8125rem;
  }

  .template-kcal {
    font-size: 0.6875rem;
  }

  .integration-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid #333;
  }

  .integration-row:last-child {
    border-bottom: none;
  }

  .int-icon {
    font-size: 1.1rem;
  }

  .int-info {
    flex: 1;
    display: flex;
    flex-direction: column;
  }

  .int-name {
    font-size: 0.8125rem;
  }

  .int-status {
    font-size: 0.6875rem;
    color: var(--text-secondary);
  }

  .int-status.connected {
    color: var(--accent-done);
  }

  .export-row {
    display: flex;
    gap: 0.5rem;
  }

  .export-row .btn {
    flex: 1;
  }
</style>