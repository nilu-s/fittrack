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
  import Icon from '$lib/components/Icon.svelte';
  import { APP_NAME } from '$lib/brand';
  import UiIconButton from '$lib/components/ui/UiIconButton.svelte';
  import type { DayData, DayEntry, MealCategory, MealEntry, Todo, TrainingSuggestion } from '$lib/types';

  let syncIcon = '✓';
  let syncClass = 'synced';
  let authChecked = false;
  let pullDistance = 0;
  let isPulling = false;
  let pullThreshold = 70;
  let isRefreshing = false;
  let touchStartY = 0;
  let mainEl: HTMLElement;
  $: isMealSettings = $page?.url?.pathname === '/settings/meals';
  $: isShopping = $page?.url?.pathname === '/shopping';
  $: isLogin = $page?.url?.pathname === '/login';
  $: isHome = $page?.url?.pathname === '/';
  $: backTarget = $page?.url?.pathname?.startsWith('/settings/') ? '/settings' : '/';


  async function loadDayData(date: string) {
    const fitSyncPromise = api.syncGoogleFit(date).catch(() => null);
    try {
      const [dayEntry, _instantiated, categories, todos, trainingSuggestion] = await Promise.all([
        api.getDayEntry(date),
        // Project the active plan before reading it.  This is idempotent and
        // keeps the dashboard independent of the removed legacy meals table.
        api.instantiateMealEntries(date).catch(() => [] as MealEntry[]),
        api.getMealCategories().catch(() => [] as MealCategory[]),
        api.getTodos(date), api.getTraining(date)
      ]);
      // Instantiation returns only rows it has just created.  Always read the
      // full day afterwards so historical and already-planned entries remain
      // visible when navigating between days.
      const mealEntries = await api.getMealEntries(date);
      const categoryById = new Map(categories.map((category) => [category.id, category]));
      const displayedEntries: MealEntry[] = mealEntries.map((entry, index) => {
        const category = categoryById.get(entry.category_id);
        return {
          ...entry,
          category_name: category?.name,
          category_sort_order: category?.sort_order ?? index,
        };
      });
      let nextTraining: TrainingSuggestion | null = null;
      if (dayEntry?.training_type) nextTraining = await api.getNextTraining(dayEntry.training_type);
      const data: DayData = { dayEntry: dayEntry ?? { date }, mealEntries: displayedEntries, todos: todos ?? [], trainingSuggestion: trainingSuggestion as TrainingSuggestion | null, nextTraining, weekStats: null };
      dayData.set(data);
      if (dayEntry) await db.dayEntries.put({ ...dayEntry, date, updated_at: dayEntry.updated_at } as any);
      const fitResult = await fitSyncPromise;
      if (fitResult) { dayData.update((d) => { if (!d || !d.dayEntry) return d; const cur = d.dayEntry; const ue = { ...cur, steps: fitResult.steps ?? cur.steps, steps_confirmed: fitResult.steps_confirmed ?? true, steps_source: fitResult.steps_source ?? 'google_fit' }; if (fitResult.sleep_hours != null && fitResult.sleep_hours > 0) { ue.sleep_hours = fitResult.sleep_hours; ue.sleep_deep_hours = fitResult.sleep_deep_hours; ue.sleep_rem_hours = fitResult.sleep_rem_hours; ue.sleep_light_hours = fitResult.sleep_light_hours; ue.sleep_awake_hours = fitResult.sleep_awake_hours; ue.sleep_efficiency = fitResult.sleep_efficiency; ue.sleep_quality = fitResult.sleep_quality; } return { ...d, dayEntry: ue as DayEntry }; }); }
    } catch (e) {
      console.warn('Failed to load day data:', e);
      const ce = await db.dayEntries.where('date').equals(date).first();
      const ct = await db.todos.where('date').equals(date).toArray();
      // Meal entries are revision-aware and online-first; never revive a
      // removed legacy IndexedDB meal record during an offline fallback.
      dayData.set({ dayEntry: ce ?? { date }, mealEntries: [], todos: ct ?? [], trainingSuggestion: null, nextTraining: null, weekStats: null });
    }
  }

  $: if ($currentDate && authChecked && $isAuthenticated) loadDayData($currentDate);

  $: if (typeof window !== 'undefined') {
    import('$lib/stores').then(({ syncStatus }) => { syncStatus.subscribe((status) => { syncIcon = { synced: '✓', syncing: '⟳', offline: '📵', error: '⚠' }[status] ?? '✓'; syncClass = status; }); });
  }

  onMount(() => {
    const timeout = new Promise<void>((resolve) => setTimeout(resolve, 3000));
    Promise.race([checkAuth(), timeout]).then(() => {
      authChecked = true;
      const checkAuthGate = () => { const p = $page?.url?.pathname ?? ''; if (p === '/login' || p.startsWith('/settings')) return; if (!$isAuthenticated) goto('/login'); };
      checkAuthGate();
    });
    if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch((e) => console.warn('SW registration failed:', e));
    initSync();
    const onOnline = () => onlineStatus.set(true);
    const onOffline = () => onlineStatus.set(false);
    window.addEventListener('online', onOnline); window.addEventListener('offline', onOffline);
    const onStart = (e: TouchEvent) => onTouchStart(e);
    const onMove = (e: TouchEvent) => onTouchMove(e);
    const onEnd = () => onTouchEnd();
    mainEl.addEventListener('touchstart', onStart, { passive: true });
    mainEl.addEventListener('touchmove', onMove, { passive: false });
    mainEl.addEventListener('touchend', onEnd, { passive: true });
    return () => { window.removeEventListener('online', onOnline); window.removeEventListener('offline', onOffline); mainEl.removeEventListener('touchstart', onStart); mainEl.removeEventListener('touchmove', onMove); mainEl.removeEventListener('touchend', onEnd); };
  });

  async function handleRefresh() { if (isRefreshing) return; isRefreshing = true; await loadDayData($currentDate); if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(30); isRefreshing = false; }

  afterUpdate(() => { const p = $page?.url?.pathname ?? ''; if (p === '/login' || p.startsWith('/settings')) return; if (authChecked && !$isAuthenticated) goto('/login'); });

  async function handleLogout() { await logout(); goto('/login'); }

  function onTouchStart(e: TouchEvent) { if (isRefreshing) return; if (window.scrollY <= 0) { touchStartY = e.touches[0].clientY; isPulling = true; } else { isPulling = false; } }
  function onTouchMove(e: TouchEvent) { if (!isPulling || isRefreshing) return; const delta = e.touches[0].clientY - touchStartY; if (delta > 0 && window.scrollY <= 0) { pullDistance = Math.min(delta * 0.5, pullThreshold * 1.5); if (pullDistance > 5) e.preventDefault(); } }
  async function onTouchEnd() { if (!isPulling || isRefreshing) return; isPulling = false; if (pullDistance >= pullThreshold) { isRefreshing = true; pullDistance = pullThreshold; await loadDayData($currentDate); if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(30); isRefreshing = false; } pullDistance = 0; }
</script>

<div class:wide-shell={isMealSettings || isShopping} class="shell">
  {#if !isLogin}<header class="hdr">
    {#if isHome}
      <a href="/" class="hdr-title" aria-label={`${APP_NAME} Startseite`}><img class="brand-icon" src="/brand-icon.svg" alt="" /><span>{APP_NAME}</span></a>
    {:else}
      <a href={backTarget} class="header-back" aria-label="Zurück"><Icon name="chevron-left" size={20} /><span>Zurück</span></a>
    {/if}
    <div class="hdr-spacer"></div>
    <div class="hdr-actions">
      {#if $isAuthenticated}<a href="/settings/profile" class="account-chip" aria-label="Profil und Konto">{$authEmail?.slice(0, 1).toUpperCase() ?? 'K'}</a>{/if}
      {#if $isAuthenticated}<a href="/settings" class="header-settings" aria-label="Einstellungen"><Icon name="settings" size={18} /></a>{/if}
      <UiIconButton onclick={handleRefresh} disabled={isRefreshing} ariaLabel="Aktualisieren"><Icon name="refresh" size={18} /></UiIconButton>
      {#if $isAuthenticated}<UiIconButton onclick={handleLogout} ariaLabel="Logout"><Icon name="logout" size={18} /></UiIconButton>{/if}
    </div>
  </header>{/if}

  <main bind:this={mainEl} class="main">
    {#if pullDistance > 0 || isRefreshing}
      <div class="ptr" style="transform: translateY({Math.min(pullDistance, pullThreshold)}px); opacity:{Math.min(pullDistance / pullThreshold, 1)}">
        <Icon name="refresh" size={20} />
      </div>
    {/if}
    <slot />
  </main>
</div>

<style>
  .shell { display: flex; flex-direction: column; min-height: 100vh; min-height: 100dvh; max-width: 480px; margin: 0 auto; width: 100%; }
  .hdr { display: flex; align-items: center; min-height: 52px; padding: 2px 16px; padding-top: calc(2px + env(safe-area-inset-top, 0px)); gap: 10px; background:var(--surface-navigation); border-bottom: 1px solid var(--border-strong); }
  .hdr-title { display:flex; align-items:center; gap:10px; font-size:17px; font-weight:720; letter-spacing:-.03em; text-transform:uppercase; color:var(--text-primary); text-decoration:none; }
  .brand-icon { display:block; width:48px; height:48px; flex:none; }
  .header-back { display:flex; align-items:center; gap:3px; min-height:var(--control-min); padding:0 8px 0 3px; border-radius:var(--radius-control); color:var(--text-primary); font-size:14px; font-weight:700; }
  .header-back:active, .header-back:focus-visible { background:var(--surface-raised); }
  .hdr-spacer { flex: 1; }
  .hdr-actions { display: flex; align-items: center; gap: 2px; }
  .account-chip { display:grid; place-items:center; width:30px; height:30px; border-radius:50%; color:var(--action-primary); border:1px solid var(--border-accent); background:var(--surface-accent); font-size:12px; font-weight:750; }
  .header-settings { display:grid; place-items:center; width:var(--control-min); height:var(--control-min); border-radius:var(--radius-control); color:var(--text-secondary); }
  .header-settings:active, .header-settings:focus-visible { background:var(--surface-raised); color:var(--text-primary); }
  .main { flex: 1; padding: 0 12px calc(24px + env(safe-area-inset-bottom, 0px)); display: flex; flex-direction: column; gap: 10px; overscroll-behavior-y: contain; position: relative; }
  .ptr { position: absolute; top: 0; left: 50%; transform: translateX(-50%); width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; z-index: 10; transition: opacity 0.15s; pointer-events: none; color: var(--text-secondary); }
  @media (min-width: 481px) {
    .shell { border-left: 1px solid var(--border-subtle); border-right: 1px solid var(--border-subtle); }
    .shell.wide-shell { max-width: 1180px; }
  }
</style>
