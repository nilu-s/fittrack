<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import SettingsHeader from '$lib/components/SettingsHeader.svelte';
  import SpaceManager from '$lib/components/SpaceManager.svelte';
  import type { Space, SpaceInvitation } from '$lib/types';
  let spaces: Space[] = [];
  let invitations: SpaceInvitation[] = [];
  async function load() { [spaces, invitations] = await Promise.all([api.getSpaces(), api.getSpaceInvitations()]); }
  onMount(load);
</script>

<svelte:head><title>Cronicl – Gemeinsame Bereiche</title></svelte:head>
<div class="page"><SettingsHeader title="Gemeinsame Bereiche" subtitle="Mitglieder, Einladungen und Projekte für Haushalt und gemeinsame Vorhaben."/><SpaceManager {spaces} {invitations} on:changed={load}/></div>

<style>.page { display:grid; gap:var(--space-3); padding-bottom:24px; }</style>
