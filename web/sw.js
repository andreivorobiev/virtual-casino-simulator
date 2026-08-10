// Own the root-scope offline-safe static shell without caching private or authoritative data. (PWA-002)
// Match the canonical packaged application release used by modules/module-manifest.json.
const APP_VERSION = '0.9.5.62';
// Prefix every Casino-owned cache so activation can prune only this application's predecessors.
const CACHE_PREFIX = 'casino-static-shell-v';
// Bind the cache identity to the canonical packaged release rather than an ad-hoc counter.
const SHELL_CACHE = `${CACHE_PREFIX}${APP_VERSION}`;
// Enumerate every public static response permitted in the offline shell cache.
const SHELL_ASSETS = Object.freeze([
  '/index.html',
  '/styles.css',
  '/app.js',
  '/brands/tiltseven.js',
  '/manifest.webmanifest',
  '/assets/favicon.svg',
  '/assets/pwa-icon-192.png',
  '/assets/pwa-icon-512.png',
  '/assets/pwa-maskable-192.png',
  '/assets/pwa-maskable-512.png',
  '/core/api.js',
  '/core/brand.js',
  '/core/celebrate.js',
  '/core/feedback.js',
  '/core/i18n.js',
  '/core/pwa.js',
  '/core/ui.js',
  '/core/voice.js',
  '/i18n/en-US/feedback.json',
  '/i18n/en-US/shell.json',
  '/i18n/ru-RU/feedback.json',
  '/i18n/ru-RU/shell.json',
]);
// Convert the exact asset list to a membership set without introducing prefix-based cache expansion.
const SHELL_ASSET_SET = new Set(SHELL_ASSETS);
// Allow shell fallback only for application routes whose response is the public index document.
const OFFLINE_NAVIGATION = [/^\/$/, /^\/index\.html$/, /^\/games\/[a-z0-9_]+\/?$/, /^\/enroll\/invitation\/?$/];

// Decide whether one route may receive the public cached index while offline.
function isOfflineNavigation(pathname) {
  // Match only the explicit application route patterns.
  return OFFLINE_NAVIGATION.some(pattern => pattern.test(pathname));
}

// Reject response types that could contain private, credentialed, or malformed content.
function isPublicStaticResponse(response) {
  // Require a successful same-origin basic response.
  if (!response || !response.ok || response.type !== 'basic') return false;
  // Normalize cache policy before checking explicit privacy directives.
  const cacheControl = String(response.headers.get('cache-control') || '').toLowerCase();
  // Reject private responses; the exact credential-free worker allowlist intentionally overrides the server's generic no-store static policy.
  if (cacheControl.includes('private')) return false;
  // Accept only responses that passed the public static and cache-policy boundary.
  return true;
}

// Fetch one public static asset without cookies or authorization and validate it before storage.
async function fetchPublicAsset(pathname) {
  // Create one abort controller so a stalled origin cannot leave the worker installing indefinitely.
  const controller = new AbortController();
  // Bound each reviewed static request independently while retaining the previous active worker on failure.
  const timeout = setTimeout(() => controller.abort(), 8000);
  // Construct a same-origin request that omits credentials, requests cookie-free public shell bytes, and bypasses stale HTTP caches.
  const request = new Request(pathname, { method: 'GET', credentials: 'omit', cache: 'reload', headers: { 'X-Casino-Public-Shell': '1' }, signal: controller.signal });
  // Start protected fetching so the timer is always released.
  try {
    // Fetch the exact allowlisted path from the origin.
    const response = await fetch(request);
    // Fail installation or runtime caching when the response is not safe public static content.
    if (!isPublicStaticResponse(response)) throw new Error('public static asset rejected');
    // Consume the complete body before the next sequential fetch so unread streams cannot exhaust the origin connection pool.
    const bytes = await response.arrayBuffer();
    // Reconstruct a detached response that preserves reviewed metadata without retaining the network stream or abort signal.
    const storedResponse = new Response(bytes, { status: response.status, statusText: response.statusText, headers: response.headers });
    // Return a signal-free cache key plus detached bytes so an expired fetch signal cannot affect later storage.
    return { request: new Request(pathname, { method: 'GET', credentials: 'omit' }), response: storedResponse };
  // Release the bounded timer on success, rejection, or abort.
  } finally {
    // Prevent completed fetches from retaining timer callbacks through the rest of installation.
    clearTimeout(timeout);
  }
}

// Populate a fresh canonical-version cache atomically during worker installation.
async function installShell() {
  // Collect validated responses in reviewed order without a connection-saturating install fan-out.
  const rows = [];
  // Track only a bounded operation class and numeric allowlist position for sanitized install diagnostics.
  let stage = 'fetch-0';
  // Assume a prior cache exists until the exact inventory read proves a clean install.
  let cacheWasPresent = true;
  // Track cache creation so a fetch rejection cannot delete unrelated storage.
  let cacheOpened = false;
  try {
    // Fetch every exact allowlisted asset sequentially before exposing a cache or worker.
    for (let index = 0; index < SHELL_ASSETS.length; index += 1) {
      // Publish only the numeric reviewed position, never a URL or response value.
      stage = `fetch-${index}`;
      // Append the validated public response in canonical allowlist order.
      rows.push(await fetchPublicAsset(SHELL_ASSETS[index]));
    }
    // Mark the bounded cache-inventory operation before reading owned cache names.
    stage = 'cache-inventory';
    // Record whether a prior canonical cache exists so failed same-version repair never deletes it.
    cacheWasPresent = (await caches.keys()).includes(SHELL_CACHE);
    // Mark the bounded cache-open operation after every source response validates.
    stage = 'cache-open';
    // Open only the canonical cache after all source responses succeeded.
    const cache = await caches.open(SHELL_CACHE);
    // Record that subsequent rollback may target only this exact canonical cache.
    cacheOpened = true;
    // Store every response through one ordered CacheStorage mutation.
    for (let index = 0; index < rows.length; index += 1) {
      // Publish only the numeric reviewed position before one cache write.
      stage = `cache-write-${index}`;
      // Store the validated response under its signal-free credential-omitting key.
      await cache.put(rows[index].request, rows[index].response);
    }
  // Emit a low-cardinality diagnostic and preserve browser rollback semantics on any install failure.
  } catch (error) {
    // Report only the bounded operation stage and standard error name for hosted acceptance diagnosis.
    console.error(`PWA_INSTALL_FAILURE stage=${stage} error=${error?.name || 'Error'}`);
    // Delete the incomplete cache only when this installation created it.
    if (cacheOpened && !cacheWasPresent) await caches.delete(SHELL_CACHE);
    // Reject installation so browser rollback semantics retain the prior active worker.
    throw error;
  }
}

// Precache the complete public static shell without forcing activation over an older working client.
self.addEventListener('install', event => {
  // Keep the worker installing until every allowlisted public asset is verified and cached.
  event.waitUntil(installShell());
});

// Remove only superseded Casino shell caches after the new complete cache activates.
self.addEventListener('activate', event => {
  // Bind cleanup and client claim to the activation lifetime.
  event.waitUntil((async () => {
    // Read all origin cache names without opening unrelated application caches.
    const names = await caches.keys();
    // Delete only older caches owned by this exact Casino prefix.
    await Promise.all(names.filter(name => name.startsWith(CACHE_PREFIX) && name !== SHELL_CACHE).map(name => caches.delete(name)));
    // Take control after the new complete shell and cleanup transaction succeeded.
    await self.clients.claim();
  })());
});

// Handle only explicit update activation and read-only canonical-version proof messages.
self.addEventListener('message', event => {
  // Activate a waiting worker only after the visible client update action requests it.
  if (event.data?.type === 'SKIP_WAITING') { self.skipWaiting(); return; }
  // Reply to version probes without exposing cache contents or client identity.
  if (event.data?.type === 'GET_VERSION' && event.source) event.source.postMessage({ type: 'PWA_VERSION', version: APP_VERSION });
});

// Serve a public static asset from the canonical cache, refreshing only with credential-free responses.
async function serveStatic(pathname) {
  // Build the same credential-free cache key used at installation.
  const request = new Request(pathname, { method: 'GET', credentials: 'omit' });
  // Read the canonical cache rather than searching unrelated origin caches.
  const cache = await caches.open(SHELL_CACHE);
  // Return the verified installed copy when present.
  const cached = await cache.match(request);
  // Use the installed response first so an unavailable origin cannot break the shell.
  if (cached) return cached;
  // Fetch and validate a missing allowlisted asset without credentials.
  const row = await fetchPublicAsset(pathname);
  // Store only the validated public response clone.
  await cache.put(row.request, row.response.clone());
  // Return the original validated response.
  return row.response;
}

// Keep private, authenticated, authoritative, and non-GET traffic entirely outside worker interception.
self.addEventListener('fetch', event => {
  // Read the request and parsed URL once for the fail-closed routing policy.
  const request = event.request;
  // Parse the request URL through the platform URL implementation.
  const url = new URL(request.url);
  // Ignore cross-origin traffic so the worker never becomes a provider proxy.
  if (url.origin !== self.location.origin) return;
  // Ignore every non-GET request so mutations always reach the authoritative server directly.
  if (request.method !== 'GET') return;
  // Ignore any explicitly authorized request even when a future path resembles a static asset.
  if (request.headers.has('authorization')) return;
  // Ignore API, Admin, wallet, ledger, auth, feedback, invitation, and OAuth traffic categorically.
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/admin')) return;
  // Serve public application navigations network-first without ever caching their responses.
  if (request.mode === 'navigate') {
    // Leave non-application navigation paths entirely to the network.
    if (!isOfflineNavigation(url.pathname)) return;
    // Fall back only to the public cached index document when the network is unavailable.
    event.respondWith(fetch(request).catch(async () => (await caches.open(SHELL_CACHE)).match('/index.html') || new Response('Offline', { status: 503, headers: { 'Content-Type': 'text/plain; charset=utf-8' } })));
    // Stop before the static-asset policy handles the navigation request.
    return;
  }
  // Ignore query-bearing requests so arbitrary cache-key expansion is impossible.
  if (url.search) return;
  // Ignore every path outside the exact reviewed public static allowlist.
  if (!SHELL_ASSET_SET.has(url.pathname)) return;
  // Serve only the reviewed public static resource from the canonical cache.
  event.respondWith(serveStatic(url.pathname));
});
