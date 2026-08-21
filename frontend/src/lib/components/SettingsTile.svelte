<script lang="ts">
  import Icon from './Icon.svelte';

  export let href: string;
  export let icon: string;
  export let title: string;
  export let description: string;
  export let summary = '';
</script>

<a class="settings-row" href={href}>
  <div class="settings-row-icon"><Icon name={icon} size={18} /></div>
  <div class="settings-row-copy">
    <strong>{title}</strong>
    <span>{description}</span>
    {#if summary}<small>{summary}</small>{/if}
  </div>
  <Icon name="chevron-right" size={18} />
</a>

<style>
  .settings-row { display: flex; align-items: center; gap: var(--space-2); min-height: 64px; padding: var(--space-3) var(--space-4); color: var(--text-primary); text-decoration: none; border-bottom: 1px solid var(--border-subtle); transition: background var(--motion-fast); }
  .settings-row:last-child { border-bottom: none; }
  .settings-row:active { background: var(--surface-raised); }
  .settings-row-icon { width: var(--control-min); height: var(--control-min); border-radius: var(--radius-control); display: flex; align-items: center; justify-content: center; flex: 0 0 var(--control-min); background: var(--surface-raised); color: var(--text-secondary); }
  .settings-row-copy { display: flex; flex: 1; flex-direction: column; gap: 1px; min-width: 0; }
  strong { font-size: 14px; font-weight: 600; }
  span { color: var(--text-secondary); font-size: 12px; line-height: 1.3; }
  small { color: var(--status-success); font-size: 11px; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .settings-row > :global(svg) { flex: 0 0 auto; color: var(--text-tertiary); }
</style>
