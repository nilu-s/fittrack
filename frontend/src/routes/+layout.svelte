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
  import UiIconButton from '$lib/components/ui/UiIconButton.svelte';
  import type { DayData, DayEntry, Meal, MealCategory, MealEntry, Recipe, Todo, TrainingSuggestion } from '$lib/types';

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
  $: isLogin = $page?.url?.pathname === '/login';
  $: isHome = $page?.url?.pathname === '/';
  $: backTarget = $page?.url?.pathname?.startsWith('/settings/') ? '/settings' : '/';


  async function loadDayData(date: string) {
    const fitSyncPromise = api.syncGoogleFit(date).catch(() => null);
    try {
      const [dayEntry, mealEntries, categories, recipes, todos, trainingSuggestion] = await Promise.all([
        api.getDayEntry(date),
        // Project the active plan before reading it.  This is idempotent and
        // keeps the dashboard independent of the removed legacy meals table.
        api.instantiateMealEntries(date).catch(() => [] as MealEntry[]),
        api.getMealCategories().catch(() => [] as MealCategory[]),
        api.getRecipes().catch(() => [] as Recipe[]),
        api.getTodos(date), api.getTraining(date)
      ]);
      const categoryById = new Map(categories.map((category) => [category.id, category]));
      const recipeById = new Map(recipes.map((recipe) => [recipe.id, recipe]));
      const meals: Meal[] = mealEntries.map((entry, index) => {
        const category = categoryById.get(entry.category_id);
        const nutrition = entry.nutrition ?? {};
        const recipeId = entry.items?.find((item) => item.recipe_id)?.recipe_id;
        return {
          id: entry.id, date: entry.date, name: entry.name ?? undefined,
          // The old component uses slots only for ordering. Category order is
          // stable and account-scoped, so it is the correct replacement.
          meal_slot: (category?.sort_order ?? index) + 1,
          default_time: category?.default_time ?? undefined,
          kcal: nutrition.kcal, protein_g: nutrition.protein_g, carbs_g: nutrition.carbs_g,
          fat_g: nutrition.fat_g, fiber_g: nutrition.fiber_g, sugar_g: nutrition.sugar_g,
          free_sugar_g: nutrition.free_sugar_g,
          // Both consumed and explicitly skipped meals are closed items.  Only
          // planned meals belong in the day's open-count and open section.
          is_done: entry.status !== 'planned', meal_entry: true,
          meal_entry_status: entry.status, category_name: category?.name,
          category_id: entry.category_id, meal_entry_items: entry.items,
          recipe_instructions: recipeId ? recipeById.get(recipeId)?.instructions ?? [] : [],
          updated_at: entry.updated_at,
        };
      });
      let nextTraining: TrainingSuggestion | null = null;
      if (dayEntry?.training_type) nextTraining = await api.getNextTraining(dayEntry.training_type);
      const data: DayData = { dayEntry: dayEntry ?? { date }, meals, todos: todos ?? [], trainingSuggestion: trainingSuggestion as TrainingSuggestion | null, nextTraining, weekStats: null };
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
      dayData.set({ dayEntry: ce ?? { date }, meals: [], todos: ct ?? [], trainingSuggestion: null, nextTraining: null, weekStats: null });
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

<div class:wide-shell={isMealSettings} class="shell">
  {#if !isLogin}<header class="hdr">
    {#if isHome}
      <a href="/" class="hdr-title" aria-label="FitTrack Startseite"><span class="brand-mark">F</span><span>FitTrack</span></a>
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
  .hdr { display: flex; align-items: center; padding: 12px 16px; padding-top: calc(12px + env(safe-area-inset-top, 0px)); gap: 8px; border-bottom: 1px solid var(--border-subtle); }
  .hdr-title { display:flex; align-items:center; gap:8px; font-size:17px; font-weight:720; letter-spacing:-.03em; color:var(--text-primary); text-decoration:none; }
  .brand-mark { display:grid; place-items:center; width:27px; height:27px; border-radius:8px; color:var(--text-on-accent); background:var(--action-primary); font-size:13px; }
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
