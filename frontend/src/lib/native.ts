import { Capacitor, registerPlugin } from '@capacitor/core';

interface NativeBridge {
  request(options: { path: string; method: string; headers: Record<string, string>; bodyBase64?: string }): Promise<{ status: number; body: string; contentType?: string }>;
  exchange(options: { loginId: string; verifier: string }): Promise<void>;
  clearSession(): Promise<void>;
  startLocation(options: { todoId: string; expiresAt: string }): Promise<void>;
  stopLocation(): Promise<void>;
  locationState(): Promise<{ active: boolean; todoId?: string }>;
}

export const nativeBridge = registerPlugin<NativeBridge>('CroniclNative');
export const isNative = () => Capacitor.isNativePlatform();

/** Credentials never cross the native bridge into JavaScript. */
export async function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
  if (!isNative()) return fetch(input, init);
  const url = new URL(input, 'https://native.invalid');
  const path = url.pathname + url.search;
  if (!path.startsWith('/api/')) throw new Error('Invalid native API path');
  const headers = new Headers(init.headers);
  let bodyBase64: string | undefined;
  if (init.body) {
    const encoded = new Response(init.body);
    if (!headers.has('Content-Type') && encoded.headers.has('Content-Type')) headers.set('Content-Type', encoded.headers.get('Content-Type')!);
    const bytes = new Uint8Array(await encoded.arrayBuffer());
    let binary = '';
    for (let index = 0; index < bytes.length; index += 8192) binary += String.fromCharCode(...bytes.subarray(index, index + 8192));
    bodyBase64 = btoa(binary);
  }
  const result = await nativeBridge.request({ path, method: init.method ?? 'GET', headers: Object.fromEntries(headers), bodyBase64 });
  return new Response(result.status === 204 ? null : result.body, { status: result.status, headers: { 'Content-Type': result.contentType ?? 'application/json' } });
}

let pendingLogin: { id: string; verifier: string } | null = null;

export async function nativeLogin(): Promise<void> {
  const bytes = crypto.getRandomValues(new Uint8Array(48));
  const verifier = btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier)));
  const challenge = btoa(String.fromCharCode(...digest)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  const response = await apiFetch('/api/native/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ challenge, platform: Capacitor.getPlatform() }) });
  if (!response.ok) throw new Error('Anmeldung konnte nicht gestartet werden.');
  const data = await response.json();
  pendingLogin = { id: data.login_id, verifier };
  const { Browser } = await import('@capacitor/browser');
  await Browser.open({ url: data.login_url });
}

let finishingLogin = false;
export async function finishNativeLogin(): Promise<boolean> {
  if (!pendingLogin || finishingLogin) return false;
  finishingLogin = true;
  try {
  await nativeBridge.exchange({ loginId: pendingLogin.id, verifier: pendingLogin.verifier });
  pendingLogin = null;
  const { Browser } = await import('@capacitor/browser');
  await Browser.close().catch(() => {});
  return true;
  } finally { finishingLogin = false; }
}

export async function registerNativePush(): Promise<boolean> {
  if (!isNative()) return false;
  const { PushNotifications } = await import('@capacitor/push-notifications');
  const permission = await PushNotifications.requestPermissions();
  if (permission.receive !== 'granted') return false;
  if (Capacitor.getPlatform() === 'android') await PushNotifications.createChannel({ id: 'travel', name: 'Anreise', importance: 4 });
  await PushNotifications.register();
  return true;
}

/** Called once by the authenticated shell; all listeners have matching cleanup. */
export async function installNativeEvents(onLogin: () => Promise<void>, onTodo: (id: string, date: string) => void) {
  if (!isNative()) return () => {};
  const { App } = await import('@capacitor/app');
  const { PushNotifications } = await import('@capacitor/push-notifications');
  const handles = await Promise.all([
    App.addListener('appUrlOpen', async ({ url }) => {
      if (url === 'cronicl://auth-complete' || url === 'cronicl://auth-complete/') {
        try { if (await finishNativeLogin()) await onLogin(); }
        catch { window.dispatchEvent(new CustomEvent('native-login-error')); }
      }
    }),
    App.addListener('appStateChange', async ({ isActive }) => {
      if (isActive && pendingLogin) {
        try { if (await finishNativeLogin()) await onLogin(); } catch { /* Browser consent may still be open. */ }
      }
    }),
    PushNotifications.addListener('registration', async ({ value }) => {
      try {
        const response = await apiFetch('/api/native/push', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token: value }) });
        if (!response.ok) window.dispatchEvent(new CustomEvent('native-push-error'));
        else window.dispatchEvent(new CustomEvent('native-push-ready'));
      } catch { window.dispatchEvent(new CustomEvent('native-push-error')); }
    }),
    PushNotifications.addListener('registrationError', () => window.dispatchEvent(new CustomEvent('native-push-error'))),
    PushNotifications.addListener('pushNotificationActionPerformed', ({ notification }) => {
      const data = notification.data;
      if (/^[0-9a-f-]{36}$/i.test(data?.todo_id ?? '') && /^\d{4}-\d{2}-\d{2}$/.test(data?.date ?? '')) onTodo(data.todo_id, data.date);
    }),
  ]);
  return () => { for (const handle of handles) void handle.remove(); };
}
