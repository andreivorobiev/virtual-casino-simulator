# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Verify the repo-owned native transport, session, lifecycle, and deep-link boundary. (TEST-172)"""

# Import concurrent execution to prove one old bearer cannot win two rotations.
from concurrent.futures import ThreadPoolExecutor
# Import JSON for governed contract and persisted-session inspection.
import json
# Import environment access for the bundled Node runtime seam.
import os
# Import portable paths for source and isolated state inspection.
from pathlib import Path
# Import regular expressions for exact source-boundary assertions.
import re
# Import subprocess execution for deterministic Node tests.
import subprocess
# Import temporary directories so auth tests never touch repository data.
import tempfile
# Import unit-test assertions and test discovery.
import unittest
# Import provider-path patching for isolated session documents.
from unittest.mock import patch

# Import the application router for direct no-listener v2 probe evidence.
from casino.app import build_router
# Import the canonical session implementation under test.
from casino.core import auth, storage
# Import production policy parsing without starting the WSGI application.
from casino.core.security import SecurityPolicy
# Import the expected stale-rotation conflict.
from casino.errors import ConflictError

# Resolve the exact checkout independently of the caller directory.
ROOT = Path(__file__).resolve().parents[1]
# Resolve the governed mobile source tree.
MOBILE = ROOT / "mobile"


class MobileCoreSecurityTests(unittest.TestCase):
    """Own deterministic host and source-level mobile security evidence."""

    # Allocate isolated user and session documents for every stateful test.
    def setUp(self) -> None:
        # Create a disposable directory outside configured application state.
        self.temporary = tempfile.TemporaryDirectory(prefix="casino-mobile-core-")
        # Derive isolated provider paths.
        root = Path(self.temporary.name)
        # Patch both identity documents used by session authentication.
        self.path_patches = [patch.object(auth, "USERS_PATH", root / "users.json"), patch.object(auth, "SESSIONS_PATH", root / "sessions.json")]
        # Activate exact path isolation before writing fixtures.
        for path_patch in self.path_patches:
            # Apply this provider-path patch.
            path_patch.start()
        # Seed one synthetic local identity without player or wallet mutation.
        self.user = {"user_id": "mobile_user", "player_id": "mobile_player", "email": "mobile@example.test", "display_name": "Mobile Test", "status": "active", "role": "player", "roles": ["player"], "identity_provider": "local", "password_hash": "unused", "terms_required": False}
        # Persist only the isolated identity fixture.
        auth.save_users({"schema_version": 1, "users": [self.user], "reservations": []})
        # Start with one empty canonical session document.
        auth.save_sessions(auth.default_sessions())

    # Restore module paths and remove disposable state after each test.
    def tearDown(self) -> None:
        # Stop patches in reverse order for symmetric restoration.
        for path_patch in reversed(self.path_patches):
            # Restore the original module path.
            path_patch.stop()
        # Delete only the test-owned temporary directory.
        self.temporary.cleanup()

    # Run complete host-runnable native runtime evidence with no SDK or network.
    def test_node_transport_lifecycle_and_deep_link_suite(self) -> None:
        """Run the complete Node suite against pure injectable runtime modules."""
        # Resolve the bundled or developer-selected Node binary.
        node = os.environ.get("CASINO_NODE_BINARY", "node")
        # Discover every tracked mobile unit test deterministically.
        test_files = sorted(str(path.relative_to(MOBILE)) for path in (MOBILE / "tests").glob("*.test.mjs"))
        # Execute all files once without package installation or native SDK access.
        result = subprocess.run([node, "--test", *test_files], cwd=MOBILE, capture_output=True, text=True, timeout=120, check=False)
        # Surface only a bounded diagnostic tail on failure.
        self.assertEqual(result.returncode, 0, (result.stdout + result.stderr)[-4000:])

    # Prove browser behavior is preserved while native owns lifecycle refresh and transient links.
    def test_transport_and_password_reset_hooks_preserve_boundaries(self) -> None:
        """Require scoped transport, authoritative reconnect, and reset-bearer rerender safety."""
        # Read shared browser transport source.
        api_source = (ROOT / "web" / "core" / "api.js").read_text(encoding="utf-8")
        # Read the native composition entry point.
        runtime_source = (MOBILE / "runtime" / "mobile-runtime.js").read_text(encoding="utf-8")
        # Read the shared auth UI controller.
        app_source = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        # Read the extracted password-reset view that now owns transient bearer state.
        reset_source = (ROOT / "web" / "views" / "reset.js").read_text(encoding="utf-8")
        # Require only the optional scoped hook in shared browser source.
        self.assertIn("globalThis.CasinoMobileTransport?.fetch", api_source)
        # Reject the former global fetch rewriting defect.
        self.assertNotRegex(runtime_source, r"window\.fetch\s*=")
        # Require reconnect and foreground to share one strict authoritative PWA refresh boundary.
        self.assertNotIn("window.CasinoPwa?.reconnect?.()", runtime_source)
        # Reject a missing controller rather than allowing optional chaining to skip refresh.
        self.assertIn("await window.CasinoPwa.reconnect()", runtime_source)
        self.assertIn("createMobileRecoveryCoordinator", runtime_source)
        # Require one explicit shared initialization handshake before native recovery marks load complete.
        self.assertIn('window.addEventListener("casino:shared-app-ready"', runtime_source)
        # Separate reusable controller construction from repeatable authoritative data readiness.
        self.assertIn('window.addEventListener("casino:shared-app-controller-ready"', runtime_source)
        self.assertIn("sharedApplicationControllerPromise", runtime_source)
        self.assertIn("sharedApplicationLoadInFlight", runtime_source)
        # Require shared load/reconnect to release mutations through an exact reconciliation ticket.
        self.assertIn("lifecycleGate.beginReconciliation()", runtime_source)
        self.assertIn("lifecycleGate.completeReconciliation(ticket)", runtime_source)
        self.assertIn("casino:shared-app-ready", app_source)
        # Require initial non-auth state failures to reject readiness rather than resolving green.
        self.assertIn("throw err;", app_source)
        # Require app and network listeners before initial snapshots so no startup edge is lost.
        self.assertLess(runtime_source.index('App.addListener("appStateChange"'), runtime_source.index("await App.getState()"))
        self.assertLess(runtime_source.index('Network.addListener("networkStatusChange"'), runtime_source.index("await Network.getStatus()"))
        # Require raw negative native edges to invalidate authority before queued observer work.
        self.assertLess(runtime_source.index("lifecycleGate.setConnected(false)"), runtime_source.index("networkObservation.event(status)"))
        self.assertLess(runtime_source.index("lifecycleGate.setActive(false)"), runtime_source.index("appObservation.event(state)"))
        # Require warm-link listener registration before the cold launch URL snapshot.
        self.assertLess(runtime_source.index('App.addListener("appUrlOpen"'), runtime_source.index("await App.getLaunchUrl()"))
        # Require one shared exclusive account-switch boundary to revoke through native code.
        self.assertIn("CasinoMobileTransport.prepareAccountSwitch()", api_source)
        # Require both registered login and guest creation to use the same compound transaction.
        self.assertEqual(api_source.count("runNativeAccountSwitch(() => post('/api/v2/auth/"), 2)
        # Require a module-held reset bearer rather than a rerender-local token.
        self.assertIn("let passwordResetBearerToken = '';", reset_source)
        # Require arrival capture and immediate token-free history replacement.
        self.assertIn("passwordResetBearerToken = holdTransientBearer(passwordResetBearerToken, arrivalToken);", reset_source)
        self.assertIn("historyRef.replaceState({}, '', '/account/reset')", reset_source)
        # Require only terminal success to clear the held reset bearer.
        self.assertEqual(reset_source.count("passwordResetBearerToken = '';"), 2)

    # Require exact verified-link, secure-vault, and header ownership source contracts.
    def test_native_verified_link_and_vault_sources_are_exact(self) -> None:
        """Verify Android and iOS source contracts without claiming signed-device evidence."""
        # Read the release-bearing Android manifest.
        android_manifest = (MOBILE / "android" / "app" / "src" / "main" / "AndroidManifest.xml").read_text(encoding="utf-8")
        # Require verified HTTPS ownership for only the canonical host.
        self.assertIn('android:autoVerify="true"', android_manifest)
        self.assertIn('android:scheme="https" android:host="casino.tiltseven.com"', android_manifest)
        # Read Android native transport implementation.
        android_source = (MOBILE / "android" / "app" / "src" / "main" / "java" / "io" / "github" / "andreivorobiev" / "virtualcasino" / "CasinoSecureTransportPlugin.java").read_text(encoding="utf-8")
        # Require Android Keystore and encrypted record primitives.
        self.assertIn('KeyStore.getInstance("AndroidKeyStore")', android_source)
        self.assertIn('Cipher.getInstance("AES/GCM/NoPadding")', android_source)
        # Require the strict native public-header allowlist and cache bypass.
        self.assertIn('Arrays.asList("accept", "content-type", "idempotency-key")', android_source)
        self.assertIn("connection.setUseCaches(false)", android_source)
        # Require Android networking resources to close through every success and exception path.
        self.assertIn("finally {", android_source)
        self.assertIn("connection.disconnect();", android_source)
        # Require terminal logout/end/revoke success and an already-invalid 401 to clear the vault once.
        self.assertIn("terminalSession && status >= 200 && status < 300", android_source)
        self.assertIn('response.getInt("status") != 200 && response.getInt("status") != 401', android_source)
        # Require the OS-vault destination to be pinned independently from JavaScript configuration.
        self.assertIn('"https://casino.tiltseven.com".equals(value)', android_source)
        # Require Java and Swift to share the exact bounded API path grammar.
        self.assertIn('^/api/(?:v1|v2)/[A-Za-z0-9_./?=&%+-]*$', android_source)
        # Require the public Android bridge to reject missing, negative, and non-integral generations.
        self.assertIn('requestedGeneration instanceof Number', android_source)
        self.assertIn('((Number) requestedGeneration).intValue() < 0', android_source)
        # Require Android native origin configuration to reject query and fragment ambiguity.
        self.assertIn('uri.getQuery() != null || uri.getFragment() != null', android_source)
        # Require every successful Android response and credential issuance to use strict standard envelopes.
        self.assertIn('successStatus && (!Boolean.TRUE.equals(envelope.opt("ok")) || data == null)', android_source)
        self.assertIn('if (credentialIssuance && !issuedSession)', android_source)
        # Restrict credential capture and persistence to exact successful issuance responses.
        self.assertIn("if (credentialIssuance && session != null)", android_source)
        self.assertIn("else if (issuedSession) saveRecord(record)", android_source)
        # Require probe generation equality, active-vault issuance rejection, and exact terminal acknowledgements.
        self.assertIn('storedSessionGeneration < 1', android_source)
        self.assertIn('active session replacement rejected', android_source)
        self.assertIn('terminal acknowledgement invalid', android_source)
        # Require a bounded recursive Android scan after exact credential capture and stripping.
        self.assertIn('rejectCredentialResidue(envelope, 0, new int[] {0})', android_source)
        self.assertIn('"credential residue"', android_source)
        # Require Android configuration and every request to share the same vault monitor.
        self.assertIn('public synchronized void configure', android_source)
        self.assertIn('private synchronized JSONObject perform', android_source)
        self.assertRegex(android_source, r'public void probe[\s\S]+synchronized \(this\)[\s\S]+public void revokeAndClear')
        # Read the iOS entitlement and native transport implementation.
        ios_entitlements = (MOBILE / "ios" / "App" / "App" / "App.entitlements").read_text(encoding="utf-8")
        # Require only the exact associated domain.
        self.assertIn("applinks:casino.tiltseven.com", ios_entitlements)
        # Read iOS secure transport implementation.
        ios_source = (MOBILE / "ios" / "App" / "App" / "CasinoSecureTransportPlugin.swift").read_text(encoding="utf-8")
        # Require device-only, non-synchronizing Keychain storage.
        self.assertIn("kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly", ios_source)
        self.assertIn("kSecAttrSynchronizable as String: false", ios_source)
        # Require cookies and caches to remain disabled in native URL sessions.
        self.assertIn("configuration.httpShouldSetCookies = false", ios_source)
        self.assertIn("configuration.urlCache = nil", ios_source)
        # Require every ephemeral iOS networking session to invalidate on every exit path.
        self.assertIn("defer { session.finishTasksAndInvalidate() }", ios_source)
        # Require iOS terminal-session clearing and already-invalid predecessor parity.
        self.assertIn("terminalSession && (200..<300).contains(http.statusCode)", ios_source)
        self.assertIn('[200, 401].contains(result["status"] as? Int ?? 0)', ios_source)
        # Require the same independently pinned credential destination on iOS.
        self.assertIn('value == "https://casino.tiltseven.com"', ios_source)
        # Require iOS to reject redirects instead of inheriting URLSession follow behavior.
        self.assertIn("willPerformHTTPRedirection", ios_source)
        # Require the public iOS bridge to reject missing or negative request generations.
        self.assertIn('guard let expectedGeneration = call.getInt("generation"), expectedGeneration >= 0', ios_source)
        # Require iOS native origin configuration to reject query and fragment ambiguity.
        self.assertIn('components.query == nil, components.fragment == nil', ios_source)
        # Require every successful iOS response and credential issuance to use strict standard envelopes.
        self.assertIn('envelopeObject["ok"] as? Bool == true', ios_source)
        self.assertIn('guard !credentialIssuance || issuedSession', ios_source)
        # Restrict iOS credential capture and vault writes to exact successful issuance responses.
        self.assertIn('if credentialIssuance, var payload = envelope["data"]', ios_source)
        self.assertIn("else if issuedSession { try saveRecord(record) }", ios_source)
        # Require probe generation equality, active-vault issuance rejection, and exact terminal acknowledgements.
        self.assertIn('sessionGeneration == storedSessionGeneration', ios_source)
        self.assertIn('["/api/v2/auth/login", "/api/v2/auth/guest"].contains(path)', ios_source)
        self.assertIn('[acknowledgement] as? Bool == true', ios_source)
        # Require a bounded recursive iOS scan after exact credential capture and stripping.
        self.assertIn('_ = try rejectCredentialResidue(envelope, depth: 0, visited: 0)', ios_source)
        self.assertIn('["token", "csrf_token", "guest_browser_nonce"].contains(name)', ios_source)
        # Require iOS configuration and every request to share the same vault mutation semaphore.
        self.assertRegex(ios_source, r'func configure[\s\S]+sessionMutation\.wait\(\)[\s\S]+func request')
        self.assertIn('if serializeSession { sessionMutation.wait() }', ios_source)
        self.assertRegex(ios_source, r'func probe[\s\S]+sessionMutation\.wait\(\)[\s\S]+serializeSession: false')

    # Require disabled-by-default server origins and secret-free checked configuration.
    def test_contract_and_configuration_are_secret_free(self) -> None:
        """Verify the governed native contract and strict public configuration."""
        # Parse the compatibility contract added for this source-complete slice.
        contract = json.loads((ROOT / "contracts" / "compatibility" / "mobile-client-security.json").read_text(encoding="utf-8"))
        # Require the browser and native authorities to remain distinct.
        self.assertEqual(contract["browser_session"]["authority"], "host-only cookie plus double-submit CSRF")
        self.assertEqual(contract["native_session"]["authority"], "OS-vault bearer plus matching per-session CSRF")
        # Require native cookies and every browser CORS authority to remain forbidden.
        self.assertEqual((contract["native_session"]["cookies"], contract["native_cors"]["status"], contract["native_cors"]["preflight"], contract["native_cors"]["response_origin_header"]), ("forbidden", "disabled", "rejected", "forbidden"))
        # Parse the public CI configuration fixture.
        example = json.loads((MOBILE / "config" / "ci.example.json").read_text(encoding="utf-8"))
        # Require exactly the three public configuration keys.
        self.assertEqual(set(example), {"environment", "backendBaseUrl", "nativeOrigins"})
        # Require the signed public fixture to select the exact governed credential destination.
        self.assertEqual(example["backendBaseUrl"], "https://casino.tiltseven.com")
        # Scan checked public config source for key-shaped secret material.
        public_text = "\n".join(path.read_text(encoding="utf-8") for path in [MOBILE / "runtime" / "config.js", MOBILE / "config" / "ci.example.json"])
        # Reject any credential-like JSON property.
        self.assertIsNone(re.search(r'(?i)["\'](?:password|secret|api[_-]?key|session[_-]?token|csrf[_-]?token)["\']\s*:', public_text))

    # Prove exact default-off origin parsing and production cleartext rejection.
    def test_mobile_origin_policy_is_default_off_and_bounded(self) -> None:
        """Accept only the two exact generated Capacitor origins when explicitly configured."""
        # Build the minimum synthetic production policy environment.
        base = {"CASINO_RESTRICTED_PREVIEW": "1", "CASINO_CANONICAL_ORIGIN": "https://casino.tiltseven.com", "CASINO_TRUSTED_PROXY": "127.0.0.1"}
        # Confirm absence leaves direct native request classification disabled.
        self.assertEqual(SecurityPolicy.from_environment(base).mobile_origins, ())
        # Confirm exact origins normalize deterministically.
        enabled = {**base, "CASINO_MOBILE_ORIGINS": "capacitor://localhost,https://localhost"}
        # Compare the complete accepted native origin tuple.
        self.assertEqual(SecurityPolicy.from_environment(enabled).mobile_origins, ("capacitor://localhost", "https://localhost"))
        # Reject wildcard, local HTTP, unknown host, duplicates, and extra origins.
        for value in ["*", "http://localhost", "https://evil.example", "https://localhost,https://localhost", "capacitor://localhost,https://localhost,https://extra.invalid"]:
            # Require each unreviewed configuration to fail before startup.
            with self.assertRaises(RuntimeError):
                # Parse this invalid exact-origin candidate.
                SecurityPolicy.from_environment({**base, "CASINO_MOBILE_ORIGINS": value})

    # Prove one bearer/CSRF rotation is atomic and predecessor credentials cannot be replayed.
    def test_mobile_rotation_is_atomic_and_generation_bound(self) -> None:
        """Allow exactly one winner for concurrent rotation from the same predecessor."""
        # Create one active session in isolated JSON storage.
        predecessor = auth.create_session(self.user, "mobile-test")
        # Attempt the same exact predecessor rotation concurrently.
        def rotate_once(_: int):
            # Return the committed record or the stable conflict classification.
            try:
                # Rotate under the exact initial generation.
                return auth.rotate_mobile_session(predecessor["session_id"], predecessor["token"], 1)
            # Classify the losing compare-and-swap without leaking values.
            except ConflictError:
                # Return a fixed loser marker.
                return "conflict"
        # Run two contenders against the same provider record.
        with ThreadPoolExecutor(max_workers=2) as pool:
            # Materialize both terminal outcomes.
            outcomes = list(pool.map(rotate_once, range(2)))
        # Require exactly one new credential and one rejected predecessor replay.
        self.assertEqual(sum(isinstance(value, dict) for value in outcomes), 1)
        self.assertEqual(outcomes.count("conflict"), 1)
        # Resolve the single winner.
        winner = next(value for value in outcomes if isinstance(value, dict))
        # Require both secret components and generation to change together.
        self.assertNotEqual((winner["token"], winner["csrf_token"]), (predecessor["token"], predecessor["csrf_token"]))
        self.assertEqual(winner["generation"], 2)
        # Require one durable session record, never overlapping predecessor and successor rows.
        stored = auth.load_sessions()["sessions"]
        self.assertEqual(len(stored), 1)
        self.assertEqual((stored[0]["token_digest"], stored[0]["generation"]), (storage.session_token_digest(winner["token"]), 2))

    # Prove native probe output is deliberately smaller than browser current-user data.
    def test_native_probe_is_minimal_and_secret_free(self) -> None:
        """Return no account, wallet, bearer, CSRF, or guest proof from the native probe."""
        # Create one active session and direct context without an HTTP listener.
        session = auth.create_session(self.user, "mobile-probe")
        # Dispatch the native-only probe through the real registered route.
        result = build_router().dispatch("GET", "/api/v2/auth/mobile/session", context={"mobile_client": True, "session": session, "user": self.user})
        # Require only the fixed top-level fields.
        self.assertEqual(set(result), {"authenticated", "session"})
        # Require the deliberately minimal session keys.
        self.assertEqual(set(result["session"]), {"generation", "issued_at", "expires_at", "status"})
        # Reject every credential and identity field recursively.
        serialized = json.dumps(result, sort_keys=True)
        self.assertNotRegex(serialized, r'"(?:token|csrf_token|guest_browser_nonce|user_id|player_id|account_id)"')

    # Prove ordinary native reads omit browser CSRF while browser compatibility remains exact.
    def test_native_current_user_reads_are_secret_free_without_mutating_session(self) -> None:
        """Project only exact native current-user reads without changing stored or browser session data."""
        # Create one active session and retain its exact persisted generation.
        session = auth.create_session(self.user, "mobile-current")
        # Provide the canonical player projection without touching shared repository state.
        with patch.object(auth.players, "get_player", return_value={"player_id": self.user["player_id"], "display_name": self.user["display_name"], "type": "human", "balance": 0.0, "status": "active"}):
            # Dispatch both native current-user compatibility paths through the real router.
            for path in ("/api/v2/me", "/api/v2/auth/session"):
                # Resolve the native payload under the exact authenticated context.
                result = build_router().dispatch("GET", path, context={"mobile_client": True, "session": session, "user": self.user})
                # Require the ordinary session summary without any credential field.
                self.assertNotRegex(json.dumps(result, sort_keys=True), r'"(?:token|csrf_token|guest_browser_nonce)"')
                # Preserve ordinary public session metadata without adding issuance-only generation fields.
                self.assertNotIn("generation", result["session"])
            # Dispatch the browser path under the same record to preserve its frozen CSRF projection.
            browser = build_router().dispatch("GET", "/api/v2/me", context={"mobile_client": False, "session": session, "user": self.user})
        # Require the browser-readable double-submit value to remain byte-compatible.
        self.assertEqual(browser["session"]["csrf_token"], session["csrf_token"])
        # Require read-only projection to leave the durable session record unchanged.
        self.assertEqual(auth.load_sessions()["sessions"][0]["generation"], session["generation"])

    # Require module ownership and the exact permanent requirement allocation.
    def test_mobile_module_and_requirements_are_governed(self) -> None:
        """Bind mobile source to one descriptor and five accepted requirement records."""
        # Parse the new module descriptor.
        descriptor = json.loads((ROOT / "modules" / "mobile.json").read_text(encoding="utf-8"))
        # Distinguish governed module version from the installable package foundation version.
        self.assertEqual((descriptor["module"], descriptor["version"], descriptor["paths"]), ("mobile", "1.0.0", ["mobile/"]))
        # Parse the generated compatibility requirement registry.
        requirements = json.loads((ROOT / "docs" / "requirements" / "requirements.json").read_text(encoding="utf-8"))["requirements"]
        # Index every permanent id once.
        by_id = {row["id"]: row for row in requirements}
        # Require the exact reviewed IDs and no invented MOBILE prefix.
        self.assertTrue(all(by_id[requirement_id]["status"] == "PASS" for requirement_id in ["CORE-032", "AUTH-019", "SEC-016", "SESSION-013", "TEST-172"]))
        # Prevent the earlier stale allocation from reappearing.
        self.assertNotIn("MOBILE-001", by_id)


# Execute focused evidence when called directly or through the central API runner.
if __name__ == "__main__":
    # Delegate reporting and exit status to unittest.
    unittest.main()
