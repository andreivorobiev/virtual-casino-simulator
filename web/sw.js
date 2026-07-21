// Casino Simulator service worker: versioned static-shell cache only. (issue #182)
// It never caches authenticated API responses, wallet values, game outcomes, ledger data, or any
// private content; those always go to the network. Offline navigation falls back to the cached
// application shell, which then presents an explicit offline state to the user.

// Version the cache so a shell change produces a fresh cache and retires the previous one.
const SHELL_VERSION = 'casino-shell-v1';
// Name the versioned cache used for static shell assets only.
const SHELL_CACHE = SHELL_VERSION;
// Precache the minimal shell needed to launch and render the offline state.
const SHELL_ASSETS = [
  '/index.html',
  '/styles.css',
  '/app.js',
  '/manifest.webmanifest',
  '/assets/favicon.svg',
];

// Restrict shell caching to the application shell so lazily-loaded game modules always load from the network.
function isShellAsset(pathname) {
  // Cache the precached shell entries exactly.
  if (SHELL_ASSETS.includes(pathname)) return true;
  // Cache shared core modules, icons, and localization resources that render the offline shell.
  return pathname.startsWith('/core/') || pathname.startsWith('/assets/') || pathname.startsWith('/i18n/');
}

// Precache the shell on install without auto-activating, so the client controls when an update applies.
self.addEventListener('install', event => {
  // Open the versioned shell cache and add the minimal launch assets.
  event.waitUntil(caches.open(SHELL_CACHE).then(cache => cache.addAll(SHELL_ASSETS)));
});

// On activation, remove superseded shell caches and take control of open clients.
self.addEventListener('activate', event => {
  // Delete every cache that is not the current shell version, then claim clients.
  event.waitUntil((async () => {
    // Read all cache names to find superseded shell versions.
    const names = await caches.keys();
    // Delete only prior Casino shell caches, never another origin's caches.
    await Promise.all(names.filter(name => name.startsWith('casino-shell-') && name !== SHELL_CACHE).map(name => caches.delete(name)));
    // Start controlling already-open pages so the update takes effect without a manual reload.
    await self.clients.claim();
  })());
});

// Apply a waiting update only when the client explicitly requests it (non-coercive update flow).
self.addEventListener('message', event => {
  // Skip the waiting phase so the new worker can activate on the client's command.
  if (event.data && event.data.type === 'SKIP_WAITING') self.skipWaiting();
});

// Decide how each request is served, keeping all private and API traffic on the network.
self.addEventListener('fetch', event => {
  // Read the request and its parsed URL once.
  const request = event.request;
  const url = new URL(request.url);
  // Never intercept cross-origin requests; let the network handle them directly.
  if (url.origin !== self.location.origin) return;
  // Leave API traffic and any non-GET method entirely to the browser so authenticated data never touches the worker.
  if (request.method !== 'GET' || url.pathname.startsWith('/api/')) {
    // Do not intercept; the request goes straight to the network without any worker involvement.
    return;
  }
  // Serve navigations network-first, falling back to the cached shell so the app can show its offline state.
  if (request.mode === 'navigate') {
    // Try the network first, then the cached index shell if offline.
    event.respondWith((async () => {
      // Attempt a live navigation response.
      try {
        // Return the fresh network document when reachable.
        return await fetch(request);
      // Fall back to the precached application shell when the network is unavailable.
      } catch (error) {
        // Serve the cached index shell so the SPA can render its explicit offline state.
        const cached = await caches.match('/index.html');
        // Return the shell or a minimal offline response if the shell is somehow absent.
        return cached || new Response('Offline', { status: 503, headers: { 'Content-Type': 'text/plain' } });
      }
    })());
    return;
  }
  // Never intercept non-shell assets such as lazily-loaded game modules; let the browser fetch them directly.
  if (!isShellAsset(url.pathname)) {
    // Do not call respondWith so the request keeps its native network timing and page-level interception.
    return;
  }
  // Serve same-origin static shell assets stale-while-revalidate within the versioned cache.
  event.respondWith((async () => {
    // Read any cached copy of this static asset.
    const cached = await caches.match(request);
    // Refresh the cached copy in the background without blocking the response.
    const network = fetch(request).then(response => {
      // Cache only successful, basic same-origin responses to avoid storing errors or opaque data.
      if (response && response.ok && response.type === 'basic') {
        // Store a clone so the original response can still be returned to the page.
        caches.open(SHELL_CACHE).then(cache => cache.put(request, response.clone()));
      }
      // Return the network response for callers awaiting it.
      return response;
    }).catch(() => cached);
    // Prefer the cached copy for speed and offline resilience, else await the network.
    return cached || network;
  })());
});
