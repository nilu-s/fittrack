<script lang="ts">
  import { currentDate } from '$lib/stores';
  import Icon from '$lib/components/Icon.svelte';

  const months = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'];
  const monthsFull = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'];
  const daysFull = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'];
  const calendarWeekdays = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];

  $: dateLabel = formatDateLabel($currentDate);
  $: isToday = $currentDate === todayStr();
  $: dow = daysFull[new Date($currentDate + 'T00:00:00').getDay()];
  let touchStartX = 0;
  let touchStartY = 0;
  let suppressClickUntil = 0;
  let pickerDialog: HTMLDialogElement;
  let calendarButton: HTMLButtonElement;
  let pickerMonth = new Date();

  type CalendarDay = { date: string; day: number; inMonth: boolean };

  function todayStr(): string { const d = new Date(); return formatDate(d); }
  function formatDate(d: Date): string { const y = d.getFullYear(); const m = String(d.getMonth() + 1).padStart(2, '0'); const day = String(d.getDate()).padStart(2, '0'); return `${y}-${m}-${day}`; }
  function formatDateLabel(dateStr: string): string { const d = new Date(dateStr + 'T00:00:00'); return `${d.getDate()}. ${months[d.getMonth()]}`; }
  function changeDate(delta: number) { const d = new Date($currentDate + 'T00:00:00'); d.setDate(d.getDate() + delta); currentDate.set(formatDate(d)); }
  function goToday() { currentDate.set(todayStr()); }
  function openPicker() {
    pickerMonth = new Date($currentDate + 'T00:00:00');
    pickerDialog.showModal();
  }
  function selectDate(date: string) {
    currentDate.set(date);
    pickerDialog.close();
  }
  function closePicker() { pickerDialog.close(); }
  function restoreCalendarFocus() { calendarButton?.focus(); }
  function changeMonth(delta: number) { pickerMonth = new Date(pickerMonth.getFullYear(), pickerMonth.getMonth() + delta, 1); }
  function calendarDays(month: Date): CalendarDay[] {
    const first = new Date(month.getFullYear(), month.getMonth(), 1);
    const start = new Date(first);
    start.setDate(first.getDate() - ((first.getDay() + 6) % 7));
    return Array.from({ length: 42 }, (_, index) => {
      const date = new Date(start);
      date.setDate(start.getDate() + index);
      return { date: formatDate(date), day: date.getDate(), inMonth: date.getMonth() === month.getMonth() };
    });
  }
  function fullDateLabel(dateStr: string): string {
    return new Date(dateStr + 'T00:00:00').toLocaleDateString('de-DE', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  }
  $: visibleCalendarDays = calendarDays(pickerMonth);
  $: pickerMonthLabel = `${monthsFull[pickerMonth.getMonth()]} ${pickerMonth.getFullYear()}`;
  function onTouchStart(e: TouchEvent) { touchStartX = e.touches[0].clientX; touchStartY = e.touches[0].clientY; }
  function onTouchEnd(e: TouchEvent) {
    const dx = e.changedTouches[0].clientX - touchStartX;
    const dy = e.changedTouches[0].clientY - touchStartY;
    if (Math.abs(dx) >= 44 && Math.abs(dx) > Math.abs(dy) * 1.4) {
      suppressClickUntil = Date.now() + 400;
      changeDate(dx > 0 ? -1 : 1);
    }
  }
  function guarded(action: () => void, e: MouseEvent) { if (Date.now() < suppressClickUntil) { e.preventDefault(); e.stopPropagation(); return; } action(); }
</script>

<nav class="dnav" aria-label="Tagesnavigation" ontouchstart={onTouchStart} ontouchend={onTouchEnd}>
  <button class="dnav-btn dnav-step" onclick={(e) => guarded(() => changeDate(-1), e)} aria-label="Vorheriger Tag"><Icon name="chevron-left" size={18} /><span>Zurück</span></button>
  <button class="dnav-mid" onclick={(e) => guarded(goToday, e)} aria-label="Heute">
    <span class="dnav-date">{dow}, {dateLabel}</span>
    <span class="dnav-today">{isToday ? 'Heute' : 'Zu heute'}</span>
  </button>
  <button bind:this={calendarButton} class="dnav-btn" type="button" onclick={openPicker} aria-label="Datum auswählen"><Icon name="calendar" size={18} /></button>
  <button class="dnav-btn dnav-step" onclick={(e) => guarded(() => changeDate(1), e)} aria-label="Nächster Tag"><span>Weiter</span><Icon name="chevron-right" size={18} /></button>
</nav>

<dialog bind:this={pickerDialog} class="date-picker" aria-labelledby="date-picker-title" onclose={restoreCalendarFocus}>
  <div class="picker-content">
    <header class="picker-header">
      <button type="button" class="month-button" onclick={() => changeMonth(-1)} aria-label="Vorheriger Monat"><Icon name="chevron-left" size={20} /></button>
      <h2 id="date-picker-title">{pickerMonthLabel}</h2>
      <button type="button" class="month-button" onclick={() => changeMonth(1)} aria-label="Nächster Monat"><Icon name="chevron-right" size={20} /></button>
      <button type="button" class="picker-close" onclick={closePicker} aria-label="Kalender schließen">×</button>
    </header>
    <div class="calendar-weekdays" aria-hidden="true">{#each calendarWeekdays as weekday}<span>{weekday}</span>{/each}</div>
    <div class="calendar-days" role="grid" aria-label={pickerMonthLabel}>
      {#each visibleCalendarDays as calendarDay (calendarDay.date)}
        <button type="button" class:outside-month={!calendarDay.inMonth} class:selected={calendarDay.date === $currentDate} class:today={calendarDay.date === todayStr()} onclick={() => selectDate(calendarDay.date)} aria-label={`${fullDateLabel(calendarDay.date)}${calendarDay.date === $currentDate ? ', ausgewählt' : ''}`} aria-current={calendarDay.date === todayStr() ? 'date' : undefined}>{calendarDay.day}</button>
      {/each}
    </div>
    <div class="picker-actions">
      <button type="button" class="picker-secondary" onclick={() => selectDate(todayStr())}>Heute</button>
      <span></span>
      <button type="button" class="picker-secondary" onclick={closePicker}>Abbrechen</button>
    </div>
  </div>
</dialog>

<style>
  .dnav { position: fixed; z-index: 40; left: 50%; bottom: max(10px, env(safe-area-inset-bottom, 0px)); transform: translateX(-50%); width: min(calc(100% - 20px), 460px); min-height: 52px; display: grid; grid-template-columns: 78px minmax(0, 1fr) 44px 78px; align-items: center; gap: 4px; padding: 4px; background: var(--surface-navigation); border: 1px solid var(--border-default); border-radius: var(--radius-surface); touch-action: pan-y; }
  .dnav-btn { width: 44px; height: 44px; border: 1px solid var(--border-default); border-radius: var(--radius-control); background: var(--surface-raised); color: var(--text-primary); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background .15s, color .15s; }
  .dnav-btn:active, .dnav-btn:focus-visible { background: var(--surface-pressed); color: var(--text-primary); }
  .dnav-step { width: 78px; gap: 2px; padding: 0 5px; font-size: 11px; font-weight: 700; }
  .dnav-mid { min-width: 0; height: 44px; display: flex; flex-direction: column; align-items: flex-start; justify-content: center; gap: 1px; background: transparent; cursor: pointer; padding: 4px 10px; border-radius: 10px; }
  .dnav-mid:active, .dnav-mid:focus-visible { background: var(--surface-accent); }
  .dnav-date { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; font-weight: 650; color: var(--text-primary); }
  .dnav-today { font-size: 10px; line-height: 1.1; color: var(--action-primary); font-weight: 700; }
  .date-picker { width: min(calc(100% - 24px), 360px); margin: auto; padding: 0; border: 1px solid var(--border-default); border-radius: var(--radius-modal); background: var(--surface-default); color: var(--text-primary); box-shadow: var(--shadow-modal); }
  .date-picker::backdrop { background: var(--overlay-backdrop); }
  .picker-content { display: grid; gap: var(--space-3); padding: var(--space-4); }
  .picker-header { display: grid; grid-template-columns: 38px minmax(0, 1fr) 38px 38px; align-items: center; gap: var(--space-1); }
  .date-picker h2 { margin: 0; font-size: 17px; }
  .month-button, .picker-close { display: grid; place-items: center; width: 38px; height: 38px; border-radius: var(--radius-control); color: var(--text-secondary); cursor: pointer; }
  .picker-close { font-size: 24px; line-height: 1; }
  .month-button:active, .month-button:focus-visible, .picker-close:active, .picker-close:focus-visible { background: var(--surface-raised); color: var(--text-primary); }
  .calendar-weekdays, .calendar-days { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 3px; }
  .calendar-weekdays span { display: grid; place-items: center; min-height: 26px; color: var(--text-tertiary); font-size: 11px; font-weight: 700; }
  .calendar-days button { display: grid; place-items: center; aspect-ratio: 1; min-height: 36px; border-radius: var(--radius-control); color: var(--text-primary); cursor: pointer; font-size: 13px; }
  .calendar-days button:active, .calendar-days button:focus-visible { background: var(--surface-raised); outline: 2px solid var(--status-info); outline-offset: -2px; }
  .calendar-days button.outside-month { color: var(--text-tertiary); opacity: .56; }
  .calendar-days button.today { box-shadow: inset 0 0 0 1px var(--action-primary); }
  .calendar-days button.selected { background: var(--action-primary); color: var(--text-on-accent); font-weight: 700; box-shadow: none; opacity: 1; }
  .picker-actions { display: grid; grid-template-columns: auto 1fr auto; gap: var(--space-2); }
  .picker-actions button { min-height: var(--control-min); padding: 8px 12px; border-radius: var(--radius-control); cursor: pointer; font: inherit; }
  .picker-secondary { border: 1px solid var(--border-default); background: var(--surface-raised); color: var(--text-secondary); }
  @media (max-width: 380px) { .dnav { grid-template-columns: 44px minmax(0, 1fr) 44px 44px; } .dnav-step { width: 44px; padding: 0; } .dnav-step span { display: none; } .picker-actions { grid-template-columns: 1fr 1fr; } .picker-actions span { display: none; } }
</style>
