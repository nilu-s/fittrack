<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import { fly } from 'svelte/transition';
  import ShoppingList from './ShoppingList.svelte';
  import Icon from './Icon.svelte';
  import type { ShoppingItem, ShoppingList as ShoppingListType } from '$lib/types';
  import { shoppingSearchTiles, shoppingSuggestions } from '$lib/shopping-suggestions';
  export let open = false;
  export let shopping: ShoppingListType | null = null;
  export let loading = false;
  export let trigger: HTMLElement | null = null;
  export let allowMealImport = true;
  export let query = '';
  export let inline = false;
  export let searchActive = false;
  const dispatch = createEventDispatcher<{ close: 'keyboard'; toggle: ShoppingItem; remove: ShoppingItem; edit: ShoppingItem; import: number; choose: string }>();
  $: suggestions = shoppingSuggestions(query, shopping?.items ?? []);
  $: searchTiles = shoppingSearchTiles(query);
  $: searchInitials = query.trim().split(/\s+/).filter(Boolean).slice(0, 2).map((word) => Array.from(word)[0]?.toLocaleUpperCase()).join('');
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
  <aside id="shopping-quick-panel" class="panel" class:inline class:searchActive aria-label="Einkaufsliste" in:fly={panelEnter()} out:fly={panelExit()}>
    {#if searchActive}
      <div class="search-underlay" inert aria-hidden="true"><ShoppingList items={shopping?.items ?? []} /></div>
      <section class="search-sheet" aria-labelledby="shopping-search-results">
        <p id="shopping-search-results" role="status">{query.trim() ? `${searchTiles.length} ${searchTiles.length === 1 ? 'Treffer' : 'Treffer'}` : 'Artikel eingeben'}</p>
        {#if query.trim()}<ul class="search-grid">{#each searchTiles as tile (tile.title)}<li class={`category-${tile.category}`}><button type="button" onclick={() => dispatch('choose', tile.title)} aria-label={`${tile.title} hinzufügen`}>{#if tile.known}<Icon name={tile.category} size={46}/>{:else}<span class="search-initials" aria-hidden="true">{searchInitials}</span>{/if}<strong>{tile.title}</strong></button></li>{/each}</ul>{/if}
      </section>
    {:else}
      {#if suggestions.length}<section class="suggestions" aria-label={query.trim() ? 'Passende Artikel' : 'Zuletzt verwendet'}><p>{query.trim() ? 'Passende Artikel' : 'Zuletzt verwendet'}</p><ul>{#each suggestions as suggestion}<li><button type="button" onclick={() => dispatch('choose', suggestion)}><span>{suggestion}</span><small>Hinzufügen</small></button></li>{/each}</ul></section>{/if}
      <div class="actions">{#if allowMealImport}<button type="button" onclick={() => dispatch('import', 7)}><Icon name="meal" size={16} />Plan · 7 Tage</button>{:else}<span class="shared-note">Gemeinsame Liste</span>{/if}<a href="/shopping" onclick={close}>Verwalten</a></div>
      <div class="body">{#if loading && !shopping}<p class="loading" role="status">Einkaufsliste wird geladen…</p>{:else}<ShoppingList items={shopping?.items ?? []} on:toggle={(e) => dispatch('toggle', e.detail)} on:edit={(e) => dispatch('edit', e.detail)} on:remove={(e) => dispatch('remove', e.detail)} />{/if}</div>
    {/if}
  </aside>
{/if}

<style>
  .panel { position:fixed; z-index:45; top:5dvh; bottom:5dvh; left:50%; transform:translateX(-50%); width:min(calc(100% - 20px),520px); display:flex; flex-direction:column; gap:10px; padding:16px; border:1px solid var(--border-default); border-radius:var(--radius-modal); background:var(--color-bg); box-shadow:var(--shadow-modal); } .suggestions { display:grid; gap:5px; margin:0; } .suggestions p { margin:0; color:var(--text-tertiary); font-size:11px; font-weight:750; letter-spacing:.05em; text-transform:uppercase; } .suggestions ul { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:5px; margin:0; padding:0; list-style:none; } .suggestions button { display:flex; align-items:center; justify-content:space-between; gap:6px; width:100%; min-height:40px; padding:7px 9px; border:1px solid var(--border-default); border-radius:var(--radius-control); background:var(--surface-raised); color:var(--text-primary); text-align:left; font:inherit; font-size:13px; } .suggestions button small { color:var(--action-primary); font-size:10px; font-weight:750; } .suggestions button:active { background:var(--surface-pressed); } .actions { display:flex; justify-content:space-between; align-items:center; gap:8px; } .actions button,.actions a,.shared-note { display:inline-flex; align-items:center; gap:6px; min-height:32px; color:var(--action-primary); font-size:12px; font-weight:700; } .actions a { text-decoration:none; } .body { min-height:0; overflow:auto; padding-right:2px; } .loading { margin:0; padding:var(--space-4); color:var(--text-tertiary); text-align:center; font-size:13px; } button:focus-visible,a:focus-visible { outline:2px solid var(--status-info); outline-offset:2px; } @media(max-width:360px) { .suggestions ul { grid-template-columns:1fr; } } @media(min-width:900px) { .panel { left:auto; right:max(18px, calc((100vw - 1160px) / 2)); transform:none; width:400px; } }
  .panel.inline.searchActive { position:fixed; z-index:45; inset:0 0 calc(52px + env(safe-area-inset-bottom, 0px)) 0; width:auto; padding:0; border:0; border-radius:0; background:transparent; box-shadow:none; overflow:hidden; } .search-underlay { position:absolute; inset:0; overflow:hidden; padding:var(--space-3); opacity:.35; filter:grayscale(.25); pointer-events:none; } .search-sheet { position:absolute; top:20dvh; right:0; bottom:0; left:0; display:grid; align-content:start; gap:var(--space-2); overflow:auto; padding:var(--space-3) max(10px, env(safe-area-inset-right, 0px)) var(--space-5) max(10px, env(safe-area-inset-left, 0px)); border-top:1px solid var(--border-default); border-radius:var(--radius-modal) var(--radius-modal) 0 0; background:var(--surface-default); box-shadow:0 -10px 28px rgb(0 0 0 / .14); } .search-sheet > p { margin:0; color:var(--text-secondary); font-size:12px; font-weight:700; } .search-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:var(--space-2); margin:0; padding:0; list-style:none; } .search-grid li { aspect-ratio:1; overflow:hidden; border:1px solid color-mix(in srgb,var(--tile-color) 78%,var(--border-default)); border-radius:var(--radius-control); background:var(--tile-color); color:var(--text-on-accent); --tile-color:var(--data-shopping-other); } .search-grid .category-produce { --tile-color:var(--data-shopping-produce); }.search-grid .category-dairy { --tile-color:var(--data-shopping-dairy); }.search-grid .category-bakery { --tile-color:var(--data-shopping-bakery); }.search-grid .category-pantry { --tile-color:var(--data-shopping-pantry); }.search-grid .category-frozen { --tile-color:var(--data-shopping-frozen); }.search-grid .category-beverage { --tile-color:var(--data-shopping-beverage); }.search-grid .category-household { --tile-color:var(--data-shopping-household); } .search-grid button { display:grid; place-content:center; justify-items:center; gap:3px; width:100%; height:100%; padding:var(--space-2); border:0; background:transparent; color:inherit; font:inherit; text-align:center; } .search-grid strong { overflow-wrap:anywhere; font-size:13px; line-height:1.15; } .search-initials { display:grid; place-items:center; min-width:46px; min-height:46px; font-size:26px; font-weight:800; line-height:1; } @media(min-width:560px) { .panel.inline.searchActive { left:50%; width:min(100%, 520px); transform:translateX(-50%); } .search-sheet { border-right:1px solid var(--border-default); border-left:1px solid var(--border-default); } }
  .panel.inline { position:static; z-index:auto; top:auto; right:auto; bottom:auto; left:auto; width:auto; min-height:0; transform:none; padding:0; border:0; border-radius:0; background:transparent; box-shadow:none; }
</style>
