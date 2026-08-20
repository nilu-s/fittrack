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
    return (a.meal_slot ?? 99) - (b.meal_slot ?? 99);
  });

  $: totalKcal = (meals ?? []).reduce((s, m) => s + (Number(m.kcal) || 0), 0);
  $: totalP = (meals ?? []).reduce((s, m) => s + (Number(m.protein_g) || 0), 0);
  $: totalKH = (meals ?? []).reduce((s, m) => s + (Number(m.carbs_g) || 0), 0);
  $: totalF = (meals ?? []).reduce((s, m) => s + (Number(m.fat_g) || 0), 0);
  $: goals = $dailyGoals;

  const SLOT_NAMES: Record<number, string> = { 1: 'Frühstück', 2: 'Mittag', 3: 'Snack', 4: 'Abend' };

  let photoInput: HTMLInputElement;
  let photoLoading = false;
  let confirmData: { slot: number; name: string; kcal: number; protein_g: number; carbs_g: number; fat_g: number } | null = null;
  let choosingSlot = false;

  function getCurrentSlot(): number {
    const now = new Date();
    const t = now.getHours() * 60 + now.getMinutes();
    if (t >= 4 * 60 && t < 10 * 60 + 30) return 1;
    if (t >= 10 * 60 + 30 && t < 14 * 60) return 2;
    if (t >= 14 * 60 && t < 17 * 60 + 30) return 3;
    if (t >= 17 * 60 + 30 && t < 22 * 60) return 4;
    return 1;
  }

  function parseVisionResult(result: any): { name: string; kcal: number; protein_g: number; carbs_g: number; fat_g: number } | null {
    if (!result?.analysis?.total) return null;
    const total = result.analysis.total;
    const firstItem = result.analysis.items?.[0];
    return {
      name: firstItem?.name ?? 'Erkanntes Gericht',
      kcal: Number(total.kcal) || 0,
      protein_g: Number(total.protein_g) || 0,
      carbs_g: Number(total.carbs_g) || 0,
      fat_g: Number(total.fat_g) || 0,
    };
  }

  async function markDone(id: string | number) {
    if (!id) return;
    try {
      await api.markMealDone(id);
      meals = meals.map((m) => (m.id === id ? { ...m, is_done: !m.is_done } : m));
    } catch {
      // graceful
    }
  }

  async function patchMeal(id: string | number, data: Partial<Meal>) {
    if (!id) return;
    try {
      await api.updateMeal(id, data);
      meals = meals.map((m) => (m.id === id ? { ...m, ...data } : m));
    } catch {
      // graceful
    }
  }

  async function updateMeal(event: CustomEvent) {
    const { id, data } = event.detail;
    await patchMeal(id, data);
  }

  async function handlePhoto(event: CustomEvent) {
    const { id, file, result } = event.detail;
    if (!file) return;
    if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(30);
    const parsed = parseVisionResult(result);
    if (parsed && id) {
      await patchMeal(id, {
        name: parsed.name,
        kcal: parsed.kcal,
        protein_g: parsed.protein_g,
        carbs_g: parsed.carbs_g,
        fat_g: parsed.fat_g,
      });
    } else if (result?.error) {
      console.warn('Photo analysis error:', result.error);
    }
  }

  function triggerStandalonePhoto() {
    photoInput?.click();
  }

  async function onStandalonePhotoSelected(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    photoLoading = true;
    try {
      const result = await api.analyzePhoto(file);
      const parsed = parseVisionResult(result);
      if (parsed) {
        confirmData = { slot: getCurrentSlot(), ...parsed };
        choosingSlot = false;
      } else if (result?.error) {
        console.warn('Photo analysis error:', result.error);
      }
    } catch {
      // graceful
    } finally {
      photoLoading = false;
      input.value = '';
    }
  }

  async function assignToSlot(slot: number) {
    if (!confirmData) return;
    const meal = meals.find((m) => m.meal_slot === slot);
    if (!meal || !meal.id) {
      choosingSlot = false;
      confirmData = null;
      return;
    }
    await patchMeal(meal.id, {
      name: confirmData.name,
      kcal: confirmData.kcal,
      protein_g: confirmData.protein_g,
      carbs_g: confirmData.carbs_g,
      fat_g: confirmData.fat_g,
    });
    try {
      await api.markMealDone(meal.id);
      meals = meals.map((m) => (m.id === meal.id ? { ...m, is_done: true } : m));
    } catch {
      // graceful
    }
    confirmData = null;
    choosingSlot = false;
  }

  function cancelConfirm() {
    confirmData = null;
    choosingSlot = false;
  }
</script>

<section class="section-card nutrition-card">
  <div class="section-header">
    <span>🍽️ Ernährung</span>
    <span class="text-sm muted">{Math.round(totalKcal)}/{goals.kcal} kcal</span>
  </div>

  <div class="card-body">
    <!-- Standalone photo card -->
    <button class="camera-card" onclick={triggerStandalonePhoto} disabled={photoLoading}>
      <span class="camera-icon">{photoLoading ? '⏳' : '📷'}</span>
      <span class="camera-label">{photoLoading ? 'Analysiere…' : 'Foto aufnehmen'}</span>
      <span class="camera-hint muted text-xs">Mahlzeit wird automatisch erkannt</span>
    </button>

    <div class="meal-grid">
      {#each sortedMeals as meal (meal.id ?? meal.meal_slot)}
        <MealCard {meal} ondon={(e) => markDone(e.detail)} onupdate={updateMeal} onphoto={handlePhoto} />
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

  <input
    bind:this={photoInput}
    type="file"
    accept="image/*"
    capture="environment"
    class="hidden-input"
    onchange={onStandalonePhotoSelected}
  />

  {#if confirmData}
    <!-- Confirmation / slot picker modal -->
    <div class="modal-overlay" onclick={cancelConfirm}>
      <div class="modal-card" onclick={(e) => e.stopPropagation()}>
        {#if choosingSlot}
          <div class="modal-title">Mahlzeit wählen</div>
          <div class="slot-list">
            {#each sortedMeals as meal (meal.id ?? meal.meal_slot)}
              <button class="slot-btn" onclick={() => assignToSlot(meal.meal_slot)}>
                <span class="slot-name">{meal.name || SLOT_NAMES[meal.meal_slot] || `Slot ${meal.meal_slot}`}</span>
                <span class="slot-time muted text-xs">{meal.default_time ? meal.default_time.slice(0, 5) : ''}</span>
              </button>
            {/each}
          </div>
          <button class="modal-secondary" onclick={cancelConfirm}>Abbrechen</button>
        {:else}
          {@const data = confirmData}
          <div class="modal-title">{data.name}</div>
          <div class="modal-body text-sm">
            <p class="muted">
              Automatisch zugewiesen zu:
              <strong class="assigned-meal">{SLOT_NAMES[data.slot] || `Slot ${data.slot}`}</strong>
            </p>
            <div class="modal-pills">
              <PillBadge value={Math.round(data.kcal)} unit="kcal" color="#f59e0b" />
              <PillBadge value={Math.round(data.protein_g)} unit="g P" color="#3b82f6" />
              <PillBadge value={Math.round(data.carbs_g)} unit="g KH" color="#8b5cf6" />
              <PillBadge value={Math.round(data.fat_g)} unit="g F" color="#ec4899" />
            </div>
          </div>
          <div class="modal-actions">
            <button class="modal-primary" onclick={() => assignToSlot(data.slot)}>Akzeptieren</button>
            <button class="modal-secondary" onclick={() => (choosingSlot = true)}>Andere wählen</button>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</section>

<style>
  .card-body {
    padding: 0.625rem;
  }

  .camera-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 100%;
    padding: 0.75rem;
    margin-bottom: 0.75rem;
    border-radius: var(--radius-md);
    background: #1f1f1f;
    border: 1px dashed var(--card-border);
    color: var(--text-primary);
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
  }

  .camera-card:disabled {
    opacity: 0.7;
    cursor: wait;
  }

  .camera-card:active {
    background: #252525;
    border-color: #555;
  }

  .camera-icon {
    font-size: 1.5rem;
    margin-bottom: 0.25rem;
  }

  .camera-label {
    font-size: 0.8125rem;
    font-weight: 500;
  }

  .camera-hint {
    margin-top: 0.125rem;
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

  .hidden-input {
    display: none;
  }

  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
    z-index: 100;
  }

  .modal-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: var(--radius-lg);
    padding: 1rem;
    width: 100%;
    max-width: 320px;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .modal-title {
    font-size: 0.9375rem;
    font-weight: 600;
    color: var(--text-primary);
    text-align: center;
  }

  .modal-body p {
    text-align: center;
    margin-bottom: 0.5rem;
  }

  .assigned-meal {
    color: var(--accent-done);
  }

  .modal-pills {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 4px;
  }

  .modal-actions {
    display: flex;
    gap: 0.5rem;
  }

  .modal-actions button,
  .modal-secondary,
  .modal-primary {
    flex: 1;
    padding: 0.625rem;
    border-radius: var(--radius-sm);
    border: 1px solid var(--card-border);
    font-size: 0.8125rem;
    font-weight: 500;
    cursor: pointer;
  }

  .modal-primary {
    background: var(--accent-done);
    color: #0f0f0f;
    border-color: var(--accent-done);
  }

  .modal-secondary {
    background: #333;
    color: var(--text-primary);
  }

  .slot-list {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
  }

  .slot-btn {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.625rem;
    border-radius: var(--radius-sm);
    background: #1f1f1f;
    border: 1px solid var(--card-border);
    color: var(--text-primary);
    cursor: pointer;
  }

  .slot-btn:active {
    background: #252525;
  }

  .slot-name {
    font-size: 0.8125rem;
    font-weight: 500;
  }
</style>
