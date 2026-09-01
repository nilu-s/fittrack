<script lang="ts">
  export let strategy: string | undefined = 'double_progression';
  export let repsLow: number | string | null | undefined = 8;
  export let repsHigh: number | string | null | undefined = 12;
  export let increment: number | string | null | undefined = 2.5;
  export let targetRir: number | string | null | undefined = 2;

  $: low = Number(repsLow) || 1;
  $: high = Math.max(low, Number(repsHigh) || low);
  $: step = Number(increment) || 0;
  $: rir = Math.max(0, Number(targetRir) || 0);
  $: stepLabel = step.toLocaleString('de-DE', { maximumFractionDigits: 2 });
  $: details = strategy === 'weight_increase'
    ? {
        title: 'Gewicht steigern',
        rule: `Erreichst du ${high} Wiederholungen mit RIR ${rir} oder weniger, steigt das Gewicht um ${stepLabel} kg.`,
        next: `Der Zielbereich bleibt bei ${low}–${high} Wiederholungen.`,
        use: 'Für Übungen mit stabiler Technik und klaren Gewichtsstufen.'
      }
    : strategy === 'reps_only'
      ? {
          title: 'Nur Wiederholungen',
          rule: `Das Gewicht bleibt gleich. Das Ziel steigt schrittweise von ${low} bis maximal ${high} Wiederholungen.`,
          next: `Bei ${high} Wiederholungen erfolgt keine automatische Gewichtserhöhung.`,
          use: 'Für Körpergewicht, Reha, Technikarbeit oder festen Widerstand.'
        }
      : {
          title: 'Wiederholungen, dann Gewicht',
          rule: `Steigere bei gleichem Gewicht schrittweise von ${low} bis ${high} Wiederholungen.`,
          next: `Bei ${high} Wiederholungen und RIR ${rir} oder weniger: +${stepLabel} kg, danach zurück auf ${low}.`,
          use: 'Empfohlener Standard für die meisten Gym-Übungen.'
        };
</script>

<div class="progression-help" aria-live="polite">
  <div class="help-top"><span class="help-icon">i</span><strong>{details.title}</strong></div>
  <div class="help-flow">
    <div><span>1</span><p>{details.rule}</p></div>
    <div><span>2</span><p>{details.next}</p></div>
  </div>
  <p class="help-use"><strong>Gut geeignet:</strong> {details.use}</p>
</div>

<style>
  .progression-help { grid-column: 1 / -1; padding: 11px; border: 1px solid var(--border-info); border-radius: 11px; background: var(--surface-info); }
  .help-top { display: flex; align-items: center; gap: 7px; margin-bottom: 9px; color: var(--status-info); }
  .help-top strong { font-size: 12px; }
  .help-icon { width: 18px; height: 18px; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; background: var(--surface-info); font-size: 11px; font-weight: 800; }
  .help-flow { display: flex; flex-direction: column; gap: 6px; }
  .help-flow > div { display: grid; grid-template-columns: 20px 1fr; align-items: start; gap: 6px; }
  .help-flow span { width: 18px; height: 18px; display: inline-flex; align-items: center; justify-content: center; border-radius: 6px; background: var(--surface-raised); color: var(--text-secondary); font-size: 9px; font-weight: 750; }
  p { margin: 0; color: var(--text-secondary); font-size: 10px; line-height: 1.45; }
  .help-use { margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border-subtle); color: var(--text-tertiary); }
  .help-use strong { color: var(--text-secondary); }
</style>
