<script lang="ts">
  import DateNav from '$lib/components/DateNav.svelte';
  import DayTracker from '$lib/components/DayTracker.svelte';
  import MealGrid from '$lib/components/MealGrid.svelte';
  import TodoSection from '$lib/components/TodoSection.svelte';
  import { dayData, currentDate } from '$lib/stores';
  import { api } from '$lib/api';

  // Reload day data when it changes externally
  $: data = $dayData;

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
  ontouchstart={onTouchStart}
  ontouchend={onTouchEnd}
>
  <DateNav />

  {#if data}
    <div class="cards-container">
      <DayTracker dayData={data} currentDate={$currentDate} />
      <MealGrid meals={data.meals} currentDate={$currentDate} />
      <TodoSection todos={data.todos} currentDate={$currentDate} />
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
</style>