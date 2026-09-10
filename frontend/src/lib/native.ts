import { Capacitor, registerPlugin } from '@capacitor/core';

interface NativeBridge {
  request(options: { path: string; method: string; headers: Record<string, string>; bodyBase64?: string }): Promise<{ status: number; body: string; contentType?: string }>;
  googleLogin(): Promise<void>;
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

export async function nativeLogin(): Promise<void> {
  if (Capacitor.getPlatform() !== 'android') throw new Error('Die Anmeldung auf dem iPhone ist noch nicht verfügbar. Bitte nutze die Website.');
  await nativeBridge.googleLogin();
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
export async function installNativeEvents(onTodo: (id: string, date: string) => void) {
  if (!isNative()) return () => {};
  const { PushNotifications } = await import('@capacitor/push-notifications');
  const handles = await Promise.all([
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
