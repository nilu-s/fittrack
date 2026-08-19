<script lang="ts">
  import { currentDate } from '$lib/stores';

  let touchStartX = 0;
  let touchStartY = 0;
  let touchEndX = 0;
  let touchEndY = 0;

  const days = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'];
  const months = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'];
  const daysFull = ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag'];

  $: dateLabel = formatDateLabel($currentDate);
  $: isToday = $currentDate === todayStr();

  function todayStr(): string {
    const d = new Date();
    return formatDate(d);
  }

  function formatDate(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  function formatDateLabel(dateStr: string): string {
    const d = new Date(dateStr + 'T00:00:00');
    return `${daysFull[d.getDay()]}, ${d.getDate()}. ${months[d.getMonth()]}`;
  }

  function changeDate(delta: number) {
    const d = new Date($currentDate + 'T00:00:00');
    d.setDate(d.getDate() + delta);
    currentDate.set(formatDate(d));
  }

  function goToday() {
    currentDate.set(todayStr());
  }

  function onTouchStart(e: TouchEvent) {
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
  }

  function onTouchEnd(e: TouchEvent) {
    touchEndX = e.changedTouches[0].clientX;
    touchEndY = e.changedTouches[0].clientY;
    const dx = touchEndX - touchStartX;
    const dy = touchEndY - touchStartY;
    // Horizontal swipe (more horizontal than vertical)
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 2) {
      if (dx > 0) {
        changeDate(-1); // swipe right = previous day
      } else {
        changeDate(1); // swipe left = next day
      }
    }
  }
</script>

<div
  class="date-nav"
  role="application"
  ontouchstart={onTouchStart}
  ontouchend={onTouchEnd}
>
  <button class="nav-btn" onclick={() => changeDate(-1)} aria-label="Vorheriger Tag">
    ‹
  </button>

  <button class="date-display" onclick={goToday} aria-label="Heute">
    <span class="date-label">{dateLabel}</span>
    {#if !isToday}
      <span class="today-link">Heute</span>
    {/if}
  </button>

  <button class="nav-btn" onclick={() => changeDate(1)} aria-label="Nächster Tag">
    ›
  </button>
</div>

<style>
  .date-nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 0.25rem;
    gap: 0.5rem;
  }

  .nav-btn {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    color: var(--text-primary);
    font-size: 1.25rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.15s;
    flex-shrink: 0;
  }

  .nav-btn:active {
    background: #444;
  }

  .date-display {
    flex: 1;
    text-align: center;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
  }

  .date-label {
    font-size: 0.9375rem;
    font-weight: 600;
  }

  .today-link {
    font-size: 0.6875rem;
    color: var(--accent-done);
  }
</style>