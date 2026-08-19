<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { isPinSet, setPin, login, initAuth } from '$lib/auth';

  let mode: 'login' | 'setup' = 'login';
  let pin = '';
  let pinConfirm = '';
  let error = '';
  let shake = false;

  onMount(() => {
    initAuth();
    mode = isPinSet() ? 'login' : 'setup';
  });

  function handleLogin() {
    if (pin.length < 4) {
      error = 'PIN muss mindestens 4 Ziffern haben';
      triggerShake();
      return;
    }
    if (login(pin)) {
      goto('/');
    } else {
      error = 'Falsche PIN';
      triggerShake();
      pin = '';
    }
  }

  function handleSetup() {
    if (pin.length < 4 || pin.length > 6) {
      error = 'PIN muss 4-6 Ziffern haben';
      triggerShake();
      return;
    }
    if (pin !== pinConfirm) {
      error = 'PINs stimmen nicht überein';
      triggerShake();
      return;
    }
    setPin(pin);
    goto('/');
  }

  function triggerShake() {
    shake = false;
    requestAnimationFrame(() => {
      shake = true;
    });
    setTimeout(() => (shake = false), 500);
  }

  function handleKey(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (mode === 'login') handleLogin();
      else handleSetup();
    }
  }

  function pressDigit(d: string) {
    if (pin.length < 6) pin = pin + d;
  }

  function pressDelete() {
    pin = pin.slice(0, -1);
  }

  $: error = '';
</script>

<svelte:head>
  <title>FitTrack - PIN</title>
</svelte:head>

<div class="login-page" class:shake>
  <div class="login-card">
    <div class="logo">💪 FitTrack</div>

    {#if mode === 'setup'}
      <h1>PIN festlegen</h1>
      <p class="subtitle">Schütze deine Daten mit einer PIN</p>
    {:else}
      <h1>PIN eingeben</h1>
      <p class="subtitle">Entsperre FitTrack</p>
    {/if}

    <div class="pin-dots">
      {#each Array(6) as _, i}
        <span class="pin-dot" class:filled={i < pin.length}></span>
      {/each}
    </div>

    {#if mode === 'setup'}
      <input
        class="hidden-pin-input"
        type="password"
        inputmode="numeric"
        bind:value={pin}
        onkeydown={handleKey}
        placeholder="PIN (4-6 Ziffern)"
        maxlength={6}
      />
      <input
        class="hidden-pin-input"
        type="password"
        inputmode="numeric"
        bind:value={pinConfirm}
        onkeydown={handleKey}
        placeholder="PIN bestätigen"
        maxlength={6}
      />
    {:else}
      <input
        class="hidden-pin-input"
        type="password"
        inputmode="numeric"
        bind:value={pin}
        onkeydown={handleKey}
        placeholder="PIN"
        maxlength={6}
      />
    {/if}

    {#if error}
      <div class="error-msg">{error}</div>
    {/if}

    <div class="keypad">
      {#each ['1', '2', '3', '4', '5', '6', '7', '8', '9'] as d}
        <button class="key" onclick={() => pressDigit(d)}>{d}</button>
      {/each}
      <div class="key-spacer"></div>
      <button class="key" onclick={() => pressDigit('0')}>0</button>
      <button class="key key-delete" onclick={pressDelete}>⌫</button>
    </div>

    <button class="submit-btn" onclick={mode === 'login' ? handleLogin : handleSetup}>
      {mode === 'login' ? 'Entsperren' : 'PIN speichern'}
    </button>
  </div>
</div>

<style>
  .login-page {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    min-height: 100dvh;
    padding: 1rem;
  }

  .login-card {
    width: 100%;
    max-width: 320px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
  }

  .logo {
    font-size: 1.75rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
  }

  h1 {
    font-size: 1.1rem;
    font-weight: 600;
    margin: 0;
  }

  .subtitle {
    font-size: 0.8125rem;
    color: var(--text-secondary);
    margin: 0;
  }

  .pin-dots {
    display: flex;
    gap: 10px;
    margin: 1rem 0 0.5rem;
  }

  .pin-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 2px solid #555;
    transition: all 0.15s;
  }

  .pin-dot.filled {
    background: var(--accent-done);
    border-color: var(--accent-done);
  }

  .hidden-pin-input {
    width: 100%;
    padding: 8px 12px;
    border-radius: 8px;
    background: #1a1a1a;
    border: 1px solid var(--card-border);
    color: var(--text-primary);
    font-size: 0.875rem;
    text-align: center;
    letter-spacing: 0.3em;
  }

  .keypad {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    width: 100%;
    margin-top: 0.5rem;
  }

  .key {
    aspect-ratio: 1;
    border-radius: 12px;
    background: #1f1f1f;
    border: 1px solid var(--card-border);
    color: var(--text-primary);
    font-size: 1.25rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.1s;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .key:active {
    transform: scale(0.95);
    background: #2a2a2a;
  }

  .key-delete {
    background: transparent;
    border: none;
  }

  .key-spacer {
  }

  .submit-btn {
    width: 100%;
    padding: 10px;
    border-radius: 10px;
    background: var(--accent-done);
    color: #0f0f0f;
    font-size: 0.9375rem;
    font-weight: 600;
    border: none;
    cursor: pointer;
    margin-top: 0.5rem;
    transition: opacity 0.15s;
  }

  .submit-btn:active {
    opacity: 0.85;
  }

  .error-msg {
    color: #ef4444;
    font-size: 0.8125rem;
    text-align: center;
  }

  .shake {
    animation: shake 0.4s;
  }

  @keyframes shake {
    0%, 100% { transform: translateX(0); }
    20% { transform: translateX(-8px); }
    40% { transform: translateX(8px); }
    60% { transform: translateX(-6px); }
    80% { transform: translateX(6px); }
  }
</style>