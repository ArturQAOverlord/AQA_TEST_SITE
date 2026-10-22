// Service Worker для миссии offline-sw: кэширует страницу и статьи, без сети отвечает из кэша.
const CACHE = 'lab-offline-v1';
const ASSETS = ['/play/offline-sw', '/static/play.css', '/static/play.js', '/api/articles'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || !ASSETS.includes(url.pathname)) return;
  // Сначала сеть (и обновляем кэш), без сети — кэш
  event.respondWith(
    fetch(event.request)
      .then(response => {
        const copy = response.clone();
        caches.open(CACHE).then(cache => cache.put(url.pathname, copy));
        return response;
      })
      .catch(() => caches.match(url.pathname))
  );
});
