<script lang="ts">
  import { onDestroy } from 'svelte';

  export let pictogramUrl = '';
  export let iconKey = '';
  export let size = 44;
  export let label: string | undefined = undefined;

  let source = '';
  let observedUrl = '';
  let retryTimer: ReturnType<typeof setTimeout> | undefined;
  let objectUrl = '';

  $: initials = (label ?? '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => Array.from(word)[0]?.toLocaleUpperCase())
    .join('') || '_';

  async function load() {
    if (!pictogramUrl) return;
    try {
      const response = await fetch(`${pictogramUrl}${pictogramUrl.includes('?') ? '&' : '?'}refresh=${Date.now()}`, { cache: 'no-store' });
      if (!response.ok) throw new Error('pictogram unavailable');
      const nextUrl = URL.createObjectURL(await response.blob());
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      objectUrl = nextUrl;
      source = nextUrl;
      if (response.headers.get('X-Pictogram-State') !== 'available') {
        retryTimer = setTimeout(load, 10_000);
      }
    } catch {
      retryTimer = setTimeout(load, 10_000);
    }
  }

  $: if (pictogramUrl !== observedUrl) {
    observedUrl = pictogramUrl;
    if (retryTimer) clearTimeout(retryTimer);
    source = '';
    if (pictogramUrl) void load();
  }

  onDestroy(() => {
    if (retryTimer) clearTimeout(retryTimer);
    if (objectUrl) URL.revokeObjectURL(objectUrl);
  });
</script>

{#if source}
  <img class="article-icon" src={source} width={size} height={size} alt={label ?? ''} data-icon-key={iconKey} />
{:else}
  <span class="initials" aria-hidden="true" style={`--size:${size}px`}>{initials}</span>
{/if}

<style>
  .article-icon { display:block; width:var(--size, 44px); height:var(--size, 44px); color:var(--text-on-accent); }
  .initials { display:grid; place-items:center; width:var(--size); height:var(--size); color:var(--text-on-accent); font-size:calc(var(--size) * .42); font-weight:800; line-height:1; }
</style>
