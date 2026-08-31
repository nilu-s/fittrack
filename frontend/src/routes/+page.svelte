<script lang="ts">
  import DateNav from '$lib/components/DateNav.svelte';
  import UnifiedDay from '$lib/components/UnifiedDay.svelte';
  import { dayData, currentDate, syncStatus, lastSync } from '$lib/stores';

  $: data = $dayData;

  function formatLastSync(ts: number | null): string { if (!ts) return ''; const d = new Date(ts); return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`; }
  function onUnifiedUpdate(e: CustomEvent) { if (!data) return; const { field, value } = e.detail; dayData.set({ ...data, dayEntry: { ...(data.dayEntry ?? { date: $currentDate }), [field]: value } }); }
  function onMealToggle(e: CustomEvent) { if (!data) return; const { id, is_done, data: mealData } = e.detail; dayData.set({ ...data, meals: data.meals.map((m) => m.id === id ? { ...m, ...(mealData ?? {}), is_done } : m) }); }
  function onTodoToggle(e: CustomEvent) { if (!data) return; const { id } = e.detail; dayData.set({ ...data, todos: (data.todos ?? []).map((t) => String(t.id) === String(id) ? { ...t, status: t.status === 'open' ? 'done' : 'open' } : t) }); }
  function onTodoAdd(e: CustomEvent) { if (!data) return; dayData.set({ ...data, todos: [...(data.todos ?? []), e.detail] }); }

</script>

<svelte:head><title>FitTrack</title></svelte:head>

<div class="page">
  {#if data}
    {#key $currentDate}
      <div class="day-slide">
        <UnifiedDay dayData={data} currentDate={$currentDate}
          on:update={onUnifiedUpdate}
          on:mealtoggle={onMealToggle}
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
    <div class="loading"><div class="spinner"></div></div>
  {/if}
  <DateNav />
</div>

<style>
  .page { display: flex; flex-direction: column; gap: 10px; padding-top: 8px; padding-bottom: calc(70px + env(safe-area-inset-bottom, 0px)); }
  .day-slide { animation: slideIn 0.32s cubic-bezier(0.22, 1, 0.36, 1); will-change: transform, opacity; }

  .loading { display: flex; justify-content: center; align-items: center; padding: 40px 16px; }
  .spinner { width: 24px; height: 24px; border-radius: 50%; border: 2.5px solid var(--card-2); border-top-color: var(--text-dim); animation: spin 0.8s linear infinite; }
  .sync { display: flex; align-items: center; justify-content: center; min-height: 24px; padding: 3px 10px; margin-top: 2px; font-size: 11px; color: var(--text-faint); }
  .sync.ok { color: var(--green); }
  .sync.syncing { color: var(--amber); }
  .sync.err { color: var(--red); }
  @keyframes spin { to { transform: rotate(360deg); } }
  @keyframes slideIn { from { opacity: 0; transform: translateX(0) scale(0.98); } to { opacity: 1; transform: translateX(0) scale(1); } }
</style>
