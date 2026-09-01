<script lang="ts">
  export let title: string;
  export let subtitle = '';
</script>

<div class="settings-header">
  <div>
    <h1>{title}</h1>
    {#if subtitle}<p>{subtitle}</p>{/if}
  </div>
</div>

<style>
  .settings-header { padding: 8px 0; }
  h1 { font-size: 18px; font-weight: 650; }
  p { margin-top: 2px; color: var(--text-tertiary); font-size: 12px; }
</style>
