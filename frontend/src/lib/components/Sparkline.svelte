<script lang="ts">
  export let data: number[] = [];
  export let color: string = 'var(--blue)';
  export let height: number = 32;
  export let width: number = 80;
  export let fill: boolean = false;

  $: points = buildPath(data);

  function buildPath(values: number[]) {
    if (!values || values.length === 0) return { path: '', area: '', min: 0, max: 0 };
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const stepX = values.length > 1 ? width / (values.length - 1) : width;
    const padY = 4;
    const coords = values.map((v, i) => ({
      x: i * stepX,
      y: height - ((v - min) / range) * (height - padY * 2) - padY
    }));
    let path = `M${coords[0].x.toFixed(1)},${coords[0].y.toFixed(1)}`;
    for (let i = 1; i < coords.length; i++) {
      const prev = coords[i - 1];
      const curr = coords[i];
      const midX = (prev.x + curr.x) / 2;
      const midY = (prev.y + curr.y) / 2;
      path += ` Q${prev.x.toFixed(1)},${prev.y.toFixed(1)} ${midX.toFixed(1)},${midY.toFixed(1)}`;
    }
    if (coords.length > 1) {
      const last = coords[coords.length - 1];
      path += ` L${last.x.toFixed(1)},${last.y.toFixed(1)}`;
    }
    const area = `${path} L${width},${height} L0,${height} Z`;
    return { path, area, min, max };
  }

  $: lastY = data.length > 0
    ? height - ((data[data.length - 1] - points.min) / (points.max - points.min || 1)) * (height - 8) - 4
    : 0;
</script>

{#if data.length > 0}
  <svg viewBox="0 0 {width} {height}" width={width} height={height} preserveAspectRatio="none" style="display:block;overflow:visible">
    {#if fill}
      <path d={points.area} fill={color} fill-opacity="0.1" />
    {/if}
    <path d={points.path} fill="none" stroke={color} stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
    <circle cx={width} cy={lastY} r="2.5" fill={color} />
  </svg>
{:else}
  <div style="width:{width}px;height:{height}px;display:inline-block"></div>
{/if}