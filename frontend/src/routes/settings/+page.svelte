<script lang="ts">
  import SettingsTile from '$lib/components/SettingsTile.svelte';
</script>

<svelte:head><title>FitTrack - Einstellungen</title></svelte:head>

<div class="page">
  <div class="section-label">Einstellungen</div>
  <section class="settings-list" aria-label="Einstellungsbereiche">
    <SettingsTile href="/settings/sport" icon="training" title="Sportprogramm" description="Gym, Cardio und Rotation" summary="Rotation und Cardio-Ziele" />
    <SettingsTile href="/settings/goals" icon="chart" title="Tagesziele" description="Ernährung, Schritte und Schlaf" />
    <SettingsTile href="/settings/meals" icon="meal" title="Mahlzeiten" description="Vorlagen und Gerichte" />
    <SettingsTile href="/settings/integrations" icon="refresh" title="Integrationen" description="Google-Konto und Synchronisation" />
    <SettingsTile href="/settings/data" icon="calendar" title="Daten & Export" description="FitTrack-Daten exportieren" />
  </section>
</div>

<style>
  .page { display: flex; flex-direction: column; gap: var(--space-2); padding-top: var(--space-2); }
  .section-label { padding: 0 var(--space-1); color: var(--text-secondary); font-size: 13px; font-weight: 500; }
  .settings-list { overflow: hidden; background: var(--surface-default); border: 1px solid var(--border-subtle); border-radius: var(--radius-surface); }
</style>
