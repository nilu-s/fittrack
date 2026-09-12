<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import type { Space } from '$lib/types';

  export let spaces: Space[] = [];
  export let activeSpaceId: string | null = null;
  export let showAllTodos = false;
  export let motionDirection = 0;
  export let motionToken = 0;
  const dispatch = createEventDispatcher<{ change: { spaceId: string | null; showAllTodos: boolean; direction: number }; manage: string }>();
  let longPress: ReturnType<typeof setTimeout> | undefined;
  let suppressClick = false;
  let animationDirection = 0;
  let animationFrame: number | undefined;
  let swipeStartX = 0;
  let swipeStartY = 0;
  let trackingSwipe = false;

  $: contexts = [
    { id: 'all' as const, name: 'Übersicht', showAllTodos: true },
    ...spaces.map((space) => ({ id: space.id, name: space.name, showAllTodos: false })),
  ];
  $: activeIndex = Math.max(0, contexts.findIndex((context) => showAllTodos ? context.showAllTodos : !context.showAllTodos && context.id === activeSpaceId));
  $: previous = activeIndex > 0 ? contexts[activeIndex - 1] : null;
  $: current = contexts[activeIndex];
  $: next = activeIndex < contexts.length - 1 ? contexts[activeIndex + 1] : null;

  function move(direction: number) {
    const targetIndex = activeIndex + direction;
    if (targetIndex < 0 || targetIndex >= contexts.length) return;
    const context = contexts[targetIndex];
    dispatch('change', { spaceId: context.showAllTodos ? null : context.id, showAllTodos: context.showAllTodos, direction });
  }
  function animateMovement(direction: number) {
    if (!direction || typeof window === 'undefined') return;
    animationDirection = 0;
    if (animationFrame) cancelAnimationFrame(animationFrame);
    animationFrame = requestAnimationFrame(() => { animationDirection = direction; });
  }
  $: if (motionToken) animateMovement(motionDirection);
  function startSwipe(event: TouchEvent) {
    swipeStartX = event.touches[0]?.clientX ?? 0;
    swipeStartY = event.touches[0]?.clientY ?? 0;
    trackingSwipe = true;
  }
  function trackSwipe(event: TouchEvent) {
    if (!trackingSwipe) return;
    const touch = event.touches[0];
    if (!touch) return;
    const dx = touch.clientX - swipeStartX;
    const dy = touch.clientY - swipeStartY;
    if (Math.abs(dx) > 10 && Math.abs(dx) > Math.abs(dy)) event.preventDefault();
  }
  function finishSwipe(event: TouchEvent) {
    if (!trackingSwipe) return;
    trackingSwipe = false;
    const touch = event.changedTouches[0];
    if (!touch) return;
    const dx = touch.clientX - swipeStartX;
    const dy = touch.clientY - swipeStartY;
    if (Math.abs(dx) >= 48 && Math.abs(dx) > Math.abs(dy) * 1.15) move(dx < 0 ? 1 : -1);
  }
  function startManage() {
    if (!activeSpaceId) return;
    suppressClick = false;
    longPress = setTimeout(() => { suppressClick = true; dispatch('manage', activeSpaceId!); }, 650);
  }
  function cancelManage() { if (longPress) clearTimeout(longPress); longPress = undefined; }
  function manage() { if (!activeSpaceId || suppressClick) { suppressClick = false; return; } dispatch('manage', activeSpaceId); }
</script>

<section class="workspace-focus" aria-label="Aktiver Arbeitsbereich" ontouchstart={startSwipe} ontouchmove={trackSwipe} ontouchend={finishSwipe} ontouchcancel={() => trackingSwipe = false}>
  <div class="wheel" class:motion-forward={animationDirection > 0} class:motion-backward={animationDirection < 0}>
    <button type="button" class="neighbor previous" onclick={() => move(-1)} disabled={!previous} aria-label={previous ? `Vorheriger Bereich: ${previous.name}` : 'Kein vorheriger Bereich'}>
      <span>{previous?.name ?? ''}</span>
    </button>
    {#if activeSpaceId && !showAllTodos}<button type="button" class="current" aria-label={`Einstellungen für ${current.name} öffnen`} onpointerdown={startManage} onpointerup={cancelManage} onpointerleave={cancelManage} onpointercancel={cancelManage} onclick={manage}><span>{current.name}</span></button>
    {:else}<div class="current" aria-live="polite"><span>{current.name}</span></div>{/if}
    <button type="button" class="neighbor next" onclick={() => move(1)} disabled={!next} aria-label={next ? `Nächster Bereich: ${next.name}` : 'Kein nächster Bereich'}>
      <span>{next?.name ?? ''}</span>
    </button>
  </div>
</section>

<style>
  .workspace-focus { overflow:hidden; height:var(--control-min); padding:0; touch-action:pan-y; }
  .wheel { display:grid; grid-template-columns:minmax(0,1fr) minmax(88px,1.15fr) minmax(0,1fr); align-items:center; gap:8px; height:var(--control-min); }
  .current { display:grid; place-items:center; align-self:stretch; padding:0 10px 2px; border:0; border-bottom:2px solid var(--action-primary); background:transparent; color:var(--text-primary); font:inherit; font-size:13px; font-weight:750; cursor:pointer; }
  .current span,.neighbor span { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .neighbor { display:flex; align-items:center; min-width:0; padding:4px 2px;min-height:var(--control-min); border:0; background:transparent; color:var(--text-tertiary); font:inherit; font-size:11px; cursor:pointer; opacity:1; }
  .previous { justify-content:flex-end; text-align:right; } .next { justify-content:flex-start; text-align:left; }
  .neighbor:focus-visible,.current:focus-visible { outline:2px solid var(--status-info); outline-offset:2px; border-radius:var(--radius-control); }
  .neighbor:disabled { visibility:hidden; }
  .motion-forward { animation:workspace-enter-forward 220ms cubic-bezier(.2,.8,.2,1); }
  .motion-backward { animation:workspace-enter-backward 220ms cubic-bezier(.2,.8,.2,1); }
  @keyframes workspace-enter-forward { from { opacity:.45; transform:translateX(18px); } to { opacity:1; transform:translateX(0); } }
  @keyframes workspace-enter-backward { from { opacity:.45; transform:translateX(-18px); } to { opacity:1; transform:translateX(0); } }
  @media (prefers-reduced-motion: reduce) { .motion-forward,.motion-backward { animation:none; } }
</style>
