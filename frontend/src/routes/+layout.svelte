<script lang="ts">
  import '../app.css';
  import { onMount, afterUpdate } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { currentDate, dayData, onlineStatus } from '$lib/stores';
  import { initSync } from '$lib/sync';
  import { api } from '$lib/api';
  import { db } from '$lib/db';
  import { aliasRequired, isAuthenticated, checkAuth } from '$lib/auth';
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
  // Keep recently visited days ready for a direct, data-correct transition.
  // This cache lives only for the active layout instance and is cleared at logout.
  const dayCache = new Map<string, DayData>();
  const dayRequests = new Map<string, Promise<DayData>>();
  let activeDayRequest = 0;
  let dayCacheGeneration = 0;
  $: isMealSettings = $page?.url?.pathname === '/settings/meals';
  $: isShopping = $page?.url?.pathname === '/shopping';
  $: isLogin = $page?.url?.pathname === '/login';
  $: isAliasOnboarding = $page?.url?.pathname === '/onboarding/alias';
  $: isHome = $page?.url?.pathname === '/';
  $: backTarget = $page?.url?.pathname?.startsWith('/settings/') ? '/settings' : '/';
  // Optimistic edits are written to the shared day store by child components.
  // Mirror them so a quick return to this day never restores an older cache copy.
  $: if ($dayData?.dayEntry?.date) dayCache.set($dayData.dayEntry.date, $dayData);


  async function fetchDayData(date: string): Promise<DayData> {
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
      let data: DayData = { dayEntry: dayEntry ?? { date }, mealEntries: displayedEntries, todos: todos ?? [], trainingSuggestion: trainingSuggestion as TrainingSuggestion | null, nextTraining, weekStats: null };
      if (dayEntry) await db.dayEntries.put({ ...dayEntry, date, updated_at: dayEntry.updated_at } as any);
      const fitResult = await fitSyncPromise;
      if (fitResult && data.dayEntry) {
        const cur = data.dayEntry;
        const updatedEntry = { ...cur, steps: fitResult.steps ?? cur.steps, steps_confirmed: fitResult.steps_confirmed ?? true, steps_source: fitResult.steps_source ?? 'google_fit' };
        if (fitResult.sleep_hours != null && fitResult.sleep_hours > 0) {
          updatedEntry.sleep_hours = fitResult.sleep_hours;
          updatedEntry.sleep_deep_hours = fitResult.sleep_deep_hours;
          updatedEntry.sleep_rem_hours = fitResult.sleep_rem_hours;
          updatedEntry.sleep_light_hours = fitResult.sleep_light_hours;
          updatedEntry.sleep_awake_hours = fitResult.sleep_awake_hours;
          updatedEntry.sleep_efficiency = fitResult.sleep_efficiency;
          updatedEntry.sleep_quality = fitResult.sleep_quality;
        }
        data = { ...data, dayEntry: updatedEntry as DayEntry };
      }
      return data;
    } catch (e) {
      console.warn('Failed to load day data:', e);
      const ce = await db.dayEntries.where('date').equals(date).first();
      const ct = await db.todos.where('date').equals(date).toArray();
      // Meal entries are revision-aware and online-first; never revive a
      // removed legacy IndexedDB meal record during an offline fallback.
      return { dayEntry: ce ?? { date }, mealEntries: [], todos: ct ?? [], trainingSuggestion: null, nextTraining: null, weekStats: null };
    }
  }

  function dayAfter(date: string, offset: number): string {
    const result = new Date(`${date}T00:00:00`);
    result.setDate(result.getDate() + offset);
    return `${result.getFullYear()}-${String(result.getMonth() + 1).padStart(2, '0')}-${String(result.getDate()).padStart(2, '0')}`;
  }

  function readDayData(date: string, force = false): Promise<DayData> {
    if (!force) {
      const cached = dayCache.get(date);
      if (cached) return Promise.resolve(cached);
    }
    const pending = dayRequests.get(date);
    if (pending) return pending;
    const generation = dayCacheGeneration;
    const request = fetchDayData(date).then((data) => {
      if (generation === dayCacheGeneration) dayCache.set(date, data);
      return data;
    }).finally(() => dayRequests.delete(date));
    dayRequests.set(date, request);
    return request;
  }

  function preloadAdjacentDays(date: string) {
    for (const offset of [-1, 1]) void readDayData(dayAfter(date, offset)).catch(() => undefined);
  }

  async function loadDayData(date: string, force = false) {
    const request = ++activeDayRequest;
    const data = await readDayData(date, force);
    // Requests can finish in any order. Only the still-selected day may replace
    // the rendered data; otherwise briefly reused cards can appear on the wrong day.
    if (request !== activeDayRequest || date !== $currentDate) return;
    dayData.set(data);
    preloadAdjacentDays(date);
  }

  $: if ($currentDate && authChecked && $isAuthenticated && !$aliasRequired) loadDayData($currentDate);

  $: if (typeof window !== 'undefined') {
    import('$lib/stores').then(({ syncStatus }) => { syncStatus.subscribe((status) => { syncIcon = { synced: '✓', syncing: '⟳', offline: '📵', error: '⚠' }[status] ?? '✓'; syncClass = status; }); });
  }

  onMount(() => {
    const timeout = new Promise<void>((resolve) => setTimeout(resolve, 3000));
    Promise.race([checkAuth(), timeout]).then(() => {
      authChecked = true;
      const checkAuthGate = () => { const p = $page?.url?.pathname ?? ''; if (!$isAuthenticated && p !== '/login') return void goto('/login'); if ($isAuthenticated && $aliasRequired && p !== '/onboarding/alias') return void goto('/onboarding/alias'); if ($isAuthenticated && !$aliasRequired && p === '/onboarding/alias') return void goto('/'); };
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

  afterUpdate(() => { if (!authChecked) return; const p = $page?.url?.pathname ?? ''; if (!$isAuthenticated && p !== '/login') return void goto('/login'); if ($isAuthenticated && $aliasRequired && p !== '/onboarding/alias') return void goto('/onboarding/alias'); if ($isAuthenticated && !$aliasRequired && p === '/onboarding/alias') return void goto('/'); });

  function onTouchStart(e: TouchEvent) { if (isRefreshing) return; if (window.scrollY <= 0) { touchStartY = e.touches[0].clientY; isPulling = true; } else { isPulling = false; } }
  function onTouchMove(e: TouchEvent) { if (!isPulling || isRefreshing) return; const delta = e.touches[0].clientY - touchStartY; if (delta > 0 && window.scrollY <= 0) { pullDistance = Math.min(delta * 0.5, pullThreshold * 1.5); if (pullDistance > 5) e.preventDefault(); } }
  async function onTouchEnd() { if (!isPulling || isRefreshing) return; isPulling = false; if (pullDistance >= pullThreshold) { isRefreshing = true; pullDistance = pullThreshold; await loadDayData($currentDate, true); if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(30); isRefreshing = false; } pullDistance = 0; }
</script>

<div class:wide-shell={isMealSettings || isShopping} class="shell">
  {#if !isLogin && !isAliasOnboarding}<header class="hdr">
    {#if isHome}
      <a href="/" class="hdr-title" aria-label={`${APP_NAME} Startseite`}><img class="brand-icon" src="/brand-icon.svg" alt="" /><span>{APP_NAME}</span></a>
    {:else}
      <a href={backTarget} class="header-back" aria-label="Zurück"><Icon name="chevron-left" size={20} /><span>Zurück</span></a>
    {/if}
    <div class="hdr-spacer"></div>
    <div class="hdr-actions">
      {#if $isAuthenticated}<a href="/contacts" class="header-friends" aria-label="Kontakte"><Icon name="contacts" size={19} /></a>{/if}
      {#if $isAuthenticated}<UiIconButton ariaLabel="Einstellungen" onclick={() => goto('/settings')}><Icon name="settings" size={18} /></UiIconButton>{/if}
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
  .header-friends { display:grid; place-items:center; min-height:var(--control-min); padding:0 8px; border-radius:var(--radius-control); color:var(--action-primary); font-size:12px; font-weight:750; text-decoration:none; }
  .header-friends:active,.header-friends:focus-visible { background:var(--surface-raised); }
  .main { flex: 1; padding: 0 12px calc(24px + env(safe-area-inset-bottom, 0px)); display: flex; flex-direction: column; gap: 10px; overscroll-behavior-y: contain; position: relative; }
  .ptr { position: absolute; top: 0; left: 50%; transform: translateX(-50%); width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; z-index: 10; transition: opacity 0.15s; pointer-events: none; color: var(--text-secondary); }
  @media (min-width: 481px) {
    .shell { border-left: 1px solid var(--border-subtle); border-right: 1px solid var(--border-subtle); }
    .shell.wide-shell { max-width: 1180px; }
  }
</style>
