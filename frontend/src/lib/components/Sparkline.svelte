<script lang="ts">
  export let data: number[] = [];
  export let color: string = '#666';
  export let height: number = 30;
  export let width: number = 60;
  export let fill: boolean = false;

  $: points = buildPath(data);

  function buildPath(values: number[]): { path: string; area: string; min: number; max: number } {
    if (!values || values.length === 0) {
      return { path: '', area: '', min: 0, max: 0 };
    }

    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const stepX = values.length > 1 ? width / (values.length - 1) : width;

    const coords = values.map((v, i) => {
      const x = i * stepX;
      const y = height - ((v - min) / range) * (height - 4) - 2;
      return { x, y };
    });

    const path = coords.map((c, i) => `${i === 0 ? 'M' : 'L'}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(' ');
    const area = `${path} L${width},${height} L0,${height} Z`;

    return { path, area, min, max };
  }
</script>

{#if data.length > 0}
  <svg class="sparkline" viewBox="0 0 {width} {height}" width={width} height={height} preserveAspectRatio="none">
    {#if fill}
      <path d={points.area} fill={color} fill-opacity="0.15" />
    {/if}
    <path d={points.path} fill="none" stroke={color} stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
    <circle cx={width} cy={height - ((data[data.length - 1] - points.min) / (points.max - points.min || 1)) * (height - 4) - 2} r="2" fill={color} />
  </svg>
{:else}
  <div class="sparkline-empty" style="width:{width}px;height:{height}px"></div>
{/if}

<style>
  .sparkline {
    display: block;
    overflow: visible;
  }

  .sparkline-empty {
    display: inline-block;
  }
</style>