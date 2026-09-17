<script lang="ts">
  import ShoppingArticleIcon from './ShoppingArticleIcon.svelte';
  import type { ShoppingItem } from '$lib/types';
  export let items: ShoppingItem[] = [];
  export let busy = false;
  import { createEventDispatcher, tick } from 'svelte';
  const dispatch = createEventDispatcher<{ toggle: ShoppingItem; remove: ShoppingItem; edit: ShoppingItem }>();
  $: grouped = { open: items.filter((item) => item.status !== 'done'), done: items.filter((item) => item.status === 'done') };
  let focusedId: string | null = null;
  let previousItems = items;
  let pressTimer: ReturnType<typeof setTimeout> | undefined;
  let pressOpened = false;
  $: if (items !== previousItems) {
    previousItems = items;
    if (focusedId) {
      const id = focusedId;
      tick().then(() => {
        if (document.activeElement === document.body) document.querySelector<HTMLButtonElement>(`button[data-shopping-id="${CSS.escape(id)}"]`)?.focus();
      });
    }
  }
  function quantity(item: ShoppingItem) { return item.quantity == null ? '' : `${Number(item.quantity.toFixed(3))} ${item.unit ?? ''}`.trim(); }
  function clearPress() { if (pressTimer) clearTimeout(pressTimer); pressTimer = undefined; }
  function openDetails(item: ShoppingItem) { clearPress(); pressOpened = true; dispatch('edit', item); }
  function startPress(item: ShoppingItem, event: PointerEvent) {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    pressOpened = false;
    clearPress();
    pressTimer = setTimeout(() => openDetails(item), 550);
  }
  function toggle(item: ShoppingItem) {
    if (pressOpened) { pressOpened = false; return; }
    dispatch('toggle', item);
  }
  function keydown(item: ShoppingItem, event: KeyboardEvent) {
    if (event.key === 'ContextMenu' || (event.shiftKey && event.key === 'F10')) {
      event.preventDefault();
      openDetails(item);
    }
  }
</script>

<div class="shopping-list" aria-live="polite">
  {#each Object.entries(grouped) as [key, group] (key)}
    {#if group.length}
    <section aria-labelledby={`shopping-category-${key}`}>
      <h3 id={`shopping-category-${key}`}>{key === 'open' ? 'Noch einkaufen' : 'Zuletzt verwendet'} · {group.length}</h3>
      <ul>
        {#each group as item (item.id)}
          <li class:done={item.status === 'done'} class={`category-${item.category_key}`}>
            <button onfocus={() => focusedId = item.id} data-shopping-id={item.id} class="tile" type="button" role="checkbox" aria-checked={item.status === 'done'} onclick={() => toggle(item)} oncontextmenu={(event) => { event.preventDefault(); openDetails(item); }} onpointerdown={(event) => startPress(item, event)} onpointerup={clearPress} onpointerleave={clearPress} onpointercancel={clearPress} onpointermove={clearPress} onkeydown={(event) => keydown(item, event)} disabled={busy} aria-label={`${item.status === 'done' ? `${item.title} erneut öffnen` : `${item.title} erledigen`}. Details über langes Drücken oder Kontextmenü.`}>
              <ShoppingArticleIcon pictogramUrl={item.pictogram_url} iconKey={item.icon_key} label={item.title} size={48} />
              <strong>{item.title}</strong>
              {#if quantity(item) || item.note}<small>{[quantity(item), item.note].filter(Boolean).join(' · ')}</small>{/if}
              {#if item.source !== 'manual'}<span class="source">Aus dem Plan</span>{/if}
            </button>
          </li>
        {/each}
      </ul>
    </section>
    {/if}
  {/each}
  {#if !items.length}
    <p class="empty">Noch nichts auf der Einkaufsliste.</p>
  {/if}
</div>

<style>
  .shopping-list { display:grid; gap:var(--space-5); }
  section { min-width:0; }
  h3 { margin:0 0 var(--space-2); color:var(--text-secondary); font-size:13px; font-weight:750; }
  ul { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:var(--space-2); margin:0; padding:0; list-style:none; }
  li { position:relative; min-width:0; aspect-ratio:1; overflow:hidden; border:1px solid color-mix(in srgb,var(--tile-color) 78%,var(--border-default)); border-radius:var(--radius-control); background:var(--tile-color); color:var(--text-on-accent); --tile-color:var(--data-shopping-other); }
  .category-produce { --tile-color:var(--data-shopping-produce); }.category-dairy { --tile-color:var(--data-shopping-dairy); }.category-bakery { --tile-color:var(--data-shopping-bakery); }.category-pantry { --tile-color:var(--data-shopping-pantry); }.category-frozen { --tile-color:var(--data-shopping-frozen); }.category-beverage { --tile-color:var(--data-shopping-beverage); }.category-household { --tile-color:var(--data-shopping-household); }
  li.done { background:color-mix(in srgb,var(--tile-color) 65%,var(--surface-default)); opacity:.7; }
  .tile { position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:3px; width:100%; min-height:var(--control-min); padding:8px; color:inherit; text-align:center; touch-action:manipulation; }
  strong { display:-webkit-box; -webkit-line-clamp:2; line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; max-width:100%; overflow-wrap:anywhere; font-size:14px; line-height:1.2; }
  small { max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:11px; }
  .source { font-size:9px; }
  button:active { background:color-mix(in srgb,var(--text-on-accent) 18%,transparent); }
  button:focus-visible { outline:2px solid var(--status-info); outline-offset:-4px; }
  button:disabled { opacity:.6; cursor:wait; }
  .empty { margin:0; padding:var(--space-4); color:var(--text-secondary); text-align:center; font-size:13px; }
</style>
