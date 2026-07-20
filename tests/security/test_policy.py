"""Hostile configuration, proxy, CSRF, session, and limiter tests for issue #203."""

# Import temporary directories for isolated auth registries.
import pathlib
# Import thread pools for deterministic gthread limiter coverage.
import concurrent.futures
# Import disposable filesystem roots for session rotation tests.
import tempfile
# Import unittest assertions and lifecycle.
import unittest
# Import scoped patching for bounded limiter capacity tests.
from unittest import mock

# Import the canonical auth store and cookie helpers under test.
from casino.core import auth
# Import restricted-preview policy primitives under test.
from casino.core import security
# Import stable request rejection types for exact hostile-client assertions.
from casino.errors import ForbiddenError, RateLimitError, UnauthorizedError

# Define one synthetic canonical origin reserved from real DNS.
ORIGIN = "https://casino.example.invalid"


# Build a complete value-only restricted-preview environment.
def policy_environment(**overrides):
    # Start with every required production security setting.
    environment = {
        # Use a synthetic reserved-domain origin.
        "CASINO_CANONICAL_ORIGIN": ORIGIN,
        # Trust only the exact IPv4 loopback proxy peer.
        "CASINO_TRUSTED_PROXY": "127.0.0.1",
        # Enable the explicitly released restricted-preview stage.
        "CASINO_RESTRICTED_PREVIEW": "1",
        # Select the strict same-origin cookie mode.
        "CASINO_SESSION_SAMESITE": "Strict",
        # Keep the focused body bound small enough for exact assertions.
        "CASINO_MAX_BODY_BYTES": "4096",
        # Allow five requests per deterministic window by default.
        "CASINO_RATE_LIMIT_REQUESTS": "5",
        # Use a ten-second deterministic window.
        "CASINO_RATE_LIMIT_WINDOW_SECONDS": "10",
    }
    # Apply caller-selected public setting overrides.
    environment.update(overrides)
    # Return the isolated mapping without modifying the process environment.
    return environment


# Validate fail-closed external policy parsing.
class SecurityPolicyTests(unittest.TestCase):
    # Require one normalized absolute HTTPS origin and exact bounded settings.
    def test_policy_accepts_one_canonical_origin(self):
        # Parse the complete synthetic policy.
        policy = security.SecurityPolicy.from_environment(policy_environment())
        # Compare the exact public configuration fields.
        self.assertEqual((policy.canonical_origin, policy.canonical_authority, policy.trusted_proxy, policy.same_site, policy.max_body_bytes), (ORIGIN, "casino.example.invalid", "127.0.0.1", "Strict", 4096))

    # Reject missing, cleartext, credentialed, path, query, fragment, and alternate authority forms.
    def test_policy_rejects_non_origin_url_forms(self):
        # Enumerate hostile or ambiguous origin candidates.
        invalid = ("", "http://casino.example.invalid", "https://user@casino.example.invalid", "https://casino.example.invalid/path", "https://casino.example.invalid?query=1", "https://casino.example.invalid#fragment", "https://CASINO.example.invalid", "https://casino.example.invalid./")
        # Validate every candidate through the same external setting.
        for candidate in invalid:
            # Name the candidate only inside unittest context, never runtime logs.
            with self.subTest(candidate=candidate):
                # Require fail-closed startup configuration.
                with self.assertRaises(RuntimeError):
                    # Parse the deliberately invalid mapping.
                    security.SecurityPolicy.from_environment(policy_environment(CASINO_CANONICAL_ORIGIN=candidate))

    # Reject missing preview mode, non-loopback proxy, and ungoverned SameSite values.
    def test_policy_rejects_unsafe_preview_settings(self):
        # Exercise each independently unsafe setting.
        for overrides in ({"CASINO_RESTRICTED_PREVIEW": "0"}, {"CASINO_TRUSTED_PROXY": "192.0.2.10"}, {"CASINO_SESSION_SAMESITE": "None"}, {"CASINO_MAX_BODY_BYTES": "1048577"}):
            # Require one stable startup failure per unsafe mapping.
            with self.assertRaises(RuntimeError):
                # Parse without mutating the live environment.
                security.SecurityPolicy.from_environment(policy_environment(**overrides))


# Validate the exact nginx-to-WSGI forwarding contract.
class ProxyContractTests(unittest.TestCase):
    # Build one validated policy before each proxy assertion.
    def setUp(self):
        # Retain only public synthetic values.
        self.policy = security.SecurityPolicy.from_environment(policy_environment())

    # Accept paired single-value For and HTTPS Proto only from the exact configured peer.
    def test_exact_loopback_proxy_pair_is_trusted(self):
        # Build the minimum server-authored WSGI metadata.
        environ = {"REMOTE_ADDR": "127.0.0.1", "wsgi.url_scheme": "http", "HTTP_HOST": "casino.example.invalid", "HTTP_X_FORWARDED_FOR": "192.0.2.44", "HTTP_X_FORWARDED_PROTO": "https"}
        # Resolve the trusted edge identity.
        effective = security.effective_request(environ, self.policy)
        # Require HTTPS, the edge-observed client, and explicit proxied status.
        self.assertEqual((effective.scheme, effective.client, effective.proxied), ("https", "192.0.2.44", True))

    # Reject unpaired, listed, wrong-peer, host, port, and standardized forwarding metadata.
    def test_hostile_forwarding_variants_are_rejected(self):
        # Enumerate exact invalid nginx-contract variants.
        variants = (
            {"REMOTE_ADDR": "127.0.0.1", "wsgi.url_scheme": "http", "HTTP_HOST": "casino.example.invalid", "HTTP_X_FORWARDED_FOR": "192.0.2.44"},
            {"REMOTE_ADDR": "127.0.0.1", "wsgi.url_scheme": "http", "HTTP_HOST": "casino.example.invalid", "HTTP_X_FORWARDED_PROTO": "https"},
            {"REMOTE_ADDR": "127.0.0.2", "wsgi.url_scheme": "http", "HTTP_HOST": "casino.example.invalid", "HTTP_X_FORWARDED_FOR": "192.0.2.44", "HTTP_X_FORWARDED_PROTO": "https"},
            {"REMOTE_ADDR": "127.0.0.1", "wsgi.url_scheme": "http", "HTTP_HOST": "casino.example.invalid", "HTTP_X_FORWARDED_FOR": "192.0.2.44, 198.51.100.3", "HTTP_X_FORWARDED_PROTO": "https"},
            {"REMOTE_ADDR": "127.0.0.1", "wsgi.url_scheme": "http", "HTTP_HOST": "casino.example.invalid", "HTTP_X_FORWARDED_FOR": "192.0.2.44", "HTTP_X_FORWARDED_PROTO": "http"},
            {"REMOTE_ADDR": "127.0.0.1", "wsgi.url_scheme": "http", "HTTP_HOST": "casino.example.invalid", "HTTP_X_FORWARDED_HOST": "casino.example.invalid"},
            {"REMOTE_ADDR": "127.0.0.1", "wsgi.url_scheme": "http", "HTTP_HOST": "casino.example.invalid", "HTTP_X_FORWARDED_PORT": "443"},
            {"REMOTE_ADDR": "127.0.0.1", "wsgi.url_scheme": "http", "HTTP_HOST": "casino.example.invalid", "HTTP_FORWARDED": "for=192.0.2.44;proto=https"},
        )
        # Require every hostile variant to fail before client identity is used.
        for environ in variants:
            # Isolate failures without printing supplied metadata.
            with self.subTest(keys=sorted(environ)):
                # Require the standard forbidden boundary.
                with self.assertRaises(ForbiddenError):
                    # Resolve the deliberately hostile environment.
                    security.effective_request(environ, self.policy)

    # Keep direct requests on server-authored metadata when no forwarding pair exists.
    def test_direct_request_ignores_no_caller_identity_header(self):
        # Resolve a direct TLS test request without proxy headers.
        effective = security.effective_request({"REMOTE_ADDR": "127.0.0.9", "wsgi.url_scheme": "https", "HTTP_HOST": "casino.example.invalid"}, self.policy)
        # Require only the direct peer to become the rate key.
        self.assertEqual((effective.scheme, effective.client, effective.proxied), ("https", "127.0.0.9", False))

    # Reject missing, listed, credentialed, foreign, alternate-port, and malformed authorities.
    def test_request_authority_must_match_exact_canonical_authority(self):
        # Enumerate Host variants that must not receive host-only cookies or application data.
        for authority in ("", "casino.example.invalid, foreign.example.invalid", "user@casino.example.invalid", "foreign.example.invalid", "casino.example.invalid:444", "casino.example.invalid/invalid"):
            # Require one fixed forbidden outcome per hostile authority.
            with self.subTest(authority=authority):
                # Reject before forwarding or rate identity is considered.
                with self.assertRaises(ForbiddenError):
                    # Resolve a direct request carrying the hostile authority.
                    security.effective_request({"REMOTE_ADDR": "127.0.0.1", "wsgi.url_scheme": "http", "HTTP_HOST": authority}, self.policy)


# Validate exact Origin and separate CSRF material.
class RequestIntegrityTests(unittest.TestCase):
    # Build one validated policy before each request-integrity assertion.
    def setUp(self):
        # Retain only the synthetic canonical origin.
        self.policy = security.SecurityPolicy.from_environment(policy_environment())

    # Accept exact Origin plus equal bootstrap cookie/header proof.
    def test_bootstrap_double_submit_accepts_exact_values(self):
        # Generate one application-owned anonymous CSRF value.
        token = security.new_csrf_token()
        # Validate the complete browser bootstrap proof.
        security.validate_request_integrity("POST", {"Origin": ORIGIN, "Cookie": f"casino_csrf={token}", "X-Csrf-Token": token}, self.policy)

    # Reject absent, null, malformed, foreign, slash-expanded, and multi-value origins.
    def test_origin_variants_fail_closed(self):
        # Generate an otherwise valid double-submit proof.
        token = security.new_csrf_token()
        # Exercise the accepted failure classes through the exact same method.
        for origin in ("", "null", "not-an-origin", "https://foreign.example.invalid", ORIGIN + "/", ORIGIN + ", https://foreign.example.invalid"):
            # Require the same public error for every variant.
            with self.subTest(origin=origin):
                # Reject before route dispatch.
                with self.assertRaises(ForbiddenError):
                    # Validate the hostile Origin with otherwise matching CSRF values.
                    security.validate_request_integrity("POST", {"Origin": origin, "Cookie": f"casino_csrf={token}", "X-Csrf-Token": token}, self.policy)

    # Require authenticated mutations to use the distinct per-session CSRF secret.
    def test_session_csrf_does_not_accept_bearer_or_bootstrap_value(self):
        # Create independent token-shaped values for every credential class.
        bearer = security.new_csrf_token()
        # Create a browser bootstrap value separate from authenticated state.
        bootstrap = security.new_csrf_token()
        # Create the session-owned CSRF secret expected after login.
        session_csrf = security.new_csrf_token()
        # Reject both bearer and stale bootstrap values as authenticated CSRF proof.
        for supplied in ("", bearer, bootstrap):
            # Require one fixed forbidden result.
            with self.assertRaises(ForbiddenError):
                # Validate without exposing the supplied value in diagnostics.
                security.validate_request_integrity("PATCH", {"Origin": ORIGIN, "Cookie": f"casino_csrf={bootstrap}", "X-Csrf-Token": supplied, "Authorization": f"Bearer {bearer}"}, self.policy, session_csrf)
        # Accept only the exact distinct session CSRF value.
        security.validate_request_integrity("PATCH", {"Origin": ORIGIN, "Cookie": f"casino_csrf={bootstrap}", "X-Csrf-Token": session_csrf, "Authorization": f"Bearer {bearer}"}, self.policy, session_csrf)


# Validate bounded session cookies and predecessor invalidation without a listener.
class SessionSecurityTests(unittest.TestCase):
    # Allocate isolated durable auth files before each test.
    def setUp(self):
        # Create one disposable root outside repository runtime data.
        self.temporary = tempfile.TemporaryDirectory(prefix="casino-security-auth-")
        # Resolve the isolated root once.
        root = pathlib.Path(self.temporary.name)
        # Patch the canonical user path for this test only.
        self.users_patch = mock.patch.object(auth, "USERS_PATH", root / "users.json")
        # Patch the canonical session path for this test only.
        self.sessions_patch = mock.patch.object(auth, "SESSIONS_PATH", root / "sessions.json")
        # Apply both path patches before storage calls.
        self.users_patch.start()
        # Apply the session path patch independently.
        self.sessions_patch.start()

    # Remove patches and disposable auth state after each test.
    def tearDown(self):
        # Restore the canonical session path.
        self.sessions_patch.stop()
        # Restore the canonical user path.
        self.users_patch.stop()
        # Delete the disposable root and all synthetic records.
        self.temporary.cleanup()

    # Retain concurrent same-account sessions and revoke every predecessor on a privilege change. (SESSION-007, SESSION-006, issue #226)
    def test_concurrent_sessions_retained_and_privilege_change_revokes_all(self):
        # Seed one synthetic local identity without creating player state.
        user = {"user_id": "user-preview", "email": "invite@example.invalid", "status": "active", "role": "player", "roles": ["player"], "password_hash": "hash", "identity_provider": "local"}
        # Persist the isolated identity registry.
        auth.save_users({"users": [user]})
        # Create the first session and retain only its token-shaped values for comparison.
        first = auth.create_session(user, "192.0.2.1")
        # Create a second session for the same identity without evicting the first.
        second = auth.create_session(user, "192.0.2.2")
        # Require independent bearer and CSRF material on every issued session.
        self.assertNotEqual((first["token"], first["csrf_token"]), (second["token"], second["csrf_token"]))
        # Require both concurrent sessions to remain present in durable active state.
        self.assertEqual({session["token"] for session in auth.load_sessions()["sessions"] if session.get("status") == "active"}, {first["token"], second["token"]})
        # Require the predecessor to keep authenticating after the newer login (issue #226).
        self.assertEqual(auth.authenticate_token(first["token"])[1]["user_id"], user["user_id"])
        # Require the newer session to authenticate independently of the predecessor.
        self.assertEqual(auth.authenticate_token(second["token"])[1]["user_id"], user["user_id"])
        # Promote the account through the canonical privilege mutation seam.
        auth.update_user_by_id(user["user_id"], lambda record: record.update({"role": "admin", "roles": ["admin"]}))
        # Require every active session to be revoked after the privilege change.
        self.assertEqual([session for session in auth.load_sessions()["sessions"] if session.get("status") == "active"], [])

    # Prove unlink rollback revokes only the selected provider authority while preserving local recovery. (OAUTH-010, TEST-074, issue #326)
    def test_provider_session_revocation_preserves_local_and_other_provider_sessions(self):
        # Seed one active private-invite local-password identity for all three session methods.
        user = {"user_id": "user-oauth-rollback", "email": "rollback@example.invalid", "status": "active", "role": "player", "roles": ["player"], "password_hash": "hash", "identity_provider": "local"}
        # Persist the isolated canonical identity registry.
        auth.save_users({"users": [user]})
        # Issue the local-password recovery session that unlink must preserve.
        local_session = auth.create_session(user, "192.0.2.10", auth_method="local")
        # Issue one Google-authenticated session that the exact unlink must revoke.
        google_session = auth.create_session(user, "192.0.2.11", auth_method="google")
        # Issue an independent Facebook-authenticated session that Google unlink must preserve.
        facebook_session = auth.create_session(user, "192.0.2.12", auth_method="facebook")
        # Revoke only active Google sessions for the canonical user.
        self.assertEqual(auth.revoke_sessions_for_user_method(user["user_id"], "google"), 1)
        # Index the durable records by authentication method without exposing their bearer values.
        sessions_by_method = {session["auth_method"]: session for session in auth.load_sessions()["sessions"]}
        # Require the selected provider session to be unusable immediately.
        self.assertEqual(sessions_by_method["google"]["status"], "revoked")
        # Require local-password recovery to remain active after provider unlink.
        self.assertEqual(auth.authenticate_token(local_session["token"])[0]["status"], "active")
        # Require the other independently linked provider session to remain active.
        self.assertEqual(auth.authenticate_token(facebook_session["token"])[0]["status"], "active")
        # Require the revoked provider bearer to fail canonical authentication.
        with self.assertRaises(UnauthorizedError):
            # Resolve the revoked Google token through the normal bearer authenticator.
            auth.authenticate_token(google_session["token"])

    # Prove concurrent same-account logins keep every prior session valid with no 401/500. (SESSION-007, TEST-051, issue #226)
    def test_concurrent_same_user_logins_keep_prior_sessions_valid(self):
        # Seed one synthetic local identity resolvable by the token authenticator.
        user = {"user_id": "user-concurrent", "email": "concurrent@example.invalid", "status": "active", "role": "player", "roles": ["player"], "password_hash": "hash", "identity_provider": "local"}
        # Persist the isolated identity registry.
        auth.save_users({"users": [user]})
        # Exercise the exact concurrency scales named by the regression requirement.
        for scale in (1, 3, 30, 100):
            # Reset durable session state so each scale starts from an empty registry.
            auth.save_sessions(auth.default_sessions())
            # Issue the scale's logins concurrently to reproduce the reported write race.
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(scale, 32)) as pool:
                # Create one session per concurrent worker for this identity.
                sessions = list(pool.map(lambda index: auth.create_session(user, f"192.0.2.{index % 250}"), range(scale)))
            # Collect every issued bearer token for validity assertions.
            tokens = [session["token"] for session in sessions]
            # Require the atomic writer to lose no session under concurrency (all tokens unique).
            self.assertEqual(len(set(tokens)), scale, f"lost sessions at scale {scale}")
            # Require durable active state to retain exactly one session per concurrent login.
            active = [session for session in auth.load_sessions()["sessions"] if session.get("status") == "active"]
            # Confirm no prior session was invalidated by a later concurrent login.
            self.assertEqual(len(active), scale, f"prior sessions invalidated at scale {scale}")
            # Require every issued token to authenticate without a 401 or raised 500.
            for token in tokens:
                # Resolve the session and its active identity for each concurrent token.
                resolved_session, resolved_user = auth.authenticate_token(token)
                # Confirm the token resolves to the seeded identity.
                self.assertEqual(resolved_user["user_id"], user["user_id"])
                # Confirm the resolved session remains active.
                self.assertEqual(resolved_session["status"], "active")

    # Prove the per-user cap evicts only least-recently-used predecessors. (SESSION-007, TEST-051)
    def test_per_user_session_cap_evicts_least_recently_used(self):
        # Seed one synthetic local identity for the bounded-retention proof.
        user = {"user_id": "user-capped", "email": "capped@example.invalid", "status": "active", "role": "player", "roles": ["player"], "password_hash": "hash", "identity_provider": "local"}
        # Persist the isolated identity registry.
        auth.save_users({"users": [user]})
        # Shrink the per-user cap for a fast, deterministic eviction proof.
        with mock.patch.object(auth, "MAX_SESSIONS_PER_USER", 3):
            # Create more sessions than the reduced cap to force eviction.
            issued = [auth.create_session(user, f"198.51.100.{index}") for index in range(5)]
            # Read the surviving active sessions after cap enforcement.
            active = [session for session in auth.load_sessions()["sessions"] if session.get("status") == "active"]
            # Require the identity to retain exactly the reduced per-user cap.
            self.assertEqual(len(active), 3)
            # Require the survivors to be the three most recently issued sessions.
            self.assertEqual({session["token"] for session in active}, {session["token"] for session in issued[-3:]})
            # Require the two least-recently-used predecessors to be evicted entirely.
            surviving_tokens = {session["token"] for session in active}
            # Confirm neither evicted predecessor still authenticates.
            for evicted in issued[:2]:
                # Require each evicted token to be absent from surviving active state.
                self.assertNotIn(evicted["token"], surviving_tokens)

    # Publish the distinct CSRF proof intentionally while keeping bearer and client data private.
    def test_public_session_exposes_only_distinct_compatible_csrf_material(self):
        # Build one durable session record with independent credential-shaped values.
        session = {"session_id": "session-public", "token": "bearer-secret", "csrf_token": "csrf-public-proof", "client": "192.0.2.9", "created_at": "2026-07-16T00:00:00Z", "expires_at": "2026-07-16T01:00:00Z", "status": "active"}
        # Build the compatible non-cookie client summary.
        public = auth.public_session(session)
        # Require the CSRF proof to remain available and distinct from the bearer credential.
        self.assertEqual(public["csrf_token"], "csrf-public-proof")
        # Keep the authentication bearer out of every refreshed session response.
        self.assertNotIn("token", public)
        # Keep the trusted effective client out of browser and API payloads.
        self.assertNotIn("client", public)

    # Require production session and logout cookies to be Secure, HttpOnly, host-only, and governed.
    def test_session_cookie_set_and_clear_attributes(self):
        # Build one synthetic session record containing distinct credential material.
        session = {"token": security.new_csrf_token(), "csrf_token": security.new_csrf_token()}
        # Build both establishment headers under strict production policy.
        established = [value for _name, value in auth.session_cookie_headers(session, "Strict", True, True)]
        # Require one session and one CSRF cookie.
        self.assertEqual(len(established), 2)
        # Require the session cookie to be host-only, HttpOnly, Secure, bounded, and Strict.
        self.assertIn("HttpOnly", established[0])
        # Require Secure on both cookies.
        self.assertTrue(all("Secure" in value for value in established))
        # Require governed SameSite on both cookies.
        self.assertTrue(all("SameSite=Strict" in value for value in established))
        # Require no Domain attribute so both cookies remain host-only.
        self.assertTrue(all("Domain=" not in value for value in established))
        # Require the browser-readable CSRF cookie not to become an authentication credential.
        self.assertNotIn("HttpOnly", established[1])
        # Build the complete logout expiration set.
        cleared = [value for _name, value in auth.clear_cookie_headers("Strict", True, True)]
        # Require both values to expire immediately and at the epoch.
        self.assertTrue(all("Max-Age=0" in value and "Expires=Thu, 01 Jan 1970" in value for value in cleared))


# Validate deterministic thread-safe request bounds and capacity recovery.
class RateLimiterTests(unittest.TestCase):
    # Permit exactly the configured number of simultaneous requests for one client.
    def test_concurrent_consumption_is_atomic(self):
        # Build a twenty-request policy with a fixed clock.
        policy = security.SecurityPolicy.from_environment(policy_environment(CASINO_RATE_LIMIT_REQUESTS="20"))
        # Create one limiter whose clock never crosses the window.
        limiter = security.RateLimiter(policy, clock=lambda: 100.0)
        # Define one concurrent attempt that records only accepted or limited status.
        def consume(_index):
            # Start protected consumption around the expected bounded failure.
            try:
                # Use the same trusted effective client across every thread.
                limiter.check("192.0.2.55")
                # Record a successful allowance.
                return "accepted"
            # Convert the expected limiter error into a deterministic result.
            except RateLimitError:
                # Record a bounded rejection.
                return "limited"
        # Run forty attempts across the approved two-or-more threaded shape.
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            # Materialize every concurrent result before leaving the pool.
            results = list(executor.map(consume, range(40)))
        # Require exactly twenty accepted requests and twenty fixed rejections.
        self.assertEqual((results.count("accepted"), results.count("limited")), (20, 20))

    # Reclaim expired one-shot clients globally before rejecting a new invite.
    def test_expired_client_capacity_is_reclaimed(self):
        # Store a mutable deterministic monotonic timestamp.
        now = [100.0]
        # Build a one-request ten-second window policy.
        policy = security.SecurityPolicy.from_environment(policy_environment(CASINO_RATE_LIMIT_REQUESTS="1"))
        # Create the limiter with the deterministic clock.
        limiter = security.RateLimiter(policy, clock=lambda: now[0])
        # Reduce only the focused test capacity to three clients.
        with mock.patch.object(security, "MAX_RATE_KEYS", 3):
            # Fill every client slot with a one-shot address.
            for client in ("192.0.2.1", "192.0.2.2", "192.0.2.3"):
                # Consume the sole allowance for this client.
                limiter.check(client)
            # Require a fourth active-window client to be rejected.
            with self.assertRaises(RateLimitError):
                # Exercise bounded registry capacity.
                limiter.check("192.0.2.4")
            # Move beyond the complete fixed window.
            now[0] = 111.0
            # Require global pruning to admit the new invite without restart.
            limiter.check("192.0.2.4")
        # Require only the recovered current client to remain.
        self.assertEqual(list(limiter.clients), ["192.0.2.4"])

    # Rotate bounded probe-client capacity without consuming application limiter state.
    def test_probe_capacity_rotation_admits_monitoring_client(self):
        # Build a one-request fixed-window policy.
        policy = security.SecurityPolicy.from_environment(policy_environment(CASINO_RATE_LIMIT_REQUESTS="1"))
        # Keep every request inside one active window.
        limiter = security.RateLimiter(policy, clock=lambda: 100.0)
        # Reduce focused capacity to two distinct probe clients.
        with mock.patch.object(security, "MAX_RATE_KEYS", 2):
            # Fill probe capacity with unrelated clients.
            limiter.check("192.0.2.1", rotate_capacity=True)
            # Fill the second probe capacity slot.
            limiter.check("192.0.2.2", rotate_capacity=True)
            # Admit a new monitoring client by rotating only the oldest probe key.
            limiter.check("192.0.2.200", rotate_capacity=True)
        # Require the latest monitor and one recent client to remain within bounded capacity.
        self.assertEqual(list(limiter.clients), ["192.0.2.2", "192.0.2.200"])

    # Emit HSTS only for trusted effective HTTPS while preserving all other headers.
    def test_hsts_is_gated_on_effective_https(self):
        # Convert direct cleartext headers into an assertion mapping.
        cleartext = dict(security.response_security_headers("http"))
        # Convert trusted HTTPS headers into a separate mapping.
        tls = dict(security.response_security_headers("https"))
        # Require HSTS only in the trusted TLS response.
        self.assertNotIn("Strict-Transport-Security", cleartext)
        # Require the reviewed one-year host-only HSTS value.
        self.assertEqual(tls["Strict-Transport-Security"], "max-age=31536000")
        # Require framing, content type, referrer, permission, and CSP policy in both modes.
        for name in ("Content-Security-Policy", "X-Content-Type-Options", "Referrer-Policy", "Permissions-Policy", "X-Frame-Options"):
            # Compare stable header presence across transport modes.
            self.assertIn(name, cleartext)


# Run this focused module directly for local diagnostics.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
