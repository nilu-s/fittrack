<script lang="ts">
  export let current: number = 0;
  export let target: number = 100;
  export let label: string = '';
  export let color: string = 'var(--text-secondary)';

  $: percentage = target > 0 ? Math.min(100, Math.round((current / target) * 100)) : 0;
  $: isComplete = percentage >= 100;
  $: fillColor = isComplete ? 'var(--status-success)' : color;
</script>

<div class="pb-wrap">
  {#if label}
    <div class="pb-label">
      <span class="pb-l">{label}</span>
      <span class="pb-v" class:done={isComplete}>{current}/{target}</span>
    </div>
  {/if}
  <div class="pb-track" role="progressbar" aria-valuenow={percentage} aria-valuemin="0" aria-valuemax="100">
    <div class="pb-fill" style="width:{percentage}%;background:{fillColor}"></div>
  </div>
</div>

<style>
  .pb-wrap { display: flex; flex-direction: column; gap: 3px; }
  .pb-label { display: flex; justify-content: space-between; align-items: baseline; font-size: 12px; }
  .pb-l { color: var(--text-secondary); }
  .pb-v { color: var(--text-primary); font-weight: 600; }
  .pb-v.done { color: var(--status-success); }
  .pb-track { width: 100%; height: 6px; background: var(--surface-raised); border-radius: 3px; overflow: hidden; }
  .pb-fill { height: 100%; border-radius: 3px; transition: width 0.3s ease; }
</style>
