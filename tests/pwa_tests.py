# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Validate the narrowed offline-safe PWA foundation without launching a browser. (PWA-001, PWA-002, TEST-095)
# Import JSON support for manifest, requirement, module, and visual-matrix assertions.
import json
# Import pathlib so every governed artifact is resolved from the repository root.
import pathlib
# Import regular expressions for static JavaScript policy extraction.
import re
# Import executable discovery for the dependency-free JavaScript lifecycle harness.
import shutil
# Import struct so PNG dimensions can be verified without image-library dependencies.
import struct
# Import subprocess execution for the real celebration module contract.
import subprocess
# Import unittest for normal repository test discovery.
import unittest

# Resolve the repository root independently from the caller's working directory.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Name the exact public static paths permitted in the service-worker cache.
EXPECTED_SHELL_ASSETS = {
    "/index.html", "/styles.css", "/app.js", "/brands/tiltseven.js", "/manifest.webmanifest", "/assets/favicon.svg",
    "/assets/pwa-icon-192.png", "/assets/pwa-icon-512.png", "/assets/pwa-maskable-192.png", "/assets/pwa-maskable-512.png",
    "/core/api.js", "/core/brand.js", "/core/celebrate.js", "/core/feedback.js", "/core/wellness.js", "/core/i18n.js", "/core/pwa.js", "/core/ui.js", "/core/voice.js",
    "/i18n/en-US/feedback.json", "/i18n/en-US/shell.json", "/i18n/ru-RU/feedback.json", "/i18n/ru-RU/shell.json",
}
# Name every governed lifecycle state required by the narrowed visual matrix.
EXPECTED_PWA_STATES = {
    "cold_start", "warm_start", "offline", "reconnecting", "update_available", "update_failed", "stale_client", "expired_session", "route_restored",
}

# Load one UTF-8 JSON document through the standard parser.
def load_json(relative_path):
    # Read and decode the governed document in one deterministic step.
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


# Read one PNG's dimensions directly from its fixed signature and IHDR fields.
def png_dimensions(path):
    # Read only the bytes required for the PNG signature, IHDR tag, width, and height.
    header = path.read_bytes()[:24]
    # Reject a missing or non-PNG asset before interpreting dimensions.
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        # Raise a focused assertion-compatible error for invalid icon assets.
        raise ValueError(f"invalid PNG header: {path.name}")
    # Decode big-endian width and height from the standard IHDR offsets.
    return struct.unpack(">II", header[16:24])


# Group browser-free PWA policy tests under one discoverable test case.
class PwaFoundationTests(unittest.TestCase):
    # Require page, worker, and canonical release identities to remain aligned.
    def test_canonical_version_alignment(self):
        # Read the canonical packaged application release.
        version = load_json("modules/module-manifest.json")["application"]
        # Read the page-side controller source.
        client = (ROOT / "web" / "core" / "pwa.js").read_text(encoding="utf-8")
        # Read the service-worker source.
        worker = (ROOT / "web" / "sw.js").read_text(encoding="utf-8")
        # Require both version constants to equal the canonical packaged release.
        self.assertIn(f"PWA_APP_VERSION = '{version}'", client)
        # Require the worker cache identity to use the same canonical release.
        self.assertIn(f"APP_VERSION = '{version}'", worker)
        # Reject the obsolete ad-hoc cache counter from the contributor draft.
        self.assertNotIn("casino-shell-v1", worker)

    # Require complete real PNG any-purpose and maskable manifest assets.
    def test_manifest_icons_are_complete_png_assets(self):
        # Load the web application manifest.
        manifest = load_json("web/manifest.webmanifest")
        # Index icons by path so size and purpose can be compared exactly.
        icons = {row["src"]: row for row in manifest["icons"]}
        # Define the reviewed icon contract and expected pixel dimensions.
        expected = {
            "/assets/pwa-icon-192.png": ("192x192", "any", (192, 192)),
            "/assets/pwa-icon-512.png": ("512x512", "any", (512, 512)),
            "/assets/pwa-maskable-192.png": ("192x192", "maskable", (192, 192)),
            "/assets/pwa-maskable-512.png": ("512x512", "maskable", (512, 512)),
        }
        # Require no missing or unreviewed icon entries.
        self.assertEqual(set(icons), set(expected))
        # Validate every manifest row against real file bytes.
        for source, (sizes, purpose, dimensions) in expected.items():
            # Resolve the manifest path beneath the web root.
            path = ROOT / "web" / source.lstrip("/")
            # Require exact MIME, declared size, and purpose values.
            self.assertEqual((icons[source]["type"], icons[source]["sizes"], icons[source]["purpose"]), ("image/png", sizes, purpose))
            # Require file dimensions to match the declared manifest dimensions.
            self.assertEqual(png_dimensions(path), dimensions)
            # Reject empty placeholder images that happen to carry a valid header.
            self.assertGreater(path.stat().st_size, 4000)
        # Require iOS home-screen metadata to use a real reviewed PNG.
        index = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        # Compare the exact Apple touch-icon path and size contract.
        self.assertIn('rel="apple-touch-icon" sizes="192x192" href="/assets/pwa-icon-192.png"', index)

    # Require the service worker to cache only the exact credential-free static allowlist.
    def test_worker_cache_allowlist_and_private_exclusions(self):
        # Read the complete service-worker source for static policy checks.
        worker = (ROOT / "web" / "sw.js").read_text(encoding="utf-8")
        # Extract the immutable shell-assets array without executing worker code.
        match = re.search(r"const SHELL_ASSETS = Object\.freeze\(\[(.*?)\]\);", worker, re.DOTALL)
        # Require the exact allowlist declaration to remain present.
        self.assertIsNotNone(match)
        # Extract each single-quoted public path from the reviewed array.
        actual_assets = set(re.findall(r"'([^']+)'", match.group(1)))
        # Reject additions, omissions, and prefix expansion.
        self.assertEqual(actual_assets, EXPECTED_SHELL_ASSETS)
        # Require credential omission for installation and runtime cache fills.
        self.assertGreaterEqual(worker.count("credentials: 'omit'"), 2)
        # Reject the contributor draft's broad prefix cache discovery.
        self.assertNotIn("pathname.startsWith('/core/')", worker)
        # Reject broad localization and asset prefix caching.
        self.assertNotIn("pathname.startsWith('/i18n/')", worker)
        # Require fail-open worker exclusion for non-GET and authorization-bearing requests.
        self.assertIn("request.method !== 'GET'", worker)
        # Require explicit Authorization exclusion.
        self.assertIn("request.headers.has('authorization')", worker)
        # Require explicit API and Admin exclusions.
        self.assertIn("url.pathname.startsWith('/api/') || url.pathname.startsWith('/admin')", worker)
        # Require query-bearing static requests to bypass worker caching.
        self.assertIn("if (url.search) return", worker)
        # Require explicit private cache directives to be rejected.
        self.assertIn("cacheControl.includes('private')", worker)
        # Require the credential-free public-shell marker on cache-population fetches.
        self.assertIn("'X-Casino-Public-Shell': '1'", worker)
        # Require both HTTP adapters to suppress shell cookies only for marker requests without credentials.
        # Read the development adapter independently.
        development_adapter = (ROOT / "casino" / "app.py").read_text(encoding="utf-8")
        # Read the production WSGI adapter independently.
        production_adapter = (ROOT / "casino" / "wsgi.py").read_text(encoding="utf-8")
        # Require the same fixed marker in both supported adapters.
        self.assertIn('PWA_PUBLIC_SHELL_HEADER = "X-Casino-Public-Shell"', development_adapter)
        # Require the production adapter to share the same fixed marker.
        self.assertIn('PWA_PUBLIC_SHELL_HEADER = "X-Casino-Public-Shell"', production_adapter)
        # Require Cookie and Authorization absence in the development marker boundary.
        self.assertIn('and not self.headers.get("Cookie") and not self.headers.get("Authorization")', development_adapter)
        # Require Cookie and Authorization absence in the production marker boundary.
        self.assertIn('and not headers.get("Cookie") and not headers.get("Authorization")', production_adapter)
        # Require cookie bootstrap to exclude reviewed public-shell requests in both adapters.
        self.assertIn('and not public_pwa_shell', development_adapter)
        # Require the production cookie bootstrap to share that exclusion.
        self.assertIn('and not public_pwa_shell', production_adapter)

    # Require atomic install, explicit activation, predecessor cleanup, and version proof.
    def test_worker_update_and_rollback_boundaries(self):
        # Read the service-worker source once for ordered policy assertions.
        worker = (ROOT / "web" / "sw.js").read_text(encoding="utf-8")
        # Require every source response to validate before the canonical cache opens.
        self.assertLess(worker.index("for (let index = 0; index < SHELL_ASSETS.length; index += 1)"), worker.index("caches.open(SHELL_CACHE)"))
        # Require bounded worker fetches so a stalled origin cannot leave installation pending indefinitely.
        self.assertIn("const controller = new AbortController()", worker)
        # Require the exact per-asset timeout boundary to abort only the active public fetch.
        self.assertIn("setTimeout(() => controller.abort(), 8000)", worker)
        # Require reviewed sequential fetch order instead of a connection-saturating install fan-out.
        self.assertNotIn("Promise.all(SHELL_ASSETS.map", worker)
        # Require each network response body to drain before the next sequential request can occupy the origin connection pool.
        self.assertIn("const bytes = await response.arrayBuffer()", worker)
        # Require cache storage to receive a detached response rather than an unread network-backed stream.
        self.assertIn("const storedResponse = new Response(bytes", worker)
        # Require body materialization to precede returning the response for deferred cache storage.
        self.assertLess(worker.index("await response.arrayBuffer()"), worker.index("response: storedResponse"))
        # Require one ordered CacheStorage mutation at a time after every response validates.
        self.assertIn("await cache.put(rows[index].request, rows[index].response)", worker)
        # Require clean-install rollback without deleting a prior canonical cache.
        self.assertIn("if (cacheOpened && !cacheWasPresent) await caches.delete(SHELL_CACHE)", worker)
        # Require low-cardinality failure diagnostics without raw allowlist paths or response values.
        self.assertIn("PWA_INSTALL_FAILURE stage=${stage} error=${error?.name || 'Error'}", worker)
        # Require activation cleanup to target only the Casino cache prefix.
        self.assertIn("name.startsWith(CACHE_PREFIX) && name !== SHELL_CACHE", worker)
        # Prohibit install-time skipWaiting so the prior complete worker remains active.
        install_block = worker[worker.index("self.addEventListener('install'"):worker.index("self.addEventListener('activate'")]
        # Verify the install block never forces activation.
        self.assertNotIn("skipWaiting", install_block)
        # Require explicit client-requested activation and read-only version response protocols.
        self.assertIn("event.data?.type === 'SKIP_WAITING'", worker)
        # Require the message event to own skipWaiting until activation settles across controlled tabs. (PWA-003)
        self.assertIn("event.waitUntil(self.skipWaiting())", worker)
        # Reject the fire-and-forget form that may terminate before Chromium promotes the waiting worker.
        self.assertNotIn("{ self.skipWaiting(); return; }", worker)
        # Require the exact low-cardinality version response.
        self.assertIn("{ type: 'PWA_VERSION', version: APP_VERSION }", worker)

    # Require client registration to observe an update that starts before listener wiring completes. (PWA-003)
    def test_client_closes_existing_installation_observer_race(self):
        # Read the production PWA controller as the executable lifecycle contract.
        client = (ROOT / "web" / "core" / "pwa.js").read_text(encoding="utf-8")
        # Require one shared observer to accept an already captured installing worker.
        self.assertIn("function observeInstallingWorker(installing)", client)
        # Require immediate state inspection in addition to future state-change observation.
        self.assertIn("installing.addEventListener('statechange', revealWhenInstalled);", client)
        # Require the immediate inspection to occur after listener attachment so no later transition is lost.
        self.assertLess(client.index("installing.addEventListener('statechange', revealWhenInstalled);"), client.index("revealWhenInstalled();"))
        # Require registration to inspect an installation that predates the updatefound listener callback.
        self.assertIn("observeInstallingWorker(registration.installing);", client)
        # Require a final waiting-slot read after listener wiring closes the installation-to-waiting edge.
        self.assertGreater(client.rindex("if (registration.waiting) { updateWaiting = true; renderPwaState('update'); }"), client.index("registration.addEventListener('updatefound'"))

    # Require browser acceptance to serialize activation before a controlled reload and controller proof.
    def test_browser_acceptance_serializes_worker_readiness(self):
        # Read the browser acceptance harness as governed source without starting Chromium.
        harness = (ROOT / "tests" / "run_tests.py").read_text(encoding="utf-8")
        # Isolate the narrowed PWA case so unrelated browser reloads cannot satisfy order checks.
        pwa_case = harness[harness.index("def pwa_installable_shell"):harness.index("run_case('BR-PWA-001")]
        # Locate the native active-registration readiness boundary.
        ready_index = pwa_case.index("navigator.serviceWorker.ready")
        # Locate the controlled reload performed only after activation completes.
        reload_index = pwa_case.index("pwa_page.reload(wait_until='domcontentloaded')")
        # Locate the metadata-driven synchronous controller assertion after the controlled navigation.
        controller_index = pwa_case.index('pwa_page.wait_for_function("(version) => Boolean(navigator.serviceWorker.controller) && window.CasinoPwa?.version===version",arg=packaged_version,timeout=8000)')
        # Locate the first explicit navigation after readiness; this is the governed offline route proof, not a bootstrap reload race.
        navigation_index = pwa_case.index("pwa_page.goto")
        # Require activation, reload, and controller proof to remain in deterministic lifecycle order.
        self.assertLess(ready_index, reload_index)
        # Require the reload to precede controller proof rather than racing an uncontrolled initial client.
        self.assertLess(reload_index, controller_index)
        # Require initial activation and controller proof before any explicit route navigation.
        self.assertLess(controller_index, navigation_index)
        # Reject the async polling predicate that previously allowed registration state to race page traffic.
        self.assertNotIn('wait_for_function("async () => (await navigator.serviceWorker.getRegistrations())', pwa_case)
        # Require Playwright's keyword-only argument boundary for each parameterized PWA display-state wait.
        self.assertIn("dataset.state===state\",arg=pwa_states[state],timeout=3000", pwa_case)
        # Require the same keyword-only boundary for locale synchronization before evidence capture.
        self.assertIn("getLocaleState().locale===locale\",arg=pwa_locale,timeout=5000", pwa_case)
        # Reject the positional forms that fail before service-worker acceptance can begin.
        self.assertNotIn("dataset.state===state\",pwa_states[state],timeout=3000", pwa_case)
        # Reject the locale positional form independently so either regression is diagnosed without a hosted browser.
        self.assertNotIn("getLocaleState().locale===locale\",pwa_locale,timeout=5000", pwa_case)
        # Require the synthetic mismatched worker message and listener-state read to share one synchronous browser task.
        self.assertIn("dispatchEvent(new MessageEvent('message',{data:{type:'PWA_VERSION',version:'0.0.0'}})); return window.CasinoPwa?.state()||''", pwa_case)
        # Reject an asynchronous stale-client poll that can lose the short-lived listener result to reconnect completion.
        self.assertNotIn("wait_for_function(\"() => window.CasinoPwa?.state()==='stale-client'\"", pwa_case)
        # Require the captured real-listener result to remain fail-closed.
        self.assertIn("assert stale_client_state=='stale-client',stale_client_state", pwa_case)

    # Require exact-head Browser evidence to exercise a real one-click multi-tab worker promotion. (PWA-003, TEST-095)
    def test_browser_acceptance_exercises_multitab_update(self):
        # Read the Browser harness as governed source without starting Chromium locally.
        harness = (ROOT / "tests" / "run_tests.py").read_text(encoding="utf-8")
        # Isolate the real update case so synthetic PWA display states cannot satisfy this contract.
        update_case = harness[harness.index("def pwa_multitab_one_click_update"):harness.index("run_case('BR-PWA-UPDATE-001")]
        # Require the prior worker to use a distinct URL derived from canonical module metadata.
        self.assertIn("previous_worker_version=f'{packaged_version}-previous'", update_case)
        # Require all three production-shaped same-origin clients from the reproduced regression.
        self.assertIn("docs_page.goto(f'{base}/api-docs'", update_case)
        # Require the public signup client independently from the API-docs seed.
        self.assertIn("signup_page.goto(f'{base}/enroll/signup'", update_case)
        # Require the Casino client to observe the genuine waiting-worker banner.
        self.assertIn("window.CasinoPwa?.state()==='update'", update_case)
        # Require exactly one player-visible Apply click in the entire real update case.
        self.assertEqual(update_case.count("get_by_test_id('pwa-update-reload').click()"), 1)
        # Require the single click to be bound to the controllerchange-owned reload.
        self.assertIn("expect_navigation(wait_until='domcontentloaded'", update_case)
        # Require each controlled tab to prove the canonical controller independently.
        self.assertIn("for update_page in update_pages", update_case)
        # Require terminal waiting and banner residue to be absent after the one reload.
        self.assertIn("not final_update['waiting']", update_case)
        # Require the exact Browser case to remain mapped to the permanent update requirements.
        self.assertIn("run_case('BR-PWA-UPDATE-001',['PWA-003','TEST-095','TEST-153']", harness)

    # Require page-side offline controls and authoritative reconnect behavior.
    def test_client_fails_closed_and_refreshes_authoritatively(self):
        # Read the PWA controller source.
        client = (ROOT / "web" / "core" / "pwa.js").read_text(encoding="utf-8")
        # Read the frozen API helper source.
        api_source = (ROOT / "web" / "core" / "api.js").read_text(encoding="utf-8")
        # Read the application reconnect integration source.
        app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        # Require Apply now to await an installing worker's bounded transition to waiting. (PWA-003)
        self.assertIn("async function resolveWaitingWorker()", client)
        # Require the click action to use the resolved worker rather than racing registration.waiting.
        self.assertIn("const worker = await resolveWaitingWorker()", client)
        # Require activation to remain explicit and controllerchange-owned.
        self.assertIn("worker.postMessage({ type: 'SKIP_WAITING' })", client)
        # Require a bounded transition wait in addition to the existing activation timeout.
        self.assertIn("window.setTimeout(() => finish(null), 4000)", client)
        # Require native disabled state rather than pointer-only suppression.
        self.assertIn("control.disabled = true", client)
        # Require PWA-owned controls to restore without overwriting application-owned disabled state.
        self.assertIn("data-pwa-offline-disabled", client)
        # Require authoritative reconnect to preserve a fail-closed failure state.
        self.assertIn("renderPwaState('reconnect-failed')", client)
        # Require offline API calls to fail before fetch and carry a stable code.
        self.assertLess(api_source.index("navigator.onLine === false"), api_source.index("await transportFetch(path, init)"))
        # Require the stable no-replay offline error to flow through the localized safe-error boundary.
        self.assertIn("playerSafeError('OFFLINE')", api_source)
        # Require the shared safe-error constructor to preserve the machine-readable code separately.
        self.assertIn("error.code = code || 'ACTION_FAILED'", api_source)
        # Require application reconnect to revalidate the session through current-user state.
        self.assertIn("const authenticated = await refreshCurrentSession()", app)
        # Require route-aware terminal status after enterAuthenticated remounts the route.
        self.assertIn("restoredRoute === 'lobby' ? 'online' : 'route-restored'", app)
        # Require protected API 401s to notify the app shell instead of leaving stale authenticated chrome mounted.
        self.assertIn("casino-session-expired", api_source)
        # Require the shell listener to ignore expected anonymous probes on public invitation/login surfaces.
        self.assertIn("window.addEventListener('casino-session-expired', () => { if (currentSession) renderExpiredSessionGate(); });", app)
        # Require login and guest-entry failures to stay local to their public auth forms.
        self.assertIn("SESSION_EXPIRY_PUBLIC_PATHS", api_source)
        # Require the shared teardown helper to clear cached current-user state.
        self.assertIn("currentSession = null", app[app.index("function clearAuthenticatedShellState(options = {})"):app.index("function renderExpiredSessionGate()")])
        # Require the session-expired shell path to run shared teardown before rendering login.
        self.assertLess(app.index("clearAuthenticatedShellState()", app.index("function renderExpiredSessionGate()")), app.index("renderLoginGate(t('pwa.expiredSession'", app.index("function renderExpiredSessionGate()")))
        # Require protected-route authorization failure handling to precede the generic game-load error panel.
        self.assertLess(app.index("err?.code === 'UNAUTHORIZED'"), app.index("Could not load ${safe(routeLabel(targetRoute))}"))

    # Require trial deep links to show an immediate route-restoration surface before slow session hydration.
    def test_initial_game_route_restore_placeholder_precedes_session_refresh(self):
        # Read the application shell source without launching a browser.
        app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        # Isolate bootstrapping so the startup order cannot be satisfied by reconnect code.
        init_block = app[app.index("async function init()"):app.index("// Poll shell state periodically")]
        # Require the startup placeholder helper to remain present.
        self.assertIn("function renderInitialRouteRestore()", app)
        # Require the placeholder to use the browser route rather than a stale active route.
        self.assertIn("const restoredRoute = routeFromLocation()", app)
        # Require the placeholder to render inside the governed game-screen outlet.
        self.assertIn("view.className = 'screen game-screen'", app)
        # Require stable test identity for browser diagnostics and future acceptance evidence.
        self.assertIn('data-testid="route-restore-loading"', app)
        # Require localized route-restoration copy instead of a blank or raw loading panel.
        self.assertIn("t('routeRestore.title'", app)
        # Locate i18n initialization because route copy depends on the loaded shell dictionary.
        i18n_index = init_block.index("await initI18n")
        # Locate the immediate placeholder render in the startup path.
        placeholder_index = init_block.index("renderInitialRouteRestore()")
        # Locate current-user refresh, which can be slow on hosted trial sessions.
        session_index = init_block.index("await refreshCurrentSession()")
        # Require i18n before placeholder so EN/RU startup copy is available.
        self.assertLess(i18n_index, placeholder_index)
        # Require the placeholder before session refresh so direct game routes never sit visually blank.
        self.assertLess(placeholder_index, session_index)

    # Prove the real wallet controller settles exact values and owns every transient lifecycle resource. (UX-023)
    def test_wallet_celebration_lifecycle_is_deterministic_and_stale_safe(self):
        # Resolve Node from PATH before consulting the desktop-bundled dependency runtime.
        node = shutil.which("node")
        # Name the bundled Node fallback used by repository frontend tests on Windows.
        bundled_node = pathlib.Path("C:/Users/andre/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe")
        # Use the bundled runtime only when PATH does not already provide Node.
        if not node and bundled_node.is_file():
            # Select the verified bundled executable without changing PATH.
            node = str(bundled_node)
        # Skip only when this environment has no JavaScript runtime at either supported location.
        if not node:
            # Report the unavailable optional runtime through unittest's normal skip mechanism.
            self.skipTest("Node is unavailable for the wallet lifecycle contract")
        # Resolve the production module through a file URL so the test executes its exact bytes.
        module_url = (ROOT / "web" / "core" / "celebrate.js").resolve().as_uri()
        # Build one dependency-free deterministic DOM, clock, and lifecycle harness around the real module.
        script = f"""
// Import the exact production controller rather than copying any implementation into the test.
import {{ createWalletCelebration, createWalletCelebrationLifecycle, MAX_COIN_COUNT }} from {json.dumps(module_url)};
// Fail with one focused label when a deterministic contract assertion is false.
const assert = (condition, label) => {{ if (!condition) throw new Error(label); }};
// Compare structured values without depending on object identity.
const equal = (actual, expected, label) => assert(JSON.stringify(actual) === JSON.stringify(expected), `${{label}}: ${{JSON.stringify(actual)}}`);
// Retain any production-path console error instead of allowing a silent Browser regression.
const consoleErrors = [];
// Replace only console.error for the duration of this isolated subprocess.
const originalConsoleError = console.error;
// Capture every unexpected error-level diagnostic without printing dynamic content.
console.error = (...args) => consoleErrors.push(args);
// Retain any asynchronous rejection that escapes the lifecycle manager.
const unhandledRejections = [];
// Capture unhandled rejections through Node's process-level browser-equivalent seam.
process.on('unhandledRejection', reason => unhandledRejections.push(reason));
// Model the exact class operations used by the wallet controller.
class FakeClassList {{
  // Allocate one private class-name set per fake element.
  constructor() {{ this.values = new Set(); }}
  // Add every requested presentation class.
  add(...names) {{ for (const name of names) this.values.add(name); }}
  // Remove every requested presentation class.
  remove(...names) {{ for (const name of names) this.values.delete(name); }}
  // Report exact class membership for lifecycle assertions.
  contains(name) {{ return this.values.has(name); }}
}}
// Model only the DOM surface required by the production controller.
class FakeElement {{
  // Initialize one detached element with owned children, attributes, and style variables.
  constructor(tag) {{ this.tag = tag; this.children = []; this.parentElement = null; this.className = ''; this.classList = new FakeClassList(); this.attributes = new Map(); this.style = {{ values: new Map(), setProperty: (name, value) => this.style.values.set(name, value) }}; this.textContent = ''; }}
  // Attach a child under this exact fake parent.
  appendChild(child) {{ child.parentElement = this; this.children.push(child); return child; }}
  // Remove this exact node without touching siblings.
  remove() {{ if (!this.parentElement) return; this.parentElement.children = this.parentElement.children.filter(child => child !== this); this.parentElement = null; }}
  // Store one attribute as normalized text.
  setAttribute(name, value) {{ this.attributes.set(name, String(value)); }}
  // Remove one owned attribute.
  removeAttribute(name) {{ this.attributes.delete(name); }}
  // Read one attribute for exact Browser-marker parity.
  getAttribute(name) {{ return this.attributes.has(name) ? this.attributes.get(name) : null; }}
  // Return the test-owned wallet for the controller's reviewed closest lookup.
  closest(selector) {{ return selector === '.wallet-pill' ? wallet : null; }}
  // Return stable wallet geometry for deterministic coin-layer placement.
  getBoundingClientRect() {{ return {{ left: 100, top: 20, width: 200, height: 52 }}; }}
}}
// Create one document body that owns every large-gain layer.
const body = new FakeElement('body');
// Provide exact element construction without observers, layout engines, or browser globals.
const documentRef = {{ body, createElement: tag => new FakeElement(tag) }};
// Create the persistent wallet pill used across lifecycle transitions.
const wallet = new FakeElement('section');
// Create the persistent authoritative amount node.
const amount = new FakeElement('strong');
// Mount the amount under the wallet so transient cleanup can be distinguished from persistent content.
wallet.appendChild(amount);
// Track deterministic timeout callbacks by exact handle.
const timerCallbacks = new Map();
// Retain every allocated callback so canceled stale callbacks can be replayed hostilely.
const timerHistory = [];
// Allocate monotonically increasing fake timer handles.
let nextTimer = 0;
// Store one callback without waiting on wall-clock time.
const setTimer = callback => {{ const handle = ++nextTimer; timerCallbacks.set(handle, callback); timerHistory.push(callback); return handle; }};
// Cancel only the exact requested fake timer.
const clearTimer = handle => timerCallbacks.delete(handle);
// Execute all currently live timers until the deterministic queue is empty.
const flushTimers = () => {{ while (timerCallbacks.size) {{ const callbacks = [...timerCallbacks.entries()]; timerCallbacks.clear(); for (const [, callback] of callbacks) callback(); }} }};
// Track lifecycle listeners so disposal proves exact removal.
const lifecycleListeners = new Map();
// Provide the controller's bounded pagehide listener surface.
const lifecycleTarget = {{ addEventListener: (name, callback) => lifecycleListeners.set(name, callback), removeEventListener: (name, callback) => {{ if (lifecycleListeners.get(name) === callback) lifecycleListeners.delete(name); }}, emit: name => lifecycleListeners.get(name)?.() }};
// Toggle the deterministic reduced-motion preference without browser media state.
let reducedMotion = false;
// Retain exact action terminal receipts for exactly-once assertions.
const completions = [];
// Retain the count of application-owned authoritative display writes.
let displayWrites = 0;
// Retain the application-authoritative current-session value across page lifecycle events.
let authoritativeBalance = 100;
// Format values exactly like the shared two-decimal wallet renderer.
const formatAmount = value => Number(value).toFixed(2);
// Settle the visible authoritative amount exactly once per owned update.
const settleDisplay = value => {{ displayWrites += 1; authoritativeBalance = value; amount.textContent = formatAmount(value); }};
// Build a fresh production controller for each authenticated or BFCache-restored generation.
const createController = () => createWalletCelebration({{ amountNode: amount, walletNode: wallet, documentRef, setTimer, clearTimer, prefersReducedMotion: () => reducedMotion, random: () => 0.5, formatAmount, onComplete: receipt => completions.push(receipt) }});
// Build the same production lifecycle manager used by app.js around those controller generations.
const lifecycle = createWalletCelebrationLifecycle({{ lifecycleTarget, createController, currentBalance: () => authoritativeBalance, settleDisplay, shouldMount: () => true }});
// Read the current controller snapshot without exposing its private identity.
const controllerSnapshot = () => lifecycle.snapshot().controller;
// Seed the first authenticated wallet render without any decorative or completion work.
amount.textContent = '100.00';
// Adopt the exact initial balance without writing it again.
lifecycle.mount(100);
// Require initial load to own no timer, node, class, action, or callback.
equal(controllerSnapshot(), {{ active: null, timers: 0, nodes: 0, disposed: false, balance: 100 }}, 'initial snapshot');
// Require the initial render not to publish a completion or duplicate wallet write.
equal([displayWrites, completions.length], [0, 0], 'initial silence');
// Settle one ordinary gain through the application-owned writer.
lifecycle.update(125, settleDisplay);
// Require one exact write plus one bounded ordinary-gain chip and timer.
equal([amount.textContent, displayWrites, controllerSnapshot().active, controllerSnapshot().nodes, controllerSnapshot().timers], ['125.00', 1, 'gain', 1, 1], 'ordinary gain active');
// Require the ordinary gain class without a large-gain coin layer.
assert(wallet.classList.contains('wallet-celebration-gain') && body.children.length === 0, 'ordinary gain presentation');
// Complete the ordinary gain without wall-clock waiting.
flushTimers();
// Require one settled receipt and synchronous transient cleanup.
equal([completions.map(row => row.outcome), controllerSnapshot().nodes, controllerSnapshot().timers, wallet.children.length], [['settled'], 0, 0, 1], 'ordinary gain settled');
// Settle one loss exactly once without creating celebratory state.
lifecycle.update(90, settleDisplay);
// Require the exact loss value, one immediate completion, and zero resources.
equal([amount.textContent, displayWrites, completions.at(-1).kind, completions.at(-1).outcome, controllerSnapshot().nodes, controllerSnapshot().timers], ['90.00', 2, 'loss', 'settled', 0, 0], 'loss settled');
// Start one large gain that owns a bounded chip, layer, and exact coin count.
lifecycle.update(400, settleDisplay);
// Resolve the single large-gain layer from the fake document body.
const firstCoinLayer = body.children[0];
// Retain its scheduled callback for hostile replay after interruption.
const staleLargeGainCallback = timerHistory.at(-1);
// Require the exact large-gain class, two owned nodes, and bounded coin count.
equal([amount.textContent, controllerSnapshot().active, controllerSnapshot().nodes, firstCoinLayer.children.length], ['400.00', 'big-gain', 2, MAX_COIN_COUNT], 'large gain bounded');
// Overlap the large gain with a newer ordinary gain before its timer settles.
lifecycle.update(425, settleDisplay);
// Require the older action to terminalize once and the latest exact amount to win immediately.
equal([amount.textContent, completions.at(-1).to, completions.at(-1).outcome, body.children.length, controllerSnapshot().active], ['425.00', 400, 'interrupted', 0, 'gain'], 'overlap ownership');
// Replay the canceled stale callback to model an already-queued browser task.
staleLargeGainCallback();
// Require stale completion to leave the newer exact display and action untouched.
equal([amount.textContent, controllerSnapshot().active, completions.filter(row => row.to === 400).length], ['425.00', 'gain', 1], 'stale callback suppressed');
// Complete the newer action through its own live timer.
flushTimers();
// Require exactly one terminal receipt for the newer gain.
equal(completions.filter(row => row.to === 425).map(row => row.outcome), ['settled'], 'newer gain settles once');
// Start a route-interruptible large gain and retain its callback.
lifecycle.update(800, settleDisplay);
// Capture the pending callback before navigation cancels it.
const staleNavigationCallback = timerHistory.at(-1);
// Interrupt the real controller through the application navigation boundary.
lifecycle.interrupt('navigation');
// Require exact value retention plus zero nodes, timers, classes, and active action.
equal([amount.textContent, controllerSnapshot().active, controllerSnapshot().nodes, controllerSnapshot().timers, wallet.getAttribute('data-wallet-celebration')], ['800.00', null, 0, 0, null], 'navigation cleanup');
// Replay the canceled navigation callback hostilely.
staleNavigationCallback();
// Require one navigation receipt and no stale display or completion publication.
equal([amount.textContent, completions.filter(row => row.to === 800).map(row => row.outcome)], ['800.00', ['navigation']], 'navigation stale-safe');
// Enable the deterministic reduced-motion branch.
reducedMotion = true;
// Settle a reduced-motion large gain through the same exact writer.
lifecycle.update(1100, settleDisplay);
// Require immediate exact completion with no transient timer, node, or class.
equal([amount.textContent, completions.at(-1).outcome, controllerSnapshot().nodes, controllerSnapshot().timers, wallet.classList.contains('wallet-celebration-big')], ['1100.00', 'settled', 0, 0, false], 'reduced motion');
// Restore normal motion before testing page-lifecycle disposal.
reducedMotion = false;
// Start one active gain that pagehide must terminalize once.
lifecycle.update(1125, settleDisplay);
// Capture the pending pre-pagehide callback for hostile replay after restoration.
const stalePagehideCallback = timerHistory.at(-1);
// Retain any synchronous error from the exact application lifecycle sequence.
let lifecycleError = '';
// Dispatch the real registered pagehide lifecycle callback.
try {{
  // Drive the real manager's pagehide path so it disposes and forgets the controller identity.
  lifecycleTarget.emit('pagehide');
  // Replay the canceled old-generation callback while no controller is mounted.
  stalePagehideCallback();
  // Model refreshBalance's single exact synchronous wallet write while the page is hidden.
  authoritativeBalance = 1200; amount.textContent = '1200.00';
  // Deliver the queued application update while hidden; the manager must ignore it without throwing.
  lifecycle.update(1200);
  // Drive the real manager's pageshow path so it settles and silently seeds the current value.
  lifecycleTarget.emit('pageshow');
  // Replay the same stale old-generation callback after a new controller owns the wallet.
  stalePagehideCallback();
  // Deliver one post-restore authoritative wallet refresh through the remounted controller.
  lifecycle.update(1225, settleDisplay);
  // Complete only the remounted action's live timer.
  flushTimers();
// Capture a synchronous integration error without allowing the subprocess to hide it.
}} catch (error) {{ lifecycleError = error.message; }}
// Require the old generation to complete once at pagehide and the manager to remain listener-bound.
equal([completions.filter(row => row.to === 1125).map(row => row.outcome), lifecycleListeners.size], [['pagehide'], 2], 'pagehide generation retired');
// Require a fresh mounted controller seeded from the hidden-period authoritative balance.
equal([lifecycle.snapshot().mounted, controllerSnapshot().balance, amount.textContent], [true, 1225, '1225.00'], 'pageshow remount current');
// Require exactly one post-restore completion and no stale old-generation completion replay.
equal([completions.filter(row => row.to === 1225).map(row => row.outcome), completions.filter(row => row.to === 1125).length], [['settled'], 1], 'pageshow refresh settles once');
// Require the remounted route to retain no timer, transient node, marker, or presentation class.
equal([controllerSnapshot().nodes, controllerSnapshot().timers, body.children.length, wallet.children.length, wallet.getAttribute('data-wallet-celebration'), wallet.classList.contains('wallet-celebration-gain'), wallet.classList.contains('wallet-celebration-big')], [0, 0, 0, 1, null, false, false], 'pageshow cleanup');
// Require the complete pagehide, pageshow, refresh, and stale-replay sequence to emit no error.
equal([lifecycleError, consoleErrors.length, unhandledRejections.length], ['', 0, 0], 'pageshow zero errors');
// Dispose the production lifecycle manager so the harness itself leaves no listener or resource.
lifecycle.dispose();
// Restore the process console after exact zero-error proof.
console.error = originalConsoleError;
// Require exact final cleanup and one application-owned write for every controller-settled change plus pageshow restore.
equal([lifecycleListeners.size, timerCallbacks.size, displayWrites], [0, 0, 9], 'harness cleanup');
"""
        # Execute the real ES module without installing packages or opening a listener.
        result = subprocess.run([node, "--input-type=module", "--eval", script], cwd=ROOT, capture_output=True, text=True, timeout=30, check=False)
        # Require a clean dependency-free lifecycle run without reflecting arbitrary subprocess output on success.
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])

    # Require explicit shell integration and reject observer- or frame-owned wallet authority. (UX-023)
    def test_wallet_celebration_integration_is_explicit_and_observer_free(self):
        # Read the exact controller source for architecture and resource-boundary assertions.
        controller = (ROOT / "web" / "core" / "celebrate.js").read_text(encoding="utf-8")
        # Read the current application integration without executing browser startup.
        app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        # Require the wallet controller to avoid ambient mutation observers and frame loops entirely.
        self.assertNotIn("MutationObserver", controller)
        # Require the controller not to schedule animation frames that could overwrite a newer value.
        self.assertNotIn("requestAnimationFrame", controller)
        # Require application settlement to precede any normal-motion presentation allocation.
        self.assertLess(controller.index("if (settleDisplay) settleDisplay(target)"), controller.index("startGain(action);"))
        # Require initial authenticated rendering before the new controller baseline is seeded.
        self.assertLess(app.index("const initialBalance = updateCurrentUserShell()"), app.index("walletCelebrationLifecycle.mount(initialBalance)"))
        # Require session teardown to dispose and forget the controller before clearing identity.
        teardown = app[app.index("function clearAuthenticatedShellState(options = {})"):app.index("function renderExpiredSessionGate()")]
        # Compare exact lifecycle ordering inside the shared teardown helper.
        self.assertLess(teardown.index("walletCelebrationLifecycle.unmount('session-cleared')"), teardown.index("currentSession = null"))
        # Require route navigation to interrupt decoration before previous-game unmount.
        navigation = app[app.index("export async function navigate"):app.index("// Initialize shell state")]
        # Compare exact interruption and unmount order inside the route controller.
        self.assertLess(navigation.index("walletCelebrationLifecycle.interrupt('navigation')"), navigation.index("loadedGames.get(previous).unmount?.()"))
        # Require refreshed game balances to decorate only after the shared helper's synchronous exact render.
        self.assertIn("queueMicrotask", app)
        # Require the queued update to reject stale session identity before decorating.
        self.assertIn("if (currentSession !== nextSession) return", app)
        # Require the queued current-user path to call the non-throwing lifecycle manager.
        self.assertIn("walletCelebrationLifecycle.update(currentTokenBalance(nextSession))", app)
        # Isolate the production BFCache manager for exact teardown and remount assertions.
        lifecycle = controller[controller.index("export function createWalletCelebrationLifecycle"):]
        # Require pagehide to dispose and forget the exact controller generation.
        self.assertIn("unmount('pagehide')", lifecycle)
        # Require pageshow to settle the current authoritative value before fresh silent seeding.
        self.assertLess(lifecycle.index("settleDisplay(value)"), lifecycle.index("mount(value);"))
        # Require inactive hidden-period updates to return without touching a disposed controller.
        self.assertIn("if (!controller) return { outcome: 'inactive', value }", lifecycle)

    # Require the full narrowed EN/RU and governed-viewport visual matrix.
    def test_visual_matrix_owns_narrowed_pwa_states(self):
        # Load the authoritative executable visual matrix.
        matrix = load_json("tests/visual/visual_matrix.json")
        # Locate the one PWA surface row.
        rows = [row for row in matrix["surfaces"] if row["id"] == "pwa_shell"]
        # Require exactly one governed PWA surface.
        self.assertEqual(len(rows), 1)
        # Read the unique PWA row.
        row = rows[0]
        # Require the exact state set authorized by Workroom #29.
        self.assertEqual(set(row["states"]), EXPECTED_PWA_STATES)
        # Require both repository locales.
        self.assertEqual(row["locales"], ["en-US", "ru-RU"])
        # Require all four governed viewports.
        self.assertEqual(row["viewports"], ["desktop_primary", "desktop_compact", "tablet", "mobile"])


# Run the focused tests when the module is executed directly.
if __name__ == "__main__":
    # Exit through unittest's normal runner and status semantics.
    unittest.main()
