<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Icon from './Icon.svelte';
  import { api } from '$lib/api';
  import type { Food, MealEntry, MealPhotoAnalysis, Recipe } from '$lib/types';

  export let meal: MealEntry | null = null;
  export let open = false;
  export let autoOpenCamera = false;
  const dispatch = createEventDispatcher<{ close: void; saved: { entry: any } }>();

  let dialog: HTMLDialogElement;
  let loadedEntryId = '';
  let recipes: Recipe[] = [];
  let foods: Food[] = [];
  let presets: Recipe[] = [];
  let query = '';
  let loading = false;
  let saving = false;
  let error = '';
  let photoInput: HTMLInputElement;
  let proposal: MealPhotoAnalysis | null = null;
  let photoName = '';
  type PhotoRow = { name: string; quantity: number; foodId: string };
  let photoRows: PhotoRow[] = [];
  let autoCameraEntryId = '';

  $: if (dialog) {
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }
  $: if (open && meal?.id && loadedEntryId !== meal.id) void load();
  $: if (open && autoOpenCamera && meal?.id && loadedEntryId === meal.id && autoCameraEntryId !== meal.id) { autoCameraEntryId = meal.id; openCamera(); }
  $: activeRecipes = recipes.filter((recipe) => recipe.status === 'active');
  $: normalizedQuery = query.trim().toLocaleLowerCase('de');
  $: recipeResults = normalizedQuery.length < 2 ? [] : activeRecipes.filter((recipe) => recipe.name.toLocaleLowerCase('de').includes(normalizedQuery)).slice(0, 8);
  $: foodResults = normalizedQuery.length < 2 ? [] : foods.filter((food) => food.name.toLocaleLowerCase('de').includes(normalizedQuery)).slice(0, 8);

  async function load() {
    if (!meal?.id || !meal.category_id) return;
    loading = true; error = ''; proposal = null; query = '';
    try {
      [recipes, foods, presets] = await Promise.all([
        api.getRecipes(), api.getFoods(), api.getMealCategoryRecipePresets(meal.category_id),
      ]);
      loadedEntryId = meal.id;
    } catch { error = 'Mahlzeit konnte nicht vorbereitet werden. Bitte Verbindung prüfen.'; }
    finally { loading = false; }
  }

  function close() { if (dialog?.open) dialog.close(); }
  function handleClose() { loadedEntryId = ''; autoCameraEntryId = ''; proposal = null; dispatch('close'); }
  function nutrition(recipe: Recipe) { const value = recipe.nutrition; return value?.kcal == null ? 'Nährwerte unvollständig' : `${Math.round(Number(value.kcal))} kcal · ${Math.round(Number(value.protein_g ?? 0))} g Protein`; }

  async function applyRecipe(recipe: Recipe) {
    if (!meal?.id) return;
    saving = true; error = '';
    try {
      const updated = await api.updateMealEntry(meal.id, {
        name: recipe.name, items: [{ recipe_id: recipe.id, quantity: 1, unit: 'serving' }], expected_updated_at: meal.updated_at,
      });
      if (!updated) throw new Error();
      dispatch('saved', { entry: updated }); close();
    } catch { error = 'Gericht konnte nicht übernommen werden. Lade den Tag neu und versuche es erneut.'; }
    finally { saving = false; }
  }

  async function applyFood(food: Food) {
    if (!meal?.id || !food.id) return;
    saving = true; error = '';
    try {
      const updated = await api.updateMealEntry(meal.id, {
        name: food.name, items: [{ food_id: food.id, quantity: 100, unit: 'g' }], expected_updated_at: meal.updated_at,
      });
      if (!updated) throw new Error();
      dispatch('saved', { entry: updated }); close();
    } catch { error = 'Lebensmittel konnte nicht übernommen werden. Lade den Tag neu und versuche es erneut.'; }
    finally { saving = false; }
  }

  function openCamera() { photoInput?.click(); }
  function analysisItems(analysis: Record<string, any> | null | undefined): PhotoRow[] {
    const items = Array.isArray(analysis?.items) ? analysis.items : [];
    return items.map((item: any) => ({ name: String(item?.name ?? 'Erkannter Bestandteil'), quantity: Number(item?.portion_grams) > 0 ? Number(item.portion_grams) : 100, foodId: '' }));
  }
  async function onPhotoSelected(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    if (!file || !meal?.id) return;
    saving = true; error = '';
    try {
      const next = await api.uploadMealEntryPhoto(meal.id, file);
      if (!next || next.state === 'failed') throw new Error();
      proposal = next;
      photoRows = analysisItems(next.analysis);
      photoName = typeof next.analysis?.name === 'string' ? next.analysis.name : meal.name ?? '';
      if (!photoRows.length) error = 'Das Foto enthält keine einzeln überprüfbaren Bestandteile.';
    } catch { error = 'Foto-Vorschlag konnte nicht erstellt werden. Die Mahlzeit wurde nicht verändert.'; }
    finally { saving = false; input.value = ''; }
  }
  function setPhotoFood(index: number, foodId: string) { photoRows = photoRows.map((row, rowIndex) => rowIndex === index ? { ...row, foodId } : row); }
  function setPhotoQuantity(index: number, raw: string) { const quantity = Number(raw); photoRows = photoRows.map((row, rowIndex) => rowIndex === index ? { ...row, quantity } : row); }
  async function rejectPhoto() {
    if (!meal?.id || !proposal) return;
    saving = true;
    try { await api.rejectMealEntryPhoto(meal.id, proposal.id); proposal = null; photoRows = []; }
    catch { error = 'Foto-Vorschlag konnte nicht verworfen werden.'; }
    finally { saving = false; }
  }
  async function acceptPhoto() {
    if (!meal?.id || !proposal || !photoName.trim() || photoRows.some((row) => !row.foodId || !Number.isFinite(row.quantity) || row.quantity <= 0)) return;
    saving = true; error = '';
    try {
      const updated = await api.acceptMealEntryPhoto(meal.id, proposal.id, {
        name: photoName.trim(), items: photoRows.map((row) => ({ food_id: row.foodId, quantity: row.quantity, unit: 'g' })),
      });
      if (!updated) throw new Error();
      dispatch('saved', { entry: updated }); close();
    } catch { error = 'Foto-Vorschlag konnte nicht übernommen werden. Bitte prüfe die Zuordnungen und versuche es erneut.'; }
    finally { saving = false; }
  }
</script>

<dialog bind:this={dialog} class="meal-editor ui-dialog" aria-labelledby="meal-editor-title" onclose={handleClose}>
  {#if meal}
    <header class="ui-dialog__header">
      <div><p>{meal.category_name ?? 'Mahlzeit'} · {meal.status === 'consumed' ? 'verzehrt' : 'geplant'}</p><h2 id="meal-editor-title">Mahlzeit anpassen</h2></div>
      <button class="close ui-dialog__close" type="button" onclick={close} aria-label="Mahlzeit anpassen schließen"><Icon name="x" size={20} /></button>
    </header>
    {#if error}<p class="error" role="alert">{error}</p>{/if}
    {#if loading}<p class="muted" role="status">Schnellauswahl wird geladen…</p>
    {:else if proposal}
      <section class="photo-review" aria-labelledby="photo-review-title">
        <div><p class="eyebrow">Foto-Vorschlag</p><h3 id="photo-review-title">Bitte Bestandteile prüfen</h3><p class="muted">Die Analyse ändert nichts, bis du jedes Element einem eigenen Lebensmittel zuordnest.</p></div>
        <label>Bezeichnung der Mahlzeit<input bind:value={photoName} maxlength="200" /></label>
        {#each photoRows as row, index}
          <div class="photo-row"><strong>{row.name}<small>Geschätzte Menge – bitte prüfen</small></strong><label>Gramm<input type="number" min="0.001" step="1" value={row.quantity} oninput={(event) => setPhotoQuantity(index, (event.currentTarget as HTMLInputElement).value)} /></label><label>Eigenes Lebensmittel<select value={row.foodId} onchange={(event) => setPhotoFood(index, (event.currentTarget as HTMLSelectElement).value)}><option value="">Zuordnen…</option>{#each foods as food (food.id)}<option value={food.id}>{food.name}</option>{/each}</select></label></div>
        {/each}
        <div class="actions"><button type="button" onclick={rejectPhoto} disabled={saving}>Verwerfen</button><button class="primary" type="button" onclick={acceptPhoto} disabled={saving || !photoRows.length || photoRows.some((row) => !row.foodId || !Number.isFinite(row.quantity) || row.quantity <= 0)}>{saving ? 'Übernehme…' : 'Geprüft übernehmen'}</button></div>
      </section>
    {:else}
      <section aria-labelledby="quick-title"><p class="eyebrow" id="quick-title">Schnellauswahl</p>{#if presets.length}<div class="preset-list">{#each presets as recipe (recipe.id)}<button class="preset" type="button" onclick={() => applyRecipe(recipe)} disabled={saving}><strong>{recipe.name}</strong><span>{nutrition(recipe)}</span></button>{/each}</div>{:else}<p class="muted">Für diese Kategorie sind noch keine Standardgerichte festgelegt.</p>{/if}</section>
      <section class="search-section" aria-labelledby="search-title"><label class="eyebrow" id="search-title" for="meal-search">Anderes Gericht suchen</label><input id="meal-search" bind:value={query} placeholder="Rezept oder Lebensmittel eingeben…" autocomplete="off" />{#if normalizedQuery.length >= 2}<div class="results" aria-live="polite">{#each recipeResults as recipe (recipe.id)}<button type="button" onclick={() => applyRecipe(recipe)} disabled={saving}><strong>{recipe.name}</strong><span>Rezept · {nutrition(recipe)}</span></button>{/each}{#each foodResults as food (food.id)}<button type="button" onclick={() => applyFood(food)} disabled={saving}><strong>{food.name}</strong><span>Lebensmittel · {food.kcal ?? '–'} kcal / 100 g</span></button>{/each}{#if !recipeResults.length && !foodResults.length}<p class="muted">Keine Treffer für „{query.trim()}“.</p>{/if}</div>{/if}</section>
      <section class="camera-section"><div><p class="eyebrow">Fotoanalyse</p><p class="muted">Erkennt Bestandteile als Vorschlag; du überprüfst sie vor dem Speichern.</p></div><button type="button" class="camera" onclick={openCamera} disabled={saving}><Icon name="camera" size={18} /> Foto analysieren</button></section>
    {/if}
  {/if}
</dialog>
<input bind:this={photoInput} class="file-input" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onchange={onPhotoSelected} />

<style>
  .meal-editor { width:min(100% - 24px, 520px); max-height:min(84dvh, 680px); margin:auto; border:1px solid var(--border-default); border-radius:var(--radius-modal); background:var(--surface-default); color:var(--text-primary); box-shadow:var(--shadow-modal); padding:var(--space-4); }
  .meal-editor::backdrop { background:var(--overlay-backdrop); } header { display:flex; justify-content:space-between; gap:var(--space-3); margin-bottom:var(--space-4); } h2,h3,p { margin:0; } h2 { font-size:18px; } h3 { font-size:15px; } header p,.eyebrow,.muted { color:var(--text-tertiary); font-size:12px; line-height:1.45; } .eyebrow { display:block; margin-bottom:5px; font-weight:700; letter-spacing:.06em; text-transform:uppercase; } .close { display:grid; place-items:center; width:38px; height:38px; flex:0 0 auto; border-radius:var(--radius-control); color:var(--text-secondary); cursor:pointer; } .close:active { background:var(--surface-raised); } section { display:grid; gap:var(--space-2); } section + section { margin-top:var(--space-4); padding-top:var(--space-4); border-top:1px solid var(--border-subtle); } .preset-list,.results { display:grid; gap:6px; } .preset,.results button { display:grid; gap:3px; width:100%; min-height:56px; padding:10px 12px; border:1px solid var(--border-default); border-radius:var(--radius-control); background:var(--surface-raised); color:var(--text-primary); text-align:left; cursor:pointer; } .preset { border-color:color-mix(in srgb,var(--status-success) 55%,var(--border-default)); background:color-mix(in srgb,var(--status-success) 7%,var(--surface-raised)); } .preset span,.results span { color:var(--text-secondary); font-size:12px; } input,select { width:100%; min-height:var(--control-min); border:1px solid var(--border-default); border-radius:var(--radius-control); background:var(--surface-raised); color:var(--text-primary); padding:8px 10px; } label { display:grid; gap:5px; color:var(--text-secondary); font-size:12px; } .camera-section { grid-template-columns:1fr auto; align-items:center; } .camera,.actions button { min-height:var(--control-min); border:1px solid var(--border-default); border-radius:var(--radius-control); color:var(--text-primary); padding:8px 12px; cursor:pointer; } .camera { display:flex; align-items:center; gap:7px; background:var(--surface-raised); } .error { margin:-4px 0 var(--space-3); color:var(--status-danger); font-size:13px; } .photo-review { gap:var(--space-3); } .photo-row { display:grid; grid-template-columns:1fr 90px minmax(150px,1fr); gap:var(--space-2); align-items:end; padding:10px; border-radius:var(--radius-control); background:var(--surface-raised); } .photo-row strong { display:grid; gap:3px; align-self:center; font-size:13px; } .photo-row small { color:var(--text-tertiary); font-size:11px; font-weight:400; } .actions { display:flex; justify-content:flex-end; gap:var(--space-2); } .actions .primary { background:var(--action-primary); border-color:var(--action-primary); color:var(--text-on-accent); font-weight:700; } button:disabled { opacity:.5; cursor:not-allowed; } .file-input { display:none; } @media(max-width:480px) { .meal-editor { width:100%; max-height:86dvh; border-radius:var(--radius-modal) var(--radius-modal) 0 0; margin:auto 0 0; } .camera-section { grid-template-columns:1fr; } .camera { justify-content:center; } .photo-row { grid-template-columns:1fr 86px; } .photo-row label:last-child { grid-column:span 2; } }
</style>
