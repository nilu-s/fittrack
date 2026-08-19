<script lang="ts">
  import MealCard from './MealCard.svelte';
  import PillBadge from './PillBadge.svelte';
  import ProgressBar from './ProgressBar.svelte';
  import { api } from '$lib/api';
  import { dailyGoals } from '$lib/stores';
  import type { Meal } from '$lib/types';

  export let meals: Meal[];
  export let currentDate: string;

  $: sortedMeals = [...(meals ?? [])].sort((a, b) => {
    const order = ['breakfast', 'lunch', 'dinner', 'snack'];
    return order.indexOf(a.meal_slot) - order.indexOf(b.meal_slot);
  });

  $: totalKcal = (meals ?? []).reduce((s, m) => s + (m.kcal ?? 0), 0);
  $: totalP = (meals ?? []).reduce((s, m) => s + (m.protein ?? 0), 0);
  $: totalKH = (meals ?? []).reduce((s, m) => s + (m.carbs ?? 0), 0);
  $: totalF = (meals ?? []).reduce((s, m) => s + (m.fat ?? 0), 0);
  $: goals = $dailyGoals;

  async function markDone(id: number) {
    if (!id) return;
    try {
      await api.markMealDone(id);
      meals = meals.map((m) => (m.id === id ? { ...m, is_done: !m.is_done } : m));
    } catch {
      // graceful
    }
  }

  async function updateMeal(event: CustomEvent) {
    const { id, data } = event.detail;
    if (!id) return;
    try {
      await api.updateMeal(id, data);
      meals = meals.map((m) => (m.id === id ? { ...m, ...data } : m));
    } catch {
      // graceful
    }
  }

  async function handlePhoto(_id: number) {
    // Photo upload - placeholder
    if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(30);
  }
</script>

<section class="section-card nutrition-card">
  <div class="section-header">
    <span>🍽️ Ernährung</span>
    <span class="text-sm muted">{Math.round(totalKcal)}/{goals.kcal} kcal</span>
  </div>

  <div class="card-body">
    <div class="meal-grid">
      {#each sortedMeals as meal (meal.id ?? meal.meal_slot)}
        <MealCard {meal} ondon={(e) => markDone(e.detail)} onupdate={updateMeal} onphoto={(e) => handlePhoto(e.detail)} />
      {:else}
        <div class="no-meals muted text-sm">Keine Mahlzeiten</div>
      {/each}
    </div>

    <!-- Nutrition summary -->
    <div class="nutrition-summary">
      <div class="summary-pills">
        <PillBadge value={Math.round(totalKcal)} unit="kcal" color="#f59e0b" />
        <PillBadge value={Math.round(totalP)} unit="g P" color="#3b82f6" />
        <PillBadge value={Math.round(totalKH)} unit="g KH" color="#8b5cf6" />
        <PillBadge value={Math.round(totalF)} unit="g F" color="#ec4899" />
      </div>
      <div class="summary-bars">
        <ProgressBar current={Math.round(totalKcal)} target={goals.kcal} label="kcal" color="#f59e0b" />
        <ProgressBar current={Math.round(totalP)} target={goals.protein} label="Protein" color="#3b82f6" />
        <ProgressBar current={Math.round(totalKH)} target={goals.carbs} label="KH" color="#8b5cf6" />
        <ProgressBar current={Math.round(totalF)} target={goals.fat} label="F" color="#ec4899" />
      </div>
    </div>
  </div>
</section>

<style>
  .card-body {
    padding: 0.625rem;
  }

  .meal-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }

  .no-meals {
    grid-column: 1 / -1;
    text-align: center;
    padding: 1rem;
  }

  .nutrition-summary {
    border-top: 1px solid var(--card-border);
    padding-top: 0.625rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .summary-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
  }

  .summary-bars {
    display: flex;
    flex-direction: column;
    gap: 5px;
  }
</style>