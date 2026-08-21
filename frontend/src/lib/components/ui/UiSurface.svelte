<script lang="ts">
  export let as: 'div' | 'section' = 'section';
  export let labelledby: string | undefined = undefined;
</script>

<svelte:element this={as} class="ui-surface" aria-labelledby={labelledby}>
  <slot />
</svelte:element>
