<script lang="ts">
  export let value: string | number;
  export let unit: string = '';
  export let color: string = '#666';

  $: displayValue = typeof value === 'number' ? (Number.isInteger(value) ? String(value) : value.toFixed(1)) : value;
</script>

<span class="pill-badge" style="--pill-color:{color}">
  <span class="pill-value">{displayValue}</span>
  {#if unit}
    <span class="pill-unit">{unit}</span>
  {/if}
</span>

<style>
  .pill-badge {
    display: inline-flex;
    align-items: baseline;
    gap: 2px;
    padding: 2px 7px;
    border-radius: 10px;
    background: var(--pill-color);
    color: #fff;
    font-size: 0.6875rem;
    font-weight: 600;
    line-height: 1.3;
    white-space: nowrap;
  }

  .pill-unit {
    font-size: 0.5625rem;
    opacity: 0.85;
    font-weight: 500;
  }
</style>