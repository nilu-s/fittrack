<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { api } from '$lib/api';
  import type { Contact, Space, SpaceInvitation } from '$lib/types';

  export let spaces: Space[] = [];
  export let invitations: SpaceInvitation[] = [];
  export let contacts: Contact[] = [];
  export let initialSpaceId = '';
  const dispatch = createEventDispatcher<{ changed: void }>();
  let name = ''; let contactId = ''; let selectedId = ''; let message = '';
  let appliedInitialSpaceId = '';
  $: selected = spaces.find((space) => space.id === selectedId) ?? null;
  $: if (initialSpaceId && initialSpaceId !== appliedInitialSpaceId && spaces.some((space) => space.id === initialSpaceId)) { selectedId = initialSpaceId; appliedInitialSpaceId = initialSpaceId; }
  async function create() { const value = name.trim(); if (!value) return; const created = await api.createSpace(value); if (created) { name = ''; selectedId = created.id; dispatch('changed'); } else message = 'Bereich konnte nicht angelegt werden.'; }
  async function invite() { if (!selectedId || !contactId) return; if (await api.inviteToSpace(selectedId, contactId)) { contactId = ''; message = 'Workspace-Anfrage wurde gesendet.'; dispatch('changed'); } else message = 'Workspace-Anfrage konnte nicht gesendet werden.'; }
  async function remove(memberId: string) { if (!selectedId || !confirm('Mitglied wirklich aus diesem Space entfernen?')) return; if (await api.removeSpaceMember(selectedId, memberId)) { message = 'Mitglied wurde entfernt.'; dispatch('changed'); } else message = 'Mitglied konnte nicht entfernt werden.'; }
  async function accept(id: string) { if (await api.acceptSpaceInvitation(id)) dispatch('changed'); }
  async function decline(id: string) { if (await api.declineSpaceInvitation(id)) dispatch('changed'); }
</script>

<section class="spaces" aria-labelledby="spaces-title">
  <header><div><p>GEMEINSAM ORGANISIEREN</p><h2 id="spaces-title">Gemeinsame Bereiche</h2></div></header>
  {#if invitations.length}<div class="invites" aria-label="Offene Einladungen">{#each invitations as invitation (invitation.id)}<p><strong>{invitation.space_name}</strong>{#if invitation.invited_by_display_name} · von {invitation.invited_by_display_name}{/if}<span><button type="button" onclick={() => accept(invitation.id)}>Annehmen</button><button type="button" onclick={() => decline(invitation.id)}>Ablehnen</button></span></p>{/each}</div>{/if}
  <form class="create" onsubmit={(event) => { event.preventDefault(); create(); }}><label for="space-name">Neuer Space<input id="space-name" bind:value={name} placeholder="z. B. Haushalt" required></label><button class="primary">Anlegen</button></form>
  {#if spaces.length}<label for="space-select">Bereich auswählen<select id="space-select" bind:value={selectedId}><option value="">Auswählen</option>{#each spaces as space (space.id)}<option value={space.id}>{space.name}</option>{/each}</select></label>{/if}
  {#if selected}<div class="details"><h3>{selected.name}</h3><p class="hint">Ein Bereich ist zugleich gemeinsame Ablage und Zugriffsgrenze für Notizen und daraus geplante To-dos.</p><ul class="members">{#each selected.members as member (member.member_id)}<li>{member.display_name ?? 'Mitglied'}{#if selected.role === 'owner' && member.role !== 'owner'}<button type="button" class="remove" onclick={() => remove(member.member_id)}>Entfernen</button>{/if}</li>{/each}</ul>{#if selected.role === 'owner'}<form onsubmit={(event) => { event.preventDefault(); invite(); }}><label for="space-invite">Kontakt einladen<select id="space-invite" bind:value={contactId} required><option value="">Kontakt auswählen</option>{#each contacts as contact (contact.id)}<option value={contact.id}>{contact.display_name}</option>{/each}</select></label><button type="submit" disabled={!contactId}>Einladen</button></form>{/if}</div>{/if}
  {#if message}<p class="message" role="status">{message}</p>{/if}
</section>

<style>
  .spaces { display:grid; gap:var(--space-3); padding:var(--space-3); border:1px solid var(--border-subtle); border-radius:var(--radius-control); background:var(--surface-default); } header p { margin:0 0 3px; color:var(--text-tertiary); font-size:11px; font-weight:700; letter-spacing:.05em; } h2,h3 { margin:0; } h2 { font-size:16px; } h3 { font-size:14px; } label { display:grid; gap:5px; color:var(--text-secondary); font-size:12px; } input,select,button { min-height:var(--control-min); font:inherit; } input,select { padding:8px 10px; border:1px solid var(--border-default); border-radius:var(--radius-control); background:var(--surface-raised); color:var(--text-primary); } button { padding:7px 10px; border:1px solid var(--border-default); border-radius:var(--radius-control); background:var(--surface-raised); color:var(--text-primary); cursor:pointer; } .remove { min-height:28px; margin-left:8px; padding:3px 7px; font-size:11px; } .primary { border:0; background:var(--action-primary); color:var(--text-on-accent); font-weight:700; } .create,form { display:flex; align-items:end; gap:var(--space-2); } .create label,form label { flex:1; } .details { display:grid; gap:var(--space-2); padding-top:var(--space-2); border-top:1px solid var(--border-subtle); } .members,.hint,.message,.invites p { margin:0; font-size:12px; color:var(--text-secondary); } ul { margin:0; padding-left:20px; color:var(--text-secondary); font-size:12px; } .invites { display:grid; gap:6px; padding:var(--space-2); border-radius:var(--radius-control); background:var(--surface-accent); } .invites p { display:flex; flex-wrap:wrap; justify-content:space-between; gap:8px; } .invites span { display:flex; gap:5px; } .message { color:var(--status-info); } button:focus-visible,input:focus-visible,select:focus-visible { outline:2px solid var(--status-info); outline-offset:2px; } @media(max-width:480px) { .create,form { display:grid; } }
</style>
