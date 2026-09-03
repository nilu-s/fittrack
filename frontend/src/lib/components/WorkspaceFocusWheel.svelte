<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import type { Space } from '$lib/types';

  export let spaces: Space[] = [];
  export let activeSpaceId: string | null = null;
  const dispatch = createEventDispatcher<{ change: string | null }>();

  $: contexts = [{ id: null as string | null, name: 'Privat' }, ...spaces.map((space) => ({ id: space.id, name: space.name }))];
  $: activeIndex = Math.max(0, contexts.findIndex((context) => context.id === activeSpaceId));
  $: previous = contexts[(activeIndex - 1 + contexts.length) % contexts.length];
  $: current = contexts[activeIndex];
  $: next = contexts[(activeIndex + 1) % contexts.length];

  function move(direction: number) {
    if (contexts.length < 2) return;
    dispatch('change', contexts[(activeIndex + direction + contexts.length) % contexts.length].id);
  }
</script>

<section class="workspace-focus" aria-label="Aktiver Arbeitsbereich">
  <div class="wheel">
    <button type="button" class="neighbor previous" onclick={() => move(-1)} disabled={contexts.length < 2} aria-label={`Vorheriger Bereich: ${previous.name}`}>
      <span>{previous.name}</span>
    </button>
    <div class="current" aria-live="polite"><span>{current.name}</span></div>
    <button type="button" class="neighbor next" onclick={() => move(1)} disabled={contexts.length < 2} aria-label={`Nächster Bereich: ${next.name}`}>
      <span>{next.name}</span>
    </button>
  </div>
</section>

<style>
  .workspace-focus { overflow:hidden; height:30px; padding:0; }
  .wheel { display:grid; grid-template-columns:minmax(0,1fr) minmax(88px,1.15fr) minmax(0,1fr); align-items:center; gap:8px; height:30px; }
  .current { display:grid; place-items:center; align-self:stretch; padding:0 10px 2px; border-bottom:2px solid var(--action-primary); color:var(--text-primary); font-size:13px; font-weight:750; }
  .current span,.neighbor span { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .neighbor { display:flex; align-items:center; min-width:0; padding:4px 2px; border:0; background:transparent; color:var(--text-tertiary); font:inherit; font-size:11px; cursor:pointer; opacity:.72; }
  .previous { justify-content:flex-end; text-align:right; } .next { justify-content:flex-start; text-align:left; }
  .neighbor:focus-visible { outline:2px solid var(--status-info); outline-offset:2px; border-radius:var(--radius-control); }
  .neighbor:disabled { visibility:hidden; }
</style>
