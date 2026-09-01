<script lang="ts">
  import SettingsHeader from '$lib/components/SettingsHeader.svelte';
  import { isAuthenticated, authEmail, disconnectGoogle } from '$lib/auth';

  async function handleDisconnect() { await disconnectGoogle(); window.location.reload(); }
</script>

<svelte:head><title>Chronickel - Integrationen</title></svelte:head>
<div class="page">
  <SettingsHeader title="Integrationen" subtitle="Verbindungen und Synchronisation" />
  <section class="section-card"><div class="section-header">Google-Konto</div><div class="body">
    {#if $isAuthenticated}<div class="connected"><div><span>Verbunden als</span><strong>{$authEmail}</strong></div><button onclick={handleDisconnect}>Trennen</button></div>{:else}<div class="empty">Nicht verbunden</div>{/if}
  </div></section>
  <section class="hint"><strong>Synchronisation</strong><p>Schritte und Schlaf können aus Google Fit übernommen werden. Sportprogramm und To-dos bleiben unabhängig von dieser Verbindung steuerbar.</p></section>
</div>
<style>
  .page { display: flex; flex-direction: column; gap: 10px; }
  .body { padding: 12px; }
  .connected { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
  .connected span, .connected strong { display: block; }
  .connected span { color: var(--text-secondary); font-size: 14px; }
  .connected strong { color: var(--status-success); font-size: 12px; margin-top: 3px; }
  button { padding: 8px 12px; border-radius: 8px; background: var(--surface-raised); border: 1px solid var(--border-default); color: var(--text-secondary); cursor: pointer; }
  .empty { color: var(--text-tertiary); font-size: 14px; }
  .hint { padding: 14px; border-radius: 12px; background: var(--surface-default); border: 1px solid var(--border-subtle); }
  .hint strong { display: block; margin-bottom: 5px; }
  p { color: var(--text-secondary); font-size: 13px; line-height: 1.4; }
</style>
