# Validate the narrowed offline-safe PWA foundation without launching a browser. (PWA-001, PWA-002, TEST-095)
# Import JSON support for manifest, requirement, module, and visual-matrix assertions.
import json
# Import pathlib so every governed artifact is resolved from the repository root.
import pathlib
# Import regular expressions for static JavaScript policy extraction.
import re
# Import struct so PNG dimensions can be verified without image-library dependencies.
import struct
# Import unittest for normal repository test discovery.
import unittest

# Resolve the repository root independently from the caller's working directory.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Name the exact public static paths permitted in the service-worker cache.
EXPECTED_SHELL_ASSETS = {
    "/index.html", "/styles.css", "/app.js", "/manifest.webmanifest", "/assets/favicon.svg",
    "/assets/pwa-icon-192.png", "/assets/pwa-icon-512.png", "/assets/pwa-maskable-192.png", "/assets/pwa-maskable-512.png",
    "/core/api.js", "/core/feedback.js", "/core/i18n.js", "/core/pwa.js", "/core/ui.js", "/core/voice.js",
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
        # Require the exact low-cardinality version response.
        self.assertIn("{ type: 'PWA_VERSION', version: APP_VERSION }", worker)

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
        # Locate the synchronous controller assertion after the controlled navigation.
        controller_index = pwa_case.index("Boolean(navigator.serviceWorker.controller) && window.CasinoPwa?.version==='0.9.5.11'")
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

    # Require page-side offline controls and authoritative reconnect behavior.
    def test_client_fails_closed_and_refreshes_authoritatively(self):
        # Read the PWA controller source.
        client = (ROOT / "web" / "core" / "pwa.js").read_text(encoding="utf-8")
        # Read the frozen API helper source.
        api_source = (ROOT / "web" / "core" / "api.js").read_text(encoding="utf-8")
        # Read the application reconnect integration source.
        app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        # Require native disabled state rather than pointer-only suppression.
        self.assertIn("control.disabled = true", client)
        # Require PWA-owned controls to restore without overwriting application-owned disabled state.
        self.assertIn("data-pwa-offline-disabled", client)
        # Require authoritative reconnect to preserve a fail-closed failure state.
        self.assertIn("renderPwaState('reconnect-failed')", client)
        # Require offline API calls to fail before fetch and carry a stable code.
        self.assertLess(api_source.index("navigator.onLine === false"), api_source.index("await fetch(path, init)"))
        # Require the stable no-replay offline error code.
        self.assertIn("error.code = 'OFFLINE'", api_source)
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
        self.assertIn("currentSession = null", app[app.index("function clearAuthenticatedShellState()"):app.index("function renderExpiredSessionGate()")])
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
