<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import ShoppingList from '$lib/components/ShoppingList.svelte';
  import ShoppingItemEditor from '$lib/components/ShoppingItemEditor.svelte';
  import ShoppingMealImport from '$lib/components/ShoppingMealImport.svelte';
  import Icon from '$lib/components/Icon.svelte';
  import type { ShoppingItem, ShoppingList as ShoppingListType } from '$lib/types';
  let shopping: ShoppingListType | null = null; let query = ''; let loading = true; let importing = false;
  let editing: ShoppingItem | null = null; let importingDialog = false;
  onMount(async () => { shopping = await api.getShoppingList(); loading = false; });
  async function add() { const title = query.trim(); if (!title) return; const item = await api.createShoppingItem({ title }); if (item && shopping) { shopping = { ...shopping, items: [...shopping.items, item] }; query = ''; } }
  async function toggle(item: ShoppingItem) { const updated = await api.toggleShoppingItem(item.id); if (updated && shopping) shopping = { ...shopping, items: shopping.items.map((value) => value.id === item.id ? updated : value) }; }
  async function remove(item: ShoppingItem) { if (await api.deleteShoppingItem(item.id) && shopping) shopping = { ...shopping, items: shopping.items.filter((value) => value.id !== item.id) }; }
  async function save(event: CustomEvent<{ id: string; data: Partial<ShoppingItem> }>) { const updated = await api.updateShoppingItem(event.detail.id, event.detail.data); if (updated && shopping) shopping = { ...shopping, items: shopping.items.map((value) => value.id === updated.id ? updated : value) }; }
  function date(offset: number) { const result = new Date(); result.setDate(result.getDate() + offset); return `${result.getFullYear()}-${String(result.getMonth() + 1).padStart(2, '0')}-${String(result.getDate()).padStart(2, '0')}`; }
</script>

<svelte:head><title>Cronicl – Einkauf</title></svelte:head>
<div class="page"><header><div><p>EINKAUF</p><h1>Deine Liste</h1><span>{shopping?.items.filter((item) => item.status === 'open').length ?? 0} offen</span></div><button type="button" onclick={() => importingDialog = true}><Icon name="meal" size={16} />Plan übernehmen</button></header><form class="add" onsubmit={(event) => { event.preventDefault(); add(); }}><label class="sr-only" for="shopping-add">Artikel suchen oder hinzufügen</label><input id="shopping-add" bind:value={query} placeholder="Artikel suchen oder hinzufügen …" autocomplete="off"/><button type="submit" disabled={!query.trim()}><Icon name="plus" size={17} /><span>Hinzufügen</span></button></form>{#if loading}<p class="empty">Lade Einkaufsliste…</p>{:else}<ShoppingList items={shopping?.items ?? []} on:toggle={(event) => toggle(event.detail)} on:edit={(event) => editing = event.detail} on:remove={(event) => remove(event.detail)} />{/if}</div><ShoppingItemEditor bind:item={editing} on:close={() => editing = null} on:save={save}/><ShoppingMealImport bind:open={importingDialog} startDate={date(0)} on:close={() => importingDialog = false} on:imported={(event) => shopping = event.detail}/>

<style>
  .page { display:grid; gap:var(--space-3); padding:var(--space-3) 0 32px; } header { display:flex; align-items:flex-end; justify-content:space-between; gap:var(--space-3); padding:0 var(--space-1); } header div { display:grid; gap:2px; } header p,header span { margin:0; color:var(--text-tertiary); font-size:11px; font-weight:700; letter-spacing:.06em; } h1 { margin:0; font-size:25px; letter-spacing:-.035em; } header button,.add button { display:flex; align-items:center; justify-content:center; gap:6px; min-height:var(--control-min); padding:8px 11px; border:1px solid var(--border-accent); border-radius:var(--radius-control); background:var(--surface-accent); color:var(--action-primary); font:inherit; font-size:12px; font-weight:750; } .add { display:flex; gap:8px; } .add input { flex:1; min-width:0; min-height:42px; padding:8px 12px; border:1px solid var(--border-default); border-radius:var(--radius-control); background:var(--surface-raised); color:var(--text-primary); font:inherit; } .add button { background:var(--action-primary); border-color:var(--action-primary); color:var(--text-on-accent); } .empty { color:var(--text-tertiary); text-align:center; padding:var(--space-5); } input:focus-visible,button:focus-visible { outline:2px solid var(--status-info); outline-offset:2px; } @media(max-width:380px) { .add button span { display:none; } }
</style>
