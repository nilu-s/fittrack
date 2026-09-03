<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Icon from './Icon.svelte';
  import type { Space } from '$lib/types';

  export let spaces: Space[] = [];
  export let activeSpaceId: string | null = null;
  const dispatch = createEventDispatcher<{ change: string | null }>();
  let touchStartX = 0;

  $: contexts = [{ id: null as string | null, name: 'Privat' }, ...spaces.map((space) => ({ id: space.id, name: space.name }))];
  $: activeIndex = Math.max(0, contexts.findIndex((context) => context.id === activeSpaceId));
  function choose(id: string | null) { if (id !== activeSpaceId) dispatch('change', id); }
  function move(direction: number) { choose(contexts[(activeIndex + direction + contexts.length) % contexts.length].id); }
  function touchEnd(event: TouchEvent) { const delta = event.changedTouches[0]?.clientX - touchStartX; if (Math.abs(delta) >= 44) move(delta < 0 ? 1 : -1); }
</script>

<nav class="contexts" aria-label="Arbeitsbereich wechseln" ontouchstart={(event) => touchStartX = event.touches[0]?.clientX ?? 0} ontouchend={touchEnd}>
  <button type="button" class="arrow" aria-label="Vorheriger Bereich" onclick={() => move(-1)} disabled={contexts.length < 2}><Icon name="chevron-left" size={18}/></button>
  <div class="context-list" aria-label="Bereiche">{#each contexts as context (context.id ?? 'private')}<button type="button" aria-current={context.id === activeSpaceId ? 'page' : undefined} class:active={context.id === activeSpaceId} onclick={() => choose(context.id)}>{context.name}</button>{/each}</div>
  <button type="button" class="arrow" aria-label="Nächster Bereich" onclick={() => move(1)} disabled={contexts.length < 2}><Icon name="chevron-right" size={18}/></button>
</nav>

<style>
  .contexts { display:grid; grid-template-columns:36px minmax(0,1fr) 36px; align-items:center; gap:4px; min-height:44px; padding:4px; border:1px solid var(--border-subtle); border-radius:var(--radius-surface); background:var(--surface-default); touch-action:pan-y; } .context-list { display:flex; gap:5px; min-width:0; overflow-x:auto; scrollbar-width:none; } .context-list::-webkit-scrollbar { display:none; } button { min-height:34px; border:1px solid var(--border-default); border-radius:var(--radius-full); background:var(--surface-raised); color:var(--text-secondary); font:inherit; font-size:12px; font-weight:650; cursor:pointer; } .context-list button { flex:none; padding:6px 12px; white-space:nowrap; } .context-list button.active { border-color:var(--action-primary); background:var(--action-primary); color:var(--text-on-accent); } .arrow { display:grid; place-items:center; width:36px; padding:0; } button:disabled { opacity:.4; cursor:not-allowed; } button:focus-visible { outline:2px solid var(--status-info); outline-offset:2px; }
</style>
