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
  .settings-header { display: flex; align-items: center; gap: var(--space-2); padding: 8px 0; }
  .back { width: var(--control-min); height: var(--control-min); border-radius: var(--radius-control); background: var(--surface-default); border: 1px solid var(--border-subtle); color: var(--text-secondary); display: flex; align-items: center; justify-content: center; text-decoration: none; flex-shrink: 0; }
  .back:active { background: var(--surface-raised); }
  h1 { font-size: 18px; font-weight: 650; }
  p { margin-top: 2px; color: var(--text-tertiary); font-size: 12px; }
</style>
