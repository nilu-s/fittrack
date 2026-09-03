<script lang="ts">
  import SettingsTile from '$lib/components/SettingsTile.svelte';
</script>

<svelte:head><title>Cronicl - Einstellungen</title></svelte:head>

<div class="page">
  <div class="intro"><p class="eyebrow">Dein Bereich</p><h1>Einstellungen</h1><p>Persönliche Daten, Routinen und Verbindungen an einem Ort.</p></div>
  <div class="section-label">Persönlich</div>
  <section class="settings-list" aria-label="Persönliche Einstellungen">
    <SettingsTile href="/settings/profile" icon="weight" title="Körperprofil" description="Größe und BMI-Berechnung" summary="Private Formeleingaben" />
    <SettingsTile href="/settings/scale" icon="weight" title="Waagenmessungen" description="Eigene Messungen und Verlauf" summary="Fehlerhafte Zuordnung entfernen" />
  </section>
  <div class="section-label">Planung</div>
  <section class="settings-list" aria-label="Planung und Ziele">
    <SettingsTile href="/settings/sport" icon="training" title="Sportprogramm" description="Gym, Cardio und Rotation" summary="Rotation und Cardio-Ziele" />
    <SettingsTile href="/settings/goals" icon="chart" title="Tagesziele" description="Ernährung, Schritte und Schlaf" />
    <SettingsTile href="/settings/meals" icon="meal" title="Mahlzeiten" description="Vorlagen und Gerichte" />
    <SettingsTile href="/settings/todos" icon="todo" title="Wiederkehrende To-dos" description="Routinen für deine Tagesliste" />
  </section>
  <div class="section-label">Gemeinsam</div>
  <section class="settings-list" aria-label="Gemeinsame Bereiche">
    <SettingsTile href="/settings/spaces" icon="todo" title="Gemeinsame Bereiche" description="Haushalt, Mitglieder und Projekte" summary="Geteilte To-dos und Einkauf" />
  </section>
  <div class="section-label">Konto &amp; Daten</div>
  <section class="settings-list" aria-label="Konto und Daten">
    <SettingsTile href="/settings/integrations" icon="refresh" title="Integrationen" description="Google-Konto und Synchronisation" />
    <SettingsTile href="/settings/data" icon="calendar" title="Daten & Export" description="Cronicl-Daten exportieren" />
  </section>
</div>

<style>
  .page { display: flex; flex-direction: column; gap: var(--space-2); padding-top: var(--space-4); }
  .intro { display:grid; gap:4px; padding:0 var(--space-1) var(--space-3); }
  .intro h1 { font-size:25px; letter-spacing:-.035em; }
  .intro p:not(.eyebrow) { color:var(--text-secondary); font-size:13px; }
  .eyebrow { color:var(--status-success); font-size:11px; font-weight:750; letter-spacing:.07em; text-transform:uppercase; }
  .section-label { padding:var(--space-2) var(--space-1) 0; color: var(--text-secondary); font-size: 12px; font-weight:700; }
  .settings-list { overflow: hidden; background: var(--surface-default); border: 1px solid var(--border-subtle); border-radius: var(--radius-surface); }
</style>
