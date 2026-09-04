<script lang="ts">
  import Icon from './Icon.svelte';
  import type { DayEntry, MealEntry } from '$lib/types';

  export let entry: DayEntry | null = null;
  export let mealEntries: MealEntry[] = [];

  $: consumedMeals = mealEntries.filter((meal) => meal.status === 'consumed');
  $: knownCalories = consumedMeals
    .map((meal) => meal.nutrition?.kcal)
    .filter((value): value is number => value != null)
    .map(Number);
  $: calories = knownCalories.length ? knownCalories.reduce((total, value) => total + value, 0) : null;
  $: metrics = [
    {
      icon: 'steps',
      value: entry?.steps != null ? Number(entry.steps).toLocaleString('de-DE') : '—',
      label: entry?.steps != null ? `${Number(entry.steps).toLocaleString('de-DE')} Schritte` : 'Keine Schritte erfasst'
    },
    {
      icon: 'sleep',
      value: entry?.sleep_hours != null ? `${Number(entry.sleep_hours).toLocaleString('de-DE', { maximumFractionDigits: 1 })} h` : '—',
      label: entry?.sleep_hours != null ? `${Number(entry.sleep_hours).toLocaleString('de-DE', { maximumFractionDigits: 1 })} Stunden Schlaf` : 'Kein Schlaf erfasst'
    },
    {
      icon: 'weight',
      value: entry?.weight_kg != null ? `${Number(entry.weight_kg).toLocaleString('de-DE', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} kg` : '—',
      label: entry?.weight_kg != null ? `${Number(entry.weight_kg).toLocaleString('de-DE', { minimumFractionDigits: 1, maximumFractionDigits: 1 })} Kilogramm Gewicht` : 'Kein Gewicht erfasst'
    },
    {
      icon: 'meal',
      value: calories == null ? '—' : `${Math.round(calories).toLocaleString('de-DE')} kcal`,
      label: calories == null ? 'Keine Energie erfasst' : `${Math.round(calories).toLocaleString('de-DE')} Kilokalorien Energie`
    }
  ];
</script>

<section class="metric-strip" aria-label="Tageskennzahlen">
  {#each metrics as metric (metric.icon)}
    <span class="metric" aria-label={metric.label} title={metric.label}>
      <Icon name={metric.icon} size={14} />
      <span>{metric.value}</span>
    </span>
  {/each}
</section>

<style>
  .metric-strip { display:flex; align-items:center; justify-content:space-between; gap:var(--space-2); min-height:28px; padding:0 var(--space-1); color:var(--text-secondary); }
  .metric { display:flex; align-items:center; min-width:0; gap:4px; font-size:11px; font-weight:700; line-height:1; white-space:nowrap; }
  .metric :global(svg) { flex:0 0 auto; color:var(--text-tertiary); }
  @media (max-width:380px) { .metric-strip { gap:6px; } .metric { gap:3px; font-size:10px; } }
</style>
