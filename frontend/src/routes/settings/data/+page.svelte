<script lang="ts">
  import SettingsHeader from '$lib/components/SettingsHeader.svelte';
  import { dailyGoals } from '$lib/stores';
  import { api } from '$lib/api';

  $: goals = $dailyGoals;
  let presetLoading = false;
  let presetMessage = '';
  let presetError = '';
  function exportData(format: 'csv' | 'json') {
    const data = { goals, exportedAt: new Date().toISOString() };
    const content = format === 'json' ? JSON.stringify(data, null, 2) : ['key,value', ...Object.entries(goals).map(([key, value]) => `${key},${value}`)].join('\n');
    const blob = new Blob([content], { type: format === 'json' ? 'application/json' : 'text/csv' });
    const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `cronicl-export.${format}`; a.click(); URL.revokeObjectURL(url);
  }

  async function applyDevelopmentPreset() {
    const confirmed = window.confirm('29 Tage Beispieldaten laden? Werte vom heutigen Tag minus 14 bis plus 14 Tage werden für dein Konto überschrieben. Andere Zeiträume bleiben unverändert.');
    if (!confirmed) return;
    presetLoading = true;
    presetError = '';
    presetMessage = '';
    try {
      const result = await api.applyDevelopmentPreset();
      if (!result) throw new Error('Preset request failed');
      presetMessage = `${result.days} Tage, ${result.todos} To-dos, ${result.foods} Lebensmittel, ${result.recipes} Rezepte und ${result.meal_entries} Mahlzeiten sind angelegt.`;
    } catch {
      presetError = 'Beispieldaten konnten nicht angelegt werden. Bitte Verbindung prüfen.';
    } finally {
      presetLoading = false;
    }
  }
</script>

<svelte:head><title>Cronicl - Daten & Export</title></svelte:head>
<div class="page">
  <SettingsHeader title="Daten & Export" subtitle="Deine Cronicl-Daten" />
  <section class="section-card"><div class="section-header">Daten exportieren</div><div class="body"><div class="actions"><button onclick={() => exportData('json')}>JSON exportieren</button><button onclick={() => exportData('csv')}>CSV exportieren</button></div></div></section>
  <section class="section-card preset"><div class="section-header">Entwicklungs-Preset</div><div class="body"><p>Legt für dein Konto 14 Tage Historie und 14 Tage Vorschau ab heute an – mit To-dos, Anreise, Lebensmitteln, Rezepten, Wochenplan und konkreten Mahlzeiten.</p><button class="preset-button" onclick={applyDevelopmentPreset} disabled={presetLoading}>{presetLoading ? 'Beispieldaten werden angelegt…' : '29 Tage Beispieldaten laden'}</button>{#if presetMessage}<p class="success" aria-live="polite">{presetMessage} Öffne die Tagesansicht, um sie zu sehen.</p>{/if}{#if presetError}<p class="error" aria-live="assertive">{presetError}</p>{/if}</div></section>
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
  .preset .body { display:grid; gap:10px; } .preset-button { background:var(--action-primary); border-color:var(--action-primary); color:var(--text-on-accent); font-weight:700; } .preset-button:disabled { opacity:.6; cursor:wait; } .success { color:var(--status-success); } .error { color:var(--status-danger); }
</style>
