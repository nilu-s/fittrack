<script lang="ts">
  import Icon from './Icon.svelte';
  import ShoppingArticleIcon from './ShoppingArticleIcon.svelte';
  import { resolveShoppingIcon } from '$lib/shopping-icons';
  import type { ShoppingItem } from '$lib/types';
  export let items: ShoppingItem[] = [];
  export let busy = false;
  import { createEventDispatcher, tick } from 'svelte';
  const dispatch = createEventDispatcher<{ toggle: ShoppingItem; remove: ShoppingItem; edit: ShoppingItem }>();
  $: grouped = { open: items.filter((item) => item.status !== 'done'), done: items.filter((item) => item.status === 'done') };
  let focusedId: string | null = null;
  let previousItems = items;
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
  function initials(title: string) {
    return title.trim().split(/[\s-]+/).filter(Boolean).slice(0, 2).map((word) => word.slice(0, 1)).join('').toLocaleUpperCase('de') || '?';
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
            <button onfocus={() => focusedId = item.id} data-shopping-id={item.id} class="tile" type="button" role="checkbox" aria-checked={item.status === 'done'} onclick={() => dispatch('toggle', item)} disabled={busy} aria-label={item.status === 'done' ? `${item.title} erneut öffnen` : `${item.title} erledigen`}>
              <span class="state"><Icon name={item.status === 'done' ? 'check' : 'plus'} size={14} /></span>
              {#if resolveShoppingIcon(item.icon_key)}
                <ShoppingArticleIcon iconKey={item.icon_key} size={48} />
              {:else}
                <span class="initials" aria-hidden="true">{initials(item.title)}</span>
              {/if}
              <strong>{item.title}</strong>
              {#if quantity(item) || item.note}<small>{[quantity(item), item.note].filter(Boolean).join(' · ')}</small>{/if}
              {#if item.source !== 'manual'}<span class="source">Aus dem Plan</span>{/if}
            </button>
            <button class="remove" type="button" onclick={() => dispatch('edit', item)} disabled={busy} aria-label={`${item.title} bearbeiten`}><Icon name="edit" size={15} /></button>
            <button class="remove" type="button" onclick={() => dispatch('remove', item)} disabled={busy} aria-label={`${item.title} entfernen`}><Icon name="trash" size={15} /></button>
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
  ul { display:grid; grid-template-columns:repeat(auto-fill,minmax(130px,1fr)); gap:var(--space-2); margin:0; padding:0; list-style:none; }
  li { position:relative; min-width:0; aspect-ratio:1; overflow:hidden; border:1px solid color-mix(in srgb,var(--tile-color) 78%,var(--border-default)); border-radius:var(--radius-control); background:var(--tile-color); color:var(--text-on-accent); --tile-color:var(--data-shopping-other); }
  .category-produce { --tile-color:var(--data-shopping-produce); }.category-dairy { --tile-color:var(--data-shopping-dairy); }.category-bakery { --tile-color:var(--data-shopping-bakery); }.category-pantry { --tile-color:var(--data-shopping-pantry); }.category-frozen { --tile-color:var(--data-shopping-frozen); }.category-beverage { --tile-color:var(--data-shopping-beverage); }.category-household { --tile-color:var(--data-shopping-household); }
  li.done { background:color-mix(in srgb,var(--tile-color) 65%,var(--surface-default)); opacity:.7; }
  .tile { position:absolute; inset:0 0 var(--control-min); display:flex; flex-direction:column; align-items:center; justify-content:center; gap:3px; width:100%; padding:8px; color:inherit; text-align:center; }
  .state { position:absolute; top:7px; right:7px; color:var(--text-on-accent); }
  .initials { display:grid; place-items:center; width:42px; height:42px; border:2px solid var(--text-on-accent); border-radius:50%; background:transparent; color:var(--text-on-accent); font-size:13px; font-weight:800; letter-spacing:.04em; line-height:1; }
  strong { display:-webkit-box; -webkit-line-clamp:2; line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; max-width:100%; overflow-wrap:anywhere; font-size:14px; line-height:1.2; }
  small { max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:11px; }
  .source { font-size:9px; }
  .remove { position:absolute; bottom:0; left:0; display:grid; place-items:center; min-width:var(--control-min); min-height:var(--control-min); color:inherit; }
  .remove:last-child { left:auto; right:0; }
  button:active { background:color-mix(in srgb,var(--text-on-accent) 18%,transparent); }
  button:focus-visible { outline:2px solid var(--status-info); outline-offset:-4px; }
  button:disabled { opacity:.6; cursor:wait; }
  .empty { margin:0; padding:var(--space-4); color:var(--text-secondary); text-align:center; font-size:13px; }
</style>
