<script lang="ts">
  import DateNav from '$lib/components/DateNav.svelte';
  import DayTracker from '$lib/components/DayTracker.svelte';
  import MealGrid from '$lib/components/MealGrid.svelte';
  import TodoSection from '$lib/components/TodoSection.svelte';
  import { dayData, currentDate, syncStatus, lastSync } from '$lib/stores';
  import { api } from '$lib/api';

  // Reload day data when it changes externally
  $: data = $dayData;

  function formatLastSync(ts: number | null): string {
    if (!ts) return '';
    const d = new Date(ts);
    const h = String(d.getHours()).padStart(2, '0');
    const m = String(d.getMinutes()).padStart(2, '0');
    return `${h}:${m}`;
  }

  // Swipe up to go to week page
  let touchStartY = 0;
  let touchEndY = 0;

  function onTouchStart(e: TouchEvent) {
    touchStartY = e.touches[0].clientY;
  }

  function onTouchEnd(e: TouchEvent) {
    touchEndY = e.changedTouches[0].clientY;
    const diff = touchStartY - touchEndY;
    // Swipe up (diff > 100) at top of page
    if (diff > 100 && window.scrollY < 10) {
      goto('/week');
    }
  }

  function goto(path: string) {
    if (typeof window !== 'undefined') {
      window.location.href = path;
    }
  }
</script>

<svelte:head>
  <title>FitTrack</title>
</svelte:head>

<div
  class="page"
  role="application"
  ontouchstart={onTouchStart}
  ontouchend={onTouchEnd}
>
  <DateNav />

  {#if data}
    <div class="cards-container">
      <DayTracker dayData={data} currentDate={$currentDate} />
      <MealGrid meals={data.meals} currentDate={$currentDate} />
      <TodoSection
        todos={data.todos}
        currentDate={$currentDate}
        dayEntry={data.dayEntry}
        meals={data.meals}
        ontrainingtoggle={(e) => {
          const updated = { ...data.dayEntry, training_done: e.detail };
          dayData.set({ ...data, dayEntry: updated });
        }}
        onmealtoggle={(e) => {
          const { id, is_done } = e.detail;
          const updatedMeals = data.meals.map((m) => m.id === id ? { ...m, is_done } : m);
          dayData.set({ ...data, meals: updatedMeals });
        }}
      />

      <div class="sync-status" class:synced={$syncStatus === 'synced'} class:syncing={$syncStatus === 'syncing'} class:offline={$syncStatus === 'offline'} class:error={$syncStatus === 'error'}>
        <span class="sync-icon">
          {#if $syncStatus === 'synced'}✓
          {:else if $syncStatus === 'syncing'}⟳
          {:else if $syncStatus === 'offline'}⊘
          {:else if $syncStatus === 'error'}⚠
          {/if}
        </span>
        <span class="sync-label">
          {#if $syncStatus === 'synced'}Synchronisiert
          {:else if $syncStatus === 'syncing'}Synchronisiere
          {:else if $syncStatus === 'offline'}Offline
          {:else if $syncStatus === 'error'}Fehler
          {/if}
        </span>
        {#if $syncStatus === 'synced' && $lastSync}
          <span class="sync-time">{formatLastSync($lastSync)}</span>
        {/if}
      </div>
    </div>
  {:else}
    <div class="loading">
      <span> loading data…</span>
    </div>
  {/if}
</div>

<style>
  .page {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .cards-container {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .loading {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 3rem 1rem;
    color: var(--text-secondary);
    font-size: 0.875rem;
  }

  .sync-status {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.4rem;
    padding: 0.5rem;
    margin-top: 0.25rem;
    border-radius: 8px;
    font-size: 0.75rem;
    color: #888;
    background: #2a2a2a;
    border: 1px solid #3a3a3a;
  }

  .sync-status.synced {
    color: #22c55e;
  }

  .sync-status.syncing {
    color: #f59e0b;
  }

  .sync-status.syncing .sync-icon {
    display: inline-block;
    animation: spin 1s linear infinite;
  }

  .sync-status.offline {
    color: #888;
  }

  .sync-status.error {
    color: #ef4444;
  }

  .sync-icon {
    font-size: 0.875rem;
    line-height: 1;
  }

  .sync-label {
    font-weight: 500;
  }

  .sync-time {
    color: #888;
    font-size: 0.6875rem;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
</style>
