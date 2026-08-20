<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import PillBadge from './PillBadge.svelte';
  import Icon from './Icon.svelte';
  import { api } from '$lib/api';
  import type { Meal } from '$lib/types';

  export let meal: Meal;
  const dispatch = createEventDispatcher();
  let expanded = false;
  let editName = ''; let editKcal = ''; let editProtein = ''; let editCarbs = ''; let editFat = '';
  let lastTap = 0;
  let photoInput: HTMLInputElement;
  let photoLoading = false;

  function handleTap() {
    const now = Date.now();
    if (now - lastTap < 300) { if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(50); dispatch('done', meal.id); lastTap = 0; }
    else { lastTap = now; setTimeout(() => { if (Date.now() - lastTap >= 300) { expanded = !expanded; if (expanded) { editName = meal.name ?? ''; editKcal = String(meal.kcal ?? ''); editProtein = String(meal.protein_g ?? ''); editCarbs = String(meal.carbs_g ?? ''); editFat = String(meal.fat_g ?? ''); } } }, 320); }
  }
  function saveEdit() { dispatch('update', { id: meal.id, data: { name: editName, kcal: parseFloat(editKcal) || 0, protein_g: parseFloat(editProtein) || 0, carbs_g: parseFloat(editCarbs) || 0, fat_g: parseFloat(editFat) || 0 } }); expanded = false; }
  function triggerPhoto() { photoInput?.click(); }
  async function onPhotoSelected(e: Event) { const input = e.target as HTMLInputElement; const file = input.files?.[0]; if (!file) return; photoLoading = true; try { const result = await api.analyzePhoto(file, meal.id); dispatch('photo', { id: meal.id, file, result }); } catch {} finally { photoLoading = false; input.value = ''; } }

  const SLOT_NAMES: Record<number, string> = { 1: 'Frühstück', 2: 'Mittag', 3: 'Snack', 4: 'Abend' };
  $: slotName = SLOT_NAMES[meal.meal_slot] ?? String(meal.meal_slot);
  $: displayTime = meal.default_time ? meal.default_time.slice(0, 5) : '';
  $: kcalNum = Number(meal.kcal) || 0;
  $: proteinNum = Number(meal.protein_g) || 0;
  $: carbsNum = Number(meal.carbs_g) || 0;
  $: fatNum = Number(meal.fat_g) || 0;
</script>

<div class="mc tap-area" class:done={meal.is_done} class:expanded onclick={handleTap} role="button" tabindex="0">
  <div class="mc-hdr">
    <div class="mc-check" class:done={meal.is_done}>{#if meal.is_done}<Icon name="check" size={14} />{/if}</div>
    <span class="mc-name">{meal.name || slotName}</span>
    {#if displayTime}<span class="mc-time">{displayTime}</span>{/if}
  </div>
  {#if meal.photo_url}<div class="mc-photo"><img src={meal.photo_url} alt={meal.name ?? ''} /></div>{/if}
  <div class="mc-pills">
    {#if kcalNum > 0}<PillBadge value={kcalNum} unit="kcal" color="var(--amber)" />{/if}
    {#if proteinNum > 0}<PillBadge value={proteinNum} unit="g" color="var(--blue)" />{/if}
    {#if carbsNum > 0}<PillBadge value={carbsNum} unit="g" color="var(--purple)" />{/if}
    {#if fatNum > 0}<PillBadge value={fatNum} unit="g" color="var(--pink)" />{/if}
  </div>
  {#if expanded}
    <div class="mc-edit slide-down" onclick={(e) => e.stopPropagation()}>
      <input placeholder="Name" bind:value={editName} />
      <div class="mc-grid"><input type="number" placeholder="kcal" bind:value={editKcal} /><input type="number" placeholder="P" bind:value={editProtein} /><input type="number" placeholder="KH" bind:value={editCarbs} /><input type="number" placeholder="F" bind:value={editFat} /></div>
      <div class="mc-actions"><button class="btn" onclick={saveEdit}>Speichern</button><button class="btn" onclick={triggerPhoto} disabled={photoLoading}>{#if photoLoading}<Icon name="refresh" size={16} />{:else}<Icon name="camera" size={16} />{/if}</button></div>
    </div>
  {/if}
  <input bind:this={photoInput} type="file" accept="image/*" capture="environment" style="display:none" onchange={onPhotoSelected} />
</div>

<style>
  .mc { background: var(--card-2); border: 1px solid var(--border); border-radius: var(--radius); padding: 12px; transition: opacity 0.15s; cursor: pointer; overflow: hidden; }
  .mc.done { opacity: 0.4; border-color: var(--green); }
  .mc.expanded { border-color: var(--border-2); }
  .mc:active { opacity: 0.8; }
  .mc-hdr { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
  .mc-check { width: 18px; height: 18px; border-radius: 50%; border: 1.5px solid var(--border-2); flex-shrink: 0; display: flex; align-items: center; justify-content: center; color: transparent; transition: all 0.2s; }
  .mc-check.done { background: var(--green); border-color: var(--green); color: #000; }
  .mc-name { flex: 1; font-size: 14px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .mc-time { font-size: 11px; color: var(--text-faint); flex-shrink: 0; }
  .mc-photo { margin: 6px 0; border-radius: 6px; overflow: hidden; }
  .mc-photo img { width: 100%; display: block; border-radius: 6px; }
  .mc-pills { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
  .mc-edit { margin-top: 8px; display: flex; flex-direction: column; gap: 8px; }
  .mc-edit input { width: 100%; padding: 8px 10px; border-radius: 6px; background: var(--bg); border: 1px solid var(--border-2); color: var(--text); font-size: 14px; }
  .mc-edit input:focus { border-color: var(--blue); }
  .mc-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  .mc-actions { display: flex; gap: 8px; }
  .mc-actions .btn { flex: 1; }
</style>