<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import { fly } from 'svelte/transition';
  import Icon from './Icon.svelte';
  import type { Todo } from '$lib/types';

  export let open = false;
  export let todos: Todo[] = [];
  export let loading = false;
  export let panelHeight = 360;
  const dispatch = createEventDispatcher<{ close: 'gesture' | 'keyboard'; toggle: Todo; remove: Todo; resize: number }>();
  let resizeStartY = 0;
  let resizeStartHeight = 0;
  let pendingHeight = 0;
  let resizing = false;
  let prefersReducedMotion = false;

  onMount(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => prefersReducedMotion = media.matches;
    update(); media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  });
  function close() { dispatch('close', 'keyboard'); }
  function onKey(event: KeyboardEvent) { if (open && event.key === 'Escape') close(); }
  function viewportHeight() { return typeof window === 'undefined' ? 900 : window.innerHeight; }
  function closeThreshold() { return Math.round(viewportHeight() * 0.25); }
  function maximumHeight() { return Math.round(viewportHeight() * 0.82); }
  function clampHeight(height: number) { return Math.min(maximumHeight(), Math.max(closeThreshold(), Math.round(height))); }
  function startResize(event: PointerEvent) { resizing = true; resizeStartY = event.clientY; resizeStartHeight = panelHeight; (event.currentTarget as HTMLElement | null)?.setPointerCapture(event.pointerId); }
  function resize(event: PointerEvent) { if (!resizing) return; pendingHeight = resizeStartHeight + resizeStartY - event.clientY; dispatch('resize', clampHeight(pendingHeight)); }
  function endResize() { if (pendingHeight && pendingHeight < closeThreshold()) dispatch('close', 'gesture'); pendingHeight = 0; resizing = false; }
  function resizeWithKeyboard(event: KeyboardEvent) { if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') return; event.preventDefault(); dispatch('resize', clampHeight(panelHeight + (event.key === 'ArrowUp' ? 40 : -40))); }
  function panelEnter() { return { y: 36, opacity: 0, duration: prefersReducedMotion ? 0 : 240 }; }
  function panelExit() { return { y: 24, opacity: 0, duration: prefersReducedMotion ? 0 : 160 }; }
</script>

<svelte:window on:keydown={onKey} />

{#if open}
  <aside id="general-todo-quick-panel" class="panel" style={`--panel-height: ${panelHeight}px`} aria-label="Allgemeine To-do-Liste" in:fly={panelEnter()} out:fly={panelExit()}>
    <div class="resize-handle" role="slider" tabindex="0" aria-label="Höhe der allgemeinen To-do-Liste" aria-valuemin={closeThreshold()} aria-valuemax={maximumHeight()} aria-valuenow={panelHeight} aria-valuetext={`${panelHeight} Pixel`} on:keydown={resizeWithKeyboard} on:pointerdown={startResize} on:pointermove={resize} on:pointerup={endResize} on:pointercancel={() => resizing = false}><span class="handle" aria-hidden="true"></span></div>
    <header><div><p>ALLGEMEINE TO-DOS</p><h2>{todos.filter((todo) => todo.status === 'open').length} offen</h2></div><button class="close" type="button" on:click={close}>Schließen</button></header>
    <p class="hint">Über das Eingabefeld unten direkt und ohne Datum hinzufügen. Ziehe die Leiste oben, um die Ansicht zu teilen.</p>
    <div class="body">
      {#if loading}<p class="loading" role="status">To-dos werden geladen…</p>
      {:else if todos.length}<ul>{#each todos as todo (todo.id)}<li class:done={todo.status === 'done'}><button class="check" type="button" on:click={() => dispatch('toggle', todo)} aria-label={todo.status === 'done' ? `${todo.title} erneut öffnen` : `${todo.title} erledigen`}>{#if todo.status === 'done'}<Icon name="check" size={14} />{/if}</button><strong>{todo.title}</strong><button class="remove" type="button" on:click={() => dispatch('remove', todo)} aria-label={`${todo.title} entfernen`}><Icon name="trash" size={15} /></button></li>{/each}</ul>
      {:else}<p class="loading">Noch keine allgemeinen To-dos.</p>{/if}
    </div>
  </aside>
{/if}

<style>
  .panel { position:fixed; z-index:45; left:50%; bottom:78px; transform:translateX(-50%); width:min(calc(100% - 20px),460px); height:min(var(--panel-height),calc(82dvh - 78px)); display:flex; flex-direction:column; gap:10px; padding:8px 12px 12px; border:1px solid var(--border-default); border-radius:var(--radius-modal); background:var(--color-bg); box-shadow:var(--shadow-modal); } .resize-handle { display:grid; place-items:center; min-height:20px; margin:0 -6px; cursor:ns-resize; touch-action:none; } .handle { display:block; width:36px; height:4px; border-radius:99px; background:var(--border-strong); } header { display:flex; align-items:start; justify-content:space-between; gap:8px; } header p,.hint { margin:0; color:var(--text-tertiary); font-size:10px; font-weight:750; letter-spacing:.07em; } .hint { letter-spacing:0; font-weight:500; } h2 { margin:2px 0 0; font-size:16px; } .close { min-height:32px; padding:5px 8px; border-radius:var(--radius-control); color:var(--text-secondary); font:inherit; font-size:12px; } .body { min-height:0; overflow:auto; padding-right:2px; } ul { margin:0; padding:0; overflow:hidden; list-style:none; border:1px solid var(--border-subtle); border-radius:var(--radius-surface); background:var(--surface-default); } li { display:flex; align-items:center; gap:8px; min-height:54px; padding:7px 9px; border-bottom:1px solid var(--border-subtle); } li:last-child { border-bottom:0; } strong { flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:14px; } .done strong { color:var(--text-tertiary); text-decoration:line-through; } .check { display:grid; place-items:center; flex:0 0 28px; width:28px; height:28px; border:1.5px solid var(--border-strong); border-radius:50%; color:var(--text-on-accent); background:transparent; } .done .check { border-color:var(--action-primary); background:var(--action-primary); } .remove { display:grid; place-items:center; width:30px; min-height:30px; color:var(--text-tertiary); } .loading { margin:0; padding:var(--space-4); color:var(--text-tertiary); text-align:center; font-size:13px; } button:focus-visible,.resize-handle:focus-visible { outline:2px solid var(--status-info); outline-offset:2px; } @media(min-width:900px) { .panel { left:auto; right:max(398px,calc((100vw - 1160px)/2 + 380px)); bottom:24px; transform:none; width:360px; height:min(var(--panel-height),calc(100dvh - 100px)); } }
</style>
