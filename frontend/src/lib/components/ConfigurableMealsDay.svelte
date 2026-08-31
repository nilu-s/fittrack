<script lang="ts">
  import { api } from '$lib/api';
  import type { Food, MealCategory, MealEntry, MealEntryItem, MealPhotoAnalysis, Recipe } from '$lib/types';

  export let date: string;
  let categories: MealCategory[] = [];
  let foods: Food[] = [];
  let recipes: Recipe[] = [];
  let entries: MealEntry[] = [];
  let loading = false;
  let saving = false;
  let error = '';
  let addCategory = '';
  let addName = '';
  let addCategoryId = '';
  let editingId = '';
  let draftName = '';
  let draftCategoryId = '';
  let draftItems: MealEntryItem[] = [];
  let sourceId = '';
  let sourceKind: 'food' | 'recipe' = 'food';
  let sourceQuantity = '100';
  let photoInput: HTMLInputElement;
  let photoEntryId = '';
  let photoProposal: MealPhotoAnalysis | null = null;

  $: consumed = entries.filter((entry) => entry.status === 'consumed');
  $: nutritionTotals = sumNutrition(consumed.map((entry) => entry.nutrition));
  $: if (date) load();

  const nutrientLabels: Array<[keyof NonNullable<MealEntry['nutrition']>, string, string]> = [
    ['kcal', 'kcal', 'var(--amber)'], ['protein_g', 'Protein', 'var(--blue)'],
    ['carbs_g', 'KH', 'var(--purple)'], ['fat_g', 'Fett', 'var(--pink)'],
  ];

  function sumNutrition(values: MealEntry['nutrition'][]): Record<string, number | null> {
    const keys = ['kcal', 'protein_g', 'carbs_g', 'fat_g'];
    return Object.fromEntries(keys.map((key) => {
      const parts = values.map((value) => value?.[key as keyof NonNullable<MealEntry['nutrition']>]);
      return [key, parts.some((value) => value == null) ? null : parts.reduce<number>((total, value) => total + Number(value ?? 0), 0)];
    })) as Record<string, number | null>;
  }

  async function load() {
    loading = true; error = '';
    try {
      [categories, entries, foods, recipes] = await Promise.all([api.getMealCategories(), api.getMealEntries(date), api.getFoods(), api.getRecipes()]);
      if (!addCategoryId) addCategoryId = categories[0]?.id ?? '';
    } catch { error = 'Mahlzeiten konnten nicht geladen werden. Bitte Verbindung prüfen und erneut versuchen.'; }
    finally { loading = false; }
  }

  function replaceEntry(updated: MealEntry) { entries = entries.map((entry) => entry.id === updated.id ? updated : entry); }
  function categoryName(id: string) { return categories.find((category) => category.id === id)?.name ?? 'Ohne Kategorie'; }
  function sourceName(item: MealEntryItem) { return item.source_snapshot?.name as string ?? foods.find((food) => food.id === item.food_id)?.name ?? recipes.find((recipe) => recipe.id === item.recipe_id)?.name ?? 'Unbekannte Zutat'; }
  function nutrition(entry: MealEntry) { const n = entry.nutrition; return n?.kcal == null ? 'Nährwerte unvollständig' : `${Math.round(Number(n.kcal))} kcal`; }
  function format(value: number | null | undefined, suffix = '') { return value == null ? '–' : `${Math.round(Number(value))}${suffix}`; }

  async function instantiate() {
    saving = true; error = '';
    try { entries = await api.instantiateMealEntries(date); }
    catch { error = 'Der Plan konnte nicht übernommen werden.'; }
    finally { saving = false; }
  }

  async function createCategory() {
    const name = addCategory.trim(); if (!name) return;
    try {
      const category = await api.createMealCategory({ name, sort_order: categories.length, is_active: true });
      if (!category) throw new Error(); categories = [...categories, category]; addCategoryId = category.id; addCategory = '';
    } catch { error = 'Kategorie konnte nicht gespeichert werden.'; }
  }

  async function createEntry() {
    const name = addName.trim();
    if (!name || !addCategoryId) { error = 'Wähle eine Kategorie und gib einen Namen ein.'; return; }
    saving = true;
    try {
      const entry = await api.createMealEntry({ date, category_id: addCategoryId, name, status: 'planned', source: 'manual', items: [] });
      if (!entry) throw new Error(); entries = [...entries, entry]; addName = '';
    } catch { error = 'Mahlzeit konnte nicht gespeichert werden.'; }
    finally { saving = false; }
  }

  async function setStatus(entry: MealEntry, status: 'consumed' | 'skipped') {
    saving = true;
    try { const updated = await api.setMealEntryStatus(entry.id, status, entry.updated_at); if (!updated) throw new Error(); replaceEntry(updated); }
    catch { error = 'Status konnte nicht geändert werden. Die Ansicht wurde möglicherweise in einem anderen Fenster geändert.'; }
    finally { saving = false; }
  }

  function beginEdit(entry: MealEntry) {
    editingId = entry.id; draftName = entry.name ?? ''; draftCategoryId = entry.category_id;
    draftItems = (entry.items ?? []).map((item) => ({ food_id: item.food_id, recipe_id: item.recipe_id, quantity: Number(item.quantity), unit: item.unit }));
    sourceId = ''; sourceKind = 'food'; sourceQuantity = '100'; error = '';
  }
  function cancelEdit() { editingId = ''; draftItems = []; }
  function addItem() {
    const quantity = Number(sourceQuantity);
    if (!sourceId || !Number.isFinite(quantity) || quantity <= 0) { error = 'Wähle ein Lebensmittel oder Rezept und eine gültige Menge.'; return; }
    draftItems = [...draftItems, sourceKind === 'food'
      ? { food_id: sourceId, quantity, unit: 'g' }
      : { recipe_id: sourceId, quantity, unit: 'serving' }];
    sourceId = ''; sourceQuantity = sourceKind === 'food' ? '100' : '1';
  }
  function removeItem(index: number) { draftItems = draftItems.filter((_, itemIndex) => itemIndex !== index); }
  async function saveEntry(entry: MealEntry) {
    const name = draftName.trim();
    if (!name || !draftCategoryId) { error = 'Name und Kategorie sind erforderlich.'; return; }
    saving = true;
    try {
      const updated = await api.updateMealEntry(entry.id, { name, category_id: draftCategoryId, items: draftItems, expected_updated_at: entry.updated_at });
      if (!updated) throw new Error(); replaceEntry(updated); cancelEdit();
    } catch { error = 'Mahlzeit konnte nicht gespeichert werden. Bitte lade den Tag neu und versuche es erneut.'; }
    finally { saving = false; }
  }
  async function deleteEntry(entry: MealEntry) {
    if (!confirm(`„${entry.name}“ wirklich löschen?`)) return;
    saving = true;
    try { if (!await api.deleteMealEntry(entry.id)) throw new Error(); entries = entries.filter((item) => item.id !== entry.id); if (editingId === entry.id) cancelEdit(); }
    catch { error = 'Mahlzeit konnte nicht gelöscht werden.'; }
    finally { saving = false; }
  }
  function choosePhoto(entry: MealEntry) { photoEntryId = entry.id; photoProposal = null; photoInput?.click(); }
  async function uploadPhoto(event: Event) {
    const input = event.currentTarget as HTMLInputElement; const file = input.files?.[0];
    if (!file || !photoEntryId) return;
    saving = true; error = '';
    try {
      const proposal = await api.uploadMealEntryPhoto(photoEntryId, file);
      if (!proposal) throw new Error(); photoProposal = proposal;
      if (proposal.state === 'failed') error = 'Das Foto konnte nicht als Mahlzeit erkannt werden. Deine Mahlzeit wurde nicht verändert.';
    } catch { error = 'Foto-Vorschlag konnte nicht erstellt werden. Deine Mahlzeit wurde nicht verändert.'; }
    finally { saving = false; input.value = ''; }
  }
  function proposalText(proposal: MealPhotoAnalysis) {
    if (proposal.state === 'failed') return 'Analyse fehlgeschlagen';
    const raw = proposal.analysis;
    const label = typeof raw?.name === 'string' ? raw.name : typeof raw?.description === 'string' ? raw.description : null;
    return label ? `Vorschlag: ${label}` : 'Foto-Vorschlag bereit – prüfe ihn, bevor du Bestandteile übernimmst.';
  }
</script>

<section class="meal-day" aria-labelledby="meal-day-title" aria-busy={loading || saving}>
  <div class="head"><div><h2 id="meal-day-title">Mahlzeiten</h2><p>{consumed.length ? `${consumed.length} verzehrt` : 'Noch nichts verzehrt'} · geplant und verzehrt sind getrennt</p></div><button onclick={instantiate} disabled={saving}>Plan übernehmen</button></div>
  {#if typeof navigator !== 'undefined' && !navigator.onLine}<p class="error" role="status">Mahlzeiten benötigen aktuell eine Verbindung; Änderungen werden erst nach erfolgreichem Speichern übernommen.</p>{/if}
  <div class="nutrition-summary" aria-label="Verzehrte Nährwerte">
    {#each nutrientLabels as [key, label, color]}<div class="macro"><span style:color={color}>{label}</span><strong>{format(nutritionTotals[key], key === 'kcal' ? '' : ' g')}</strong></div>{/each}
  </div>
  {#if error}<p class="error" role="alert">{error}</p>{/if}
  {#if categories.length === 0}
    <form class="setup" onsubmit={(event) => { event.preventDefault(); createCategory(); }}><label>Erste Kategorie<input bind:value={addCategory} placeholder="z. B. Frühstück" maxlength="120" /></label><button>Speichern</button></form>
  {:else}
    <form class="add" onsubmit={(event) => { event.preventDefault(); createEntry(); }}><select aria-label="Kategorie" bind:value={addCategoryId}>{#each categories as category}<option value={category.id}>{category.name}</option>{/each}</select><input aria-label="Name der Mahlzeit" bind:value={addName} placeholder="Mahlzeit hinzufügen" maxlength="200" /><button disabled={saving}>Hinzufügen</button></form>
    <div class="entries">
      {#each entries as entry (entry.id)}
        <article class:consumed={entry.status === 'consumed'} class:skipped={entry.status === 'skipped'}>
          {#if editingId === entry.id}
            <form class="editor" onsubmit={(event) => { event.preventDefault(); saveEntry(entry); }}>
              <div class="editor-fields"><select aria-label="Kategorie" bind:value={draftCategoryId}>{#each categories as category}<option value={category.id}>{category.name}</option>{/each}</select><input aria-label="Name der Mahlzeit" bind:value={draftName} maxlength="200" /></div>
              <div class="item-list"><strong>Bestandteile</strong>{#each draftItems as item, index}<div class="draft-item"><span>{sourceName(item)} · {item.quantity} {item.unit === 'serving' ? 'Portion(en)' : item.unit}</span><button type="button" class="icon" aria-label="Bestandteil entfernen" onclick={() => removeItem(index)}>×</button></div>{:else}<small>Keine Bestandteile – du kannst die Mahlzeit zunächst nur planen.</small>{/each}</div>
              <div class="add-item"><select aria-label="Art" bind:value={sourceKind} onchange={() => { sourceId = ''; sourceQuantity = sourceKind === 'food' ? '100' : '1'; }}><option value="food">Lebensmittel</option><option value="recipe">Rezept</option></select><select aria-label="Lebensmittel oder Rezept" bind:value={sourceId}><option value="">Auswählen…</option>{#if sourceKind === 'food'}{#each foods as food}<option value={food.id}>{food.name}</option>{/each}{:else}{#each recipes.filter((recipe) => recipe.status !== 'archived') as recipe}<option value={recipe.id}>{recipe.name}</option>{/each}{/if}</select><input aria-label="Menge" type="number" bind:value={sourceQuantity} min="0.001" step="0.001" /><button type="button" onclick={addItem}>+</button></div>
              <div class="editor-actions"><button class="primary" disabled={saving}>Speichern</button><button type="button" onclick={() => choosePhoto(entry)} disabled={saving}>Foto-Vorschlag</button><button type="button" onclick={cancelEdit}>Abbrechen</button></div>
              {#if photoProposal?.meal_entry_id === entry.id}<p class:proposal-error={photoProposal.state === 'failed'} class="proposal" role="status">{proposalText(photoProposal)}</p>{/if}
            </form>
          {:else}
            <div class="entry-body"><small>{categoryName(entry.category_id)} · {entry.status === 'planned' ? 'geplant' : entry.status === 'consumed' ? 'verzehrt' : 'übersprungen'}</small><strong>{entry.name}</strong><span>{nutrition(entry)}{#if entry.items?.length} · {entry.items.length} Bestandteil{entry.items.length === 1 ? '' : 'e'}{/if}</span></div>
            <div class="actions"><button class="subtle" aria-label={`${entry.name} bearbeiten`} onclick={() => beginEdit(entry)}>Bearbeiten</button>{#if entry.status !== 'consumed'}<button onclick={() => setStatus(entry, 'consumed')}>Verzehrt</button>{/if}{#if entry.status !== 'skipped'}<button class="subtle" onclick={() => setStatus(entry, 'skipped')}>Überspringen</button>{/if}<button class="danger" aria-label={`${entry.name} löschen`} onclick={() => deleteEntry(entry)}>×</button></div>
          {/if}
        </article>
      {:else}<p class="empty">Noch keine Mahlzeiten für diesen Tag. Übernimm einen Plan oder füge einen Eintrag hinzu.</p>{/each}
    </div>
  {/if}
  <input bind:this={photoInput} class="file-input" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onchange={uploadPhoto} />
</section>

<style>
  .meal-day { background:var(--card); border:1px solid var(--border); border-radius:12px; overflow:hidden; } .head { display:flex; gap:12px; align-items:center; justify-content:space-between; padding:14px; } h2,p { margin:0; } h2 { font-size:16px; } .head p,small,span,.empty { color:var(--text-faint); font-size:12px; } button,select,input { min-height:40px; border-radius:8px; font:inherit; } button { border:1px solid var(--border-2); background:var(--card-2); color:var(--text); padding:0 10px; cursor:pointer; } button:disabled { opacity:.5; cursor:not-allowed; } button:focus-visible,input:focus-visible,select:focus-visible { outline:2px solid var(--blue); outline-offset:2px; } .nutrition-summary { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; padding:0 14px 14px; } .macro { display:grid; gap:2px; } .macro span { font-size:11px; text-transform:uppercase; font-weight:700; } .macro strong { font-size:14px; } .add,.setup,.editor-fields,.add-item,.editor-actions { display:flex; gap:8px; padding:0 14px 14px; } input,select { min-width:0; flex:1; border:1px solid var(--border-2); background:var(--card-2); color:var(--text); padding:0 10px; } .setup label { flex:1; display:grid; gap:5px; font-size:12px; color:var(--text-dim); } .entries { border-top:1px solid var(--border); } article { display:flex; gap:8px; align-items:center; justify-content:space-between; padding:11px 14px; border-bottom:1px solid var(--border); } .entry-body { min-width:0; display:grid; gap:2px; } strong { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:14px; } .actions { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:5px; flex-shrink:0; } .actions button,.editor button { min-height:32px; font-size:12px; } .subtle { opacity:.75; } .danger,.icon { color:var(--red); } .consumed>.entry-body strong { color:var(--green); } .skipped>.entry-body { opacity:.55; text-decoration:line-through; } .empty,.error { padding:14px; } .error,.proposal-error { color:var(--red); } .editor { width:100%; display:grid; gap:8px; } .editor-fields,.add-item,.editor-actions { padding:0; } .add-item select:first-child { flex:0 0 110px; } .add-item input { flex:0 0 72px; } .add-item button { flex:0 0 40px; } .item-list { display:grid; gap:5px; padding:8px; border-radius:8px; background:var(--card-2); } .draft-item { display:flex; align-items:center; justify-content:space-between; gap:8px; } .icon { padding:0; width:30px; min-height:30px; } .primary { background:var(--green); border-color:var(--green); color:#07120a; font-weight:700; } .proposal { padding:0; font-size:12px; color:var(--text-dim); } .file-input { display:none; } @media(max-width:620px) { .head { align-items:flex-start; flex-direction:column; } .nutrition-summary { grid-template-columns:repeat(2,1fr); } article { align-items:flex-start; flex-direction:column; } .actions { justify-content:flex-start; } .add-item { flex-wrap:wrap; } .add-item select:nth-child(2) { flex-basis:150px; } } @media(max-width:420px) { .add,.editor-fields { flex-wrap:wrap; } .add input { min-width:160px; } }
</style>
