import { clearTravel } from "./travel";
import { apiFetch, isNative, nativeBridge, nativeLogin } from "./native";
import { writable } from 'svelte/store';
import { clearAccountData } from './db';

export const isAuthenticated = writable<boolean>(false);
export const authEmail = writable<string | null>(null);
export const authDisplayName = writable<string | null>(null);
export const aliasRequired = writable<boolean>(false);

const API_BASE =
  !isNative() && typeof window !== 'undefined' && window.location.hostname === 'localhost'
    ? 'http://localhost:8000/api'
    : '/api';

export async function checkAuth(): Promise<void> {
  try {
    const resp = await apiFetch(`${API_BASE}/auth/me`, {
      credentials: 'include',
    });
    if (!resp.ok) {
      await clearAccountData();
    clearTravel(true);
      window.localStorage.removeItem('app_account_id');
      isAuthenticated.set(false);
      authEmail.set(null);
      authDisplayName.set(null);
      aliasRequired.set(false);
      return;
    }
    const data = await resp.json();
    if (data.authenticated) {
      const previousAccountId = window.localStorage.getItem('app_account_id');
      if (previousAccountId && previousAccountId !== data.id) {
        await clearAccountData();
        clearTravel(true);
      }
      window.localStorage.setItem('app_account_id', data.id);
      isAuthenticated.set(true);
      authEmail.set(data.email);
      authDisplayName.set(data.display_name ?? null);
      aliasRequired.set(Boolean(data.alias_required));
    } else {
      await clearAccountData();
      clearTravel(true);
      window.localStorage.removeItem("app_account_id");
      isAuthenticated.set(false);
      authEmail.set(null);
      authDisplayName.set(null);
      aliasRequired.set(false);
    }
  } catch {
    // Network/SSL error — assume not authenticated, show login
    await clearAccountData();
    clearTravel(true);
    window.localStorage.removeItem('app_account_id');
    isAuthenticated.set(false);
    authEmail.set(null);
    authDisplayName.set(null);
    aliasRequired.set(false);
  }
}

export async function logout(): Promise<void> {
  try {
    await apiFetch(`${API_BASE}/${isNative() ? "native/logout" : "auth/logout"}`, {
      method: 'POST',
      credentials: 'include',
    });
  } catch {
    // ignore network errors
  }
  if (isNative()) await nativeBridge.clearSession();
  isAuthenticated.set(false);
  authEmail.set(null);
  authDisplayName.set(null);
  aliasRequired.set(false);
  await clearAccountData();
  clearTravel();
  window.localStorage.removeItem('app_account_id');
}

export async function disconnectGoogle(): Promise<void> {
  try {
    await apiFetch(`${API_BASE}/auth/google/disconnect`, {
      method: 'POST',
      credentials: 'include',
    });
  } catch {
    // ignore
  }
}

export async function googleLogin(): Promise<void> {
  if (isNative()) { await nativeLogin(); await checkAuth(); return; }
  window.location.href = `${API_BASE}/auth/google/login`;
}
