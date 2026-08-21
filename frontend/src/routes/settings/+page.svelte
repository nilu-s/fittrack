<script lang="ts">
  import SettingsTile from '$lib/components/SettingsTile.svelte';
  import SettingsHeader from '$lib/components/SettingsHeader.svelte';
</script>

<svelte:head><title>FitTrack - Einstellungen</title></svelte:head>

<div class="page">
  <SettingsHeader title="Einstellungen" subtitle="Bereiche getrennt verwalten" back="/" />
  <section class="intro">
    <span class="eyebrow">FitTrack konfigurieren</span>
    <h2>Was möchtest du einstellen?</h2>
    <p>Sportprogramm, Ernährung, Ziele und Integrationen bleiben fachlich getrennt. Im Tagesplan kommen sie nur dort zusammen, wo daraus konkrete To-dos entstehen.</p>
  </section>

  <div class="tiles">
    <SettingsTile href="/settings/sport" icon="training" title="Sportprogramm" description="Gym + Cardio eigenständig steuern" summary="Rotation und Cardio-Ziele" />
    <SettingsTile href="/settings/goals" icon="chart" title="Tagesziele" description="Ernährungs-, Schritt- und Schlafziele" />
    <SettingsTile href="/settings/meals" icon="meal" title="Mahlzeiten" description="Vorlagen und Gerichte verwalten" />
    <SettingsTile href="/settings/integrations" icon="refresh" title="Integrationen" description="Google-Konto und Synchronisation" />
    <SettingsTile href="/settings/data" icon="calendar" title="Daten & Export" description="FitTrack-Daten exportieren" />
  </div>
</div>

<style>
  .page { display: flex; flex-direction: column; gap: 12px; }
  .intro { padding: 14px; border-radius: var(--radius-modal); background: var(--surface-default); border: 1px solid var(--border-subtle); }
  .eyebrow { display: block; color: var(--status-info); font-size: 11px; font-weight: 650; letter-spacing: .05em; text-transform: uppercase; margin-bottom: 6px; }
  h2 { font-size: 18px; font-weight: 700; margin-bottom: 5px; }
  p { color: var(--text-secondary); font-size: 13px; line-height: 1.45; }
  .tiles { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--space-2); }
  @media (max-width: 360px) { .tiles { grid-template-columns: 1fr; } }
</style>
