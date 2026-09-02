<script lang="ts">
  import { onMount } from 'svelte';
  import { fly } from 'svelte/transition';
  import DateNav from '$lib/components/DateNav.svelte';
  import UnifiedDay from '$lib/components/UnifiedDay.svelte';
  import { dayData, currentDate, syncStatus, lastSync } from '$lib/stores';
  import { api } from '$lib/api';
  import TodoDetailsSheet from '$lib/components/TodoDetailsSheet.svelte';
  import AssistantChatSheet from '$lib/components/AssistantChatSheet.svelte';
  import ShoppingQuickPanel from '$lib/components/ShoppingQuickPanel.svelte';
  import ShoppingItemEditor from '$lib/components/ShoppingItemEditor.svelte';
  import ShoppingMealImport from '$lib/components/ShoppingMealImport.svelte';
  import { pageTitle } from '$lib/brand';

  $: data = $dayData;
  let todoTitle = '';
  let todoAdding = false;
  let todoAddError = '';
  let todoDetails: import('$lib/types').Todo | null = null;
  let suggestedPlaceQuery = '';
  let suggestedTravelMode: import('$lib/types').Todo['travel_mode'] = null;
  let assistantOpen = false;
  let shoppingOpen = false;
  let shoppingPanelHeight = 360;
  let shoppingTitle = '';
  let shoppingAdding = false;
  let shopping: import('$lib/types').ShoppingList | null = null;
  let shoppingLoading = false;
  let editingShopping: import('$lib/types').ShoppingItem | null = null;
  let mealImportOpen = false;
  let renderedDate = '';
  let previousRenderedDate = '';
  let dayTransitionDirection = 1;
  let prefersReducedMotion = false;

  $: renderedDate = data?.dayEntry?.date ?? '';
  $: if (renderedDate && renderedDate !== previousRenderedDate) {
    if (previousRenderedDate) dayTransitionDirection = renderedDate > previousRenderedDate ? 1 : -1;
    previousRenderedDate = renderedDate;
  }

  onMount(() => {
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    const updateMotionPreference = () => prefersReducedMotion = query.matches;
    updateMotionPreference();
    query.addEventListener('change', updateMotionPreference);
    return () => query.removeEventListener('change', updateMotionPreference);
  });

  function incomingDayTransition() {
    return { x: 28 * dayTransitionDirection, opacity: 0, duration: prefersReducedMotion ? 0 : 260, easing: (t: number) => 1 - Math.pow(1 - t, 3) };
  }

  function outgoingDayTransition() {
    return { x: -20 * dayTransitionDirection, opacity: 0, duration: prefersReducedMotion ? 0 : 180, easing: (t: number) => t * t * t };
  }

  function formatLastSync(ts: number | null): string { if (!ts) return ''; const d = new Date(ts); return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`; }
  function onUnifiedUpdate(e: CustomEvent) { if (!data) return; const { field, value } = e.detail; dayData.set({ ...data, dayEntry: { ...(data.dayEntry ?? { date: $currentDate }), [field]: value } }); }
  function onMealEntryChange(e: CustomEvent) { if (!data) return; const entry = e.detail.entry; dayData.set({ ...data, mealEntries: data.mealEntries.map((current) => current.id === entry.id ? { ...current, ...entry } : current) }); }
  function onTodoToggle(e: CustomEvent) { if (!data) return; const { id, status } = e.detail; dayData.set({ ...data, todos: (data.todos ?? []).map((t) => String(t.id) === String(id) ? { ...t, status: status ?? (t.status === 'open' ? 'done' : 'open') } : t) }); }
  function onTodoAdd(e: CustomEvent) { if (!data) return; dayData.set({ ...data, todos: [...(data.todos ?? []), e.detail] }); }
  function routineFromText(text: string) {
    const match = text.match(/\b(?:jeden|jede)\s+(montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag)\b/i);
    if (!match) return null;
    const weekdays: Record<string, number> = { montag: 0, dienstag: 1, mittwoch: 2, donnerstag: 3, freitag: 4, samstag: 5, sonntag: 6 };
    const time = text.match(/\b([01]?\d|2[0-3])[:.]([0-5]\d)\b/);
    const title = text.replace(match[0], '').replace(/\b\d{1,2}[:.]\d{2}\b/, '').trim().replace(/^[,\-–]+\s*/, '');
    return title ? { title, weekdays: [weekdays[match[1].toLowerCase()]], due_time: time ? `${time[1].padStart(2, '0')}:${time[2]}` : null, priority: 2, is_active: true } : null;
  }
  async function addFooterTodo(event: CustomEvent<string>) {
    const title = event.detail.trim();
    if (!title || todoAdding) return;
    todoAdding = true;
    todoAddError = '';
    try {
      const routine = routineFromText(title);
      if (routine) {
        const createdRoutine = await api.createTodoRoutine(routine);
        if (!createdRoutine) throw new Error('Routine konnte nicht erstellt werden.');
        todoTitle = '';
        todoAddError = 'Routine wurde angelegt.';
        return;
      }
      const created = await api.createTodo({ due_date: $currentDate, title, status: 'open', priority: 2, source: 'manual' });
      if (!created) throw new Error('To-do konnte nicht erstellt werden.');
      onTodoAdd(new CustomEvent('todoadd', { detail: created }));
      todoTitle = '';
      suggestedPlaceQuery = ''; suggestedTravelMode = null;
      todoDetails = created;
    } catch {
      todoAddError = 'To-do konnte nicht hinzugefügt werden. Bitte versuche es erneut.';
    } finally {
      todoAdding = false;
    }
  }

  function onTodoDetailsUpdate(event: CustomEvent<import('$lib/types').Todo>) {
    if (!data) return;
    const updated = event.detail;
    dayData.set({ ...data, todos: (data.todos ?? []).map((todo) => String(todo.id) === String(updated.id) ? updated : todo) });
  }
  async function loadShopping() {
    if (shopping || shoppingLoading) return;
    shoppingLoading = true;
    try { shopping = await api.getShoppingList(); }
    finally { shoppingLoading = false; }
  }
  async function addShopping(event: CustomEvent<string>) { if (shoppingAdding || !event.detail.trim()) return; shoppingAdding = true; const item = await api.createShoppingItem({ title: event.detail.trim() }); if (item) { shopping = shopping ? { ...shopping, items: [...shopping.items, item] } : await api.getShoppingList(); shoppingTitle = ''; } shoppingAdding = false; }
  async function toggleShopping(item: import('$lib/types').ShoppingItem) { const updated = await api.toggleShoppingItem(item.id); if (updated && shopping) shopping = { ...shopping, items: shopping.items.map((value) => value.id === updated.id ? updated : value) }; }
  async function removeShopping(item: import('$lib/types').ShoppingItem) { if (await api.deleteShoppingItem(item.id) && shopping) shopping = { ...shopping, items: shopping.items.filter((value) => value.id !== item.id) }; }
  async function saveShopping(event: CustomEvent<{ id: string; data: Partial<import('$lib/types').ShoppingItem> }>) { const updated = await api.updateShoppingItem(event.detail.id, event.detail.data); if (updated && shopping) shopping = { ...shopping, items: shopping.items.map((value) => value.id === updated.id ? updated : value) }; }
  function setShoppingPanelHeight(height: number) { shoppingPanelHeight = Math.max(1, Math.min(900, Math.round(height))); }
  function openShoppingFromFooter(event: CustomEvent<number>) { shoppingOpen = true; setShoppingPanelHeight(220 + event.detail); void loadShopping(); }

  // Preload the drawer's content before it is opened, matching the day-view cache.
  onMount(() => { void loadShopping(); });

</script>

<svelte:head><title>{pageTitle()}</title></svelte:head>
<svelte:body class:shopping-open={shoppingOpen} />

<div class="page">
  {#if data && renderedDate === $currentDate}
    {#key renderedDate}
      <div class="day-slide" in:fly={incomingDayTransition()} out:fly={outgoingDayTransition()}>
        <UnifiedDay dayData={data} currentDate={renderedDate}
          on:update={onUnifiedUpdate}
          on:mealentrychange={onMealEntryChange}
          on:trainingtoggle={(e) => onUnifiedUpdate(new CustomEvent('update', { detail: { field: 'training_done', value: e.detail } }))}
          on:cardiotoggle={(e) => onUnifiedUpdate(new CustomEvent('update', { detail: { field: 'cardio_done', value: e.detail } }))}
          on:todotoggle={onTodoToggle}
          on:todoadd={onTodoAdd} />
      </div>
    {/key}
    <div class="sync" class:ok={$syncStatus === 'synced'} class:syncing={$syncStatus === 'syncing'} class:off={$syncStatus === 'offline'} class:err={$syncStatus === 'error'}>
      {#if $syncStatus === 'synced'}Sync {formatLastSync($lastSync)}
      {:else if $syncStatus === 'syncing'}Synchronisiere…
      {:else if $syncStatus === 'offline'}Offline
      {:else}Sync-Fehler{/if}
    </div>
  {:else}
    <div class="loading" role="status" aria-live="polite"><div class="spinner"></div><span class="sr-only">Tagesdaten werden geladen</span></div>
  {/if}
  <DateNav bind:todoTitle {todoAdding} {todoAddError} bind:shoppingOpen bind:shoppingTitle {shoppingAdding} shoppingCount={shopping?.items.filter((item) => item.status === 'open').length ?? 0} on:todoadd={addFooterTodo} on:shoppinggesture={openShoppingFromFooter} on:shoppingadd={addShopping} on:aiplan={() => assistantOpen = true} />
  <ShoppingQuickPanel bind:open={shoppingOpen} {shopping} loading={shoppingLoading} query={shoppingTitle} panelHeight={shoppingPanelHeight} on:resize={(event) => setShoppingPanelHeight(event.detail)} on:close={(event) => { shoppingOpen = false; if (event.detail === 'keyboard') document.querySelector<HTMLElement>('.shopping-toggle')?.focus(); }} on:choose={(event) => shoppingTitle = event.detail} on:toggle={(event) => toggleShopping(event.detail)} on:edit={(event) => editingShopping = event.detail} on:remove={(event) => removeShopping(event.detail)} on:import={() => mealImportOpen = true} />
  <ShoppingItemEditor bind:item={editingShopping} on:close={() => editingShopping = null} on:save={saveShopping} />
  <ShoppingMealImport bind:open={mealImportOpen} startDate={$currentDate} on:close={() => mealImportOpen = false} on:imported={(event) => shopping = event.detail} />
  <TodoDetailsSheet bind:todo={todoDetails} {suggestedPlaceQuery} {suggestedTravelMode} on:close={() => { todoDetails = null; suggestedPlaceQuery = ''; suggestedTravelMode = null; }} on:updated={onTodoDetailsUpdate} />
  <AssistantChatSheet bind:open={assistantOpen} date={$currentDate} initialText={todoTitle} on:close={() => assistantOpen = false} />
</div>

<style>
  .page { display: flex; flex-direction: column; gap: 10px; padding-top: 8px; padding-bottom: calc(136px + env(safe-area-inset-bottom, 0px)); }
  .day-slide { will-change: transform, opacity; }

  .loading { display: flex; justify-content: center; align-items: center; padding: 40px 16px; }
  .sr-only { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; }
  .spinner { width: 24px; height: 24px; border-radius: 50%; border: 2.5px solid var(--surface-raised); border-top-color: var(--text-secondary); animation: spin 0.8s linear infinite; }
  .sync { display: flex; align-items: center; justify-content: center; min-height: 24px; padding: 3px 10px; margin-top: 2px; font-size: 11px; color: var(--text-tertiary); }
  .sync.ok { color: var(--status-success); }
  .sync.syncing { color: var(--status-warning); }
  .sync.err { color: var(--status-danger); }
  @media (min-width:900px) { :global(body.shopping-open .shell) { max-width:1180px; } :global(body.shopping-open .page) { padding-right:380px; } }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
