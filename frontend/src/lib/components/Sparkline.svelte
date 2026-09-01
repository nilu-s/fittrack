<script lang="ts">
  import { buildTrendLine, trendSegmentPaths } from '$lib/trend-lines';
  import type { TrendPoint } from '$lib/types';

  export let points: TrendPoint[] = [];
  export let endDate: string;
  export let days: number = 7;
  export let color: string = 'var(--status-info)';
  export let height: number = 32;
  export let width: number = 80;

  $: line = buildTrendLine(points, endDate, days);
  $: chart = buildChart(line);
  $: xLabels = line.map((day) => ({
    date: day.date,
    label: new Date(`${day.date}T00:00`).toLocaleDateString('de-DE', { weekday: 'short' }).replace('.', ''),
  }));

  function buildChart(values: ReturnType<typeof buildTrendLine>) {
    if (!values.length) return null;
    const min = Math.min(...values.map((day) => day.value));
    const max = Math.max(...values.map((day) => day.value));
    const range = max - min || 1;
    const padY = 4;
    const coords = values.map((day, index) => ({
      x: values.length > 1 ? index * (width / (values.length - 1)) : width / 2,
      y: height - ((day.value - min) / range) * (height - padY * 2) - padY,
    }));
    return { coords, paths: trendSegmentPaths(values, coords) };
  }
</script>

{#if chart}
  <div class="sparkline">
    <svg viewBox="0 0 {width} {height}" width={width} height={height} preserveAspectRatio="none" role="img" aria-label="Verlauf: durchgezogen sind erfasste Werte, gestrichelt interpolierte Werte und grau gestrichelt die Baseline außerhalb der Messungen.">
      {#each chart.coords as point}<line x1={point.x} y1="2" x2={point.x} y2={height - 2} stroke="var(--border-subtle)" stroke-width="1" />{/each}
      {#if chart.paths.baseline}<path d={chart.paths.baseline} fill="none" stroke="var(--text-tertiary)" stroke-width="1.25" stroke-dasharray="3 3" stroke-linecap="round" />{/if}
      {#if chart.paths.interpolated}<path d={chart.paths.interpolated} fill="none" stroke={color} stroke-width="1.5" stroke-dasharray="3 3" stroke-linecap="round" />{/if}
      {#if chart.paths.actual}<path d={chart.paths.actual} fill="none" stroke={color} stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" />{/if}
      {#each line as day, index}
        {#if day.state === 'actual'}<circle cx={chart.coords[index].x} cy={chart.coords[index].y} r="2" fill={color}><title>{day.date}: {day.value}</title></circle>{/if}
      {/each}
    </svg>
    <div class="axis" style={`grid-template-columns:repeat(${xLabels.length},minmax(0,1fr))`} aria-hidden="true">{#each xLabels as label}<span title={label.date}>{label.label}</span>{/each}</div>
  </div>
{:else}
  <div style="width:{width}px;height:{height}px;display:inline-block"></div>
{/if}

<style>
  .sparkline { width:100%; min-width:0; }
  svg { display:block; width:100%; overflow:visible; }
  .axis { display:grid; margin-top:4px; color:var(--text-tertiary); font-size:10px; line-height:1; }
  .axis span { text-align:center; }
  .axis span:first-child { text-align:left; }
  .axis span:last-child { text-align:right; }
</style>
