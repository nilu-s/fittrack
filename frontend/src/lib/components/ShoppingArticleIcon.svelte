<script lang="ts">
  export let pictogramUrl = '';
  export let iconKey = '';
  export let size = 44;
  export let label: string | undefined = undefined;
</script>

{#if pictogramUrl}
  <img class="article-icon" src={pictogramUrl} width={size} height={size} alt={label ?? ''} data-icon-key={iconKey} />
{/if}

<style>
  .article-icon { display:block; width:var(--size, 44px); height:var(--size, 44px); color:var(--text-on-accent); }
</style>
