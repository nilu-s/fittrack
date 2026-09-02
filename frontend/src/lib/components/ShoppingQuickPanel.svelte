<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import ShoppingList from './ShoppingList.svelte';
  import Icon from './Icon.svelte';
  import type { ShoppingItem, ShoppingList as ShoppingListType } from '$lib/types';
  export let open = false;
  export let shopping: ShoppingListType | null = null;
  export let trigger: HTMLElement | null = null;
  export let query = '';
  const dispatch = createEventDispatcher<{ close: void; toggle: ShoppingItem; remove: ShoppingItem; edit: ShoppingItem; import: number; choose: string }>();
  const catalog = ['Äpfel', 'Bananen', 'Brot', 'Eier', 'Haferflocken', 'Joghurt', 'Käse', 'Kartoffeln', 'Milch', 'Nudeln', 'Paprika', 'Reis', 'Skyr', 'Tomaten'];
  $: suggestions = query.trim().length ? [...new Set([...(shopping?.items.map((item) => item.title) ?? []), ...catalog])].filter((item) => item.toLocaleLowerCase('de').includes(query.trim().toLocaleLowerCase('de'))).slice(0, 5) : [];
  function close() { dispatch('close'); trigger?.focus(); }
  function onKey(e: KeyboardEvent) { if (open && e.key === 'Escape') close(); }
</script>

<svelte:window on:keydown={onKey} />

{#if open}
  <aside id="shopping-quick-panel" class="panel" aria-label="Einkaufsliste">
    <header><span class="handle" aria-hidden="true"></span><div><p>EINKAUF</p><h2>{shopping?.items.filter((item) => item.status === 'open').length ?? 0} offen</h2></div><button type="button" onclick={close} aria-label="Einkaufsliste schließen"><Icon name="x" size={20} /></button></header>
    <p class="hint">Artikel direkt unten suchen oder hinzufügen.</p>
    {#if suggestions.length}<ul class="suggestions" aria-label="Passende Artikel">{#each suggestions as suggestion}<li><button type="button" onclick={() => dispatch('choose', suggestion)}>{suggestion}</button></li>{/each}</ul>{/if}
    <div class="actions"><button type="button" onclick={() => dispatch('import', 7)}><Icon name="meal" size={16} />Plan · 7 Tage</button><a href="/shopping" onclick={close}>Verwalten</a></div>
    <div class="body"><ShoppingList items={shopping?.items ?? []} on:toggle={(e) => dispatch('toggle', e.detail)} on:edit={(e) => dispatch('edit', e.detail)} on:remove={(e) => dispatch('remove', e.detail)} /></div>
  </aside>
{/if}

<style>
  .panel { position:fixed; z-index:45; left:50%; bottom:78px; transform:translateX(-50%); width:min(calc(100% - 20px),460px); max-height:min(62dvh,590px); display:flex; flex-direction:column; gap:10px; padding:12px; border:1px solid var(--border-default); border-radius:var(--radius-modal); background:var(--color-bg); box-shadow:var(--shadow-modal); } header { display:grid; grid-template-columns:1fr auto; align-items:start; gap:8px; } header p,.hint { margin:0; color:var(--text-tertiary); font-size:10px; font-weight:750; letter-spacing:.07em; } .hint { letter-spacing:0; font-weight:500; } h2 { margin:2px 0 0; font-size:16px; } header button { display:grid; place-items:center; width:38px; min-height:38px; border:1px solid var(--border-default); border-radius:var(--radius-control); background:var(--surface-raised); color:var(--text-primary); } .handle { display:block; grid-column:1/-1; justify-self:center; width:36px; height:4px; border-radius:99px; background:var(--border-strong); } .suggestions { display:flex; gap:5px; margin:0; padding:0; overflow:auto; list-style:none; } .suggestions button { min-height:30px; padding:5px 9px; border:1px solid var(--border-default); border-radius:var(--radius-full); background:var(--surface-raised); color:var(--text-secondary); white-space:nowrap; font-size:11px; } .actions { display:flex; justify-content:space-between; align-items:center; gap:8px; } .actions button,.actions a { display:inline-flex; align-items:center; gap:6px; min-height:32px; color:var(--action-primary); font-size:12px; font-weight:700; } .actions a { text-decoration:none; } .body { overflow:auto; padding-right:2px; } button:focus-visible,a:focus-visible { outline:2px solid var(--status-info); outline-offset:2px; } @media(min-width:900px) { .panel { left:auto; right:max(18px, calc((100vw - 1160px) / 2)); bottom:24px; transform:none; width:360px; max-height:calc(100dvh - 100px); } }
</style>
