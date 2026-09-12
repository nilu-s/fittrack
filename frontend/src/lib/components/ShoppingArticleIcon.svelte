<script lang="ts">
  import { resolveShoppingIcon } from '$lib/shopping-icons';
  export let iconKey = 'shopping';
  export let size = 44;
  export let label: string | undefined = undefined;
  $: icon = resolveShoppingIcon(iconKey);
  $: category = icon.category;
</script>

<svg class={`article-icon article-icon--${category}`} width={size} height={size} viewBox="0 0 64 64" role={label ? 'img' : undefined} aria-hidden={label ? undefined : 'true'} aria-label={label}>
  {#if label}<title>{label}</title>{/if}
  {#if icon.key === 'apple'}<path class="main" d="M32 55C17 55 12 43 15 30c2-10 9-15 17-12 8-3 15 2 17 12 3 13-2 25-17 25Z"/><path class="leaf" d="M32 19c2-9 10-12 16-10-2 7-8 11-16 10Z"/><path class="detail" d="M32 20c-1-5 1-9 5-13"/>
  {:else if icon.key === 'banana'}<path class="main" d="M15 16c5 20 16 29 34 29-5 8-14 11-23 7C15 47 10 35 11 22Z"/><path class="detail" d="M15 16c-2-3 1-7 5-5M49 45c4 0 6 4 2 6"/>
  {:else if icon.key === 'carrot'}<path class="main" d="M20 21c12 2 20 10 23 19-5 9-17 13-27 11-3-10-1-22 4-30Z"/><path class="leaf" d="M23 22 18 11m9 10 4-12m1 14 10-7"/><path class="detail" d="m23 34 14 5m-17 3 10 4"/>
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
  {:else}<path class="main" d="M16 23h32l-2 28H18Z"/><path class="accent" d="M24 23v-5a8 8 0 0 1 16 0v5"/><path class="detail" d="M24 35h16"/>{/if}
</svg>

<style>
  .article-icon { display:block; overflow:visible; --main:var(--data-shopping-other); --accent:color-mix(in srgb,var(--data-shopping-other) 56%,white); --detail:color-mix(in srgb,var(--icon-outline) 72%,var(--data-shopping-other)); }
  .article-icon--produce { --main:var(--data-shopping-produce); --accent:color-mix(in srgb,var(--data-shopping-produce) 55%,#d6e29e); }
  .article-icon--dairy { --main:var(--data-shopping-dairy); --accent:color-mix(in srgb,var(--data-shopping-dairy) 48%,#e4edf0); }
  .article-icon--bakery { --main:var(--data-shopping-bakery); --accent:color-mix(in srgb,var(--data-shopping-bakery) 55%,#efd59c); }
  .article-icon--pantry { --main:var(--data-shopping-pantry); --accent:color-mix(in srgb,var(--data-shopping-pantry) 55%,#f0c88f); }
  .article-icon--frozen { --main:var(--data-shopping-frozen); --accent:color-mix(in srgb,var(--data-shopping-frozen) 48%,#d8eff2); }
  .article-icon--beverage { --main:var(--data-shopping-beverage); --accent:color-mix(in srgb,var(--data-shopping-beverage) 46%,#d6e2b3); }
  .article-icon--household { --main:var(--data-shopping-household); --accent:color-mix(in srgb,var(--data-shopping-household) 48%,#e4d9ef); }
  .main,.accent,.detail,.leaf { stroke:var(--icon-outline); stroke-width:3.5; stroke-linecap:round; stroke-linejoin:round; }
  .main { fill:var(--main); }.accent,.leaf { fill:var(--accent); }.detail { fill:none; stroke:var(--detail); stroke-width:3; }.detail-fill { fill:var(--detail); }
</style>
