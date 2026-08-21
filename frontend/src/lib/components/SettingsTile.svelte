<script lang="ts">
  import Icon from './Icon.svelte';

  export let href: string;
  export let icon: string;
  export let title: string;
  export let description: string;
  export let summary = '';
</script>

<a class="tile" href={href}>
  <div class="tile-icon"><Icon name={icon} size={21} /></div>
  <div class="tile-copy"><strong>{title}</strong><span>{description}</span>{#if summary}<small>{summary}</small>{/if}</div>
  <Icon name="chevron-right" size={18} />
</a>

<style>
  .tile { min-height: 104px; padding: 14px; border-radius: var(--radius-surface); background: var(--surface-default); border: 1px solid var(--border-subtle); color: var(--text-primary); text-decoration: none; display: flex; flex-direction: column; gap: 9px; transition: border-color var(--motion-fast), transform var(--motion-fast), background var(--motion-fast); }
  .tile:active { transform: scale(.98); background: var(--surface-raised); }
  .tile > :global(svg) { align-self: flex-end; color: var(--text-tertiary); margin-top: auto; }
  .tile-icon { width: var(--control-min); height: var(--control-min); border-radius: var(--radius-control); display: flex; align-items: center; justify-content: center; background: var(--surface-raised); color: var(--status-info); }
  .tile-copy { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  strong { font-size: 14px; font-weight: 650; }
  span { color: var(--text-secondary); font-size: 12px; line-height: 1.25; }
  small { color: var(--status-success); font-size: 11px; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
</style>
