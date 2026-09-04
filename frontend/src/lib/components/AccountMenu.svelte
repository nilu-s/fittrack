<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { authDisplayName, authEmail } from '$lib/auth';
  import Icon from '$lib/components/Icon.svelte';

  let root: HTMLElement;
  let trigger: HTMLButtonElement;
  let firstMenuItem: HTMLAnchorElement;
  let open = false;

  $: accountName = $authDisplayName?.trim() || $authEmail?.split('@')[0] || 'Konto';
  $: initials = accountName
    .split(/[\s._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toLocaleUpperCase('de-DE'))
    .join('') || 'K';

  async function toggle() {
    open = !open;
    if (open) {
      await tick();
      firstMenuItem?.focus();
    }
  }

  function close(restoreFocus = false) {
    if (!open) return;
    open = false;
    if (restoreFocus) trigger?.focus();
  }

  function onKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      event.preventDefault();
      close(true);
    }
  }

  onMount(() => {
    const onPointerDown = (event: PointerEvent) => {
      if (open && root && !root.contains(event.target as Node)) close();
    };
    document.addEventListener('pointerdown', onPointerDown);
    return () => document.removeEventListener('pointerdown', onPointerDown);
  });
</script>

<div class="account-menu" bind:this={root}>
  <button
    bind:this={trigger}
    class="account-trigger"
    type="button"
    aria-label={`Kontomenü für ${accountName}`}
    aria-expanded={open}
    aria-controls="account-navigation"
    onclick={toggle}
  >
    <span aria-hidden="true">{initials}</span>
  </button>

  {#if open}
    <nav id="account-navigation" class="account-popover" aria-label="Konto">
      <div class="account-identity">
        <strong>{accountName}</strong>
        {#if $authEmail}<span>{$authEmail}</span>{/if}
      </div>
      <a bind:this={firstMenuItem} href="/contacts" onkeydown={onKeydown} onclick={() => close()}>
        <Icon name="contacts" size={18} />
        Kontakte
      </a>
      <a href="/settings" onkeydown={onKeydown} onclick={() => close()}>
        <Icon name="settings" size={18} />
        Einstellungen
      </a>
    </nav>
  {/if}
</div>

<style>
  .account-menu { position:absolute; z-index:20; top:calc(12px + env(safe-area-inset-top, 0px)); right:16px; }
  .account-trigger { display:grid; place-items:center; width:40px; height:40px; border:1px solid var(--border-strong); border-radius:var(--radius-full); background:var(--action-primary); color:var(--text-on-accent); font-size:13px; font-weight:750; letter-spacing:.02em; cursor:pointer; }
  .account-trigger:active { background:color-mix(in srgb, var(--action-primary) 82%, black); }
  .account-popover { position:absolute; top:calc(100% + 8px); right:0; display:grid; min-width:220px; overflow:hidden; border:1px solid var(--border-default); border-radius:var(--radius-surface); background:var(--surface-default); }
  .account-identity { display:grid; gap:2px; padding:12px 14px; border-bottom:1px solid var(--border-subtle); }
  .account-identity strong { overflow:hidden; color:var(--text-primary); font-size:13px; text-overflow:ellipsis; white-space:nowrap; }
  .account-identity span { overflow:hidden; color:var(--text-tertiary); font-size:11px; text-overflow:ellipsis; white-space:nowrap; }
  a { display:flex; align-items:center; gap:10px; min-height:44px; padding:0 14px; color:var(--text-primary); font-size:14px; text-decoration:none; }
  a + a { border-top:1px solid var(--border-subtle); }
  a:active { background:var(--surface-raised); }
  a :global(svg) { color:var(--text-secondary); }
</style>
