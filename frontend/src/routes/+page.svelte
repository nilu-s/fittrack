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

  // --- Swipe: horizontal = Tage wechseln, vertikal = Wochenübersicht ---
  let touchStartX = 0; let touchStartY = 0; let touchEndX = 0; let touchEndY = 0;
  let slideDir = 0; // -1 = prev, 1 = next, 0 = none

  function todayStr(): string { const d = new Date(); const y = d.getFullYear(); const m = String(d.getMonth() + 1).padStart(2, '0'); const day = String(d.getDate()).padStart(2, '0'); return `${y}-${m}-${day}`; }
  function formatDate(d: Date): string { const y = d.getFullYear(); const m = String(d.getMonth() + 1).padStart(2, '0'); const day = String(d.getDate()).padStart(2, '0'); return `${y}-${m}-${day}`; }
  function changeDate(delta: number) { const d = new Date($currentDate + 'T00:00:00'); d.setDate(d.getDate() + delta); slideDir = delta; currentDate.set(formatDate(d)); }
  function goto(path: string) { if (typeof window !== 'undefined') window.location.href = path; }

  function onTouchStart(e: TouchEvent) { touchStartX = e.touches[0].clientX; touchStartY = e.touches[0].clientY; }
  function onTouchEnd(e: TouchEvent) {
    touchEndX = e.changedTouches[0].clientX; touchEndY = e.changedTouches[0].clientY;
    const dx = touchEndX - touchStartX; const dy = touchEndY - touchStartY;
    if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) {
      // Horizontaler Swipe: rechts→prev, links→next
      if (dx > 0) changeDate(-1); else changeDate(1);
    } else if (touchStartY - touchEndY > 100 && Math.abs(dx) < 50 && window.scrollY < 10) {
      // Vertikaler Swipe nach oben → Wochenübersicht
      goto('/week');
    }
  }
</script>

<svelte:head><title>FitTrack</title></svelte:head>

<div class="page" role="application" ontouchstart={onTouchStart} ontouchend={onTouchEnd}>
  <DateNav />
  {#if data}
    {#key $currentDate}
      <div class="day-slide" data-dir={slideDir}>
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
</div>

<style>
  .page { display: flex; flex-direction: column; gap: 10px; }
  .day-slide { animation: slideIn 0.32s cubic-bezier(0.22, 1, 0.36, 1); will-change: transform, opacity; }
  .day-slide[data-dir="1"] { animation-name: slideInLeft; }
  .day-slide[data-dir="-1"] { animation-name: slideInRight; }
  .loading { display: flex; justify-content: center; align-items: center; padding: 40px 16px; }
  .spinner { width: 24px; height: 24px; border-radius: 50%; border: 2.5px solid var(--card-2); border-top-color: var(--text-dim); animation: spin 0.8s linear infinite; }
  .sync { display: flex; align-items: center; justify-content: center; padding: 6px 12px; margin-top: 2px; border-radius: 8px; font-size: 12px; color: var(--text-faint); background: var(--card); border: 1px solid var(--border); }
  .sync.ok { color: var(--green); }
  .sync.syncing { color: var(--amber); }
  .sync.err { color: var(--red); }
  @keyframes spin { to { transform: rotate(360deg); } }
  @keyframes slideIn { from { opacity: 0; transform: translateX(0) scale(0.98); } to { opacity: 1; transform: translateX(0) scale(1); } }
  @keyframes slideInLeft { from { opacity: 0; transform: translateX(48px) scale(0.98); } to { opacity: 1; transform: translateX(0) scale(1); } }
  @keyframes slideInRight { from { opacity: 0; transform: translateX(-48px) scale(0.98); } to { opacity: 1; transform: translateX(0) scale(1); } }
</style>