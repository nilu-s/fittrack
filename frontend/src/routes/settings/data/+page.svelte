<script lang="ts">
  import SettingsHeader from '$lib/components/SettingsHeader.svelte';
  import { dailyGoals } from '$lib/stores';
  import { api } from '$lib/api';

  $: goals = $dailyGoals;
  function exportData(format: 'csv' | 'json') {
    const data = { goals, exportedAt: new Date().toISOString() };
    const content = format === 'json' ? JSON.stringify(data, null, 2) : ['key,value', ...Object.entries(goals).map(([key, value]) => `${key},${value}`)].join('\n');
    const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/csv' });
    const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `fittrack-export.${format}`; a.click(); URL.revokeObjectURL(url);
  }
</script>

<svelte:head><title>FitTrack - Daten & Export</title></svelte:head>
<div class="page">
  <SettingsHeader title="Daten & Export" subtitle="Deine FitTrack-Daten" />
  <section class="section-card"><div class="section-header">Daten exportieren</div><div class="body"><div class="actions"><button onclick={() => exportData('json')}>JSON exportieren</button><button onclick={() => exportData('csv')}>CSV exportieren</button></div></div></section>
  <section class="hint"><strong>Keine Löschung hier</strong><p>Historische Sport-, Ernährungs- und Tagesdaten bleiben in ihren jeweiligen Bereichen getrennt erhalten.</p></section>
</div>
<style>
  .page { display: flex; flex-direction: column; gap: 10px; }
  .body { padding: 12px; }
  .actions { display: flex; gap: 8px; }
  button { flex: 1; padding: 11px 10px; border-radius: 8px; background: var(--surface-raised); border: 1px solid var(--border-default); color: var(--text-secondary); cursor: pointer; }
  .hint { padding: 14px; border-radius: 12px; background: var(--surface-default); border: 1px solid var(--border-subtle); }
  .hint strong { display: block; margin-bottom: 5px; }
  p { color: var(--text-secondary); font-size: 13px; line-height: 1.4; }
</style>
