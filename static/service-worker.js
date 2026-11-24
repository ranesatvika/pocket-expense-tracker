
const CACHE_NAME = "pocket-expense-v2";
const APP_FILES = [
    "/",
    "/static/style.css",
    "/static/manifest.json",
    "/static/icon-192.png",
    "/static/icon-512.png",
    "/static/icon.svg",
    "/offline"
];
// Install service worker
self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(APP_FILES);
        })
    );

    self.skipWaiting();
});

// Activate service worker
self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );

    self.clients.claim();
});

// Handle requests
self.addEventListener("fetch", (event) => {
    if (event.request.method !== "GET") return;

    event.respondWith(
        fetch(event.request).catch(async () => {
            const cachedResponse = await caches.match(event.request);

            if (cachedResponse) {
                return cachedResponse;
            }

            if (event.request.mode === "navigate") {
                return caches.match("/offline");
            }
        })
    );
});
