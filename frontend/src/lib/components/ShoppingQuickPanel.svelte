<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import { fly } from 'svelte/transition';
  import ShoppingList from './ShoppingList.svelte';
  import Icon from './Icon.svelte';
  import type { ShoppingItem, ShoppingList as ShoppingListType } from '$lib/types';
  export let open = false;
  export let shopping: ShoppingListType | null = null;
  export let loading = false;
  export let trigger: HTMLElement | null = null;
  export let query = '';
  export let panelHeight = 360;
  const dispatch = createEventDispatcher<{ close: 'gesture' | 'keyboard'; toggle: ShoppingItem; remove: ShoppingItem; edit: ShoppingItem; import: number; choose: string; resize: number }>();
  const catalog = ['Äpfel', 'Bananen', 'Brot', 'Eier', 'Haferflocken', 'Joghurt', 'Käse', 'Kartoffeln', 'Milch', 'Nudeln', 'Paprika', 'Reis', 'Skyr', 'Tomaten'];
  $: suggestions = query.trim().length ? [...new Set([...(shopping?.items.map((item) => item.title) ?? []), ...catalog])].filter((item) => item.toLocaleLowerCase('de').includes(query.trim().toLocaleLowerCase('de'))).slice(0, 5) : [];
  function close() { dispatch('close', 'keyboard'); trigger?.focus(); }
  function onKey(e: KeyboardEvent) { if (open && e.key === 'Escape') close(); }
  let resizeStartY = 0;
  let resizeStartHeight = 0;
  let pendingHeight = 0;
  let resizing = false;
  let prefersReducedMotion = false;

  onMount(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const updateMotionPreference = () => prefersReducedMotion = query.matches;
    updateMotionPreference();
    query.addEventListener('change', updateMotionPreference);
    return () => query.removeEventListener('change', updateMotionPreference);
  });

  function panelEnter() { return { y: 36, opacity: 0, duration: prefersReducedMotion ? 0 : 240 }; }
  function panelExit() { return { y: 24, opacity: 0, duration: prefersReducedMotion ? 0 : 160 }; }
  function viewportHeight() { return typeof window === 'undefined' ? 900 : window.innerHeight; }
  function closeThreshold() { return Math.round(viewportHeight() * 0.25); }
  function maximumHeight() { return Math.round(viewportHeight() * 0.82); }
  function clampHeight(height: number) { return Math.min(maximumHeight(), Math.max(closeThreshold(), Math.round(height))); }
  function startResize(event: PointerEvent) { resizing = true; resizeStartY = event.clientY; resizeStartHeight = panelHeight; (event.currentTarget as HTMLElement | null)?.setPointerCapture(event.pointerId); }
  function resize(event: PointerEvent) {
    if (!resizing) return;
    pendingHeight = resizeStartHeight + resizeStartY - event.clientY;
    dispatch('resize', clampHeight(pendingHeight));
  }
  function endResize() {
    if (pendingHeight && pendingHeight < closeThreshold()) dispatch('close', 'gesture');
    pendingHeight = 0;
    resizeStartY = 0;
    resizing = false;
  }
  function cancelResize() { pendingHeight = 0; resizeStartY = 0; resizing = false; }
  function resizeWithKeyboard(event: KeyboardEvent) { if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') return; event.preventDefault(); dispatch('resize', clampHeight(panelHeight + (event.key === 'ArrowUp' ? 40 : -40))); }
</script>

<svelte:window on:keydown={onKey} />

{#if open}
  <aside id="shopping-quick-panel" class="panel" style={`--panel-height: ${panelHeight}px`} aria-label="Einkaufsliste" in:fly={panelEnter()} out:fly={panelExit()}>
    <div class="resize-handle" role="slider" tabindex="0" aria-label="Höhe der Einkaufsliste" aria-valuemin={closeThreshold()} aria-valuemax={maximumHeight()} aria-valuenow={panelHeight} aria-valuetext={`${panelHeight} Pixel`} onkeydown={resizeWithKeyboard} onpointerdown={startResize} onpointermove={resize} onpointerup={endResize} onpointercancel={cancelResize}><span class="handle" aria-hidden="true"></span></div>
    <header><div><p>EINKAUF</p><h2>{shopping?.items.filter((item) => item.status === 'open').length ?? 0} offen</h2></div><button class="close" type="button" onclick={close}>Schließen</button></header>
    <p class="hint">Über das Eingabefeld in diesem Bereich direkt hinzufügen. Ziehe die Leiste oben, um die Ansicht zu teilen.</p>
    {#if suggestions.length}<ul class="suggestions" aria-label="Passende Artikel">{#each suggestions as suggestion}<li><button type="button" onclick={() => dispatch('choose', suggestion)}>{suggestion}</button></li>{/each}</ul>{/if}
    <div class="actions"><button type="button" onclick={() => dispatch('import', 7)}><Icon name="meal" size={16} />Plan · 7 Tage</button><a href="/shopping" onclick={close}>Verwalten</a></div>
    <div class="body">{#if loading && !shopping}<p class="loading" role="status">Einkaufsliste wird geladen…</p>{:else}<ShoppingList items={shopping?.items ?? []} on:toggle={(e) => dispatch('toggle', e.detail)} on:edit={(e) => dispatch('edit', e.detail)} on:remove={(e) => dispatch('remove', e.detail)} />{/if}</div>
  </aside>
{/if}

<style>
  .panel { position:fixed; z-index:45; left:50%; bottom:78px; transform:translateX(-50%); width:min(calc(100% - 20px),460px); height:min(var(--panel-height), calc(82dvh - 78px)); display:flex; flex-direction:column; gap:10px; padding:8px 12px 12px; border:1px solid var(--border-default); border-radius:var(--radius-modal); background:var(--color-bg); box-shadow:var(--shadow-modal); } .resize-handle { display:grid; place-items:center; min-height:20px; margin:0 -6px; cursor:ns-resize; touch-action:none; } header { display:flex; align-items:start; justify-content:space-between; gap:8px; } header p,.hint { margin:0; color:var(--text-tertiary); font-size:10px; font-weight:750; letter-spacing:.07em; } .hint { letter-spacing:0; font-weight:500; } h2 { margin:2px 0 0; font-size:16px; } .close { min-height:32px; padding:5px 8px; border-radius:var(--radius-control); color:var(--text-secondary); font:inherit; font-size:12px; } .handle { display:block; width:36px; height:4px; border-radius:99px; background:var(--border-strong); } .suggestions { display:flex; gap:5px; margin:0; padding:0; overflow:auto; list-style:none; } .suggestions button { min-height:30px; padding:5px 9px; border:1px solid var(--border-default); border-radius:var(--radius-full); background:var(--surface-raised); color:var(--text-secondary); white-space:nowrap; font-size:11px; } .actions { display:flex; justify-content:space-between; align-items:center; gap:8px; } .actions button,.actions a { display:inline-flex; align-items:center; gap:6px; min-height:32px; color:var(--action-primary); font-size:12px; font-weight:700; } .actions a { text-decoration:none; } .body { min-height:0; overflow:auto; padding-right:2px; } .loading { margin:0; padding:var(--space-4); color:var(--text-tertiary); text-align:center; font-size:13px; } button:focus-visible,a:focus-visible,.resize-handle:focus-visible { outline:2px solid var(--status-info); outline-offset:2px; } @media(min-width:900px) { .panel { left:auto; right:max(18px, calc((100vw - 1160px) / 2)); bottom:24px; transform:none; width:360px; height:min(var(--panel-height), calc(100dvh - 100px)); } }
</style>
