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
  .tile { min-height: 104px; padding: 14px; border-radius: 14px; background: var(--card); border: 1px solid var(--border); color: var(--text); text-decoration: none; display: flex; flex-direction: column; gap: 9px; transition: border-color 0.15s, transform 0.15s; }
  .tile:active { transform: scale(0.98); background: var(--card-2); }
  .tile > :global(svg) { align-self: flex-end; color: var(--text-faint); margin-top: auto; }
  .tile-icon { width: 34px; height: 34px; border-radius: 9px; display: flex; align-items: center; justify-content: center; background: var(--card-2); color: var(--blue); }
  .tile-copy { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  strong { font-size: 14px; font-weight: 650; }
  span { color: var(--text-dim); font-size: 12px; line-height: 1.25; }
  small { color: var(--green); font-size: 11px; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
</style>
