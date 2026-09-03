<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { goto } from '$app/navigation';
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
  import NoteBoard from '$lib/components/NoteBoard.svelte';
  import WorkspaceFocusWheel from '$lib/components/WorkspaceFocusWheel.svelte';
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
  let generalTodoOpen = false;
  let generalTodoPanelHeight = 360;
  let generalTodoTitle = '';
  let generalTodoAdding = false;
  let generalTodos: import('$lib/types').Note[] = [];
  let generalTodosLoading = false;
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
  let spaces: import('$lib/types').Space[] = [];
  let activeSpaceId: string | null = null;
  let workspaceSwipeStartX = 0;
  let workspaceSwipeStartY = 0;
  let trackingWorkspaceSwipe = false;

  async function loadSpaces() {
    spaces = await api.getSpaces();
    if (activeSpaceId && !spaces.some((space) => space.id === activeSpaceId)) activeSpaceId = null;
  }
  function changeSpace(event: CustomEvent<string | null>) {
    activeSpaceId = event.detail; shopping = null;
    if (typeof localStorage !== 'undefined') localStorage.setItem('active_space_id', activeSpaceId ?? '');
    void loadGeneralTodos();
  }
  function manageSpace(event: CustomEvent<string>) { void goto(`/settings/spaces?space=${encodeURIComponent(event.detail)}`); }
  function moveSpace(direction: number) {
    const contexts = [{ id: null as string | null }, ...spaces.map((space) => ({ id: space.id }))];
    const index = Math.max(0, contexts.findIndex((context) => context.id === activeSpaceId));
    changeSpace(new CustomEvent('change', { detail: contexts[(index + direction + contexts.length) % contexts.length].id }));
  }
  function startWorkspaceSwipe(event: TouchEvent) {
    const target = event.target as HTMLElement | null;
    if (target?.closest('.day-footer') || shoppingOpen || generalTodoOpen || assistantOpen || todoDetails || editingShopping || mealImportOpen) return;
    workspaceSwipeStartX = event.touches[0]?.clientX ?? 0;
    workspaceSwipeStartY = event.touches[0]?.clientY ?? 0;
    trackingWorkspaceSwipe = true;
  }
  function finishWorkspaceSwipe(event: TouchEvent) {
    if (!trackingWorkspaceSwipe) return;
    trackingWorkspaceSwipe = false;
    const touch = event.changedTouches[0];
    if (!touch) return;
    const dx = touch.clientX - workspaceSwipeStartX;
    const dy = touch.clientY - workspaceSwipeStartY;
    if (Math.abs(dx) >= 72 && Math.abs(dx) > Math.abs(dy) * 1.2) moveSpace(dx < 0 ? 1 : -1);
  }

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
  async function addFooterTodo(event: CustomEvent<string>) {
    const title = event.detail.trim();
    if (!title || todoAdding) return;
    todoAdding = true;
    todoAddError = '';
    try {
      const created = await api.createNote({ title });
      if (!created) throw new Error('Notiz konnte nicht erstellt werden.');
      generalTodos = [created, ...generalTodos];
      todoTitle = '';
    } catch {
      todoAddError = 'Notiz konnte nicht hinzugefügt werden. Bitte versuche es erneut.';
    } finally {
      todoAdding = false;
    }
  }

  function onTodoDetailsUpdate(event: CustomEvent<import('$lib/types').Todo>) {
    const updated = event.detail;
    if (data) dayData.set({ ...data, todos: (data.todos ?? []).map((todo) => String(todo.id) === String(updated.id) ? updated : todo) });
  }
  async function loadGeneralTodos() {
    if (generalTodosLoading) return;
    generalTodosLoading = true;
    try { generalTodos = await api.getNotes(); }
    finally { generalTodosLoading = false; }
  }
  async function addGeneralTodo(event: CustomEvent<string>) {
    const title = event.detail.trim();
    if (!title || generalTodoAdding) return;
    generalTodoAdding = true;
    const created = await api.createNote({ title });
    if (created) { generalTodos = [...generalTodos, created]; generalTodoTitle = ''; }
    generalTodoAdding = false;
  }
  async function openGeneralTodos(height: number) {
    shoppingOpen = false; generalTodoOpen = true;
    generalTodoPanelHeight = Math.max(1, Math.min(900, Math.round(220 + height)));
    await tick(); document.querySelector<HTMLInputElement>('#footer-entry-title')?.focus();
    void loadGeneralTodos();
  }
  async function loadShopping() {
    if (shopping || shoppingLoading) return;
    shoppingLoading = true;
    try { shopping = await api.getShoppingList(activeSpaceId ?? undefined); }
    finally { shoppingLoading = false; }
  }
  async function addShopping(event: CustomEvent<string>) { if (shoppingAdding || !event.detail.trim()) return; shoppingAdding = true; const item = await api.createShoppingItem({ title: event.detail.trim() }, activeSpaceId ?? undefined); if (item) { shopping = shopping ? { ...shopping, items: [...shopping.items, item] } : await api.getShoppingList(activeSpaceId ?? undefined); shoppingTitle = ''; } shoppingAdding = false; }
  async function toggleShopping(item: import('$lib/types').ShoppingItem) { const updated = await api.toggleShoppingItem(item.id); if (updated && shopping) shopping = { ...shopping, items: shopping.items.map((value) => value.id === updated.id ? updated : value) }; }
  async function removeShopping(item: import('$lib/types').ShoppingItem) { if (await api.deleteShoppingItem(item.id) && shopping) shopping = { ...shopping, items: shopping.items.filter((value) => value.id !== item.id) }; }
  async function saveShopping(event: CustomEvent<{ id: string; data: Partial<import('$lib/types').ShoppingItem> }>) { const updated = await api.updateShoppingItem(event.detail.id, event.detail.data); if (updated && shopping) shopping = { ...shopping, items: shopping.items.map((value) => value.id === updated.id ? updated : value) }; }
  function setShoppingPanelHeight(height: number) { shoppingPanelHeight = Math.max(1, Math.min(900, Math.round(height))); }
  function openShoppingFromFooter(event: CustomEvent<number>) { shopping = null; shoppingOpen = true; setShoppingPanelHeight(220 + event.detail); void loadShopping(); }

  // Preload the drawer's content before it is opened, matching the day-view cache.
  onMount(() => { const saved = localStorage.getItem('active_space_id'); activeSpaceId = saved || null; void loadShopping(); void loadGeneralTodos(); void loadSpaces(); const refreshSpaces = () => void loadSpaces(); const onVisibilityChange = () => { if (document.visibilityState === 'visible') refreshSpaces(); }; window.addEventListener('focus', refreshSpaces); window.addEventListener('pageshow', refreshSpaces); document.addEventListener('visibilitychange', onVisibilityChange); const interval = window.setInterval(refreshSpaces, 5_000); return () => { window.removeEventListener('focus', refreshSpaces); window.removeEventListener('pageshow', refreshSpaces); document.removeEventListener('visibilitychange', onVisibilityChange); window.clearInterval(interval); }; });

</script>

<svelte:head><title>{pageTitle()}</title></svelte:head>
<svelte:body class:shopping-open={shoppingOpen} class:general-todo-open={generalTodoOpen} />
<svelte:window ontouchstart={startWorkspaceSwipe} ontouchend={finishWorkspaceSwipe} />

<div class="page">
  {#if data && renderedDate === $currentDate}
    <WorkspaceFocusWheel {spaces} {activeSpaceId} on:change={changeSpace} on:manage={manageSpace} />
    {#key renderedDate}
      <div class="day-slide" in:fly={incomingDayTransition()} out:fly={outgoingDayTransition()}>
        <UnifiedDay dayData={{ ...data, todos: (data.todos ?? []).filter((todo) => activeSpaceId ? todo.space_id === activeSpaceId : !todo.space_id) }} currentDate={renderedDate} workspaceMode={Boolean(activeSpaceId)}
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
  <DateNav bind:todoTitle {todoAdding} {todoAddError} bind:shoppingOpen bind:shoppingTitle {shoppingAdding} shoppingCount={shopping?.items.filter((item) => item.status === 'open').length ?? 0} bind:generalTodoOpen bind:generalTodoTitle {generalTodoAdding} generalTodoCount={generalTodos.filter((note) => !note.space_id && note.status === 'active').length} on:todoadd={addFooterTodo} on:shoppinggesture={(event) => { generalTodoOpen = false; openShoppingFromFooter(event); }} on:shoppingadd={addShopping} on:generaltodogesture={(event) => openGeneralTodos(event.detail)} on:generaltodoadd={addGeneralTodo} on:aiplan={() => assistantOpen = true} />
  <NoteBoard bind:open={generalTodoOpen} notes={generalTodos} {spaces} loading={generalTodosLoading} on:close={() => { generalTodoOpen = false; document.querySelector<HTMLElement>('.todo-toggle')?.focus(); }} on:changed={loadGeneralTodos} />
  <ShoppingQuickPanel bind:open={shoppingOpen} {shopping} loading={shoppingLoading} query={shoppingTitle} panelHeight={shoppingPanelHeight} allowMealImport={!activeSpaceId} on:resize={(event) => setShoppingPanelHeight(event.detail)} on:close={(event) => { shoppingOpen = false; if (event.detail === 'keyboard') document.querySelector<HTMLElement>('.shopping-toggle')?.focus(); }} on:choose={(event) => shoppingTitle = event.detail} on:toggle={(event) => toggleShopping(event.detail)} on:edit={(event) => editingShopping = event.detail} on:remove={(event) => removeShopping(event.detail)} on:import={() => mealImportOpen = true} />
  <ShoppingItemEditor bind:item={editingShopping} on:close={() => editingShopping = null} on:save={saveShopping} />
  <ShoppingMealImport bind:open={mealImportOpen} startDate={$currentDate} on:close={() => mealImportOpen = false} on:imported={(event) => shopping = event.detail} />
  <TodoDetailsSheet bind:todo={todoDetails} {suggestedPlaceQuery} {suggestedTravelMode} {spaces} on:close={() => { todoDetails = null; suggestedPlaceQuery = ''; suggestedTravelMode = null; }} on:updated={onTodoDetailsUpdate} />
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
  @media (min-width:900px) { :global(body.shopping-open .shell),:global(body.general-todo-open .shell) { max-width:1180px; } :global(body.shopping-open .page) { padding-right:380px; } :global(body.general-todo-open .page) { padding-left:380px; } }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
