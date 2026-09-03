<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Icon from './Icon.svelte';
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
  <p class="eyebrow">Arbeitsbereich</p>
  <div class="wheel">
    <button type="button" class="neighbor previous" onclick={() => move(-1)} disabled={contexts.length < 2} aria-label={`Vorheriger Bereich: ${previous.name}`}>
      <Icon name="chevron-left" size={18} /><span>{previous.name}</span>
    </button>
    <div class="current" aria-live="polite"><span>{current.name}</span></div>
    <button type="button" class="neighbor next" onclick={() => move(1)} disabled={contexts.length < 2} aria-label={`Nächster Bereich: ${next.name}`}>
      <span>{next.name}</span><Icon name="chevron-right" size={18} />
    </button>
  </div>
  {#if contexts.length > 1}<p class="hint">Im Tagesablauf nach links oder rechts wischen</p>{/if}
</section>

<style>
  .workspace-focus { display:grid; gap:5px; padding:5px 0 2px; overflow:hidden; }
  .eyebrow,.hint { margin:0; text-align:center; color:var(--text-tertiary); font-size:10px; font-weight:700; letter-spacing:.07em; text-transform:uppercase; }
  .hint { letter-spacing:0; text-transform:none; font-weight:500; }
  .wheel { display:grid; grid-template-columns:minmax(0,1fr) minmax(116px,1.2fr) minmax(0,1fr); align-items:center; gap:6px; }
  .current { display:grid; place-items:center; min-height:42px; padding:0 14px; border:1px solid var(--action-primary); border-radius:var(--radius-full); background:var(--action-primary); color:var(--text-on-accent); box-shadow:0 5px 14px color-mix(in srgb, var(--action-primary) 25%, transparent); font-size:14px; font-weight:750; }
  .current span,.neighbor span { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .neighbor { display:flex; align-items:center; min-width:0; gap:2px; padding:8px 2px; border:0; background:transparent; color:var(--text-tertiary); font:inherit; font-size:12px; cursor:pointer; }
  .previous { justify-content:flex-end; text-align:right; } .next { justify-content:flex-start; text-align:left; }
  .neighbor:focus-visible { outline:2px solid var(--status-info); outline-offset:2px; border-radius:var(--radius-control); }
  .neighbor:disabled { visibility:hidden; }
</style>
