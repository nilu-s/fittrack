<script lang="ts">
  import { onMount } from 'svelte';
  import SettingsHeader from '$lib/components/SettingsHeader.svelte';
  import UiButton from '$lib/components/ui/UiButton.svelte';
  import { api } from '$lib/api';
  import type { BodyProfile } from '$lib/types';
  let profile: BodyProfile = { height_cm: null, birth_date: null, calculation_sex: null };
  let loading = true; let saving = false; let message = '';
  onMount(async () => { try { profile = (await api.getBodyProfile()) ?? profile; } finally { loading = false; } });
  async function save() { saving = true; message = ''; try { const updated = await api.updateBodyProfile(profile); message = updated ? 'Körperprofil gespeichert.' : 'Speichern nicht möglich. Bitte Verbindung prüfen.'; if (updated) profile = updated; } finally { saving = false; } }
</script>
<svelte:head><title>Chronickel – Körperprofil</title></svelte:head>
<div class="page"><SettingsHeader title="Körperprofil" subtitle="Nur für deine eigenen Berechnungen" />
<section class="section-card" aria-busy={loading}><div class="section-header">BMI &amp; Formeleingaben</div><form onsubmit={(event) => { event.preventDefault(); save(); }}>
<label>Größe <span>für BMI und spätere BIA-Schätzungen</span><input type="number" min="50" max="300" step="0.1" bind:value={profile.height_cm} placeholder="z. B. 178" /><small>cm</small></label>
<label>Geburtsdatum <span>wird nur bei einer späteren BIA-Formel benötigt</span><input type="date" bind:value={profile.birth_date} /></label>
<label>Berechnungsparameter <span>keine Identitätsangabe; nur verwenden, wenn eine dokumentierte Formel ihn verlangt</span><select bind:value={profile.calculation_sex}><option value={null}>Nicht festgelegt</option><option value="female">weiblich</option><option value="male">männlich</option></select></label>
{#if message}<p class="status" role="status">{message}</p>{/if}<UiButton variant="primary" type="submit" disabled={saving || loading}>{saving ? 'Speichere…' : 'Speichern'}</UiButton></form></section>
<section class="notice"><strong>Hinweis zu Körperzusammensetzung</strong><p>Körperzusammensetzung ist eine BIA-Schätzung zur Verlaufskontrolle und keine medizinische Messung oder Diagnose. Ohne echte Impedanzdaten zeigt Chronickel nur Gewicht und BMI.</p></section></div>
<style>.page{display:grid;gap:var(--space-3);padding-top:var(--space-2)}form{display:grid;gap:var(--space-4);padding:var(--space-4)}label{display:grid;gap:5px;color:var(--text-primary);font-size:14px;font-weight:650}label span,small{color:var(--text-tertiary);font-size:12px;font-weight:400;line-height:1.4}input,select{width:100%;min-height:var(--control-min);padding:8px 10px;border:1px solid var(--border-default);border-radius:var(--radius-control);background:var(--surface-raised);color:var(--text-primary)}.status{color:var(--status-success);font-size:13px}.notice{display:grid;gap:5px;padding:var(--space-4);border-left:3px solid var(--status-info);background:var(--surface-raised);color:var(--text-secondary);font-size:13px;line-height:1.45}.notice strong{color:var(--text-primary)}</style>
