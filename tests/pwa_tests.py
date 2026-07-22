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
        self.assertLess(worker.index("Promise.all(SHELL_ASSETS.map"), worker.index("caches.open(SHELL_CACHE)"))
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
