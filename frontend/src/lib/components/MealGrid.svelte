<script lang="ts">
  import MealCard from './MealCard.svelte';
  import PillBadge from './PillBadge.svelte';
  import ProgressBar from './ProgressBar.svelte';
  import Icon from './Icon.svelte';
  import { api } from '$lib/api';
  import { dailyGoals } from '$lib/stores';
  import type { Meal } from '$lib/types';

  export let meals: Meal[];
  export let currentDate: string;
  $: sortedMeals = [...(meals ?? [])].sort((a, b) => (a.meal_slot ?? 99) - (b.meal_slot ?? 99));
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

  function getCurrentSlot(): number { const now = new Date(); const t = now.getHours() * 60 + now.getMinutes(); if (t >= 240 && t < 630) return 1; if (t >= 630 && t < 840) return 2; if (t >= 840 && t < 1050) return 3; if (t >= 1050 && t < 1320) return 4; return 1; }
  function parseVisionResult(result: any): { name: string; kcal: number; protein_g: number; carbs_g: number; fat_g: number } | null { if (!result?.analysis?.total) return null; const total = result.analysis.total; const firstItem = result.analysis.items?.[0]; return { name: firstItem?.name ?? 'Erkanntes Gericht', kcal: Number(total.kcal) || 0, protein_g: Number(total.protein_g) || 0, carbs_g: Number(total.carbs_g) || 0, fat_g: Number(total.fat_g) || 0 }; }
  async function markDone(id: string | number) { if (!id) return; try { await api.markMealDone(id); meals = meals.map((m) => (m.id === id ? { ...m, is_done: !m.is_done } : m)); } catch {} }
  async function patchMeal(id: string | number, data: Partial<Meal>) { if (!id) return; try { await api.updateMeal(id, data); meals = meals.map((m) => (m.id === id ? { ...m, ...data } : m)); } catch {} }
  async function updateMeal(event: CustomEvent) { const { id, data } = event.detail; await patchMeal(id, data); }
  async function handlePhoto(event: CustomEvent) { const { id, file, result } = event.detail; if (!file) return; if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(30); const parsed = parseVisionResult(result); if (parsed && id) { await patchMeal(id, { name: parsed.name, kcal: parsed.kcal, protein_g: parsed.protein_g, carbs_g: parsed.carbs_g, fat_g: parsed.fat_g }); } }
  function triggerStandalonePhoto() { photoInput?.click(); }
  async function onStandalonePhotoSelected(e: Event) { const input = e.target as HTMLInputElement; const file = input.files?.[0]; if (!file) return; photoLoading = true; try { const result = await api.analyzePhoto(file); const parsed = parseVisionResult(result); if (parsed) { confirmData = { slot: getCurrentSlot(), ...parsed }; choosingSlot = false; } } catch {} finally { photoLoading = false; input.value = ''; } }
  async function assignToSlot(slot: number) { if (!confirmData) return; const meal = meals.find((m) => m.meal_slot === slot); if (!meal || !meal.id) { choosingSlot = false; confirmData = null; return; } await patchMeal(meal.id, { name: confirmData.name, kcal: confirmData.kcal, protein_g: confirmData.protein_g, carbs_g: confirmData.carbs_g, fat_g: confirmData.fat_g }); try { await api.markMealDone(meal.id); meals = meals.map((m) => (m.id === meal.id ? { ...m, is_done: true } : m)); } catch {} confirmData = null; choosingSlot = false; }
  function cancelConfirm() { confirmData = null; choosingSlot = false; }
</script>

<section class="section-card">
  <div class="section-header"><span>Ernährung</span><span class="text-sm muted">{Math.round(totalKcal)}/{goals.kcal} kcal</span></div>
  <div class="body">
    <button class="cam-btn" onclick={triggerStandalonePhoto} disabled={photoLoading}>
      <Icon name="camera" size={24} />
      <span>{photoLoading ? 'Analysiere…' : 'Foto aufnehmen'}</span>
      <span class="cam-hint">Mahlzeit wird automatisch erkannt</span>
    </button>
    <div class="grid">
      {#each sortedMeals as meal (meal.id ?? meal.meal_slot)}<MealCard {meal} ondon={(e) => markDone(e.detail)} onupdate={updateMeal} onphoto={handlePhoto} />{:else}<div class="empty">Keine Mahlzeiten</div>{/each}
    </div>
    <div class="summary">
      <div class="sum-pills"><PillBadge value={Math.round(totalKcal)} unit="kcal" color="var(--amber)" /><PillBadge value={Math.round(totalP)} unit="g P" color="var(--blue)" /><PillBadge value={Math.round(totalKH)} unit="g KH" color="var(--purple)" /><PillBadge value={Math.round(totalF)} unit="g F" color="var(--pink)" /></div>
      <div class="sum-bars"><ProgressBar current={Math.round(totalKcal)} target={goals.kcal} label="kcal" color="var(--amber)" /><ProgressBar current={Math.round(totalP)} target={goals.protein} label="Protein" color="var(--blue)" /><ProgressBar current={Math.round(totalKH)} target={goals.carbs} label="KH" color="var(--purple)" /><ProgressBar current={Math.round(totalF)} target={goals.fat} label="F" color="var(--pink)" /></div>
    </div>
  </div>
  <input bind:this={photoInput} type="file" accept="image/*" capture="environment" style="display:none" onchange={onStandalonePhotoSelected} />
  {#if confirmData}
    <div class="modal-overlay" onclick={cancelConfirm}><div class="modal-card" onclick={(e) => e.stopPropagation()}>
      {#if choosingSlot}<div class="modal-title">Mahlzeit wählen</div><div class="slot-list">{#each sortedMeals as meal (meal.id ?? meal.meal_slot)}<button class="slot-btn" onclick={() => assignToSlot(meal.meal_slot)}><span>{meal.name || SLOT_NAMES[meal.meal_slot] || `Slot ${meal.meal_slot}`}</span><span class="slot-t">{meal.default_time ? meal.default_time.slice(0, 5) : ''}</span></button>{/each}</div><button class="modal-secondary" onclick={cancelConfirm}>Abbrechen</button>
      {:else}{@const d = confirmData}<div class="modal-title">{d.name}</div><p class="modal-hint">Zugewiesen zu <strong style="color:var(--green)">{SLOT_NAMES[d.slot] || `Slot ${d.slot}`}</strong></p><div class="modal-pills"><PillBadge value={Math.round(d.kcal)} unit="kcal" color="var(--amber)" /><PillBadge value={Math.round(d.protein_g)} unit="g P" color="var(--blue)" /><PillBadge value={Math.round(d.carbs_g)} unit="g KH" color="var(--purple)" /><PillBadge value={Math.round(d.fat_g)} unit="g F" color="var(--pink)" /></div><div class="modal-actions"><button class="modal-primary" onclick={() => assignToSlot(d.slot)}>Akzeptieren</button><button class="modal-secondary" onclick={() => (choosingSlot = true)}>Andere wählen</button></div>{/if}
    </div></div>
  {/if}
</section>

<style>
  .body { padding: 12px; }
  .cam-btn { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; padding: 16px; margin-bottom: 12px; border-radius: var(--radius); background: var(--card-2); border: 1px dashed var(--border-2); color: var(--text-dim); cursor: pointer; transition: background 0.15s; }
  .cam-btn:active { background: #26272a; }
  .cam-btn span { font-size: 14px; font-weight: 500; margin-top: 6px; color: var(--text); }
  .cam-hint { font-size: 12px; color: var(--text-faint); margin-top: 2px; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; }
  .empty { grid-column: 1 / -1; text-align: center; padding: 20px; color: var(--text-faint); font-size: 14px; }
  .summary { border-top: 1px solid var(--border); padding-top: 12px; display: flex; flex-direction: column; gap: 8px; }
  .sum-pills { display: flex; flex-wrap: wrap; gap: 4px; }
  .sum-bars { display: flex; flex-direction: column; gap: 4px; }
  .slot-list { display: flex; flex-direction: column; gap: 8px; }
  .slot-btn { display: flex; align-items: center; justify-content: space-between; padding: 12px; border-radius: 8px; background: var(--card-2); border: 1px solid var(--border-2); color: var(--text); cursor: pointer; font-size: 14px; font-weight: 500; }
  .slot-t { font-size: 12px; color: var(--text-faint); }
  .modal-hint { text-align: center; font-size: 14px; color: var(--text-dim); }
  .modal-pills { display: flex; flex-wrap: wrap; justify-content: center; gap: 4px; }
</style>