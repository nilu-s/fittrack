<script lang="ts">
  export let variant: 'primary' | 'secondary' | 'danger' = 'secondary';
  export let type: 'button' | 'submit' | 'reset' = 'button';
  export let disabled = false;
  export let ariaLabel: string | undefined = undefined;
  export let onclick: (event: MouseEvent) => void = () => {};
</script>

<button class={`ui-button ui-button--${variant}`} {type} {disabled} aria-label={ariaLabel} onclick={onclick}>
  <slot />
</button>
