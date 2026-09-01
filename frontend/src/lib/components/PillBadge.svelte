<script lang="ts">
  export let value: string | number;
  export let unit: string = '';
  export let color: string = 'var(--text-secondary)';

  $: displayValue = typeof value === 'number' ? (Number.isInteger(value) ? String(value) : value.toFixed(1)) : value;
</script>

<span class="pill" style="--c:{color}">
  <span class="pill-v">{displayValue}</span>
  {#if unit}<span class="pill-u">{unit}</span>{/if}
</span>

<style>
  .pill {
    display: inline-flex;
    align-items: baseline;
    gap: 2px;
    padding: 2px 8px;
    border-radius: 6px;
    background: var(--surface-raised);
    color: var(--c);
    font-size: 12px;
    font-weight: 600;
    line-height: 1.4;
    white-space: nowrap;
  }
  .pill-u { font-size: 10px; opacity: 0.6; font-weight: 500; }
</style>