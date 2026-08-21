<script lang="ts">
  export let type: 'button' | 'submit' | 'reset' = 'button';
  export let disabled = false;
  export let ariaLabel: string;
  export let onclick: (event: MouseEvent) => void = () => {};
</script>

<button class="ui-icon-button" {type} {disabled} aria-label={ariaLabel} onclick={onclick}>
  <slot />
</button>
