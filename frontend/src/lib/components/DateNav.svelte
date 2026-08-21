<script lang="ts">
  import { currentDate } from '$lib/stores';
  import Icon from '$lib/components/Icon.svelte';

  const months = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'];
  const daysFull = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'];

  $: dateLabel = formatDateLabel($currentDate);
  $: isToday = $currentDate === todayStr();
  $: dow = daysFull[new Date($currentDate + 'T00:00:00').getDay()];
  let touchStartX = 0;
  let touchStartY = 0;
  let suppressClickUntil = 0;

  function todayStr(): string { const d = new Date(); return formatDate(d); }
  function formatDate(d: Date): string { const y = d.getFullYear(); const m = String(d.getMonth() + 1).padStart(2, '0'); const day = String(d.getDate()).padStart(2, '0'); return `${y}-${m}-${day}`; }
  function formatDateLabel(dateStr: string): string { const d = new Date(dateStr + 'T00:00:00'); return `${d.getDate()}. ${months[d.getMonth()]}`; }
  function changeDate(delta: number) { const d = new Date($currentDate + 'T00:00:00'); d.setDate(d.getDate() + delta); currentDate.set(formatDate(d)); }
  function goToday() { currentDate.set(todayStr()); }
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
  function guardLink(e: MouseEvent) { if (Date.now() < suppressClickUntil) { e.preventDefault(); e.stopPropagation(); } }
</script>

<nav class="dnav" aria-label="Tagesnavigation" ontouchstart={onTouchStart} ontouchend={onTouchEnd}>
  <button class="dnav-btn" onclick={(e) => guarded(() => changeDate(-1), e)} aria-label="Vorheriger Tag"><Icon name="chevron-left" size={20} /></button>
  <button class="dnav-mid" onclick={(e) => guarded(goToday, e)} aria-label="Heute">
    <span class="dnav-date">{dow}, {dateLabel}</span>
    <span class="dnav-today">{isToday ? 'Heute' : 'Zu heute'}</span>
  </button>
  <a class="dnav-btn" href="/week" onclick={guardLink} aria-label="Wochenübersicht"><Icon name="calendar" size={18} /></a>
  <button class="dnav-btn" onclick={(e) => guarded(() => changeDate(1), e)} aria-label="Nächster Tag"><Icon name="chevron-right" size={20} /></button>
</nav>

<style>
  .dnav { position: fixed; z-index: 40; left: 50%; bottom: 8px; transform: translateX(-50%); width: min(calc(100% - 20px), 460px); min-height: 52px; display: grid; grid-template-columns: 44px minmax(0, 1fr) 44px 44px; align-items: center; gap: 2px; padding: 4px; padding-bottom: max(4px, env(safe-area-inset-bottom, 0px)); background: #1a1b1e; border: 1px solid var(--border-2); border-radius: 14px; box-shadow: 0 8px 28px rgba(0,0,0,.42); touch-action: pan-y; }
  .dnav-btn { width: 44px; height: 44px; border-radius: 10px; background: transparent; border: 0; color: var(--text-dim); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: background .15s, color .15s; }
  .dnav-btn:active, .dnav-btn:focus-visible { background: var(--card-2); color: var(--text); }
  .dnav-mid { min-width: 0; height: 44px; display: flex; flex-direction: column; align-items: flex-start; justify-content: center; gap: 1px; background: transparent; cursor: pointer; padding: 4px 10px; border-radius: 10px; }
  .dnav-mid:active, .dnav-mid:focus-visible { background: var(--card-2); }
  .dnav-date { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; font-weight: 650; color: var(--text); }
  .dnav-today { font-size: 10px; line-height: 1.1; color: var(--green); font-weight: 600; }
  @media (min-width: 481px) { .dnav { bottom: 14px; } }
</style>