<script lang="ts">
  export let current: number = 0;
  export let target: number = 100;
  export let label: string = '';
  export let color: string = '#666';

  $: percentage = target > 0 ? Math.min(100, Math.round((current / target) * 100)) : 0;
  $: isComplete = percentage >= 100;
  $: fillColor = isComplete ? 'var(--accent-done)' : color;
</script>

<div class="progress-bar-wrapper">
  {#if label}
    <div class="progress-label">
      <span class="label-text">{label}</span>
      <span class="label-value">{current}/{target}</span>
    </div>
  {/if}
  <div class="progress-bar" role="progressbar" aria-valuenow={percentage} aria-valuemin="0" aria-valuemax="100">
    <div class="progress-fill" style="width:{percentage}%;background:{fillColor}"></div>
  </div>
</div>

<style>
  .progress-bar-wrapper {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .progress-label {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    font-size: 0.6875rem;
  }

  .label-text {
    color: var(--text-secondary);
  }

  .label-value {
    color: var(--text-primary);
    font-weight: 500;
  }

  .progress-bar {
    width: 100%;
    height: 5px;
    background: var(--progress-bg);
    border-radius: 3px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.3s ease, background 0.2s ease;
    min-width: 0;
  }
</style>