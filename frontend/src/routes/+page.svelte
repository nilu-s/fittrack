<script lang="ts">
  import DateNav from '$lib/components/DateNav.svelte';
  import UnifiedDay from '$lib/components/UnifiedDay.svelte';
  import { dayData, currentDate, syncStatus, lastSync } from '$lib/stores';

  $: data = $dayData;

  function formatLastSync(ts: number | null): string { if (!ts) return ''; const d = new Date(ts); return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`; }

  function onUnifiedUpdate(e: CustomEvent) { if (!data) return; const { field, value } = e.detail; dayData.set({ ...data, dayEntry: { ...data.dayEntry, [field]: value } }); }
  function onMealToggle(e: CustomEvent) { if (!data) return; const { id, is_done } = e.detail; dayData.set({ ...data, meals: data.meals.map((m) => m.id === id ? { ...m, is_done } : m) }); }
  function onTodoToggle(e: CustomEvent) { if (!data) return; const { id } = e.detail; dayData.set({ ...data, todos: (data.todos ?? []).map((t) => String(t.id) === String(id) ? { ...t, status: t.status === 'open' ? 'done' : 'open' } : t) }); }
  function onTodoAdd(e: CustomEvent) { if (!data) return; dayData.set({ ...data, todos: [...(data.todos ?? []), e.detail] }); }

  let touchStartY = 0; let touchEndY = 0;
  function onTouchStart(e: TouchEvent) { touchStartY = e.touches[0].clientY; }
  function onTouchEnd(e: TouchEvent) { touchEndY = e.changedTouches[0].clientY; if (touchStartY - touchEndY > 100 && window.scrollY < 10) goto('/week'); }
  function goto(path: string) { if (typeof window !== 'undefined') window.location.href = path; }
</script>

<svelte:head><title>FitTrack</title></svelte:head>

<div class="page" role="application" ontouchstart={onTouchStart} ontouchend={onTouchEnd}>
  <DateNav />
  {#if data}
    <UnifiedDay dayData={data} currentDate={$currentDate}
      on:update={onUnifiedUpdate}
      on:mealtoggle={onMealToggle}
      on:trainingtoggle={(e) => onUnifiedUpdate(new CustomEvent('update', { detail: { field: 'training_done', value: e.detail } }))}
      on:cardiotoggle={(e) => onUnifiedUpdate(new CustomEvent('update', { detail: { field: 'cardio_done', value: e.detail } }))}
      on:todotoggle={onTodoToggle}
      on:todoadd={onTodoAdd} />
    <div class="sync" class:ok={$syncStatus === 'synced'} class:syncing={$syncStatus === 'syncing'} class:off={$syncStatus === 'offline'} class:err={$syncStatus === 'error'}>
      {#if $syncStatus === 'synced'}Sync {formatLastSync($lastSync)}
      {:else if $syncStatus === 'syncing'}Synchronisiere…
      {:else if $syncStatus === 'offline'}Offline
      {:else}Sync-Fehler{/if}
    </div>
  {:else}
    <div class="loading"><div class="spinner"></div></div>
  {/if}
</div>

<style>
  .page { display: flex; flex-direction: column; gap: 10px; }
  .loading { display: flex; justify-content: center; align-items: center; padding: 40px 16px; }
  .spinner { width: 24px; height: 24px; border-radius: 50%; border: 2.5px solid var(--card-2); border-top-color: var(--text-dim); animation: spin 0.8s linear infinite; }
  .sync { display: flex; align-items: center; justify-content: center; padding: 6px 12px; margin-top: 2px; border-radius: 8px; font-size: 12px; color: var(--text-faint); background: var(--card); border: 1px solid var(--border); }
  .sync.ok { color: var(--green); }
  .sync.syncing { color: var(--amber); }
  .sync.err { color: var(--red); }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>