<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import { currentDate, dayData, onlineStatus } from '$lib/stores';
  import { initSync } from '$lib/sync';
  import { api } from '$lib/api';
  import { db } from '$lib/db';
  import type { DayData, DayEntry, Meal, Todo, TrainingSet, TrainingRotation } from '$lib/types';

  let syncIcon = '✓';
  let syncClass = 'synced';
  let dateDisplay = '';

  // Format date for header
  $: dateDisplay = formatDate($currentDate);

  function formatDate(dateStr: string): string {
    const days = ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag'];
    const months = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'];
    const d = new Date(dateStr + 'T00:00:00');
    return `${days[d.getDay()]}, ${d.getDate()}. ${months[d.getMonth()]}`;
  }

  // Load day data
  async function loadDayData(date: string) {
    try {
      const [dayEntry, meals, todos, training] = await Promise.all([
        api.getDayEntry(date),
        api.getMeals(date),
        api.getTodos(date),
        api.getTraining(date),
      ]);

      // Try to get next training from rotation
      let nextTraining: TrainingRotation | null = null;
      if (dayEntry?.training_type) {
        nextTraining = await api.getNextTraining(dayEntry.training_type);
      }

      const data: DayData = {
        dayEntry: dayEntry ?? { date },
        meals: meals ?? [],
        todos: todos ?? [],
        training: training ?? [],
        nextTraining,
        weekStats: null,
      };

      dayData.set(data);

      // Also cache in IndexedDB
      if (dayEntry) {
        await db.dayEntries.put({ ...dayEntry, date, updatedAt: dayEntry.updated_at });
      }
    } catch (e) {
      console.warn('Failed to load day data:', e);
      // Load from IndexedDB as fallback
      const cachedEntry = await db.dayEntries.where('date').equals(date).first();
      const cachedMeals = await db.meals.where('date').equals(date).toArray();
      const cachedTodos = await db.todos.where('date').equals(date).toArray();

      dayData.set({
        dayEntry: cachedEntry ?? { date },
        meals: cachedMeals ?? [],
        todos: cachedTodos ?? [],
        training: [],
        nextTraining: null,
        weekStats: null,
      });
    }
  }

  // React to date changes
  $: if ($currentDate) {
    loadDayData($currentDate);
  }

  // Sync status icon
  $: if (typeof window !== 'undefined') {
    import('$lib/stores').then(({ syncStatus }) => {
      syncStatus.subscribe((status) => {
        syncIcon = { synced: '✓', syncing: '⟳', offline: '📵', error: '⚠' }[status] ?? '✓';
        syncClass = status;
      });
    });
  }

  onMount(() => {
    // Register service worker
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch((e) => {
        console.warn('SW registration failed:', e);
      });
    }

    // Init sync
    initSync();

    // Online/offline tracking
    const onOnline = () => onlineStatus.set(true);
    const onOffline = () => onlineStatus.set(false);
    window.addEventListener('online', onOnline);
    window.addEventListener('offline', onOffline);

    return () => {
      window.removeEventListener('online', onOnline);
      window.removeEventListener('offline', onOffline);
    };
  });
</script>

<div class="app-shell">
  <header class="app-header">
    <div class="header-left">
      <span class="app-title">FitTrack</span>
    </div>
    <div class="header-center">
      <span class="date-display">{dateDisplay}</span>
    </div>
    <div class="header-right">
      <span class="sync-icon {syncClass}">{syncIcon}</span>
    </div>
  </header>

  <main class="app-main">
    <slot />
  </main>
</div>

<style>
  .app-shell {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    min-height: 100dvh;
    max-width: 500px;
    margin: 0 auto;
    width: 100%;
  }

  .app-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1rem;
    padding-top: calc(0.75rem + env(safe-area-inset-top, 0px));
    gap: 0.5rem;
  }

  .header-left {
    flex: 0 0 auto;
  }

  .header-center {
    flex: 1;
    text-align: center;
  }

  .header-right {
    flex: 0 0 auto;
    width: 24px;
    text-align: right;
  }

  .app-title {
    font-size: 1.1rem;
    font-weight: 700;
    letter-spacing: -0.02em;
  }

  .date-display {
    font-size: 0.8125rem;
    color: var(--text-secondary);
  }

  .app-main {
    flex: 1;
    padding: 0 0.75rem 2rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  @media (min-width: 501px) {
    .app-shell {
      border-left: 1px solid var(--card-border);
      border-right: 1px solid var(--card-border);
      min-height: 100vh;
    }
  }
</style>