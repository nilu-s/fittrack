<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import { fly } from 'svelte/transition';
  import ShoppingList from './ShoppingList.svelte';
  import Icon from './Icon.svelte';
  import type { ShoppingItem, ShoppingList as ShoppingListType } from '$lib/types';
  import { shoppingSuggestions } from '$lib/shopping-suggestions';
  export let open = false;
  export let shopping: ShoppingListType | null = null;
  export let loading = false;
  export let trigger: HTMLElement | null = null;
  export let allowMealImport = true;
  export let query = '';
  export let inline = false;
  const dispatch = createEventDispatcher<{ close: 'keyboard'; toggle: ShoppingItem; remove: ShoppingItem; edit: ShoppingItem; import: number; choose: string }>();
  $: suggestions = shoppingSuggestions(query, shopping?.items ?? []);
  function close() { dispatch('close', 'keyboard'); trigger?.focus(); }
  function onKey(e: KeyboardEvent) { if (open && e.key === 'Escape') close(); }
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
</script>

<svelte:window on:keydown={onKey} />

{#if open}
  <aside id="shopping-quick-panel" class="panel" class:inline aria-label="Einkaufsliste" in:fly={panelEnter()} out:fly={panelExit()}>
    {#if suggestions.length}<section class="suggestions" aria-label={query.trim() ? 'Passende Artikel' : 'Zuletzt verwendet'}><p>{query.trim() ? 'Passende Artikel' : 'Zuletzt verwendet'}</p><ul>{#each suggestions as suggestion}<li><button type="button" onclick={() => dispatch('choose', suggestion)}><span>{suggestion}</span><small>Hinzufügen</small></button></li>{/each}</ul></section>{/if}
    <div class="actions">{#if allowMealImport}<button type="button" onclick={() => dispatch('import', 7)}><Icon name="meal" size={16} />Plan · 7 Tage</button>{:else}<span class="shared-note">Gemeinsame Liste</span>{/if}<a href="/shopping" onclick={close}>Verwalten</a></div>
    <div class="body">{#if loading && !shopping}<p class="loading" role="status">Einkaufsliste wird geladen…</p>{:else}<ShoppingList items={shopping?.items ?? []} on:toggle={(e) => dispatch('toggle', e.detail)} on:edit={(e) => dispatch('edit', e.detail)} on:remove={(e) => dispatch('remove', e.detail)} />{/if}</div>
  </aside>
{/if}

<style>
  .panel { position:fixed; z-index:45; top:5dvh; bottom:5dvh; left:50%; transform:translateX(-50%); width:min(calc(100% - 20px),520px); display:flex; flex-direction:column; gap:10px; padding:16px; border:1px solid var(--border-default); border-radius:var(--radius-modal); background:var(--color-bg); box-shadow:var(--shadow-modal); } .suggestions { display:grid; gap:5px; margin:0; } .suggestions p { margin:0; color:var(--text-tertiary); font-size:11px; font-weight:750; letter-spacing:.05em; text-transform:uppercase; } .suggestions ul { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:5px; margin:0; padding:0; list-style:none; } .suggestions button { display:flex; align-items:center; justify-content:space-between; gap:6px; width:100%; min-height:40px; padding:7px 9px; border:1px solid var(--border-default); border-radius:var(--radius-control); background:var(--surface-raised); color:var(--text-primary); text-align:left; font:inherit; font-size:13px; } .suggestions button small { color:var(--action-primary); font-size:10px; font-weight:750; } .suggestions button:active { background:var(--surface-pressed); } .actions { display:flex; justify-content:space-between; align-items:center; gap:8px; } .actions button,.actions a,.shared-note { display:inline-flex; align-items:center; gap:6px; min-height:32px; color:var(--action-primary); font-size:12px; font-weight:700; } .actions a { text-decoration:none; } .body { min-height:0; overflow:auto; padding-right:2px; } .loading { margin:0; padding:var(--space-4); color:var(--text-tertiary); text-align:center; font-size:13px; } button:focus-visible,a:focus-visible { outline:2px solid var(--status-info); outline-offset:2px; } @media(max-width:360px) { .suggestions ul { grid-template-columns:1fr; } } @media(min-width:900px) { .panel { left:auto; right:max(18px, calc((100vw - 1160px) / 2)); transform:none; width:400px; } }
  .panel.inline { position:static; z-index:auto; top:auto; right:auto; bottom:auto; left:auto; width:auto; min-height:0; transform:none; padding:0; border:0; border-radius:0; background:transparent; box-shadow:none; }
</style>
