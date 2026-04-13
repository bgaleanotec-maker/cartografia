/**
 * Service Worker - Gestor Cartografico Campo Lite
 * Permite uso 100% offline en zonas veredales sin cobertura
 */

const CACHE_VERSION = 'campo-lite-v2';
const TILE_CACHE = 'map-tiles-v1';
const PHOTO_CACHE = 'photos-offline-v1';

// Recursos esenciales que se cachean al instalar
const CORE_ASSETS = [
  '/mobile/field',
  '/static/js/offline-manager.js',
  '/static/manifest.json',
  // CDN resources
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
  'https://cdn.tailwindcss.com',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js'
];

// ============================================================
// INSTALL - Pre-cache core assets
// ============================================================
self.addEventListener('install', (event) => {
  console.log('[SW] Installing...');
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => {
      return cache.addAll(CORE_ASSETS).catch((err) => {
        console.warn('[SW] Some assets failed to cache:', err);
      });
    })
  );
  self.skipWaiting();
});

// ============================================================
// ACTIVATE - Clean old caches
// ============================================================
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating...');
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter((key) => key !== CACHE_VERSION && key !== TILE_CACHE && key !== PHOTO_CACHE)
          .map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

// ============================================================
// FETCH - Intercept requests
// ============================================================
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // --- Map tiles: cache-first (essential for offline in veredas) ---
  if (isTileRequest(url)) {
    event.respondWith(tileStrategy(event.request));
    return;
  }

  // --- API calls: network-first, queue if offline ---
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(event.request));
    return;
  }

  // --- Core assets: cache-first ---
  event.respondWith(cacheFirst(event.request));
});

// ============================================================
// STRATEGIES
// ============================================================

// Cache-first: serve from cache, fallback to network (and update cache)
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_VERSION);
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    // Offline fallback for navigation requests
    if (request.mode === 'navigate') {
      const fallback = await caches.match('/mobile/field');
      if (fallback) return fallback;
    }
    return new Response('Offline - sin conexion', {
      status: 503,
      headers: { 'Content-Type': 'text/plain' }
    });
  }
}

// Network-first: try network, fallback to cache
async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_VERSION);
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    const cached = await caches.match(request);
    if (cached) return cached;
    return new Response(JSON.stringify({ error: 'offline', message: 'Sin conexion' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// Tile strategy: cache-first with dedicated tile cache
async function tileStrategy(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(TILE_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (err) {
    // Return a blank tile placeholder when offline and tile not cached
    return new Response(blankTileSVG(), {
      status: 200,
      headers: { 'Content-Type': 'image/svg+xml' }
    });
  }
}

// ============================================================
// HELPERS
// ============================================================

function isTileRequest(url) {
  return (
    url.hostname.includes('tile.openstreetmap.org') ||
    url.hostname.includes('arcgisonline.com') ||
    url.hostname.includes('tiles.stadiamaps.com') ||
    url.hostname.includes('basemaps.cartocdn.com') ||
    url.pathname.includes('/tile/')
  );
}

function blankTileSVG() {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256">
    <rect width="256" height="256" fill="#1a2332"/>
    <line x1="0" y1="128" x2="256" y2="128" stroke="#2a3342" stroke-width="0.5"/>
    <line x1="128" y1="0" x2="128" y2="256" stroke="#2a3342" stroke-width="0.5"/>
    <text x="128" y="128" text-anchor="middle" fill="#3a4352" font-size="10" font-family="sans-serif">Sin mapa</text>
  </svg>`;
}

// ============================================================
// BACKGROUND SYNC (for queued visits)
// ============================================================
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-visits') {
    event.waitUntil(syncVisits());
  }
});

async function syncVisits() {
  // This will be triggered when connectivity returns
  const clients = await self.clients.matchAll();
  clients.forEach((client) => {
    client.postMessage({ type: 'SYNC_VISITS' });
  });
}

// Listen for messages from the app
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'CACHE_TILES') {
    event.waitUntil(cacheTilesForArea(event.data.bounds, event.data.zoom));
  }
  if (event.data && event.data.type === 'SAVE_PHOTO') {
    event.waitUntil(savePhotoOffline(event.data.photoId, event.data.blob));
  }
});

// Pre-cache tiles for an area (called from app before going to field)
async function cacheTilesForArea(bounds, maxZoom) {
  const cache = await caches.open(TILE_CACHE);
  const minZoom = 13;
  const targetZoom = Math.min(maxZoom || 17, 18);
  let count = 0;

  for (let z = minZoom; z <= targetZoom; z++) {
    const minTile = latLngToTile(bounds.south, bounds.west, z);
    const maxTile = latLngToTile(bounds.north, bounds.east, z);

    for (let x = minTile.x; x <= maxTile.x; x++) {
      for (let y = maxTile.y; y <= minTile.y; y++) {
        const tileUrl = `https://a.tile.openstreetmap.org/${z}/${x}/${y}.png`;
        const cached = await cache.match(tileUrl);
        if (!cached) {
          try {
            const resp = await fetch(tileUrl);
            if (resp.ok) {
              await cache.put(tileUrl, resp);
              count++;
            }
          } catch (e) { /* skip failed tiles */ }
        }
      }
    }
  }

  // Notify app of completion
  const clients = await self.clients.matchAll();
  clients.forEach((client) => {
    client.postMessage({ type: 'TILES_CACHED', count });
  });
}

function latLngToTile(lat, lng, zoom) {
  const n = Math.pow(2, zoom);
  const x = Math.floor(((lng + 180) / 360) * n);
  const y = Math.floor(
    ((1 - Math.log(Math.tan((lat * Math.PI) / 180) + 1 / Math.cos((lat * Math.PI) / 180)) / Math.PI) / 2) * n
  );
  return { x, y };
}

// Save photo blob to cache
async function savePhotoOffline(photoId, blob) {
  const cache = await caches.open(PHOTO_CACHE);
  const response = new Response(blob, {
    headers: { 'Content-Type': 'image/jpeg' }
  });
  await cache.put(`/offline-photos/${photoId}`, response);
}
