<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let icon: string = '';
  export let label: string = '';
  export let value: string | number | null = null;
  export let unit: string = '';
  export let editable: boolean = true;
  export let checkable: boolean = false;
  export let checked: boolean = false;

  const dispatch = createEventDispatcher();

  let isEditing = false;
  let editValue: string = '';

  function startEdit() {
    if (!editable) return;
    editValue = value != null ? String(value) : '';
    isEditing = true;
  }

  function commitEdit() {
    isEditing = false;
    const parsed = parseValue(editValue);
    if (parsed !== value) {
      dispatch('change', parsed);
    }
  }

  function parseValue(v: string): string | number {
    const trimmed = v.trim();
    if (trimmed === '') return '';
    const num = parseFloat(trimmed);
    if (!isNaN(num) && /^\d+\.?\d*$/.test(trimmed)) return num;
    return trimmed;
  }

  function onCheck() {
    if (!checkable) return;
    if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(30);
    dispatch('check', !checked);
  }

  function handleKey(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      e.preventDefault();
      commitEdit();
    } else if (e.key === 'Escape') {
      isEditing = false;
    }
  }
</script>

<div class="metric-row" class:checked={checkable && checked}>
  <span class="metric-icon">{icon}</span>
  <span class="metric-label">{label}</span>

  {#if isEditing}
    <input
      class="metric-input"
      type="text"
      inputmode="decimal"
      bind:value={editValue}
      on:blur={commitEdit}
      on:keydown={handleKey}
      use:focusInput
    />
  {:else}
    <span class="metric-value tap-area" on:click={startEdit}>
      {value != null && value !== '' ? value : '—'}
      {#if unit && value != null && value !== ''}
        <span class="metric-unit">{unit}</span>
      {/if}
    </span>
  {/if}

  {#if checkable}
    <button
      class="check-btn"
      class:is-checked={checked}
      on:click={onCheck}
      aria-label={checked ? 'Erledigt' : 'Als erledigt markieren'}
    >
      {checked ? '✓' : '○'}
    </button>
  {/if}
</div>

<script context="module" lang="ts">
  function focusInput(node: HTMLInputElement) {
    setTimeout(() => node.focus(), 0);
    return {
      destroy() {}
    };
  }
</script>

<style>
  .metric-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid #333;
  }

  .metric-row:last-child {
    border-bottom: none;
  }

  .metric-row.checked {
    opacity: 0.6;
  }

  .metric-icon {
    width: 24px;
    text-align: center;
    font-size: 1rem;
    flex-shrink: 0;
  }

  .metric-label {
    flex: 1;
    font-size: 0.8125rem;
    color: var(--text-secondary);
  }

  .metric-value {
    font-size: 0.875rem;
    font-weight: 500;
    text-align: right;
    min-width: 60px;
    padding: 2px 4px;
    border-radius: 4px;
  }

  .metric-value:active {
    background: #333;
  }

  .metric-unit {
    font-size: 0.6875rem;
    color: var(--text-secondary);
    margin-left: 2px;
  }

  .metric-input {
    flex: 0 1 80px;
    text-align: right;
    padding: 2px 4px;
    border-radius: 4px;
    background: #1a1a1a;
    border: 1px solid var(--pill-p);
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-primary);
  }

  .check-btn {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: transparent;
    border: 1px solid var(--card-border);
    color: var(--text-secondary);
    font-size: 0.875rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: all 0.2s;
  }

  .check-btn.is-checked {
    background: var(--accent-done);
    border-color: var(--accent-done);
    color: #0f0f0f;
    font-weight: 700;
  }

  .check-btn:active {
    transform: scale(0.9);
  }
</style>