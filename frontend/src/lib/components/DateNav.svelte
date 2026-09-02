<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { currentDate } from '$lib/stores';
  import Icon from '$lib/components/Icon.svelte';

  export let todoTitle = '';
  export let todoAdding = false;
  export let todoAddError = '';
  export let shoppingOpen = false;
  export let shoppingTitle = '';
  export let shoppingAdding = false;
  export let shoppingCount = 0;
  const dispatch = createEventDispatcher<{ todoadd: string; aiplan: string; shoppingtoggle: void; shoppingadd: string; shoppinggesture: number }>();
  const months = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'];
  const daysFull = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'];
  $: dateLabel = formatDateLabel($currentDate);
  $: isToday = $currentDate === todayStr();
  $: dow = daysFull[new Date(`${$currentDate}T00:00:00`).getDay()];
  let touchStartX = 0;
  let touchStartY = 0;
  let suppressClickUntil = 0;
  let calendarButton: HTMLButtonElement;
  let shoppingGestureStart = 0;
  let shoppingGestureUsed = false;
  let calendarGestureStart = 0;
  let calendarGestureUsed = false;
  let calendarOpen = false;
  let calendarDragStart = 0;
  let calendarDragOffset = 0;
  let pickerMonth = new Date();

  function formatDate(d: Date) { return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; }
  function todayStr() { return formatDate(new Date()); }
  function formatDateLabel(dateStr: string) { const d = new Date(`${dateStr}T00:00:00`); return `${d.getDate()}. ${months[d.getMonth()]}`; }
  function changeDate(delta: number) { const d = new Date(`${$currentDate}T00:00:00`); d.setDate(d.getDate() + delta); currentDate.set(formatDate(d)); }
  function openPicker() { pickerMonth = new Date(`${$currentDate}T00:00:00`); calendarOpen = true; }
  function closePicker() { calendarOpen = false; calendarDragOffset = 0; calendarButton?.focus(); }
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
  function onTouchStart(e: TouchEvent) { touchStartX = e.touches[0].clientX; touchStartY = e.touches[0].clientY; }
  function onTouchEnd(e: TouchEvent) { const dx = e.changedTouches[0].clientX - touchStartX; const dy = e.changedTouches[0].clientY - touchStartY; if (Math.abs(dx) >= 44 && Math.abs(dx) > Math.abs(dy) * 1.4) { suppressClickUntil = Date.now() + 400; changeDate(dx > 0 ? -1 : 1); } }
  function guarded(action: () => void, e: MouseEvent) { if (Date.now() < suppressClickUntil) { e.preventDefault(); e.stopPropagation(); return; } action(); }
  function submitTodo() { dispatch('todoadd', todoTitle); }
  function submitShopping() { dispatch('shoppingadd', shoppingTitle); }
  function updateFooterEntry(event: Event) { if (shoppingOpen) shoppingTitle = (event.currentTarget as HTMLInputElement).value; else todoTitle = (event.currentTarget as HTMLInputElement).value; }
  function startShoppingGesture(event: PointerEvent) { shoppingGestureStart = event.clientY; shoppingGestureUsed = false; (event.currentTarget as HTMLElement | null)?.setPointerCapture(event.pointerId); }
  function moveShoppingGesture(event: PointerEvent) { const distance = Math.max(0, shoppingGestureStart - event.clientY); if (distance < 6) return; shoppingGestureUsed = true; dispatch('shoppinggesture', distance); }
  function endShoppingGesture() { shoppingGestureStart = 0; }
  function toggleShopping() { if (!shoppingGestureUsed) dispatch('shoppingtoggle'); shoppingGestureUsed = false; }
  function startCalendarGesture(event: PointerEvent) { calendarGestureStart = event.clientY; calendarGestureUsed = false; (event.currentTarget as HTMLElement | null)?.setPointerCapture(event.pointerId); }
  function moveCalendarGesture(event: PointerEvent) { if (calendarGestureStart - event.clientY >= 18) calendarGestureUsed = true; }
  function endCalendarGesture() { if (calendarGestureUsed) openPicker(); calendarGestureStart = 0; }
  function toggleCalendar() { if (!calendarGestureUsed) openPicker(); calendarGestureUsed = false; }
  function startCalendarDrag(event: PointerEvent) { calendarDragStart = event.clientY; (event.currentTarget as HTMLElement | null)?.setPointerCapture(event.pointerId); }
  function moveCalendarDrag(event: PointerEvent) { calendarDragOffset = Math.max(0, event.clientY - calendarDragStart); }
  function endCalendarDrag() { if (calendarDragOffset >= 88) closePicker(); else calendarDragOffset = 0; calendarDragStart = 0; }
  function closeCalendarFromHandle(event: KeyboardEvent) { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); closePicker(); } }
  function onWindowKeydown(event: KeyboardEvent) { if (calendarOpen && event.key === 'Escape') closePicker(); }
</script>

<svelte:window onkeydown={onWindowKeydown} />

<footer class="day-footer" aria-label="Tagesaktionen">
  <form class="todo-add" onsubmit={(event) => { event.preventDefault(); shoppingOpen ? submitShopping() : submitTodo(); }}>
    <label class="sr-only" for="footer-entry-title">{shoppingOpen ? 'Artikel suchen oder hinzufügen' : `To-do für ${dateLabel} hinzufügen`}</label>
    <input id="footer-entry-title" placeholder={shoppingOpen ? 'Artikel suchen oder hinzufügen…' : '+ To-do hinzufügen…'} value={shoppingOpen ? shoppingTitle : todoTitle} oninput={updateFooterEntry} disabled={shoppingOpen ? shoppingAdding : todoAdding} aria-describedby={!shoppingOpen && todoAddError ? 'footer-todo-error' : undefined} />
    <button type="submit" disabled={shoppingOpen ? !shoppingTitle.trim() || shoppingAdding : !todoTitle.trim() || todoAdding} aria-label={shoppingOpen ? 'Artikel hinzufügen' : 'To-do hinzufügen'}><Icon name="plus" size={16} /></button>
    {#if !shoppingOpen}
      <button class="todo-ai" type="button" disabled={todoAdding} aria-label="KI-Assistent öffnen" title="Mit KI besprechen" onclick={() => dispatch('aiplan', todoTitle)}>✦</button>
    {/if}
  </form>
  {#if todoAddError}<p id="footer-todo-error" class="todo-add-error" role="status">{todoAddError}</p>{/if}
  <nav class="dnav" aria-label="Tagesnavigation" ontouchstart={onTouchStart} ontouchend={onTouchEnd}>
    <button class="dnav-arrow" onclick={(e) => guarded(() => changeDate(-1), e)} aria-label="Vorheriger Tag"><Icon name="chevron-left" size={20} /></button>
    <div class="dnav-mid" aria-live="polite"><span class="dnav-date">{dow}, {dateLabel}</span><span class="dnav-today">{isToday ? 'Heute' : 'Im Footer wischen'}</span></div>
    <button class:active={shoppingOpen} class="drawer-zone shopping-toggle" type="button" onclick={toggleShopping} onpointerdown={startShoppingGesture} onpointermove={moveShoppingGesture} onpointerup={endShoppingGesture} onpointercancel={endShoppingGesture} aria-expanded={shoppingOpen} aria-controls="shopping-quick-panel" aria-label="Einkaufsliste durch Hochziehen öffnen"><span class="drawer-grip" aria-hidden="true"></span><span>Einkauf</span><span class="shopping-count">{shoppingCount}</span></button>
    <button bind:this={calendarButton} class="drawer-zone calendar-toggle" type="button" onclick={toggleCalendar} onpointerdown={startCalendarGesture} onpointermove={moveCalendarGesture} onpointerup={endCalendarGesture} onpointercancel={endCalendarGesture} aria-label="Kalender durch Hochziehen öffnen"><span class="drawer-grip" aria-hidden="true"></span><span>Kalender</span></button>
    <button class="dnav-arrow" onclick={(e) => guarded(() => changeDate(1), e)} aria-label="Nächster Tag"><Icon name="chevron-right" size={20} /></button>
  </nav>
</footer>

{#if calendarOpen}
<aside class="date-picker" style={`--drag-offset: ${calendarDragOffset}px`} aria-labelledby="date-picker-title">
  <div class="picker-content">
    <div class="picker-handle" role="button" tabindex="0" aria-label="Kalender schließen" onkeydown={closeCalendarFromHandle} onpointerdown={startCalendarDrag} onpointermove={moveCalendarDrag} onpointerup={endCalendarDrag} onpointercancel={endCalendarDrag}><span aria-hidden="true"></span></div>
    <header class="picker-header"><button type="button" class="month-button" onclick={() => changeMonth(-1)} aria-label="Vorheriger Monat"><Icon name="chevron-left" size={20} /></button><h2 id="date-picker-title">{pickerMonthLabel}</h2><button type="button" class="month-button" onclick={() => changeMonth(1)} aria-label="Nächster Monat"><Icon name="chevron-right" size={20} /></button></header>
    <div class="calendar-weekdays" aria-hidden="true"><span>Mo</span><span>Di</span><span>Mi</span><span>Do</span><span>Fr</span><span>Sa</span><span>So</span></div>
    <div class="calendar-days" role="grid" aria-label={pickerMonthLabel}>{#each visibleCalendarDays as calendarDay (calendarDay.date)}<button type="button" class:outside-month={!calendarDay.inMonth} class:selected={calendarDay.date === $currentDate} class:today={calendarDay.date === todayStr()} onclick={() => selectDate(calendarDay.date)} aria-label={calendarDay.date}>{calendarDay.day}</button>{/each}</div>
    <div class="picker-actions"><button type="button" class="picker-secondary" onclick={() => selectDate(todayStr())}>Heute</button></div>
  </div>
</aside>
{/if}

<style>
  .day-footer { position:fixed; z-index:50; left:50%; bottom:max(10px, env(safe-area-inset-bottom, 0px)); transform:translateX(-50%); display:grid; gap:6px; width:min(calc(100% - 20px), 460px); }
  .todo-add { display:flex; gap:8px; }
  .todo-add input { flex:1; min-width:0; min-height:40px; padding:8px 12px; border:1px solid var(--border-default); border-radius:var(--radius-control); background:var(--surface-raised); color:var(--text-primary); font:inherit; font-size:14px; }
  .todo-add input:focus-visible,.todo-add button:focus-visible { outline:2px solid var(--status-info); outline-offset:2px; }
  .todo-add input::placeholder { color:var(--text-tertiary); }
  .todo-add button { display:grid; place-items:center; width:40px; min-height:40px; border:0; border-radius:var(--radius-control); background:var(--action-primary); color:var(--text-on-accent); cursor:pointer; }
  .todo-add .todo-ai { border:1px solid var(--border-accent); background:var(--surface-accent); color:var(--action-primary); font-size:18px; }
  .todo-add button:disabled { opacity:.4; cursor:default; }
  .todo-add-error { margin:0; padding:7px 10px; border-radius:var(--radius-control); background:var(--surface-navigation); color:var(--status-danger); font-size:12px; }
  .sr-only { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; }
  .dnav { min-height:52px; display:grid; grid-template-columns:44px minmax(0,1fr) 68px 68px 44px; align-items:center; gap:4px; padding:4px; background:var(--surface-accent); border:1px solid var(--border-default); border-radius:var(--radius-surface); touch-action:pan-y; }
  .dnav-arrow { display:grid; place-items:center; width:44px; height:44px; padding:0; border:0; background:transparent; color:var(--text-tertiary); cursor:pointer; }
  .dnav-arrow:active,.dnav-arrow:focus-visible { color:var(--action-primary); outline:2px solid var(--status-info); outline-offset:2px; }
  .drawer-zone { position:relative; display:grid; place-items:center; gap:1px; width:68px; height:44px; padding:2px 0; border:0; border-radius:var(--radius-control); background:transparent; color:var(--text-secondary); font:inherit; font-size:10px; font-weight:700; cursor:ns-resize; touch-action:none; }
  .drawer-zone:active,.drawer-zone:focus-visible { background:var(--surface-pressed); outline:2px solid var(--status-info); outline-offset:2px; }
  .drawer-grip { width:28px; height:3px; border-radius:99px; background:var(--border-strong); }
  .shopping-toggle { color:var(--action-primary); }
  .shopping-toggle.active { color:var(--action-primary); background:var(--surface-navigation); }
  .shopping-count { position:absolute; top:-4px; right:-3px; display:grid; place-items:center; min-width:16px; height:16px; padding:0 3px; border-radius:99px; background:var(--action-primary); color:var(--text-on-accent); font-size:9px; font-weight:750; }
  .shopping-toggle.active .shopping-count { background:var(--surface-raised); color:var(--action-primary); }
  .dnav-mid { min-width:0; height:44px; display:flex; flex-direction:column; align-items:flex-start; justify-content:center; gap:1px; padding:4px 10px; }
  .dnav-date { max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:14px; font-weight:650; color:var(--text-primary); }
  .dnav-today { font-size:10px; line-height:1.1; color:var(--action-primary); font-weight:700; }
  .date-picker { position:fixed; z-index:45; left:50%; bottom:78px; transform:translateX(-50%) translateY(var(--drag-offset)); width:min(calc(100% - 20px),460px); padding:0; border:1px solid var(--border-default); border-radius:var(--radius-modal); background:var(--surface-default); color:var(--text-primary); box-shadow:var(--shadow-modal); animation:drawer-in 180ms cubic-bezier(.22,1,.36,1); }
  .picker-content { display:grid; gap:var(--space-3); padding:var(--space-4); }
  .picker-handle { display:grid; place-items:center; min-height:20px; margin:-8px -8px 0; cursor:ns-resize; touch-action:none; }
  .picker-handle span { width:36px; height:4px; border-radius:99px; background:var(--border-strong); }
  .picker-header { display:grid; grid-template-columns:38px minmax(0,1fr) 38px; align-items:center; gap:var(--space-1); }
  .date-picker h2 { margin:0; font-size:17px; }
  .month-button { display:grid; place-items:center; width:38px; height:38px; border-radius:var(--radius-control); color:var(--text-secondary); cursor:pointer; }
  .month-button:active,.month-button:focus-visible { background:var(--surface-raised); color:var(--text-primary); }
  .calendar-weekdays,.calendar-days { display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:3px; }
  .calendar-weekdays span { display:grid; place-items:center; min-height:26px; color:var(--text-tertiary); font-size:11px; font-weight:700; }
  .calendar-days button { display:grid; place-items:center; aspect-ratio:1; min-height:36px; border-radius:var(--radius-control); color:var(--text-primary); cursor:pointer; font-size:13px; }
  .calendar-days button:active,.calendar-days button:focus-visible { background:var(--surface-raised); outline:2px solid var(--status-info); outline-offset:-2px; }
  .calendar-days button.outside-month { color:var(--text-tertiary); opacity:.56; }
  .calendar-days button.today { box-shadow:inset 0 0 0 1px var(--action-primary); }
  .calendar-days button.selected { background:var(--action-primary); color:var(--text-on-accent); font-weight:700; box-shadow:none; opacity:1; }
  .picker-actions { display:flex; justify-content:flex-start; gap:var(--space-2); }
  .picker-actions button { min-height:var(--control-min); padding:8px 12px; border-radius:var(--radius-control); cursor:pointer; font:inherit; }
  .picker-secondary { border:1px solid var(--border-default); background:var(--surface-raised); color:var(--text-secondary); }
  @keyframes drawer-in { from { transform:translateX(-50%) translateY(100%); } to { transform:translateX(-50%) translateY(0); } }
</style>
