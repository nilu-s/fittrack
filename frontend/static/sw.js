/* FitTrack Service Worker */
const CACHE_NAME = 'fittrack-v1';
const STATIC_CACHE = 'fittrack-static-v1';
const API_CACHE = 'fittrack-api-v1';

const STATIC_ASSETS = [
  '/',
  '/manifest.json',
  '/icon.svg',
  '/icon-192.svg',
  '/icon-512.svg',
  '/offline.html'
];

// Install: pre-cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(STATIC_ASSETS)).catch(() => {})
  );
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => ![STATIC_CACHE, API_CACHE].includes(k)).map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// Fetch strategy
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // API calls: network-first
  if (url.pathname.startsWith('/api')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Cache successful GET responses
          if (request.method === 'GET' && response.ok) {
            const clone = response.clone();
            caches.open(API_CACHE).then((cache) => cache.put(request, clone)).catch(() => {});
          }
          return response;
        })
        .catch(() => {
          // Fallback to cache
          if (request.method === 'GET') {
            return caches.match(request).then((cached) => cached || new Response('{"error":"offline"}', {
              status: 503,
              headers: { 'Content-Type': 'application/json' }
            }));
          }
          return new Response('{"error":"offline"}', {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
          });
        })
    );
    return;
  }

  // Static assets: cache-first
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request)
        .then((response) => {
          if (response.ok && request.method === 'GET') {
            const clone = response.clone();
            caches.open(STATIC_CACHE).then((cache) => cache.put(request, clone)).catch(() => {});
          }
          return response;
        })
        .catch(() => {
          // Offline fallback
          if (request.headers.get('accept')?.includes('text/html')) {
            return caches.match('/offline.html').then((r) => r || new Response('Offline', { status: 503 }));
          }
          return new Response('', { status: 503 });
        });
    })
  );
});