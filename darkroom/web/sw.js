// Network-first service worker: makes the app installable and keeps the shell available offline.
// API calls and images are never cached (edits must always be fresh).
const SHELL = "darkroom-shell-v1";
const FILES = ["/", "/static/style.css", "/static/app.js", "/static/icon-192.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(SHELL).then(c => c.addAll(FILES)).catch(() => {})); self.skipWaiting(); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== SHELL).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.pathname.startsWith("/api/")) return;
  e.respondWith(fetch(e.request).then(r => { const copy = r.clone(); caches.open(SHELL).then(c => c.put(e.request, copy)); return r; }).catch(() => caches.match(e.request)));
});
