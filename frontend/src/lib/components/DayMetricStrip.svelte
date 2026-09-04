<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Icon from './Icon.svelte';
  import type { DayEntry, MealEntry } from '$lib/types';

  export let entry: DayEntry | null = null;
  export let mealEntries: MealEntry[] = [];
  const dispatch = createEventDispatcher<{ open: { metric: 'steps' | 'sleep' | 'weight' | 'calories'; trigger: HTMLButtonElement } }>();

  $: consumedMeals = mealEntries.filter((meal) => meal.status === 'consumed');
  $: knownCalories = consumedMeals
    .map((meal) => meal.nutrition?.kcal)
    .filter((value): value is number => value != null)
    .map(Number);
  $: calories = knownCalories.length ? knownCalories.reduce((total, value) => total + value, 0) : null;
  $: metrics = [
    {
      key: 'steps' as const,
      icon: 'steps',
      value: entry?.steps != null ? Number(entry.steps).toLocaleString('de-DE') : '—',
      label: entry?.steps != null ? `${Number(entry.steps).toLocaleString('de-DE')} Schritte` : 'Keine Schritte erfasst'
    },
    {
      key: 'sleep' as const,
      icon: 'sleep',
      value: entry?.sleep_hours != null ? `${Number(entry.sleep_hours).toLocaleString('de-DE', { maximumFractionDigits: 1 })} h` : '—',
      label: entry?.sleep_hours != null ? `${Number(entry.sleep_hours).toLocaleString('de-DE', { maximumFractionDigits: 1 })} Stunden Schlaf` : 'Kein Schlaf erfasst'
    },
    {
      key: 'weight' as const,
      icon: 'weight',
      value: entry?.weight_kg != null ? `${Number(entry.weight_kg).toLocaleString('de-DE', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} kg` : '—',
      label: entry?.weight_kg != null ? `${Number(entry.weight_kg).toLocaleString('de-DE', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} Kilogramm Gewicht` : 'Kein Gewicht erfasst'
    },
    {
      key: 'calories' as const,
      icon: 'meal',
      value: calories == null ? '—' : `${Math.round(calories).toLocaleString('de-DE')} kcal`,
      label: calories == null ? 'Keine Energie erfasst' : `${Math.round(calories).toLocaleString('de-DE')} Kilokalorien Energie`
    }
  ];
</script>

<section class="metric-strip" aria-label="Tageskennzahlen">
  {#each metrics as metric (metric.icon)}
    <button type="button" class="metric" aria-label={`${metric.label}. Details öffnen`} title={`${metric.label} – Details öffnen`} onclick={(event) => dispatch('open', { metric: metric.key, trigger: event.currentTarget })}>
      <Icon name={metric.icon} size={14} />
      <span>{metric.value}</span>
    </button>
  {/each}
</section>

<style>
  .metric-strip { display:flex; align-items:center; justify-content:space-between; gap:var(--space-2); min-height:28px; padding:0 var(--space-1); color:var(--text-secondary); }
  .metric { display:flex; align-items:center; min-width:0; gap:4px; padding:3px; border:0; border-radius:var(--radius-control); background:transparent; color:inherit; font:inherit; font-size:11px; font-weight:700; line-height:1; white-space:nowrap; cursor:pointer; }
  .metric :global(svg) { flex:0 0 auto; color:var(--text-tertiary); }
  .metric:active { background:var(--surface-pressed); }
  .metric:focus-visible { outline:2px solid var(--status-info); outline-offset:2px; }
  @media (max-width:380px) { .metric-strip { gap:6px; } .metric { gap:3px; font-size:10px; } }
</style>
