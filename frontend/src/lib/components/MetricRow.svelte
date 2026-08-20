<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Icon from './Icon.svelte';

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
  let lastTap = 0;
  let editTimeout: ReturnType<typeof setTimeout> | null = null;

  function startEdit() { if (!editable) return; editValue = value != null ? String(value) : ''; isEditing = true; }
  function commitEdit() { isEditing = false; const parsed = parseValue(editValue); if (parsed !== value) dispatch('change', parsed); }
  function parseValue(v: string): string | number {
    const trimmed = v.trim(); if (trimmed === '') return '';
    const num = parseFloat(trimmed); if (!isNaN(num) && /^\d+\.?\d*$/.test(trimmed)) return num; return trimmed;
  }
  function onCheck() { if (!checkable) return; if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(30); dispatch('check', !checked); }
  function handleRowTap() {
    if (!checkable) return;
    const now = Date.now();
    if (now - lastTap < 300) { if (editTimeout) clearTimeout(editTimeout); onCheck(); lastTap = 0; } else { lastTap = now; }
  }
  function handleValueTap() {
    if (!editable) return;
    const now = Date.now();
    if (now - lastTap < 300) { if (editTimeout) clearTimeout(editTimeout); lastTap = 0; return; }
    lastTap = now;
    editTimeout = setTimeout(() => { if (Date.now() - lastTap >= 300) startEdit(); }, 320);
  }
  function handleKey(e: KeyboardEvent) { if (e.key === 'Enter') { e.preventDefault(); commitEdit(); } else if (e.key === 'Escape') isEditing = false; }
</script>

<div class="mrow" class:checked={checkable && checked} onclick={handleRowTap} role={checkable ? 'button' : undefined} tabindex={checkable ? 0 : undefined}>
  {#if icon}<Icon name={icon} size={18} />{/if}
  <span class="mrow-label">{label}</span>
  {#if isEditing}
    <input class="mrow-input" type="text" inputmode="decimal" bind:value={editValue} onblur={commitEdit} onkeydown={handleKey} use:focusInput />
  {:else}
    <span class="mrow-value tap-area" onclick={handleValueTap}>
      {value != null && value !== '' ? value : '—'}
      {#if unit && value != null && value !== ''}<span class="mrow-unit">{unit}</span>{/if}
    </span>
  {/if}
  {#if checkable}
    <button class="mrow-check" class:done={checked} onclick={onCheck} aria-label={checked ? 'Erledigt' : 'Markieren'}>
      {#if checked}<Icon name="check" size={14} />{/if}
    </button>
  {/if}
</div>

<script context="module" lang="ts">
  function focusInput(node: HTMLInputElement) { setTimeout(() => node.focus(), 0); return { destroy() {} }; }
</script>

<style>
  .mrow { display: flex; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 1px solid var(--border); transition: opacity 0.15s; }
  .mrow:last-child { border-bottom: none; }
  .mrow.checked { opacity: 0.5; }
  .mrow-label { flex: 1; font-size: 14px; color: var(--text-dim); }
  .mrow-value { font-size: 15px; font-weight: 600; text-align: right; min-width: 60px; padding: 2px 6px; border-radius: 6px; }
  .mrow-value:active { background: var(--card-2); }
  .mrow-unit { font-size: 12px; color: var(--text-faint); margin-left: 2px; font-weight: 400; }
  .mrow-input { flex: 0 1 80px; text-align: right; padding: 2px 6px; border-radius: 6px; background: var(--card-2); border: 1px solid var(--blue); font-size: 15px; font-weight: 600; color: var(--text); }
  .mrow-check { width: 28px; height: 28px; border-radius: 50%; background: transparent; border: 1.5px solid var(--border-2); color: transparent; cursor: pointer; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: all 0.2s; }
  .mrow-check.done { background: var(--green); border-color: var(--green); color: #000; }
  .mrow-check:active { transform: scale(0.9); }
</style>