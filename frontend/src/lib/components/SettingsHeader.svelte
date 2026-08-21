<script lang="ts">
  import Icon from './Icon.svelte';

  export let title: string;
  export let subtitle = '';
  export let back = '/settings';
</script>

<div class="settings-header">
  <a class="back" href={back} aria-label="Zurück"><Icon name="chevron-left" size={20} /></a>
  <div>
    <h1>{title}</h1>
    {#if subtitle}<p>{subtitle}</p>{/if}
  </div>
</div>

<style>
  .settings-header { display: flex; align-items: center; gap: 10px; padding: 8px 0; }
  .back { width: 34px; height: 34px; border-radius: 8px; background: var(--card); border: 1px solid var(--border); color: var(--text-dim); display: flex; align-items: center; justify-content: center; text-decoration: none; flex-shrink: 0; }
  .back:active { background: var(--card-2); }
  h1 { font-size: 18px; font-weight: 650; }
  p { margin-top: 2px; color: var(--text-faint); font-size: 12px; }
</style>
