<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { goto } from '$app/navigation';
  import { fly } from 'svelte/transition';
  import DateNav from '$lib/components/DateNav.svelte';
  import UnifiedDay from '$lib/components/UnifiedDay.svelte';
  import { dayData, currentDate } from '$lib/stores';
  import { api } from '$lib/api';
  import TodoDetailsSheet from '$lib/components/TodoDetailsSheet.svelte';
  import AssistantChatSheet from '$lib/components/AssistantChatSheet.svelte';
  import ShoppingQuickPanel from '$lib/components/ShoppingQuickPanel.svelte';
  import ShoppingItemEditor from '$lib/components/ShoppingItemEditor.svelte';
  import ShoppingMealImport from '$lib/components/ShoppingMealImport.svelte';
  import NoteBoard from '$lib/components/NoteBoard.svelte';
  import WorkspaceFocusWheel from '$lib/components/WorkspaceFocusWheel.svelte';
  import DayMetricStrip from '$lib/components/DayMetricStrip.svelte';
  import { pageTitle } from '$lib/brand';

  $: data = $dayData;
  let todoTitle = '';
  let todoAdding = false;
  let todoAddError = '';
  let noteTitle = '';
  let noteAdding = false;
  let noteAddError = '';
  let shoppingTitle = '';
  let todoDetails: import('$lib/types').Todo | null = null;
  let suggestedPlaceQuery = '';
  let suggestedTravelMode: import('$lib/types').Todo['travel_mode'] = null;
  let assistantOpen = false;
  let shoppingOpen = false;
  let noteBoardOpen = false;
  let noteAreaId: string | null = null;
  let generalTodos: import('$lib/types').Note[] = [];
  let generalTodosLoading = false;
  let shoppingAdding = false;
  let shoppingAddError = '';
  let shopping: import('$lib/types').ShoppingList | null = null;
  let shoppingLoading = false;
  let shoppingRequestId = 0;
  let editingShopping: import('$lib/types').ShoppingItem | null = null;
  let mealImportOpen = false;
  let renderedDate = '';
  let previousRenderedDate = '';
  let dayTransitionDirection = 1;
  let prefersReducedMotion = false;
  let spaces: import('$lib/types').Space[] = [];
  let activeSpaceId: string | null = null;
  let showAllTodos = false;
  let unifiedDay: { openFooterMetricDetails: (metric: 'steps' | 'sleep' | 'weight' | 'calories', trigger: HTMLElement) => void } | null = null;

  async function loadSpaces() {
    spaces = await api.getSpaces();
    if (activeSpaceId && !spaces.some((space) => space.id === activeSpaceId)) activeSpaceId = null;
  }
  function changeSpace(event: CustomEvent<{ spaceId: string | null; showAllTodos: boolean }>) {
    activeSpaceId = event.detail.spaceId;
    showAllTodos = event.detail.showAllTodos;
    shopping = null;
    if (typeof localStorage !== 'undefined') localStorage.setItem('active_space_id', showAllTodos ? 'all' : activeSpaceId ?? '');
    if (shoppingOpen) void loadShopping();
  }
  function manageSpace(event: CustomEvent<string>) { void goto(`/settings/spaces?space=${encodeURIComponent(event.detail)}`); }
  function moveSpace(direction: number) {
    const contexts = [{ spaceId: null as string | null, showAllTodos: true }, { spaceId: null as string | null, showAllTodos: false }, ...spaces.map((space) => ({ spaceId: space.id, showAllTodos: false }))];
    const index = Math.max(0, contexts.findIndex((context) => context.showAllTodos === showAllTodos && (context.showAllTodos || context.spaceId === activeSpaceId)));
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= contexts.length) return;
    changeSpace(new CustomEvent('change', { detail: contexts[targetIndex] }));
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
      const created = await api.createTodo({ due_date: $currentDate, title, status: 'open', priority: 2, source: 'manual' });
      if (!created) throw new Error('To-do konnte nicht erstellt werden.');
      onTodoAdd(new CustomEvent('todoadd', { detail: created }));
      todoTitle = '';
    } catch {
      todoAddError = 'To-do konnte nicht hinzugefügt werden. Bitte versuche es erneut.';
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
  function onNoteChanged(event: CustomEvent<import('$lib/types').Note>) {
    const note = event.detail;
    generalTodos = generalTodos.map((current) => current.id === note.id ? note : current);
    void loadGeneralTodos();
  }
  async function addNote(event: CustomEvent<string>) {
    const title = event.detail.trim();
    if (!title || noteAdding) return;
    noteAdding = true;
    noteAddError = '';
    try {
      const note = await api.createNote({ title, space_id: noteAreaId ?? undefined });
      if (!note) throw new Error('Notiz konnte nicht erstellt werden.');
      generalTodos = [note, ...generalTodos];
      noteTitle = '';
    } catch {
      noteAddError = 'Notiz konnte nicht hinzugefügt werden. Bitte versuche es erneut.';
    } finally {
      noteAdding = false;
    }
  }
  async function openNoteBoard() {
    if (noteBoardOpen) { noteBoardOpen = false; noteAreaId = null; return; }
    shoppingOpen = false;
    noteAreaId = null;
    noteBoardOpen = true;
    await tick();
    void loadGeneralTodos();
  }
  async function loadShopping() {
    const spaceId = activeSpaceId;
    const requestId = ++shoppingRequestId;
    shoppingLoading = true;
    try {
      const list = await api.getShoppingList(spaceId ?? undefined);
      if (requestId === shoppingRequestId && spaceId === activeSpaceId) shopping = list;
    } finally {
      if (requestId === shoppingRequestId) shoppingLoading = false;
    }
  }
  async function addShopping(event: CustomEvent<string>) {
    const title = event.detail.trim();
    if (shoppingAdding || !title) return;
    shoppingAdding = true;
    shoppingAddError = '';
    try {
      const item = await api.createShoppingItem({ title }, activeSpaceId ?? undefined);
      if (!item) throw new Error('Einkaufsartikel konnte nicht erstellt werden.');
      shopping = shopping ? { ...shopping, items: [...shopping.items, item] } : await api.getShoppingList(activeSpaceId ?? undefined);
      shoppingTitle = '';
    } catch {
      shoppingAddError = 'Artikel konnte nicht hinzugefügt werden. Bitte versuche es erneut.';
    } finally {
      shoppingAdding = false;
    }
  }
  async function toggleShopping(item: import('$lib/types').ShoppingItem) { const updated = await api.toggleShoppingItem(item.id); if (updated && shopping) shopping = { ...shopping, items: shopping.items.map((value) => value.id === updated.id ? updated : value) }; }
  async function removeShopping(item: import('$lib/types').ShoppingItem) { if (await api.deleteShoppingItem(item.id) && shopping) shopping = { ...shopping, items: shopping.items.filter((value) => value.id !== item.id) }; }
  async function saveShopping(event: CustomEvent<{ id: string; data: Partial<import('$lib/types').ShoppingItem> }>) { const updated = await api.updateShoppingItem(event.detail.id, event.detail.data); if (updated && shopping) shopping = { ...shopping, items: shopping.items.map((value) => value.id === updated.id ? updated : value) }; }
  function openShoppingFromFooter() {
    if (shoppingOpen) { shoppingOpen = false; return; }
    noteBoardOpen = false;
    noteAreaId = null;
    shopping = null;
    shoppingOpen = true;
    void loadShopping();
  }

  // Preload the drawer's content before it is opened, matching the day-view cache.
  onMount(() => { const saved = localStorage.getItem('active_space_id'); showAllTodos = saved === 'all'; activeSpaceId = showAllTodos ? null : saved || null; void loadShopping(); void loadGeneralTodos(); void loadSpaces(); const refreshSpaces = () => void loadSpaces(); const onVisibilityChange = () => { if (document.visibilityState === 'visible') refreshSpaces(); }; window.addEventListener('focus', refreshSpaces); window.addEventListener('pageshow', refreshSpaces); document.addEventListener('visibilitychange', onVisibilityChange); const interval = window.setInterval(refreshSpaces, 5_000); return () => { window.removeEventListener('focus', refreshSpaces); window.removeEventListener('pageshow', refreshSpaces); document.removeEventListener('visibilitychange', onVisibilityChange); window.clearInterval(interval); }; });

</script>

<svelte:head><title>{pageTitle()}</title></svelte:head>
<div class="page">
  <main class="content-area">
    {#if data && renderedDate === $currentDate}
      <header class="workspace-header">
        <WorkspaceFocusWheel {spaces} {activeSpaceId} {showAllTodos} on:change={changeSpace} on:manage={manageSpace} />
      </header>
      {#key renderedDate}
        <div class="day-slide" in:fly={incomingDayTransition()} out:fly={outgoingDayTransition()}>
          <UnifiedDay bind:this={unifiedDay} dayData={{ ...data, todos: showAllTodos ? data.todos ?? [] : (data.todos ?? []).filter((todo) => activeSpaceId ? todo.space_id === activeSpaceId : !todo.space_id) }} currentDate={renderedDate} workspaceMode={Boolean(activeSpaceId)} allTasksMode={showAllTodos} showDayList={!shoppingOpen && !noteBoardOpen}
            on:update={onUnifiedUpdate}
            on:mealentrychange={onMealEntryChange}
            on:trainingtoggle={(e) => onUnifiedUpdate(new CustomEvent('update', { detail: { field: 'training_done', value: e.detail } }))}
            on:cardiotoggle={(e) => onUnifiedUpdate(new CustomEvent('update', { detail: { field: 'cardio_done', value: e.detail } }))}
            on:todotoggle={onTodoToggle}
            on:todoadd={onTodoAdd}
            on:workspacechange={(event) => moveSpace(event.detail)}>
            <svelte:fragment slot="content">
              {#if noteBoardOpen}
                <NoteBoard open notes={generalTodos} {spaces} date={$currentDate} loading={generalTodosLoading} inline on:close={() => { noteBoardOpen = false; noteAreaId = null; }} on:changed={onNoteChanged} on:areachange={(event) => noteAreaId = event.detail} />
              {:else if shoppingOpen}
                <ShoppingQuickPanel open {shopping} loading={shoppingLoading} query={shoppingTitle} inline allowMealImport={!activeSpaceId} on:close={() => shoppingOpen = false} on:choose={(event) => shoppingTitle = event.detail} on:toggle={(event) => toggleShopping(event.detail)} on:edit={(event) => editingShopping = event.detail} on:remove={(event) => removeShopping(event.detail)} on:import={() => mealImportOpen = true} />
              {/if}
            </svelte:fragment>
          </UnifiedDay>
        </div>
      {/key}
    {:else}
      <div class="loading" role="status" aria-live="polite"><div class="spinner"></div><span class="sr-only">Tagesdaten werden geladen</span></div>
    {/if}
  </main>
  <DateNav bind:todoTitle bind:noteTitle bind:shoppingTitle {todoAdding} {noteAdding} {shoppingAdding} {todoAddError} {noteAddError} {shoppingAddError} {shoppingOpen} {noteBoardOpen} noteTargetName={spaces.find((space) => space.id === noteAreaId)?.name ?? ''} shoppingCount={shopping?.items.filter((item) => item.status === 'open').length ?? 0} noteCount={generalTodos.filter((note) => !note.space_id && note.status === 'active').length} on:todoadd={addFooterTodo} on:noteadd={addNote} on:shoppingadd={addShopping} on:shoppingopen={openShoppingFromFooter} on:noteboardopen={openNoteBoard} on:aiplan={() => assistantOpen = true}>
    {#if data && renderedDate === $currentDate}
      <DayMetricStrip entry={data.dayEntry} mealEntries={data.mealEntries} on:open={(event) => unifiedDay?.openFooterMetricDetails(event.detail.metric, event.detail.trigger)} />
    {/if}
  </DateNav>
  <ShoppingItemEditor bind:item={editingShopping} on:close={() => editingShopping = null} on:save={saveShopping} />
  <ShoppingMealImport bind:open={mealImportOpen} startDate={$currentDate} on:close={() => mealImportOpen = false} on:imported={(event) => shopping = event.detail} />
  <TodoDetailsSheet bind:todo={todoDetails} {suggestedPlaceQuery} {suggestedTravelMode} {spaces} on:close={() => { todoDetails = null; suggestedPlaceQuery = ''; suggestedTravelMode = null; }} on:updated={onTodoDetailsUpdate} />
  <AssistantChatSheet bind:open={assistantOpen} date={$currentDate} initialText={todoTitle} on:close={() => assistantOpen = false} />
</div>

<style>
  .page { display: flex; flex-direction: column; gap: 10px; padding-top: 8px; padding-bottom: calc(174px + env(safe-area-inset-bottom, 0px)); }
  .content-area { min-width: 0; }
  .workspace-header { padding: 4px 52px 6px 0; background: transparent; }
  .day-slide { will-change: transform, opacity; }

  .loading { display: flex; justify-content: center; align-items: center; padding: 40px 16px; }
  .sr-only { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; }
  .spinner { width: 24px; height: 24px; border-radius: 50%; border: 2.5px solid var(--surface-raised); border-top-color: var(--text-secondary); animation: spin 0.8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
