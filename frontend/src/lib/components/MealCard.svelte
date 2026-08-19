<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import PillBadge from './PillBadge.svelte';
  import { api } from '$lib/api';
  import type { Meal } from '$lib/types';

  export let meal: Meal;

  const dispatch = createEventDispatcher();

  let expanded = false;
  let editName = '';
  let editKcal = '';
  let editProtein = '';
  let editCarbs = '';
  let editFat = '';
  let lastTap = 0;
  let photoInput: HTMLInputElement;
  let photoLoading = false;

  function handleTap() {
    const now = Date.now();
    if (now - lastTap < 300) {
      // Doppel-tap = mark done
      if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(50);
      dispatch('done', meal.id);
      lastTap = 0;
    } else {
      lastTap = now;
      // Single-tap after delay = expand
      setTimeout(() => {
        if (Date.now() - lastTap >= 300) {
          expanded = !expanded;
          if (expanded) {
            editName = meal.name ?? '';
            editKcal = String(meal.kcal ?? '');
            editProtein = String(meal.protein_g ?? '');
            editCarbs = String(meal.carbs_g ?? '');
            editFat = String(meal.fat_g ?? '');
          }
        }
      }, 320);
    }
  }

  function saveEdit() {
    dispatch('update', {
      id: meal.id,
      data: {
        name: editName,
        kcal: parseFloat(editKcal) || 0,
        protein_g: parseFloat(editProtein) || 0,
        carbs_g: parseFloat(editCarbs) || 0,
        fat_g: parseFloat(editFat) || 0,
      },
    });
    expanded = false;
  }

  function triggerPhoto() {
    photoInput?.click();
  }

  async function onPhotoSelected(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    photoLoading = true;
    try {
      const result = await api.analyzePhoto(file, meal.id);
      dispatch('photo', { id: meal.id, file, result });
    } catch {
      // graceful
    } finally {
      photoLoading = false;
      input.value = '';
    }
  }

  const SLOT_NAMES: Record<number, string> = { 1: 'Frühstück', 2: 'Mittag', 3: 'Abend', 4: 'Snack' };
  $: slotName = SLOT_NAMES[meal.meal_slot] ?? String(meal.meal_slot);
  $: displayTime = meal.default_time ? meal.default_time.slice(0, 5) : '';
  $: kcalNum = Number(meal.kcal) || 0;
  $: proteinNum = Number(meal.protein_g) || 0;
  $: carbsNum = Number(meal.carbs_g) || 0;
  $: fatNum = Number(meal.fat_g) || 0;
</script>

<div class="meal-card tap-area" class:done={meal.is_done} class:expanded={expanded} onclick={handleTap}>
  <div class="meal-header">
    {#if meal.is_done}
      <span class="done-check">✓</span>
    {/if}
    <span class="meal-name">{meal.name || slotName}</span>
    {#if displayTime}
      <span class="meal-time">{displayTime}</span>
    {/if}
  </div>

  {#if meal.photo_url}
    <div class="meal-photo">
      <img src={meal.photo_url} alt={meal.name ?? ''} />
    </div>
  {/if}

  <div class="meal-pills">
    {#if kcalNum > 0}
      <PillBadge value={kcalNum} unit="kcal" color="#f59e0b" />
    {/if}
    {#if proteinNum > 0}
      <PillBadge value={proteinNum} unit="g" color="#3b82f6" />
    {/if}
    {#if carbsNum > 0}
      <PillBadge value={carbsNum} unit="g" color="#8b5cf6" />
    {/if}
    {#if fatNum > 0}
      <PillBadge value={fatNum} unit="g" color="#ec4899" />
    {/if}
  </div>

  {#if expanded}
    <div class="meal-edit slide-down" onclick={(e) => e.stopPropagation()}>
      <input class="edit-input" placeholder="Name" bind:value={editName} />
      <div class="edit-grid">
        <input class="edit-input" type="number" placeholder="kcal" bind:value={editKcal} />
        <input class="edit-input" type="number" placeholder="P" bind:value={editProtein} />
        <input class="edit-input" type="number" placeholder="KH" bind:value={editCarbs} />
        <input class="edit-input" type="number" placeholder="F" bind:value={editFat} />
      </div>
      <div class="edit-actions">
        <button class="btn" onclick={saveEdit}>Speichern</button>
        <button class="btn btn-photo" onclick={triggerPhoto} disabled={photoLoading}>
          {photoLoading ? '⏳ …' : '📷 Foto'}
        </button>
      </div>
    </div>
  {/if}

  <input
    bind:this={photoInput}
    type="file"
    accept="image/*"
    capture="environment"
    class="hidden-input"
    onchange={onPhotoSelected}
  />
</div>

<style>
  .meal-card {
    background: #1f1f1f;
    border: 1px solid var(--card-border);
    border-radius: var(--radius-md);
    padding: 0.625rem;
    transition: opacity 0.2s, border-color 0.2s;
    cursor: pointer;
    overflow: hidden;
  }

  .meal-card.done {
    opacity: 0.5;
    border-color: var(--accent-done);
  }

  .meal-card.expanded {
    border-color: #555;
  }

  .meal-header {
    display: flex;
    align-items: center;
    gap: 4px;
    margin-bottom: 4px;
  }

  .done-check {
    color: var(--accent-done);
    font-weight: 700;
    font-size: 0.875rem;
  }

  .meal-name {
    flex: 1;
    font-size: 0.8125rem;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .meal-time {
    font-size: 0.6875rem;
    color: var(--text-secondary);
    flex-shrink: 0;
  }

  .meal-photo {
    margin: 4px 0;
    border-radius: 6px;
    overflow: hidden;
  }

  .meal-photo img {
    width: 100%;
    display: block;
    border-radius: 6px;
  }

  .meal-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: 4px;
  }

  .meal-edit {
    margin-top: 0.5rem;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .edit-input {
    width: 100%;
    padding: 6px 8px;
    border-radius: 6px;
    background: #1a1a1a;
    border: 1px solid var(--card-border);
    color: var(--text-primary);
    font-size: 0.75rem;
  }

  .edit-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
  }

  .edit-actions {
    display: flex;
    gap: 6px;
  }

  .edit-actions .btn {
    flex: 1;
  }

  .btn-photo {
    background: #333;
  }

  .hidden-input {
    display: none;
  }
</style>