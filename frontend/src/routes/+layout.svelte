<script lang="ts">
  import '../app.css';
  import { onMount, afterUpdate } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { currentDate, dayData, onlineStatus } from '$lib/stores';
  import { initSync } from '$lib/sync';
  import { api } from '$lib/api';
  import { db } from '$lib/db';
  import { isAuthenticated, authEmail, checkAuth, logout } from '$lib/auth';
  import type { DayData, DayEntry, Meal, Todo, TrainingSuggestion, TrainingRotation } from '$lib/types';

  let syncIcon = '✓';
  let syncClass = 'synced';
  let dateDisplay = '';
  let authChecked = false;

  // Pull-to-refresh state
  let pullDistance = 0;
  let isPulling = false;
  let pullThreshold = 70;
  let isRefreshing = false;
  let touchStartY = 0;
  let mainEl: HTMLElement;

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
      const [dayEntry, meals, todos, trainingSuggestion] = await Promise.all([
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
        trainingSuggestion: trainingSuggestion as TrainingSuggestion | null,
        nextTraining,
        weekStats: null,
      };

      dayData.set(data);

      // Also cache in IndexedDB
      if (dayEntry) {
        await db.dayEntries.put({ ...dayEntry, date, updated_at: dayEntry.updated_at } as any);
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
        trainingSuggestion: null,
        nextTraining: null,
        weekStats: null,
      });
    }
  }

  // React to date changes
  $: if ($currentDate && authChecked && $isAuthenticated) {
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

  onMount(async () => {
    // Race checkAuth against a 3s timeout
    const timeout = new Promise<void>((resolve) => setTimeout(resolve, 3000));
    await Promise.race([checkAuth(), timeout]);
    authChecked = true;

    // Auth gate: redirect to login if not authenticated and not on /login
    const checkAuthGate = () => {
      const path = $page?.url?.pathname ?? '';
      if (path === '/login') return;
      if (!$isAuthenticated) {
        goto('/login');
      }
    };
    checkAuthGate();

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

  // Re-check auth when page or auth state changes
  afterUpdate(() => {
    const path = $page?.url?.pathname ?? '';
    if (path === '/login') return;
    if (authChecked && !$isAuthenticated) {
      goto('/login');
    }
  });

  async function handleLogout() {
    await logout();
    goto('/login');
  }

  // Pull-to-refresh handlers
  function onTouchStart(e: TouchEvent) {
    if (isRefreshing) return;
    if (window.scrollY <= 0) {
      touchStartY = e.touches[0].clientY;
      isPulling = true;
    } else {
      isPulling = false;
    }
  }

  function onTouchMove(e: TouchEvent) {
    if (!isPulling || isRefreshing) return;
    const delta = e.touches[0].clientY - touchStartY;
    if (delta > 0 && window.scrollY <= 0) {
      pullDistance = Math.min(delta * 0.5, pullThreshold * 1.5);
      if (pullDistance > 5) e.preventDefault();
    }
  }

  async function onTouchEnd() {
    if (!isPulling || isRefreshing) return;
    isPulling = false;
    if (pullDistance >= pullThreshold) {
      isRefreshing = true;
      pullDistance = pullThreshold;
      await loadDayData($currentDate);
      if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(30);
      isRefreshing = false;
    }
    pullDistance = 0;
  }
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
      <a href="/settings" class="header-link" title="Einstellungen">⚙️</a>
      {#if $isAuthenticated}
        <button class="header-link" onclick={handleLogout} title="Logout">🔒</button>
      {/if}
      <span class="sync-icon {syncClass}">{syncIcon}</span>
    </div>
  </header>

  <main class="app-main" bind:this={mainEl}
    ontouchstart={onTouchStart}
    ontouchmove={onTouchMove}
    ontouchend={onTouchEnd}
  >
    {#if pullDistance > 0 || isRefreshing}
      <div class="ptr-indicator" style="transform: translateY({Math.min(pullDistance, pullThreshold)}px); opacity:{Math.min(pullDistance / pullThreshold, 1)}">
        <span class="ptr-spinner {isRefreshing ? 'spinning' : ''}">{isRefreshing ? '⟳' : pullDistance >= pullThreshold ? '↓' : '↕'}</span>
      </div>
    {/if}
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
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .header-link {
    color: var(--text-secondary);
    text-decoration: none;
    font-size: 1rem;
    cursor: pointer;
    background: none;
    border: none;
    padding: 0;
    display: flex;
    align-items: center;
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
    padding: 0 0.75rem calc(2rem + env(safe-area-inset-bottom, 0px));
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    overscroll-behavior-y: contain;
    position: relative;
  }

  .ptr-indicator {
    position: absolute;
    top: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10;
    transition: opacity 0.2s;
    pointer-events: none;
  }

  .ptr-spinner {
    font-size: 1.25rem;
    color: var(--text-secondary);
  }

  .ptr-spinner.spinning {
    animation: ptr-spin 0.8s linear infinite;
  }

  @keyframes ptr-spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  @media (min-width: 501px) {
    .app-shell {
      border-left: 1px solid var(--card-border);
      border-right: 1px solid var(--card-border);
      min-height: 100vh;
    }
  }
</style>