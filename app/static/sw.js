const CACHE_NAME = 'gemini-agent-v6'; // Bump version for fresh install

self.addEventListener('install', (event) => {
  console.log('Service Worker v6 installing...');
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      // Pre-cache only essential, non-dynamic assets
      // (Root path '/' removed to avoid caching redirects)
      return cache.addAll([
        '/static/style.css',
        '/static/script.js',
        '/static/icon.svg',
        '/static/icon-192.png',
        '/static/icon-512.png',
        '/static/maskable-icon-512.png',
        '/manifest.json'
      ]);
    }).catch((error) => {
      console.error('Service Worker install failed:', error);
    })
  );
});

self.addEventListener('activate', (event) => {
  console.log('Service Worker v6 activating...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.filter((cacheName) => {
          return cacheName !== CACHE_NAME;
        }).map((cacheName) => {
          console.log(`[SW] Deleting old cache: ${cacheName}`);
          return caches.delete(cacheName);
        })
      );
    })
  );
  event.waitUntil(self.clients.claim()); // Take control of un-controlled clients
});

self.addEventListener('fetch', (event) => {
  console.log('[SW] Fetching:', event.request.url);

  // Network-first strategy for all requests
  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        // If the network response is good, cache it and return it
        if (networkResponse.ok && networkResponse.type === 'basic' && event.request.method === 'GET') {
          const clonedResponse = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            // Only cache requests for paths that typically don't change often and are not main HTML docs
            const urlWithoutQuery = event.request.url.split('?')[0].replace(self.location.origin, '');
            if (urlWithoutQuery.startsWith('/static/') || urlWithoutQuery === '/manifest.json') {
                 console.log(`[SW] Caching network response for: ${event.request.url}`);
                cache.put(event.request, clonedResponse);
            }
          });
        }
        return networkResponse;
      })
      .catch((error) => {
        console.warn(`[SW] Network request failed for: ${event.request.url}. Trying cache.`, error);
        // Fallback to cache if network fails
        return caches.match(event.request).then((cachedResponse) => {
          if (cachedResponse) {
            console.log(`[SW] Serving from cache: ${event.request.url}`);
            return cachedResponse;
          }
          // If neither network nor cache has a response, return a generic offline page or error
          console.error(`[SW] No cache match for offline: ${event.request.url}`);
          // For navigation requests, can show an offline page
          if (event.request.mode === 'navigate') {
            return new Response('<h1>Offline</h1><p>You are offline and this page is not available.</p>', { headers: { 'Content-Type': 'text/html' } });
          }
          // For other requests, return a network error
          return new Response(null, { status: 503, statusText: 'Service Unavailable (Offline)' });
        });
      })
  );
});
