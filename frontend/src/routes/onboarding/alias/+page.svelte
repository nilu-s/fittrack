<script lang="ts">
  import { goto } from '$app/navigation';
  import { api } from '$lib/api';
  import { checkAuth } from '$lib/auth';
  let alias = ''; let error = ''; let saving = false;
  async function save() { saving = true; error = ''; if (await api.setAccountAlias(alias)) { await checkAuth(); goto('/'); } else { error = 'Dieser Alias ist nicht verfügbar oder ungültig.'; } saving = false; }
</script>

<svelte:head><title>Cronicl – Alias wählen</title></svelte:head>
<div class="onboarding"><form onsubmit={(event) => { event.preventDefault(); save(); }}><p>WILLKOMMEN</p><h1>Wähle deinen @alias</h1><span>Darüber können dich andere Personen finden und dir eine Kontaktanfrage senden. Er kann später nicht geändert werden.</span><label for="alias">Alias<input id="alias" bind:value={alias} placeholder="z. B. alex" autocomplete="username" required minlength="3" maxlength="32" pattern={'[A-Za-z0-9][A-Za-z0-9._-]{2,31}'} /></label><small>3–32 Zeichen: Buchstaben, Zahlen, Punkt, Unterstrich oder Bindestrich.</small>{#if error}<p class="error" role="alert">{error}</p>{/if}<button type="submit" disabled={saving}>{saving ? 'Wird gespeichert…' : 'Alias festlegen'}</button></form></div>

<style>.onboarding{min-height:70vh;display:grid;place-items:center;padding:24px}.onboarding form{display:grid;gap:14px;width:min(100%,380px);padding:24px;border:1px solid var(--border-subtle);border-radius:var(--radius-modal);background:var(--surface-default)}.onboarding form>p:first-child{margin:0;color:var(--action-primary);font-size:11px;font-weight:750;letter-spacing:.08em}.onboarding h1{margin:0;font-size:25px}.onboarding span,small{color:var(--text-secondary);font-size:13px;line-height:1.5}.onboarding label{display:grid;gap:6px;font-weight:650}.onboarding button{min-height:var(--control-min);background:var(--action-primary);color:#fff}.error{margin:0;color:var(--status-danger)}</style>
