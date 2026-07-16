"""Focused OAuth callback and flow-proof tests for GitHub issue #70.

Requirements: OAUTH-003 and TEST-045.
"""

# Import unittest so focused tests run without third-party dependencies.
import unittest

# Import the isolated callback helpers under test.
from casino.core.oauth.callbacks import build_callback_url, canonical_callback_path, new_flow_secrets, pkce_s256_challenge, validate_callback_query, validate_nonce
# Import standard error classes so fail-closed behavior is asserted precisely.
from casino.errors import UnauthorizedError, ValidationError

# Use a bounded deterministic state value only inside service-free tests.
EXPECTED_STATE = "s" * 43
# Use a distinct bounded deterministic nonce value only inside service-free tests.
EXPECTED_NONCE = "n" * 43


# Validate exact callback construction and secret-safe query handling.
class CallbackValidationTests(unittest.TestCase):
    # Verify the exact issue-#75 provider path reservation.
    def test_canonical_callback_paths_are_exact(self):
        # Assert the exact Google path without a trailing slash.
        self.assertEqual(canonical_callback_path("google"), "/api/v2/auth/oauth/google/callback")
        # Assert the exact Facebook path without a trailing slash.
        self.assertEqual(canonical_callback_path("facebook"), "/api/v2/auth/oauth/facebook/callback")

    # Verify fixed local-copy and future HTTPS callback origins without opening listeners.
    def test_callback_urls_use_reserved_origins(self):
        # Build a string-only local-copy callback on the non-user port 8766.
        local_callback = build_callback_url("http://localhost:8766", "google")
        # Assert exact local host, port, path, case, and trailing-slash behavior.
        self.assertEqual(local_callback, "http://localhost:8766/api/v2/auth/oauth/google/callback")
        # Build a string-only future HTTPS callback without contacting the hostname.
        public_callback = build_callback_url("https://casino.example.test", "facebook")
        # Assert the canonical HTTPS origin and provider path.
        self.assertEqual(public_callback, "https://casino.example.test/api/v2/auth/oauth/facebook/callback")

    # Verify unsafe callback bases fail closed without reflected values.
    def test_callback_urls_reject_unsafe_bases(self):
        # List malformed, alias, public-HTTP, path-bearing, credential-bearing, and raw-IP examples.
        invalid_bases = ("http://127.0.0.1:8766", "http://localhost:9999", "http://casino.example.test", "https://casino.example.test:8443", "https://casino.example.test/base", "https://user:password@casino.example.test", "https://203.0.113.10", "https://127.1", "https://0x7f.0.0.1", "https://[broken")
        # Validate every unsafe base independently.
        for invalid_base in invalid_bases:
            # Label the failing case without placing secrets in assertion output.
            with self.subTest(kind=invalid_bases.index(invalid_base)):
                # Assert structural validation rejects the base.
                with self.assertRaises(ValidationError):
                    # Build no URL and open no network connection.
                    build_callback_url(invalid_base, "google")
        # Define a malformed port marker that must not survive in an exception cause.
        unsafe_port_marker = "embedded-secret-marker"
        # Capture a malformed port failure for secret-safe exception inspection.
        with self.assertRaises(ValidationError) as raised:
            # Parse no live URL and retain no underlying urllib exception text.
            build_callback_url(f"https://casino.example.test:{unsafe_port_marker}", "google")
        # Assert the parser cause cannot leak malformed input through tracebacks.
        self.assertIsNone(raised.exception.__cause__)
        # Assert the marker is absent from the public validation error.
        self.assertNotIn(unsafe_port_marker, str(raised.exception))

    # Verify local password and unknown providers cannot acquire OAuth callbacks.
    def test_callback_path_rejects_non_oauth_providers(self):
        # Assert local password login remains outside the OAuth route shape.
        with self.assertRaises(ValidationError):
            # Requesting a local OAuth callback must fail.
            canonical_callback_path("local")
        # Assert unknown identifiers are not normalized or reflected.
        with self.assertRaises(ValidationError):
            # Requesting an unknown callback must fail.
            canonical_callback_path("GOOGLE")

    # Verify freshly generated state and nonce values stay out of repr output.
    def test_flow_secrets_are_independent_and_repr_safe(self):
        # Generate local in-memory proof values without persistence.
        flow_secrets = new_flow_secrets()
        # Assert state and nonce are independent.
        self.assertNotEqual(flow_secrets.state, flow_secrets.nonce)
        # Assert both values meet the bounded minimum length.
        self.assertGreaterEqual(len(flow_secrets.state), 32)
        # Assert the state value is absent from the object representation.
        self.assertNotIn(flow_secrets.state, repr(flow_secrets))
        # Assert the nonce value is absent from the object representation.
        self.assertNotIn(flow_secrets.nonce, repr(flow_secrets))
        # Assert the PKCE verifier value is absent from the object representation.
        self.assertNotIn(flow_secrets.pkce_verifier, repr(flow_secrets))
        # Assert the generated verifier produces a bounded S256 challenge.
        self.assertEqual(len(pkce_s256_challenge(flow_secrets.pkce_verifier)), 43)

    # Verify the RFC 7636 S256 example and fail-closed verifier validation.
    def test_pkce_s256_challenge_is_standard_and_secret_safe(self):
        # Use the published RFC 7636 verifier test vector.
        verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        # Assert the exact published S256 challenge.
        self.assertEqual(pkce_s256_challenge(verifier), "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM")
        # Assert a too-short verifier fails without reflection.
        with self.assertRaises(ValidationError):
            # Derive no challenge for an invalid verifier.
            pkce_s256_challenge("short")

    # Verify valid success callbacks retain codes only in repr-suppressed fields.
    def test_success_callback_is_validated_and_secret_safe(self):
        # Define one synthetic authorization code that must never appear in diagnostics.
        authorization_code = "mock-authorization-code-secret"
        # Validate the callback with the exact retained state.
        result = validate_callback_query("google", {"state": EXPECTED_STATE, "code": authorization_code}, EXPECTED_STATE)
        # Assert the future exchange path receives the code.
        self.assertEqual(result.code, authorization_code)
        # Assert the callback outcome is successful.
        self.assertTrue(result.succeeded)
        # Assert repr output suppresses the authorization code.
        self.assertNotIn(authorization_code, repr(result))
        # Assert public diagnostics suppress the authorization code.
        self.assertNotIn(authorization_code, repr(result.diagnostic()))
        # Define one whitespace-bearing opaque code to verify no normalization occurs.
        opaque_code = " code-with-significant-whitespace "
        # Validate the exact opaque code value.
        opaque_result = validate_callback_query("google", {"state": EXPECTED_STATE, "code": opaque_code}, EXPECTED_STATE)
        # Assert the callback helper preserves the authorization code exactly.
        self.assertEqual(opaque_result.code, opaque_code)

    # Verify provider denial is sanitized and arbitrary descriptions are ignored.
    def test_provider_error_callback_is_sanitized(self):
        # Define arbitrary provider text that must never be returned.
        unsafe_description = "user text with token=secret-value"
        # Validate a denied callback while including an ignored description.
        result = validate_callback_query("facebook", {"state": EXPECTED_STATE, "error": "access_denied", "error_description": unsafe_description}, EXPECTED_STATE)
        # Assert the sanitized provider error identifier is retained.
        self.assertEqual(result.error_code, "access_denied")
        # Assert the callback cannot proceed to code exchange.
        self.assertFalse(result.succeeded)
        # Assert ignored provider description text is absent from repr output.
        self.assertNotIn(unsafe_description, repr(result))
        # Validate an unsafe error identifier separately.
        generic_result = validate_callback_query("google", {"state": EXPECTED_STATE, "error": "bad error with spaces"}, EXPECTED_STATE)
        # Assert unsafe provider error text becomes one stable identifier.
        self.assertEqual(generic_result.error_code, "provider_error")
        # Define a regex-shaped provider error marker that diagnostics must not retain.
        secret_shaped_error = "synthetic_secret_marker"
        # Validate the unknown provider-specific error without retaining its value.
        secret_safe_result = validate_callback_query("google", {"state": EXPECTED_STATE, "error": secret_shaped_error}, EXPECTED_STATE)
        # Assert arbitrary identifier-shaped values collapse to the generic error code.
        self.assertEqual(secret_safe_result.error_code, "provider_error")
        # Assert the arbitrary provider value is absent from public diagnostics.
        self.assertNotIn(secret_shaped_error, repr(secret_safe_result.diagnostic()))

    # Verify callback ambiguity, duplication, omission, and anti-forgery failures.
    def test_invalid_callback_queries_fail_closed(self):
        # Define failing queries and the expected public error class.
        cases = (({"code": "code"}, UnauthorizedError), ({"state": "x" * 43, "code": "code"}, UnauthorizedError), ({"state": [EXPECTED_STATE, EXPECTED_STATE], "code": "code"}, ValidationError), ({"state": EXPECTED_STATE}, ValidationError), ({"state": EXPECTED_STATE, "code": "code", "error": "access_denied"}, ValidationError), ({"state": EXPECTED_STATE, "code": "c" * 4097}, ValidationError), ({"state": EXPECTED_STATE, "code": 123}, ValidationError), ({"state": EXPECTED_STATE, "code": "code\r\ninjected"}, ValidationError), ({"state": EXPECTED_STATE, "code": "café"}, ValidationError), ({"state": " " + EXPECTED_STATE, "code": "code"}, UnauthorizedError), ({"state": EXPECTED_STATE + " ", "code": "code"}, UnauthorizedError), ({"state": "é" * 32, "code": "code"}, UnauthorizedError))
        # Validate each fail-closed case without reflecting query values.
        for index, (query, error_class) in enumerate(cases):
            # Label the case by stable numeric index only.
            with self.subTest(case=index):
                # Assert the expected safe public error class.
                with self.assertRaises(error_class):
                    # Validate without any provider exchange or session creation.
                    validate_callback_query("google", query, EXPECTED_STATE)

    # Verify nonce comparison accepts only the exact retained opaque value.
    def test_nonce_validation_is_exact(self):
        # Assert the exact retained nonce succeeds.
        validate_nonce(EXPECTED_NONCE, EXPECTED_NONCE)
        # Assert a different bounded nonce fails with an authentication error.
        with self.assertRaises(UnauthorizedError):
            # Compare distinct nonce values without exposing them in error text.
            validate_nonce("x" * 43, EXPECTED_NONCE)
        # Assert surrounding whitespace is a mismatch rather than normalized away.
        with self.assertRaises(UnauthorizedError):
            # Compare a whitespace-altered nonce without exposing it in error text.
            validate_nonce(" " + EXPECTED_NONCE, EXPECTED_NONCE)
        # Assert non-ASCII proof values fail safely instead of reaching compare_digest.
        with self.assertRaises(UnauthorizedError):
            # Compare a Unicode nonce without exposing it in error text.
            validate_nonce("é" * 32, EXPECTED_NONCE)


# Run focused tests when this file is invoked directly.
if __name__ == "__main__":
    # Delegate process status and reporting to unittest.
    unittest.main()
