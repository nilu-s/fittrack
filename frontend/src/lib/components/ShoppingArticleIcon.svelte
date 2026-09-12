<script lang="ts">
  import { resolveShoppingIcon } from '$lib/shopping-icons';
  const emptyIcon = { key: '', category: 'other' as const };
  export let iconKey = '';
  export let size = 44;
  export let label: string | undefined = undefined;
  $: icon = resolveShoppingIcon(iconKey) ?? emptyIcon;
  $: category = icon.category;
</script>

<svg class={`article-icon article-icon--${category}`} width={size} height={size} viewBox="0 0 64 64" role={label ? 'img' : undefined} aria-hidden={label ? undefined : 'true'} aria-label={label}>
  {#if label}<title>{label}</title>{/if}
  {#if icon.key === 'apple'}<path class="main" d="M32 55C17 55 12 43 15 30c2-10 9-15 17-12 8-3 15 2 17 12 3 13-2 25-17 25Z"/><path class="leaf" d="M32 19c2-9 10-12 16-10-2 7-8 11-16 10Z"/><path class="detail" d="M32 20c-1-5 1-9 5-13"/>
  {:else if icon.key === 'orange'}<circle class="main" cx="32" cy="35" r="18"/><path class="leaf" d="M31 17c1-7 7-11 13-9-2 6-6 9-13 9Z"/><path class="detail" d="M22 35h20m-10-10v20"/>
  {:else if icon.key === 'strawberry'}<path class="main" d="M18 25c8-5 20-5 28 0 0 15-6 27-14 27S18 40 18 25Z"/><path class="leaf" d="m32 25-8-9 8 3 8-3Z"/><path class="detail" d="m25 33 1 1m12-1 1 1m-8 8 1 1"/>
  {:else if icon.key === 'banana'}<path class="main" d="M15 16c5 20 16 29 34 29-5 8-14 11-23 7C15 47 10 35 11 22Z"/><path class="detail" d="M15 16c-2-3 1-7 5-5M49 45c4 0 6 4 2 6"/>
  {:else if icon.key === 'avocado'}<path class="main" d="M32 11c13 8 19 19 16 30-2 9-8 14-16 14s-14-5-16-14c-3-11 3-22 16-30Z"/><circle class="accent" cx="32" cy="38" r="7"/>
  {:else if icon.key === 'carrot'}<path class="main" d="M20 21c12 2 20 10 23 19-5 9-17 13-27 11-3-10-1-22 4-30Z"/><path class="leaf" d="M23 22 18 11m9 10 4-12m1 14 10-7"/><path class="detail" d="m23 34 14 5m-17 3 10 4"/>
  {:else if icon.key === 'pepper'}<path class="main" d="M25 20c-2-7 2-12 8-12 4 0 7 3 7 7-3-1-5 0-6 3 10-1 15 7 13 18-2 12-8 18-15 18S17 48 17 36c0-10 3-17 8-18Z"/><path class="detail" d="M32 18c0 5 2 8 6 10"/>
  {:else if icon.key === 'cucumber'}<path class="main" d="M17 45c0-15 10-27 24-27 5 0 8 3 8 8 0 15-10 28-24 28-5 0-8-3-8-9Z"/><path class="detail" d="m25 39 1 1m8-10 1 1m2 12 1 1"/>
  {:else if icon.key === 'onion'}<path class="main" d="M32 17c11 8 16 17 14 27-1 8-6 12-14 12s-13-4-14-12c-2-10 3-19 14-27Z"/><path class="leaf" d="M32 17V8m0 9-7-6m7 6 7-6"/><path class="detail" d="M32 24v25"/>
  {:else if icon.key === 'tomato'}<path class="main" d="M13 36c0-13 8-22 19-22s19 9 19 22-8 19-19 19-19-6-19-19Z"/><path class="leaf" d="m32 17-9-7 3 9-8 3 10 1 4 7 3-7 10-1-8-3 3-9Z"/><path class="detail" d="M24 32c-3 4-3 8-1 11"/>
  {:else if icon.key === 'salad'}<path class="main" d="M14 50c1-20 10-33 18-33 8 0 17 13 18 33Z"/><path class="leaf" d="M32 49V14m0 21L18 24m14 11 14-11"/>
  {:else if icon.key === 'potato'}<path class="main" d="M14 37c0-12 7-21 18-21 12 0 19 8 19 19 0 12-9 19-20 19-10 0-17-6-17-17Z"/><circle class="detail-fill" cx="25" cy="30" r="2"/><circle class="detail-fill" cx="39" cy="40" r="2"/>
  {:else if icon.key === 'lemon'}<path class="main" d="M18 38c0-14 9-24 20-24 7 0 12 6 12 14 0 13-11 23-24 23-5 0-8-5-8-13Z"/><path class="leaf" d="M24 19c-1-7 4-12 11-12-1 6-5 10-11 12Z"/><path class="detail" d="M27 28c6-4 11-3 15 2"/>
  {:else if icon.key === 'milk'}<path class="main" d="M20 15h22l-3 9v28H23V24Z"/><path class="accent" d="M20 15h22l-3 9H23Z"/><path class="detail" d="M24 34h14"/>
  {:else if icon.key === 'cheese'}<path class="main" d="m13 48 27-31 12 31Z"/><circle class="detail-fill" cx="37" cy="37" r="3"/><circle class="detail-fill" cx="29" cy="43" r="2"/>
  {:else if icon.key === 'yogurt'}<path class="main" d="M18 20h28l-4 32H22Z"/><path class="accent" d="M15 14h34v8H15Z"/><path class="detail" d="M26 34h12"/>
  {:else if icon.key === 'egg'}<path class="main" d="M32 12c9 9 15 19 15 29 0 9-6 14-15 14s-15-5-15-14c0-10 6-20 15-29Z"/><path class="accent" d="M27 39c0-4 2-7 5-7s5 3 5 7-2 6-5 6-5-2-5-6Z"/>
  {:else if icon.key === 'bread'}<path class="main" d="M14 50V29c0-10 8-16 18-16 11 0 18 6 18 16v21Z"/><path class="detail" d="m23 25 5 5m8-5 5 5"/>
  {:else if icon.key === 'croissant'}<path class="main" d="M14 39c3-15 12-23 18-23s15 8 18 23c-5 7-11 10-18 10s-13-3-18-10Z"/><path class="accent" d="M19 31c7 2 19 2 26 0M24 22c3 8 3 15 1 22m15-22c-3 8-3 15-1 22"/>
  {:else if icon.key === 'pasta'}<path class="main" d="M15 20h34v28H15Z"/><path class="accent" d="M12 15h40v8H12Z"/><path class="detail" d="M23 31v10m9-10v10m9-10v10"/>
  {:else if icon.key === 'rice'}<path class="main" d="M15 34h34c-1 13-7 19-17 19s-16-6-17-19Z"/><path class="accent" d="M18 34c2-7 7-11 14-11s12 4 14 11Z"/><path class="detail" d="m24 28 2-8m6 7 1-9m6 10 2-7"/>
  {:else if icon.key === 'oil'}<path class="main" d="M24 18h16l-2 35H26Z"/><path class="accent" d="M27 10h10v10H27Z"/><path class="detail" d="M28 36h8"/>
  {:else if icon.key === 'canned'}<rect class="main" x="17" y="13" width="30" height="40" rx="4"/><path class="accent" d="M17 20h30v8H17Z"/><path class="detail" d="M24 39h16"/>
  {:else if icon.key === 'spices'}<path class="main" d="M20 25h24l-3 28H23Z"/><path class="accent" d="M23 13h18v12H23Z"/><path class="detail" d="m28 35 8 8m0-8-8 8"/>
  {:else if icon.key === 'coffee'}<path class="main" d="M17 24h27v21H17Z"/><path class="accent" d="M44 28h5c5 0 5 12 0 12h-5"/><path class="detail" d="M24 18c-3-4 3-6 0-10m9 10c-3-4 3-6 0-10"/>
  {:else if icon.key === 'water'}<path class="main" d="M23 12h18l4 40H19Z"/><path class="accent" d="M23 12h18v10H23Z"/><path class="detail" d="M23 38h18"/>
  {:else if icon.key === 'juice'}<path class="main" d="M19 15h26l-3 38H22Z"/><path class="accent" d="M23 9h10v8H23Z"/><path class="detail" d="M28 34c6 0 8 4 8 8h-12c0-4 2-8 4-8Z"/>
  {:else if icon.key === 'icecream'}<path class="main" d="M20 28c0-8 5-14 12-14s12 6 12 14Z"/><path class="accent" d="m26 28 6 27 6-27Z"/><path class="detail" d="M24 23h1m14 0h1"/>
  {:else if icon.key === 'cleaner'}<path class="main" d="M21 24h22l-2 29H23Z"/><path class="accent" d="M25 12h10v12h-10Z"/><path class="detail" d="M27 36h10"/>
  {:else if icon.key === 'toilet-paper'}<path class="main" d="M16 18h30v30H16Z"/><circle class="accent" cx="31" cy="33" r="7"/><circle class="detail-fill" cx="31" cy="33" r="2"/>
  {:else if icon.key === 'laundry'}<path class="main" d="M17 14h30v40H17Z"/><path class="accent" d="M17 14h30v10H17Z"/><circle class="detail" cx="32" cy="38" r="8"/>
  {:else if icon.key === 'pet'}<path class="main" d="M22 52c-7 0-10-5-7-10 2-4 7-4 10-1-2-6 0-13 7-13s9 7 7 13c3-3 8-3 10 1 3 5 0 10-7 10Z"/><ellipse class="accent" cx="22" cy="26" rx="5" ry="8" transform="rotate(-25 22 26)"/><ellipse class="accent" cx="42" cy="26" rx="5" ry="8" transform="rotate(25 42 26)"/>
  {:else if icon.key === 'mushroom'}<path class="main" d="M15 34c2-13 10-20 17-20s15 7 17 20Z"/><path class="detail" d="M25 34v16h14V34"/>
  {:else if icon.key === 'meat'}<path class="main" d="M20 19c9-8 25-3 27 9 2 11-9 22-19 19-12-3-15-19-8-28Z"/><circle class="detail" cx="33" cy="31" r="5"/>
  {:else if icon.key === 'chicken'}<path class="main" d="M18 31c0-10 7-17 16-17 10 0 16 7 16 16 0 9-7 17-17 17H22"/><path class="detail" d="M22 46c-8 1-10 7-5 9m5-9c-6-3-10 3-6 7"/>
  {:else if icon.key === 'fish'}<path class="main" d="M14 33c8-13 22-15 33-5l6-7v24l-6-7c-11 10-25 8-33-5Z"/><circle class="detail-fill" cx="25" cy="30" r="2"/>
  {:else if icon.key === 'cereal'}<path class="main" d="M15 34h34c-1 12-7 19-17 19s-16-7-17-19Z"/><path class="detail" d="M22 29c2-6 6-8 10-8s8 2 10 8m-18-4 2 2m9-4 2 2"/>
  {:else if icon.key === 'chocolate'}<rect class="main" x="17" y="15" width="30" height="34" rx="2"/><path class="detail" d="M32 15v34M17 26h30M17 38h30"/>
  {:else if icon.key === 'chips'}<path class="main" d="M21 14h22l4 38H17Z"/><path class="detail" d="M23 26h18m-13 9 8 6m-9 2 8-6"/>
  {:else if icon.key === 'cookies'}<circle class="main" cx="32" cy="33" r="18"/><circle class="detail-fill" cx="25" cy="27" r="2.5"/><circle class="detail-fill" cx="38" cy="31" r="2.5"/><circle class="detail-fill" cx="30" cy="40" r="2.5"/>
  {:else if icon.key === 'tea'}<path class="main" d="M17 25h27v20H17Z"/><path class="detail" d="M44 29h5c5 0 5 12 0 12h-5M31 25V12"/><path class="leaf" d="M31 18c5-4 8-3 10 1-4 3-7 3-10-1Z"/>
  {:else if icon.key === 'soda'}<path class="main" d="M23 14h18l-3 38H26Z"/><path class="detail" d="M23 23h18m-13 9h8"/>
  {:else if icon.key === 'beer'}<path class="main" d="M20 21h25v28H20Z"/><path class="detail" d="M45 27h5c5 0 5 14 0 14h-5M23 18c0-6 6-6 6 0m2 0c0-6 6-6 6 0m2 0c0-6 6-6 6 0"/>
  {:else if icon.key === 'wine'}<path class="main" d="M23 13h18c0 12-3 18-9 18s-9-6-9-18Z"/><path class="detail" d="M32 31v16m-9 5h18"/>
  {:else if icon.key === 'soap'}<path class="main" d="M17 31c6-8 24-8 30 0v17H17Z"/><path class="detail" d="M23 25c0-7 8-9 8-15m7 15c0-4 5-6 5-10"/>
  {:else if icon.key === 'toothpaste'}<path class="main" d="m17 42 28-15 5 10-28 15Z"/><path class="detail" d="m43 28 5-9 4 8"/>
  {:else if icon.key === 'shampoo'}<path class="main" d="M22 20h20l-2 33H24Z"/><path class="detail" d="M27 20v-8h11v8m-10 13h8"/>
  {:else if icon.key === 'paper-towels'}<path class="main" d="M18 22h28v25H18Z"/><ellipse class="detail" cx="32" cy="34" rx="7" ry="12"/><path class="detail" d="M18 22 27 13h19"/>
  {:else if icon.key === 'batteries'}<rect class="main" x="18" y="20" width="28" height="26" rx="3"/><path class="detail" d="M27 20v-5h10v5m-10 13h10m-5-5v10"/>
  {:else if icon.key === 'flowers'}<circle class="main" cx="32" cy="28" r="6"/><path class="main" d="M32 22c-8-12-18-1-10 6-12 4-4 16 3 8 3 12 15 4 8-3 12 2 13-11 1-11-8-7-8 0Z"/><path class="detail" d="M32 34v20m0 10-8-7m8 2 8-7"/>
  {/if}
</svg>

<style>
  .article-icon { display:block; overflow:visible; color:var(--text-on-accent); }
  .main,.accent,.detail,.leaf { fill:none; stroke:currentColor; stroke-width:4; stroke-linecap:round; stroke-linejoin:round; }
  .detail { stroke-width:3.25; }.detail-fill { fill:currentColor; }
</style>
