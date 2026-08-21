<script lang="ts">
  import { onMount } from 'svelte';
  import SettingsHeader from '$lib/components/SettingsHeader.svelte';
  import { api } from '$lib/api';

  let templates: any[] = [];
  onMount(async () => { try { templates = await api.getMealTemplates(); } catch {} });
</script>

<svelte:head><title>FitTrack - Mahlzeiten</title></svelte:head>
<div class="page">
  <SettingsHeader title="Mahlzeiten" subtitle="Vorlagen und Gerichte" />
  <section class="section-card"><div class="section-header">Mahlzeit-Vorlagen</div><div class="body">
    {#if templates.length > 0}{#each templates as t}<div class="row"><span class="slot">Slot {t.slot}</span><strong>{t.name}</strong><span class="kcal">{t.kcal ?? 0} kcal</span></div>{/each}{:else}<div class="empty">Keine Vorlagen</div>{/if}
  </div></section>
  <section class="hint"><strong>Gerichte bearbeiten</strong><p>Gerichte und Portionsgrößen werden direkt an einer Mahlzeit im Tagesplan ausgewählt und angepasst.</p></section>
</div>
<style>
  .page { display: flex; flex-direction: column; gap: 10px; }
  .body { padding: 12px; }
  .row { display: flex; align-items: center; gap: 8px; padding: 10px 0; border-bottom: 1px solid var(--border); }
  .row:last-child { border-bottom: none; }
  .slot { width: 56px; color: var(--text-faint); font-size: 12px; flex-shrink: 0; }
  strong { flex: 1; font-size: 14px; }
  .kcal { color: var(--text-faint); font-size: 12px; }
  .empty { color: var(--text-faint); font-size: 14px; }
  .hint { padding: 14px; border-radius: 12px; background: var(--card); border: 1px solid var(--border); }
  .hint strong { display: block; margin-bottom: 5px; }
  p { color: var(--text-dim); font-size: 13px; line-height: 1.4; }
</style>
