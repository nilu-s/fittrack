<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { api } from '$lib/api';
  import SettingsHeader from '$lib/components/SettingsHeader.svelte';
  import SpaceManager from '$lib/components/SpaceManager.svelte';
  import type { Contact, Space, SpaceInvitation } from '$lib/types';
  let spaces: Space[] = [];
  let invitations: SpaceInvitation[] = [];
  let contacts: Contact[] = [];
  $: initialSpaceId = $page.url.searchParams.get('space') ?? '';
  async function load() { [spaces, invitations, contacts] = await Promise.all([api.getSpaces(), api.getSpaceInvitations(), api.getContacts()]); }
  onMount(load);
</script>

<svelte:head><title>Cronicl – Gemeinsame Bereiche</title></svelte:head>
<div class="page"><SettingsHeader title="Gemeinsame Bereiche" subtitle="Mitglieder und Zugriffe für geteilte Notizen und geplante To-dos."/><SpaceManager {spaces} {invitations} {contacts} {initialSpaceId} on:changed={load}/></div>

<style>.page { display:grid; gap:var(--space-3); padding-bottom:24px; }</style>
