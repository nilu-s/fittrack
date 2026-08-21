<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import PillBadge from './PillBadge.svelte';
  import Icon from './Icon.svelte';
  import { api } from '$lib/api';
  import type { Meal, Dish, PhotoAnalysisResponse } from '$lib/types';

  export let meal: Meal;
  const dispatch = createEventDispatcher();

  let expanded = false;
  let editName = ''; let editKcal = ''; let editProtein = ''; let editCarbs = ''; let editFat = ''; let editFiber = ''; let editSugar = '';
  let lastTap = 0;
  let photoInput: HTMLInputElement;
  let photoLoading = false;

  // Long-press state
  let pressTimer: ReturnType<typeof setTimeout> | null = null;
  let longPressed = false;
  let editModal = false;
  let dishes: Dish[] = [];
  let loadingDishes = false;

  const SLOT_NAMES: Record<number, string> = { 1: 'Frühstück', 2: 'Mittag', 3: 'Snack', 4: 'Abendessen' };
  $: slotName = SLOT_NAMES[meal.meal_slot] ?? String(meal.meal_slot);
  $: displayTime = meal.default_time ? meal.default_time.slice(0, 5) : '';
  $: kcalNum = Number(meal.kcal) || 0;
  $: proteinNum = Number(meal.protein_g) || 0;
  $: carbsNum = Number(meal.carbs_g) || 0;
  $: fatNum = Number(meal.fat_g) || 0;
  $: fiberNum = Number(meal.fiber_g) || 0;
  $: sugarNum = Number(meal.sugar_g) || 0;

  // --- Gesture handling ---
  function onTouchStart() {
    longPressed = false;
    pressTimer = setTimeout(() => {
      longPressed = true;
      if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(80);
      openEditModal();
    }, 500);
  }

  function onTouchEnd() {
    if (pressTimer) { clearTimeout(pressTimer); pressTimer = null; }
  }

  function onTouchMove() {
    if (pressTimer) { clearTimeout(pressTimer); pressTimer = null; }
  }

  function handleTap() {
    if (longPressed) return; // long-press already handled
    const now = Date.now();
    if (now - lastTap < 300) {
      // Double tap → toggle done
      if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(50);
      dispatch('done', meal.id);
      lastTap = 0;
    } else {
      lastTap = now;
      setTimeout(() => {
        if (Date.now() - lastTap >= 300) {
          // Single tap → expand
          expanded = !expanded;
          if (expanded) {
            editName = meal.name ?? '';
            editKcal = String(meal.kcal ?? '');
            editProtein = String(meal.protein_g ?? '');
            editCarbs = String(meal.carbs_g ?? '');
            editFat = String(meal.fat_g ?? '');
            editFiber = String(meal.fiber_g ?? '');
            editSugar = String(meal.sugar_g ?? '');
          }
        }
      }, 320);
    }
  }

  // --- Edit modal (long-press) ---
  async function openEditModal() {
    editModal = true;
    loadingDishes = true;
    try {
      dishes = await api.getDishes(meal.meal_slot);
    } catch { dishes = []; }
    loadingDishes = false;
  }

  function closeEditModal() {
    editModal = false;
  }

  async function selectDish(dish: Dish) {
    if (!dish.id) return;
    dispatch('update', {
      id: meal.id,
      data: {
        name: dish.name,
        kcal: Number(dish.kcal) || 0,
        protein_g: Number(dish.protein_g) || 0,
        carbs_g: Number(dish.carbs_g) || 0,
        fat_g: Number(dish.fat_g) || 0,
        fiber_g: Number(dish.fiber_g) || 0,
        sugar_g: Number(dish.sugar_g) || 0,
        free_sugar_g: Number(dish.free_sugar_g) || 0,
      },
    });
    try { await api.incrementDishUsage(dish.id); } catch {}
    editModal = false;
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
      const result = await api.analyzePhoto(file, meal.id) as PhotoAnalysisResponse | null;
      if (result?.analysis?.total) {
        const total = result.analysis.total;
        const firstName = result.analysis.items?.[0]?.name ?? 'Erkanntes Gericht';
        // Update meal with analysis values
        dispatch('update', {
          id: meal.id,
          data: {
            name: firstName,
            kcal: Number(total.kcal) || 0,
            protein_g: Number(total.protein_g) || 0,
            carbs_g: Number(total.carbs_g) || 0,
            fat_g: Number(total.fat_g) || 0,
            fiber_g: Number(total.fiber_g) || 0,
            sugar_g: Number(total.sugar_g) || 0, free_sugar_g: Number(total.free_sugar_g) || 0,
          },
        });

        // Handle dish match
        if (result.dish_match?.matched && result.dish_match.dish) {
          // Existing dish found — just increment usage
          try { await api.incrementDishUsage(result.dish_match.dish.id!); } catch {}
        } else {
          // No match — create new dish in DB
          try {
            await api.createDish({
              slot: meal.meal_slot,
              name: firstName,
              kcal: Number(total.kcal) || 0,
              protein_g: Number(total.protein_g) || 0,
              carbs_g: Number(total.carbs_g) || 0,
              fat_g: Number(total.fat_g) || 0,
              fiber_g: Number(total.fiber_g) || 0,
              sugar_g: Number(total.sugar_g) || 0, free_sugar_g: Number(total.free_sugar_g) || 0,
              source: 'photo',
            });
          } catch {}
        }
      }
    } catch {} finally {
      photoLoading = false;
      input.value = '';
      editModal = false;
    }
  }

  function saveManualEdit() {
    dispatch('update', {
      id: meal.id,
      data: {
        name: editName,
        kcal: parseFloat(editKcal) || 0,
        protein_g: parseFloat(editProtein) || 0,
        carbs_g: parseFloat(editCarbs) || 0,
        fat_g: parseFloat(editFat) || 0,
        fiber_g: parseFloat(editFiber) || 0,
        sugar_g: parseFloat(editSugar) || 0,
      },
    });
    expanded = false;
  }
</script>

<div
  class="mc tap-area"
  class:done={meal.is_done}
  class:expanded
  onclick={handleTap}
  ontouchstart={onTouchStart}
  ontouchend={onTouchEnd}
  ontouchmove={onTouchMove}
  oncontextmenu={(e: Event) => e.preventDefault()}
  role="button"
  tabindex="0"
>
  <div class="mc-slot"><span>{slotName}</span>{#if displayTime}<span>{displayTime}</span>{/if}</div>
  <div class="mc-hdr">
    <div class="mc-check" class:done={meal.is_done}>{#if meal.is_done}<Icon name="check" size={14} />{/if}</div>
    <span class="mc-name">{meal.name || 'Gericht auswählen'}</span>
  </div>
  {#if meal.photo_url}<div class="mc-photo"><img src={meal.photo_url} alt={meal.name ?? ''} /></div>{/if}
  <div class="mc-pills">
    {#if kcalNum > 0}<PillBadge value={kcalNum} unit="kcal" color="var(--amber)" />{/if}
    {#if proteinNum > 0}<PillBadge value={proteinNum} unit="g" color="var(--blue)" />{/if}
    {#if carbsNum > 0}<PillBadge value={carbsNum} unit="g" color="var(--purple)" />{/if}
    {#if fatNum > 0}<PillBadge value={fatNum} unit="g F" color="var(--pink)" />{/if}
    {#if fiberNum > 0}<PillBadge value={fiberNum} unit="g Ballaststoffe" color="var(--green)" />{/if}
    {#if sugarNum > 0}<PillBadge value={sugarNum} unit="g Zucker" color="var(--amber)" />{/if}
  </div>
  <div class="mc-hint">Lange drücken zum Bearbeiten · Doppeltap = Done</div>
  {#if expanded}
    <div class="mc-edit slide-down" onclick={(e) => e.stopPropagation()}>
      <input placeholder="Name" bind:value={editName} />
      <div class="mc-grid">
        <input type="number" placeholder="kcal" bind:value={editKcal} />
        <input type="number" placeholder="P" bind:value={editProtein} />
        <input type="number" placeholder="KH" bind:value={editCarbs} />
        <input type="number" placeholder="F" bind:value={editFat} />
        <input type="number" placeholder="Ballaststoffe" bind:value={editFiber} />
        <input type="number" placeholder="Zucker" bind:value={editSugar} />
      </div>
      <div class="mc-actions">
        <button class="btn" onclick={saveManualEdit}>Speichern</button>
        <button class="btn" onclick={triggerPhoto} disabled={photoLoading}>
          {#if photoLoading}<Icon name="refresh" size={16} />{:else}<Icon name="camera" size={16} />{/if}
        </button>
      </div>
    </div>
  {/if}
  <input bind:this={photoInput} type="file" accept="image/*" capture="environment" style="display:none" onchange={onPhotoSelected} />
</div>

<!-- Edit Modal (long-press) -->
{#if editModal}
  <div class="modal-overlay" onclick={closeEditModal}>
    <div class="modal-card" onclick={(e) => e.stopPropagation()}>
      <div class="modal-title">{slotName} bearbeiten</div>

      <!-- Preset list -->
      <div class="modal-section-label">Presets</div>
      {#if loadingDishes}
        <div class="modal-loading">Lade Presets…</div>
      {:else if dishes.length === 0}
        <div class="modal-empty">Keine Presets vorhanden</div>
      {:else}
        <div class="dish-list">
          {#each dishes as dish (dish.id)}
            <button
              class="dish-btn"
              class:active={dish.name === meal.name}
              class:default={dish.is_default}
              onclick={() => selectDish(dish)}
            >
              <div class="dish-info">
                <span class="dish-name">{dish.name}</span>
                {#if dish.is_default}<span class="dish-badge">Standard</span>{/if}
                {#if (dish.usage_count ?? 0) > 0}<span class="dish-uses">{dish.usage_count}×</span>{/if}
              </div>
              <div class="dish-macros">
                <span>{Math.round(Number(dish.kcal) || 0)} kcal</span>
                <span>{Math.round(Number(dish.protein_g) || 0)}g P</span>
                <span>{Math.round(Number(dish.fiber_g) || 0)}g Ballaststoffe</span>
                <span>{Math.round(Number(dish.sugar_g) || 0)}g Zucker</span>
              </div>
            </button>
          {/each}
        </div>
      {/if}

      <!-- Actions -->
      <div class="modal-actions">
        <button class="modal-primary cam-action" onclick={triggerPhoto} disabled={photoLoading}>
          {#if photoLoading}<Icon name="refresh" size={18} />{:else}<Icon name="camera" size={18} />{/if}
          <span>{photoLoading ? 'Analysiere…' : 'Foto analysieren'}</span>
        </button>
        <button class="modal-secondary" onclick={closeEditModal}>Abbrechen</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .mc { background: var(--card-2); border: 1px solid var(--border); border-radius: var(--radius); padding: 12px; transition: opacity 0.15s; cursor: pointer; overflow: hidden; }
  .mc.done { opacity: 0.4; border-color: var(--green); }
  .mc.expanded { border-color: var(--border-2); }
  .mc:active { opacity: 0.8; }
  .mc-slot { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; color: var(--blue); font-size: 10px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }
  .mc-slot span:last-child { color: var(--text-faint); font-weight: 500; letter-spacing: 0; text-transform: none; }
  .mc-hdr { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
  .mc-check { width: 18px; height: 18px; border-radius: 50%; border: 1.5px solid var(--border-2); flex-shrink: 0; display: flex; align-items: center; justify-content: center; color: transparent; transition: all 0.2s; }
  .mc-check.done { background: var(--green); border-color: var(--green); color: #000; }
  .mc-name { flex: 1; font-size: 14px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .mc-time { font-size: 11px; color: var(--text-faint); flex-shrink: 0; }
  .mc-photo { margin: 6px 0; border-radius: 6px; overflow: hidden; }
  .mc-photo img { width: 100%; display: block; border-radius: 6px; }
  .mc-pills { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
  .mc-hint { font-size: 10px; color: var(--text-faint); margin-top: 6px; opacity: 0.6; }
  .mc-edit { margin-top: 8px; display: flex; flex-direction: column; gap: 8px; }
  .mc-edit input { width: 100%; padding: 8px 10px; border-radius: 6px; background: var(--bg); border: 1px solid var(--border-2); color: var(--text); font-size: 14px; }
  .mc-edit input:focus { border-color: var(--blue); }
  .mc-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .mc-actions { display: flex; gap: 8px; }
  .mc-actions .btn { flex: 1; }

  /* Modal */
  .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 16px; }
  .modal-card { background: var(--card); border: 1px solid var(--border-2); border-radius: 16px; padding: 20px; max-width: 420px; width: 100%; max-height: 80vh; overflow-y: auto; }
  .modal-title { font-size: 18px; font-weight: 700; margin-bottom: 16px; text-align: center; }
  .modal-section-label { font-size: 12px; color: var(--text-dim); margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.5px; }
  .modal-loading, .modal-empty { text-align: center; padding: 20px; color: var(--text-faint); font-size: 14px; }

  .dish-list { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
  .dish-btn { display: flex; align-items: center; justify-content: space-between; padding: 12px; border-radius: 10px; background: var(--card-2); border: 1px solid var(--border); color: var(--text); cursor: pointer; transition: border-color 0.15s, background 0.15s; text-align: left; }
  .dish-btn:active { background: #2a2b2e; }
  .dish-btn.active { border-color: var(--blue); background: rgba(59,130,246,0.1); }
  .dish-btn.default { border-color: var(--green); }
  .dish-info { display: flex; align-items: center; gap: 6px; flex: 1; min-width: 0; }
  .dish-name { font-size: 14px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .dish-badge { font-size: 9px; padding: 2px 6px; border-radius: 4px; background: var(--green); color: #000; font-weight: 600; flex-shrink: 0; }
  .dish-uses { font-size: 11px; color: var(--text-faint); flex-shrink: 0; }
  .dish-macros { display: flex; gap: 8px; font-size: 11px; color: var(--text-dim); flex-shrink: 0; }

  .modal-actions { display: flex; flex-direction: column; gap: 8px; }
  .cam-action { display: flex; align-items: center; justify-content: center; gap: 8px; }
  .modal-primary { padding: 14px; border-radius: 10px; background: var(--blue); color: #fff; border: none; font-size: 15px; font-weight: 600; cursor: pointer; }
  .modal-primary:active { opacity: 0.85; }
  .modal-primary:disabled { opacity: 0.5; }
  .modal-secondary { padding: 12px; border-radius: 10px; background: var(--card-2); border: 1px solid var(--border-2); color: var(--text-dim); font-size: 14px; cursor: pointer; }
</style>