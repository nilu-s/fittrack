<script lang="ts">
  import Icon from './Icon.svelte';
  import type { ShoppingItem } from '$lib/types';
  export let items: ShoppingItem[] = [];
  export let busy = false;
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher<{ toggle: ShoppingItem; remove: ShoppingItem; edit: ShoppingItem }>();
  const categoryNames: Record<string, string> = { produce: 'Obst & Gemüse', dairy: 'Kühlregal', bakery: 'Backwaren', pantry: 'Vorrat', frozen: 'Tiefkühlung', beverage: 'Getränke', household: 'Haushalt', other: 'Sonstiges' };
  $: grouped = items.reduce((groups: Record<string, ShoppingItem[]>, item) => { (groups[item.category_key] ??= []).push(item); return groups; }, {});
  function quantity(item: ShoppingItem) { return item.quantity == null ? '' : `${Number(item.quantity.toFixed(3))} ${item.unit ?? ''}`.trim(); }
</script>

<div class="shopping-list" aria-live="polite">
  {#each Object.entries(grouped) as [key, group] (key)}
    <section aria-labelledby={`shopping-category-${key}`}>
      <h3 id={`shopping-category-${key}`}><Icon name={group[0].icon_key} size={16} />{categoryNames[key] ?? 'Sonstiges'}</h3>
      <ul>
        {#each group as item (item.id)}
          <li class:done={item.status === 'done'}>
            <button class="check" type="button" onclick={() => dispatch('toggle', item)} disabled={busy} aria-label={item.status === 'done' ? `${item.title} erneut öffnen` : `${item.title} erledigen`}>
              {#if item.status === 'done'}<Icon name="check" size={14} />{/if}
            </button>
            <div class="copy"><strong>{item.title}</strong>{#if quantity(item) || item.note}<small>{[quantity(item), item.note].filter(Boolean).join(' · ')}</small>{/if}</div>
            {#if item.source !== 'manual'}<span class="source" title="Aus dem Mahlzeitenplan">Plan</span>{/if}
            <button class="remove" type="button" onclick={() => dispatch('edit', item)} disabled={busy} aria-label={`${item.title} bearbeiten`}><Icon name="edit" size={15} /></button>
            <button class="remove" type="button" onclick={() => dispatch('remove', item)} disabled={busy} aria-label={`${item.title} entfernen`}><Icon name="trash" size={15} /></button>
          </li>
        {/each}
      </ul>
    </section>
  {:else}
    <p class="empty">Noch nichts auf der Einkaufsliste.</p>
  {/each}
</div>

<style>
  .shopping-list { display:grid; gap:var(--space-3); } section { display:grid; gap:4px; } h3 { display:flex; align-items:center; gap:7px; margin:0; padding:0 2px; color:var(--text-secondary); font-size:11px; font-weight:750; letter-spacing:.06em; text-transform:uppercase; } ul { margin:0; padding:0; list-style:none; border:1px solid var(--border-subtle); border-radius:var(--radius-surface); overflow:hidden; background:var(--surface-default); } li { display:flex; align-items:center; gap:8px; min-height:54px; padding:7px 9px; border-bottom:1px solid var(--border-subtle); } li:last-child { border-bottom:0; } .check { display:grid; place-items:center; flex:0 0 28px; width:28px; height:28px; border:1.5px solid var(--border-strong); border-radius:50%; color:var(--text-on-accent); background:transparent; } .done .check { border-color:var(--action-primary); background:var(--action-primary); } .copy { display:grid; flex:1; min-width:0; gap:2px; } strong { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:14px; } small { color:var(--text-tertiary); font-size:11px; } .done strong { color:var(--text-tertiary); text-decoration:line-through; } .source { padding:2px 5px; border-radius:var(--radius-full); background:var(--surface-accent); color:var(--action-primary); font-size:9px; font-weight:750; } .remove { display:grid; place-items:center; width:30px; min-height:30px; color:var(--text-tertiary); } .remove:focus-visible,.check:focus-visible { outline:2px solid var(--status-info); outline-offset:2px; } .empty { margin:0; padding:var(--space-4); color:var(--text-tertiary); text-align:center; font-size:13px; }
</style>
