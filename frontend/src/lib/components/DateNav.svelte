<script lang="ts">
  import { currentDate } from '$lib/stores';
  import Icon from '$lib/components/Icon.svelte';

  const months = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'];
  const daysFull = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'];

  $: dateLabel = formatDateLabel($currentDate);
  $: isToday = $currentDate === todayStr();
  $: dow = daysFull[new Date($currentDate + 'T00:00:00').getDay()];

  function todayStr(): string { const d = new Date(); return formatDate(d); }
  function formatDate(d: Date): string { const y = d.getFullYear(); const m = String(d.getMonth() + 1).padStart(2, '0'); const day = String(d.getDate()).padStart(2, '0'); return `${y}-${m}-${day}`; }
  function formatDateLabel(dateStr: string): string { const d = new Date(dateStr + 'T00:00:00'); return `${d.getDate()}. ${months[d.getMonth()]}`; }
  function changeDate(delta: number) { const d = new Date($currentDate + 'T00:00:00'); d.setDate(d.getDate() + delta); currentDate.set(formatDate(d)); }
  function goToday() { currentDate.set(todayStr()); }
</script>

<div class="dnav">
  <button class="dnav-btn" onclick={() => changeDate(-1)} aria-label="Zurück"><Icon name="chevron-left" size={20} /></button>
  <button class="dnav-mid" onclick={goToday} aria-label="Heute">
    <span class="dnav-dow">{dow}</span>
    <span class="dnav-date">{dateLabel}</span>
    {#if !isToday}<span class="dnav-today">Heute</span>{/if}
  </button>
  <button class="dnav-btn" onclick={() => changeDate(1)} aria-label="Weiter"><Icon name="chevron-right" size={20} /></button>
</div>

<style>
  .dnav { display: flex; align-items: center; justify-content: space-between; padding: 8px 4px; gap: 8px; }
  .dnav-btn { width: 36px; height: 36px; border-radius: 8px; background: var(--card); border: 1px solid var(--border); color: var(--text-dim); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background 0.15s; flex-shrink: 0; }
  .dnav-btn:active { background: var(--card-2); color: var(--text); }
  .dnav-mid { flex: 1; display: flex; align-items: center; justify-content: center; gap: 8px; background: transparent; border: none; cursor: pointer; padding: 4px 12px; border-radius: 8px; transition: background 0.15s; }
  .dnav-mid:active { background: var(--card); }
  .dnav-dow { font-size: 12px; font-weight: 600; color: var(--text-dim); }
  .dnav-date { font-size: 16px; font-weight: 600; color: var(--text); }
  .dnav-today { font-size: 11px; color: var(--green); font-weight: 500; }
</style>