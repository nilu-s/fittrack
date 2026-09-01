import { writable } from 'svelte/store';
import { clearAccountData } from './db';

export const isAuthenticated = writable<boolean>(false);
export const authEmail = writable<string | null>(null);

const API_BASE =
  typeof window !== 'undefined' && window.location.hostname === 'localhost'
    ? 'http://localhost:8000/api'
    : '/api';

export async function checkAuth(): Promise<void> {
  try {
    const resp = await fetch(`${API_BASE}/auth/me`, {
      credentials: 'include',
    });
    if (!resp.ok) {
      await clearAccountData();
      window.localStorage.removeItem('app_account_id');
      isAuthenticated.set(false);
      authEmail.set(null);
      return;
    }
    const data = await resp.json();
    if (data.authenticated) {
      const previousAccountId = window.localStorage.getItem('app_account_id');
      if (previousAccountId && previousAccountId !== data.id) {
        await clearAccountData();
      }
      window.localStorage.setItem('app_account_id', data.id);
      isAuthenticated.set(true);
      authEmail.set(data.email);
    } else {
      isAuthenticated.set(false);
      authEmail.set(null);
    }
  } catch {
    // Network/SSL error — assume not authenticated, show login
    await clearAccountData();
    window.localStorage.removeItem('app_account_id');
    isAuthenticated.set(false);
    authEmail.set(null);
  }
}

export async function logout(): Promise<void> {
  try {
    await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    });
  } catch {
    // ignore network errors
  }
  isAuthenticated.set(false);
  authEmail.set(null);
  await clearAccountData();
  window.localStorage.removeItem('app_account_id');
}

export async function disconnectGoogle(): Promise<void> {
  try {
    await fetch(`${API_BASE}/auth/google/disconnect`, {
      method: 'POST',
      credentials: 'include',
    });
  } catch {
    // ignore
  }
}

export function googleLogin(): void {
  window.location.href = `${API_BASE}/auth/google/login`;
}
