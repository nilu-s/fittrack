import { writable } from 'svelte/store';

export const isAuthenticated = writable<boolean>(false);

const PIN_KEY = 'fittrack-pin-set';
const AUTH_KEY = 'fittrack-authed';

function hashPin(pin: string): string {
  return btoa(`fittrack:${pin}`);
}

export function isPinSet(): boolean {
  if (typeof localStorage === 'undefined') return false;
  return localStorage.getItem(PIN_KEY) !== null;
}

export function setPin(pin: string): void {
  if (typeof localStorage === 'undefined') return;
  localStorage.setItem(PIN_KEY, hashPin(pin));
  sessionStorage.setItem(AUTH_KEY, 'true');
  isAuthenticated.set(true);
}

export function verifyPin(pin: string): boolean {
  if (typeof localStorage === 'undefined') return false;
  const stored = localStorage.getItem(PIN_KEY);
  if (!stored) return false;
  return stored === hashPin(pin);
}

export function login(pin: string): boolean {
  if (verifyPin(pin)) {
    if (typeof sessionStorage !== 'undefined') {
      sessionStorage.setItem(AUTH_KEY, 'true');
    }
    isAuthenticated.set(true);
    return true;
  }
  return false;
}

export function logout(): void {
  if (typeof sessionStorage !== 'undefined') {
    sessionStorage.removeItem(AUTH_KEY);
  }
  isAuthenticated.set(false);
}

export function changePin(oldPin: string, newPin: string): boolean {
  if (!verifyPin(oldPin)) return false;
  setPin(newPin);
  return true;
}

export function initAuth(): void {
  if (typeof localStorage === 'undefined' || typeof sessionStorage === 'undefined') return;
  const pinSet = localStorage.getItem(PIN_KEY) !== null;
  const authed = sessionStorage.getItem(AUTH_KEY) === 'true';
  isAuthenticated.set(!pinSet || authed);
}