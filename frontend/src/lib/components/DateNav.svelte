<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { currentDate } from '$lib/stores';
  import Icon from '$lib/components/Icon.svelte';

  export let todoTitle = '';
  export let noteTitle = '';
  export let shoppingTitle = '';
  export let todoAdding = false;
  export let noteAdding = false;
  export let shoppingAdding = false;
  export let todoAddError = '';
  export let noteAddError = '';
  export let shoppingAddError = '';
  export let shoppingOpen = false;
  export let noteBoardOpen = false;
  export let shoppingCount = 0;
  export let noteCount = 0;
  export let noteTargetName = '';
  const dispatch = createEventDispatcher<{ todoadd: string; noteadd: string; shoppingadd: string; aiplan: string; shoppingopen: void; noteboardopen: void }>();
  const months = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'];
  const daysFull = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'];
  $: dateLabel = formatDateLabel($currentDate);
  $: isToday = $currentDate === todayStr();
  $: dow = daysFull[new Date(`${$currentDate}T00:00:00`).getDay()];
  let calendarButton: HTMLButtonElement;
  let calendarOpen = false;
  let dateTapTimer: ReturnType<typeof setTimeout> | null = null;
  let pickerMonth = new Date();
  let footerTouchStart: { x: number; y: number } | null = null;
  let suppressFooterClick = false;

  function formatDate(d: Date) { return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; }
  function todayStr() { return formatDate(new Date()); }
  function formatDateLabel(dateStr: string) { const d = new Date(`${dateStr}T00:00:00`); return `${d.getDate()}. ${months[d.getMonth()]}`; }
  function changeDate(delta: number) { const d = new Date(`${$currentDate}T00:00:00`); d.setDate(d.getDate() + delta); currentDate.set(formatDate(d)); }
  function openPicker() { pickerMonth = new Date(`${$currentDate}T00:00:00`); calendarOpen = true; }
  function onDateTap() { if (dateTapTimer) { clearTimeout(dateTapTimer); dateTapTimer = null; currentDate.set(todayStr()); return; } dateTapTimer = setTimeout(() => { dateTapTimer = null; openPicker(); }, 240); }
  function closePicker() { calendarOpen = false; calendarButton?.focus(); }
  function selectDate(date: string) { currentDate.set(date); closePicker(); }
  function changeMonth(delta: number) { pickerMonth = new Date(pickerMonth.getFullYear(), pickerMonth.getMonth() + delta, 1); }
  function calendarDays(month: Date) {
    const first = new Date(month.getFullYear(), month.getMonth(), 1);
    const start = new Date(first);
    start.setDate(first.getDate() - ((first.getDay() + 6) % 7));
    return Array.from({ length: 42 }, (_, index) => {
      const date = new Date(start);
      date.setDate(start.getDate() + index);
      return { date: formatDate(date), day: date.getDate(), inMonth: date.getMonth() === month.getMonth() };
    });
  }
  $: visibleCalendarDays = calendarDays(pickerMonth);
  $: pickerMonthLabel = `${months[pickerMonth.getMonth()]} ${pickerMonth.getFullYear()}`;
  $: entryMode = shoppingOpen ? 'shopping' : noteBoardOpen ? 'note' : 'todo';
  $: entryTitle = entryMode === 'shopping' ? shoppingTitle : entryMode === 'note' ? noteTitle : todoTitle;
  $: entryAdding = entryMode === 'shopping' ? shoppingAdding : entryMode === 'note' ? noteAdding : todoAdding;
  $: entryError = entryMode === 'shopping' ? shoppingAddError : entryMode === 'note' ? noteAddError : todoAddError;
  $: entryLabel = entryMode === 'shopping' ? 'Artikel zur Einkaufsliste hinzufügen' : entryMode === 'note' ? `Notiz${noteTargetName ? ` für ${noteTargetName}` : ' im privaten Eingang'} hinzufügen` : 'To-do für den gewählten Tag hinzufügen';
  $: entryPlaceholder = entryMode === 'shopping' ? 'Artikel suchen oder hinzufügen…' : entryMode === 'note' ? noteTargetName ? `Notiz für ${noteTargetName} festhalten…` : 'Notiz festhalten…' : 'To-do für heute hinzufügen…';
  $: submitLabel = entryMode === 'shopping' ? 'Artikel hinzufügen' : entryMode === 'note' ? 'Notiz hinzufügen' : 'To-do hinzufügen';
  function updateEntry(event: Event) {
    const value = (event.currentTarget as HTMLInputElement).value;
    if (entryMode === 'shopping') shoppingTitle = value;
    else if (entryMode === 'note') noteTitle = value;
    else todoTitle = value;
  }
  function submitEntry() {
    if (entryMode === 'shopping') dispatch('shoppingadd', shoppingTitle);
    else if (entryMode === 'note') dispatch('noteadd', noteTitle);
    else dispatch('todoadd', todoTitle);
  }
  function startFooterSwipe(event: TouchEvent) {
    const target = event.target as HTMLElement | null;
    if (calendarOpen || target?.closest('input, textarea, select, [contenteditable="true"]')) return;
    const touch = event.touches[0];
    if (touch) footerTouchStart = { x: touch.clientX, y: touch.clientY };
  }
  function finishFooterSwipe(event: TouchEvent) {
    if (!footerTouchStart) return;
    const start = footerTouchStart;
    footerTouchStart = null;
    const touch = event.changedTouches[0];
    if (!touch) return;
    const dx = touch.clientX - start.x;
    const dy = touch.clientY - start.y;
    if (Math.abs(dx) < 48 || Math.abs(dx) <= Math.abs(dy) * 1.15) return;
    suppressFooterClick = true;
    changeDate(dx < 0 ? 1 : -1);
    setTimeout(() => { suppressFooterClick = false; }, 0);
  }
  function changeDateFromButton(delta: number) { if (!suppressFooterClick) changeDate(delta); }
  function openNoteBoard() { if (!suppressFooterClick) dispatch('noteboardopen'); }
  function openShopping() { if (!suppressFooterClick) dispatch('shoppingopen'); }
  function openDatePicker() { if (!suppressFooterClick) onDateTap(); }
  function onWindowKeydown(event: KeyboardEvent) { if (calendarOpen && event.key === 'Escape') closePicker(); }
</script>

<svelte:window onkeydown={onWindowKeydown} />

<footer class="day-footer" aria-label="Tagesaktionen">
  <form class="todo-add" onsubmit={(event) => { event.preventDefault(); submitEntry(); }}>
    <label class="sr-only" for="footer-entry-title">{entryLabel}</label>
    <input id="footer-entry-title" placeholder={entryPlaceholder} value={entryTitle} oninput={updateEntry} disabled={entryAdding} aria-describedby={entryError ? 'footer-entry-error' : undefined} />
    <button type="submit" disabled={!entryTitle.trim() || entryAdding} aria-label={submitLabel} title={submitLabel}><Icon name="plus" size={16} /></button>
    {#if entryMode === 'todo'}<button class="todo-ai" type="button" disabled={todoAdding} aria-label="KI-Assistent öffnen" title="Mit KI besprechen" onclick={() => dispatch('aiplan', todoTitle)}>✦</button>{/if}
  </form>
  {#if entryError}<p id="footer-entry-error" class="todo-add-error" role="status">{entryError}</p>{/if}
  <nav class="dnav" aria-label="Tagesnavigation; horizontal wischen, um den Tag zu wechseln" ontouchstart={startFooterSwipe} ontouchend={finishFooterSwipe}>
    <button type="button" class="footer-icon day-arrow" aria-label="Vorheriger Tag" title="Vorheriger Tag" onclick={() => changeDateFromButton(-1)}><Icon name="chevron-left" size={20} /></button>
    <button type="button" class="footer-icon" class:open={noteBoardOpen} aria-controls="note-board" aria-expanded={noteBoardOpen} aria-label="Notiz-Board öffnen" title="Notizen" onclick={openNoteBoard}><Icon name="edit" size={18} />{#if noteCount}<span class="count">{noteCount}</span>{/if}</button>
    <button bind:this={calendarButton} type="button" class="dnav-mid" onclick={openDatePicker} aria-haspopup="dialog" aria-expanded={calendarOpen} aria-label="Kalender öffnen; doppeltippen für heute"><span class="dnav-date">{dow}, {dateLabel}</span><span class="dnav-today">{isToday ? 'Heute' : 'Datum wählen'}</span></button>
    <button type="button" class="footer-icon" class:open={shoppingOpen} aria-controls="shopping-quick-panel" aria-expanded={shoppingOpen} aria-label="Einkaufsliste öffnen" title="Einkauf" onclick={openShopping}><Icon name="shopping" size={18} />{#if shoppingCount}<span class="count">{shoppingCount}</span>{/if}</button>
    <button type="button" class="footer-icon day-arrow" aria-label="Nächster Tag" title="Nächster Tag" onclick={() => changeDateFromButton(1)}><Icon name="chevron-right" size={20} /></button>
  </nav>
  <div class="footer-status">
    <slot />
  </div>
</footer>

{#if calendarOpen}
<div class="calendar-overlay" role="presentation">
  <button class="overlay-backdrop" type="button" onclick={closePicker} aria-label="Kalender schließen"></button>
  <div class="date-picker" role="dialog" aria-modal="true" aria-labelledby="date-picker-title">
    <div class="picker-content">
      <header class="picker-header"><button type="button" class="month-button" onclick={() => changeMonth(-1)} aria-label="Vorheriger Monat"><Icon name="chevron-left" size={20} /></button><h2 id="date-picker-title">{pickerMonthLabel}</h2><button type="button" class="month-button" onclick={() => changeMonth(1)} aria-label="Nächster Monat"><Icon name="chevron-right" size={20} /></button></header>
      <div class="calendar-weekdays" aria-hidden="true"><span>Mo</span><span>Di</span><span>Mi</span><span>Do</span><span>Fr</span><span>Sa</span><span>So</span></div>
      <div class="calendar-days" role="grid" aria-label={pickerMonthLabel}>{#each visibleCalendarDays as calendarDay (calendarDay.date)}<button type="button" class:outside-month={!calendarDay.inMonth} class:selected={calendarDay.date === $currentDate} class:today={calendarDay.date === todayStr()} onclick={() => selectDate(calendarDay.date)} aria-label={calendarDay.date}>{calendarDay.day}</button>{/each}</div>
      <div class="picker-actions"><button type="button" class="picker-secondary" onclick={() => selectDate(todayStr())}>Heute</button></div>
    </div>
  </div>
</div>
{/if}

<style>
  .day-footer{position:fixed;z-index:50;left:50%;bottom:max(10px,env(safe-area-inset-bottom,0px));transform:translateX(-50%);display:grid;gap:6px;width:min(calc(100% - 20px),460px)}.todo-add{display:flex;gap:8px}.todo-add input{flex:1;min-width:0;min-height:40px;padding:8px 12px;border:1px solid var(--border-default);border-radius:var(--radius-control);background:var(--surface-raised);color:var(--text-primary);font:inherit;font-size:14px}.todo-add input::placeholder{color:var(--text-tertiary)}.todo-add button{display:grid;place-items:center;width:40px;min-height:40px;border:0;border-radius:var(--radius-control);background:var(--action-primary);color:var(--text-on-accent);cursor:pointer}.todo-add .todo-ai{border:1px solid var(--border-accent);background:var(--surface-accent);color:var(--action-primary);font-size:18px}.todo-add button:disabled{opacity:.4;cursor:default}.todo-add-error{margin:0;padding:7px 10px;border-radius:var(--radius-control);background:var(--surface-navigation);color:var(--status-danger);font-size:12px}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}.dnav{display:grid;grid-template-columns:40px 40px minmax(0,1fr) 40px 40px;align-items:center;gap:2px;min-height:52px;padding:4px;background:var(--surface-accent);border:1px solid var(--border-default);border-radius:var(--radius-surface);touch-action:pan-y}.footer-status{display:grid;gap:4px;padding:0 var(--space-1)}.footer-icon{position:relative;display:grid;place-items:center;width:40px;height:40px;padding:0;border:0;border-radius:var(--radius-control);background:transparent;color:var(--text-secondary);cursor:pointer}.footer-icon:active{background:var(--surface-pressed)}.footer-icon.open{color:var(--action-primary)}.day-arrow{color:var(--text-primary)}.count{position:absolute;top:1px;right:1px;display:grid;place-items:center;min-width:14px;height:14px;padding:0 2px;border-radius:99px;background:var(--text-primary);color:var(--surface-default);font-size:9px;font-weight:750}.dnav-mid{min-width:0;height:44px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1px;padding:4px 10px;border:0;background:transparent;color:inherit;font:inherit;text-align:center;cursor:pointer}.dnav-date{max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:14px;font-weight:650;color:var(--text-primary)}.dnav-today{font-size:10px;line-height:1.1;color:var(--action-primary);font-weight:700}.todo-add input:focus-visible,.todo-add button:focus-visible,.footer-icon:focus-visible,.dnav-mid:focus-visible{outline:2px solid var(--status-info);outline-offset:2px}.calendar-overlay{position:fixed;z-index:60;inset:0;display:grid;place-items:center;padding:12px}.overlay-backdrop{position:absolute;inset:0;border:0;background:var(--overlay-backdrop)}.date-picker{position:relative;z-index:1;box-sizing:border-box;width:min(100%,360px);max-height:calc(100dvh - 24px);padding:0;border:1px solid var(--border-default);border-radius:var(--radius-modal);background:var(--surface-default);color:var(--text-primary);box-shadow:var(--shadow-modal);animation:overlay-in 180ms cubic-bezier(.22,1,.36,1)}.picker-content{display:grid;gap:var(--space-3);padding:var(--space-4);overflow:auto}.picker-header{display:grid;grid-template-columns:38px minmax(0,1fr) 38px;align-items:center;gap:var(--space-1)}.date-picker h2{margin:0;font-size:17px}.month-button{display:grid;place-items:center;width:38px;height:38px;border-radius:var(--radius-control);color:var(--text-secondary);cursor:pointer}.month-button:active,.month-button:focus-visible{background:var(--surface-raised);color:var(--text-primary)}.calendar-weekdays,.calendar-days{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:3px}.calendar-weekdays span{display:grid;place-items:center;min-height:26px;color:var(--text-tertiary);font-size:11px;font-weight:700}.calendar-days button{display:grid;place-items:center;aspect-ratio:1;min-height:36px;border-radius:var(--radius-control);color:var(--text-primary);cursor:pointer;font-size:13px}.calendar-days button:active,.calendar-days button:focus-visible{background:var(--surface-raised);outline:2px solid var(--status-info);outline-offset:-2px}.calendar-days button.outside-month{color:var(--text-tertiary);opacity:.56}.calendar-days button.today{box-shadow:inset 0 0 0 1px var(--action-primary)}.calendar-days button.selected{background:var(--action-primary);color:var(--text-on-accent);font-weight:700;box-shadow:none;opacity:1}.picker-actions{display:flex;justify-content:flex-start;gap:var(--space-2)}.picker-secondary{border:1px solid var(--border-default);background:var(--surface-raised);color:var(--text-secondary)}@keyframes overlay-in{from{opacity:0;transform:scale(.96)}to{opacity:1;transform:scale(1)}}@media(prefers-reduced-motion:reduce){.date-picker{animation:none}}
</style>
