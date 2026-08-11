# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Listener-free hostile-client proof for the restricted-preview WSGI boundary."""

# Import in-memory request streams for direct WSGI calls.
import io
# Import JSON encoding and decoding for standard API envelopes.
import json
# Import environment access for the disposable external log scan.
import os
# Import portable paths for exact checkout and external logs.
import pathlib
# Import regular expressions for recursive credential-name rejection in native read envelopes.
import re
# Import interpreter path control for exact checkout module resolution.
import sys
# Import immutable-record replacement for one focused application-limiter policy.
from dataclasses import replace

# Resolve the exact repository root independently of the caller.
ROOT = pathlib.Path(__file__).resolve().parents[2]
# Prepend the exact checkout so direct script execution imports its casino package.
sys.path.insert(0, str(ROOT))

# Import the already environment-validated production application.
from casino.wsgi import application
# Import the production limiter so static and API accounting can be verified at the adapter boundary. (issue #570)
from casino.core.security import RateLimiter
# Import the live rate-policy service so the application seam can be isolated without provider mutation. (SEC-015)
from casino.core import rate_settings

# Preserve the synthetic exact origin supplied by the parent test.
ORIGIN = os.environ["CASINO_CANONICAL_ORIGIN"]
# Preserve the exact Android Capacitor origin enabled by the parent test. (SEC-016)
MOBILE_ORIGIN = "https://localhost"
# Preserve only its public authority for the required Host header.
AUTHORITY = ORIGIN.removeprefix("https://")
# Define one synthetic marker that must never enter application logs.
SENTINEL = "SENTINEL-SECURITY-MATERIAL"


# Call the WSGI application directly without creating any listener.
def request(method: str, path: str, body=None, headers=None, remote="127.0.0.1", proxied=True, content_length=None):
    # Encode one optional JSON body exactly once.
    payload = b"" if body is None else json.dumps(body).encode("utf-8")
    # Split the decoded application path from the raw query component.
    path_info, _, query = path.partition("?")
    # Build the minimum server-authored WSGI request environment.
    environ = {
        # Select the method under test.
        "REQUEST_METHOD": method,
        # Supply the decoded path that must never be logged raw.
        "PATH_INFO": path_info,
        # Supply the raw query independently from routing.
        "QUERY_STRING": query,
        # Identify the exact direct peer.
        "REMOTE_ADDR": remote,
        # Supply the canonical application authority.
        "HTTP_HOST": AUTHORITY,
        # Supply an in-memory body stream.
        "wsgi.input": io.BytesIO(payload),
        # Declare the standard WSGI version.
        "wsgi.version": (1, 0),
        # Mark the synthetic request as one process.
        "wsgi.multiprocess": False,
        # Match the approved threaded server behavior.
        "wsgi.multithread": True,
        # Mark the call as non-reentrant.
        "wsgi.run_once": False,
        # Retain standard errors only in memory.
        "wsgi.errors": io.StringIO(),
        # Keep the direct hop cleartext behind the synthetic edge.
        "wsgi.url_scheme": "http",
        # Declare the exact request body length unless a hostile value is supplied.
        "CONTENT_LENGTH": str(len(payload)) if content_length is None else str(content_length),
    }
    # Add the reviewed nginx forwarding pair only when the caller selects the proxy path.
    if proxied:
        # Supply one edge-observed synthetic client address.
        environ["HTTP_X_FORWARDED_FOR"] = "192.0.2.77"
        # Supply only the reviewed HTTPS forwarding protocol.
        environ["HTTP_X_FORWARDED_PROTO"] = "https"
    # Mark JSON bodies with their standard media type.
    if body is not None:
        # Supply only the accepted application JSON type.
        environ["CONTENT_TYPE"] = "application/json"
    # Translate caller headers into WSGI HTTP variables.
    for name, value in (headers or {}).items():
        # Preserve synthetic values only inside this request mapping.
        environ["HTTP_" + name.upper().replace("-", "_")] = value
    # Capture one complete response without collapsing duplicate Set-Cookie headers.
    response = {}

    # Record the status and ordered response headers supplied by the application.
    def start_response(status, response_headers):
        # Retain the stable public status line.
        response["status"] = status
        # Retain the ordered header pairs for cookie assertions.
        response["headers"] = list(response_headers)

    # Materialize the bounded response iterable.
    response["body"] = b"".join(application(environ, start_response))
    # Return the direct response record.
    return response


# Decode one JSON response body into its public envelope.
def decoded(response):
    # Parse UTF-8 bytes only after the caller has received a response.
    return json.loads(response["body"].decode("utf-8"))


# Return all response values for one repeated header name.
def header_values(response, name):
    # Filter case-insensitively while preserving header order.
    return [value for header, value in response["headers"] if header.lower() == name.lower()]


# Build exact OS-owned native headers without cookies or browser bootstrap state. (AUTH-019, SEC-016)
def native_headers(token=None, csrf=None, origin=MOBILE_ORIGIN, guest_nonce=None):
    # Start with the exact native marker and configured Capacitor origin.
    headers = {"Origin": origin, "X-Casino-Mobile-Client": "1"}
    # Add one OS-vault bearer only when the caller supplies it.
    if token:
        # Keep the disposable bearer inside this request mapping.
        headers["Authorization"] = f"Bearer {token}"
    # Add the matching OS-vault CSRF proof only when supplied.
    if csrf:
        # Keep the distinct session proof inside this request mapping.
        headers["X-CSRF-Token"] = csrf
    # Add the matching guest-browser proof only for a guest-owned lifecycle request.
    if guest_nonce:
        # Keep the disposable nonce inside this request mapping.
        headers["X-Guest-Browser-Nonce"] = guest_nonce
    # Return the complete credential-free-or-vault-owned header set.
    return headers


# Extract one named cookie value from ordered Set-Cookie response headers.
def response_cookie(response, name):
    # Scan every independent Set-Cookie header.
    for value in header_values(response, "Set-Cookie"):
        # Match only the requested leading cookie pair.
        if value.startswith(name + "="):
            # Return the scalar before its first attribute separator.
            return value.split(";", 1)[0].split("=", 1)[1]
    # Fail the focused probe when the expected cookie is absent.
    raise AssertionError("expected cookie was absent")


# Build the exact browser integrity headers for one state-changing request.
def mutation_headers(csrf, token=None, cookie_name="casino_csrf"):
    # Start with exact Origin, double-submit cookie, and explicit CSRF proof.
    headers = {"Origin": ORIGIN, "Cookie": f"{cookie_name}={csrf}", "X-CSRF-Token": csrf}
    # Add the disposable bearer only for authenticated API clients.
    if token:
        # Keep the bearer in request-local memory.
        headers["Authorization"] = f"Bearer {token}"
    # Return the complete request-local mapping.
    return headers


# Bootstrap the browser shell through the exact trusted proxy contract.
shell = request("GET", "/")
# Require the packaged application shell to load.
assert shell["status"] == "200 OK"
# Require HSTS only because the trusted proxy proved effective HTTPS.
assert header_values(shell, "Strict-Transport-Security") == ["max-age=31536000"]
# Require the reviewed CSP and framing policy.
assert header_values(shell, "Content-Security-Policy") and header_values(shell, "X-Frame-Options") == ["DENY"]
# Extract the anonymous double-submit bootstrap value.
bootstrap_csrf = response_cookie(shell, "casino_csrf")
# Require the bootstrap cookie to be Secure, host-only, and Strict without becoming HttpOnly.
bootstrap_cookie = next(value for value in header_values(shell, "Set-Cookie") if value.startswith("casino_csrf="))
# Assert the complete bootstrap attribute boundary.
assert "Secure" in bootstrap_cookie and "SameSite=Strict" in bootstrap_cookie and "Domain=" not in bootstrap_cookie and "HttpOnly" not in bootstrap_cookie

# Reject a sign-in that lost its double-submit cookie entirely, matching the stranded precached-shell browser. (issue #224)
cookieless_login = request("POST", "/api/v2/auth/login", {"email": "preview-admin@example.invalid", "password": "synthetic-preview-password"}, {"Origin": ORIGIN, "X-CSRF-Token": ""})
# Require the fixed fail-closed CSRF rejection for the cookie-less form.
assert cookieless_login["status"] == "403 Forbidden"
# Recover through the public CSRF bootstrap route exactly like the one-shot client retry. (issue #224)
csrf_bootstrap = request("GET", "/api/v2/auth/csrf")
# Require the anonymous recovery route to answer inside the standard envelope.
assert csrf_bootstrap["status"] == "200 OK" and decoded(csrf_bootstrap)["ok"] is True
# Read the re-issued host-only double-submit value.
recovered_csrf = response_cookie(csrf_bootstrap, "casino_csrf")
# Read the complete re-issued cookie attributes for boundary assertions.
recovered_cookie = next(value for value in header_values(csrf_bootstrap, "Set-Cookie") if value.startswith("casino_csrf="))
# Require the recovery cookie to keep the exact bootstrap attribute boundary without becoming HttpOnly.
assert 32 <= len(recovered_csrf) <= 128 and "Secure" in recovered_cookie and "SameSite=Strict" in recovered_cookie and "Domain=" not in recovered_cookie and "HttpOnly" not in recovered_cookie
# Require no token material in the public response body.
assert recovered_csrf.encode("utf-8") not in csrf_bootstrap["body"]
# Require an existing bounded double-submit value to be preserved rather than rotated on refresh. (issue #224)
preserved = request("GET", "/api/v2/auth/csrf", headers={"Cookie": f"casino_csrf={recovered_csrf}"})
# Require idempotent re-issue so a racing tab cannot invalidate the sibling tab's pending form.
assert response_cookie(preserved, "casino_csrf") == recovered_csrf
# Authenticate with the recovered pair exactly like the retried sign-in form. (issue #224)
recovered_login = request("POST", "/api/v2/auth/login", {"email": "preview-admin@example.invalid", "password": "synthetic-preview-password"}, mutation_headers(recovered_csrf))
# Require the previously stranded browser to sign in without reloading the shell.
assert recovered_login["status"] == "200 OK"

# Reject login without an Origin even when CSRF values match.
missing_origin = request("POST", "/api/v2/auth/login", {"email": "preview-admin@example.invalid", "password": "synthetic-preview-password"}, {"Cookie": f"casino_csrf={bootstrap_csrf}", "X-CSRF-Token": bootstrap_csrf})
# Require the fixed request-integrity failure.
assert missing_origin["status"] == "403 Forbidden" and decoded(missing_origin)["error"]["code"] == "FORBIDDEN"
# Reject null, malformed, foreign, and slash-expanded Origin variants equally.
for hostile_origin in ("null", "not-an-origin", "https://foreign.example.invalid", ORIGIN + "/"):
    # Send an otherwise valid double-submit login request.
    rejected = request("POST", "/api/v2/auth/login", {"email": "preview-admin@example.invalid", "password": "synthetic-preview-password"}, {"Origin": hostile_origin, "Cookie": f"casino_csrf={bootstrap_csrf}", "X-CSRF-Token": bootstrap_csrf})
    # Require the fixed forbidden outcome.
    assert rejected["status"] == "403 Forbidden"

# Authenticate the synthetic manually provisioned Admin through exact Origin and CSRF proof.
login = request("POST", "/api/v2/auth/login", {"email": "preview-admin@example.invalid", "password": "synthetic-preview-password"}, mutation_headers(bootstrap_csrf))
# Require successful local login.
assert login["status"] == "200 OK"
# Read the compatible session result inside disposable process memory.
login_session = decoded(login)["data"]["session"]
# Retain the disposable bearer and distinct CSRF proof.
first_token = login_session["token"]
# Retain the explicit non-cookie-client CSRF proof.
first_csrf = login_session["csrf_token"]
# Require the two credential classes to be distinct.
assert first_token != first_csrf
# Inspect the host-only session cookie attributes.
session_cookie = next(value for value in header_values(login, "Set-Cookie") if value.startswith("casino_session="))
# Require Secure, HttpOnly, Strict, bounded, and no Domain.
assert "Secure" in session_cookie and "HttpOnly" in session_cookie and "SameSite=Strict" in session_cookie and "Max-Age=" in session_cookie and "Domain=" not in session_cookie

# Create a second concurrent session using the current browser CSRF cookie value (issue #226).
rotated_login = request("POST", "/api/v2/auth/login", {"email": "preview-admin@example.invalid", "password": "synthetic-preview-password"}, mutation_headers(first_csrf))
# Require the second concurrent login to succeed.
assert rotated_login["status"] == "200 OK"
# Read the second concurrent session summary.
rotated_session = decoded(rotated_login)["data"]["session"]
# Retain the new disposable bearer.
admin_token = rotated_session["token"]
# Retain the new distinct CSRF proof.
admin_csrf = rotated_session["csrf_token"]
# Require both credential classes to be independent of the first session.
assert admin_token != first_token and admin_csrf != first_csrf and admin_token != admin_csrf
# Prove the predecessor bearer still authenticates under bounded concurrent sessions (issue #226, SESSION-007).
old_session = request("GET", "/api/v2/me", headers={"Authorization": f"Bearer {first_token}"})
# Require the predecessor session to remain valid.
assert old_session["status"] == "200 OK"
# Prove the replacement bearer authenticates current-user reads.
current = request("GET", "/api/v2/me", headers={"Authorization": f"Bearer {admin_token}"})
# Require the expected synthetic identity without client metadata.
assert current["status"] == "200 OK" and "client" not in decoded(current)["data"]["session"] and "token" not in decoded(current)["data"]["session"] and decoded(current)["data"]["session"]["csrf_token"] == admin_csrf

# Reject even an exact-marker WebView preflight because native OS networking requires no CORS. (SEC-016)
native_preflight = request("OPTIONS", "/api/v2/auth/mobile/session/rotate", headers={"Origin": MOBILE_ORIGIN, "X-Casino-Mobile-Client": "1", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization, content-type, x-csrf-token, x-casino-mobile-client"})
# Require a fixed denial with no browser-readable origin or credential authority.
assert native_preflight["status"] == "403 Forbidden" and not header_values(native_preflight, "Access-Control-Allow-Origin") and not header_values(native_preflight, "Access-Control-Allow-Credentials")
# Reject a missing marker, foreign origin, wildcard header, and unknown header through the same no-CORS boundary.
for hostile_headers in ({"Origin": MOBILE_ORIGIN, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"}, {"Origin": "https://foreign.example.invalid", "X-Casino-Mobile-Client": "1", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"}, {"Origin": MOBILE_ORIGIN, "X-Casino-Mobile-Client": "1", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "*"}, {"Origin": MOBILE_ORIGIN, "X-Casino-Mobile-Client": "1", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "x-unreviewed"}):
    # Send the hostile preflight without any application mutation.
    rejected_preflight = request("OPTIONS", "/api/v2/auth/mobile/session/rotate", headers=hostile_headers)
    # Require no successful CORS authority or credential header.
    assert rejected_preflight["status"] == "403 Forbidden" and not header_values(rejected_preflight, "Access-Control-Allow-Origin") and not header_values(rejected_preflight, "Access-Control-Allow-Credentials")

# Create a dedicated session through the primary native login path without cookie/bootstrap-CSRF authority.
native_seed_login = request("POST", "/api/v2/auth/login", {"email": "preview-admin@example.invalid", "password": "synthetic-preview-password"}, native_headers())
# Require no browser-readable CORS, no browser cookie, and the complete native credential pair.
assert native_seed_login["status"] == "200 OK" and not header_values(native_seed_login, "Access-Control-Allow-Origin") and not header_values(native_seed_login, "Set-Cookie")
# Retain the disposable predecessor only inside the child process.
native_seed = decoded(native_seed_login)["data"]["session"]
# Require the OS bridge's documented issuance wire contract before it strips secrets from JavaScript.
assert native_seed["token"] and native_seed["csrf_token"] and native_seed["generation"] >= 1 and native_seed["token"] != native_seed["csrf_token"]
# Reject a native protected read without an OS-vault bearer.
native_without_bearer = request("GET", "/api/v2/auth/mobile/session", headers=native_headers())
# Require the generic unauthorized boundary with no CORS or cookies.
assert native_without_bearer["status"] == "401 Unauthorized" and not header_values(native_without_bearer, "Access-Control-Allow-Origin") and not header_values(native_without_bearer, "Set-Cookie")
# Read both current-user compatibility routes through exact native bearer authority before rotation.
for native_current_path in ("/api/v2/me", "/api/v2/auth/session"):
    # Request the ordinary secret-free payload through direct OS-network classification.
    native_current = request("GET", native_current_path, headers=native_headers(native_seed["token"]))
    # Parse the response only after exact transport success.
    native_current_data = decoded(native_current)["data"] if native_current["status"] == "200 OK" else {}
    # Require no issuance or guest credential field in either ordinary read envelope.
    assert native_current["status"] == "200 OK" and native_current_data.get("session") and not re.search(rb'"(?:token|csrf_token|guest_browser_nonce)"', native_current["body"])
# Reject cookie authority even when a valid bearer and CSRF proof are also present.
native_with_cookie = request("GET", "/api/v2/auth/mobile/session", headers={**native_headers(native_seed["token"]), "Cookie": f"casino_session={native_seed['token']}"})
# Require cookie/native authority confusion to fail before route dispatch.
assert native_with_cookie["status"] == "403 Forbidden"
# Reject rotation without the matching session CSRF.
native_missing_csrf = request("POST", "/api/v2/auth/mobile/session/rotate", {"expected_generation": native_seed["generation"]}, native_headers(native_seed["token"]))
# Require the fixed integrity rejection without rotating the predecessor.
assert native_missing_csrf["status"] == "403 Forbidden"
# Rotate through the exact native bearer, CSRF, marker, and Origin boundary.
native_rotated = request("POST", "/api/v2/auth/mobile/session/rotate", {"expected_generation": native_seed["generation"]}, native_headers(native_seed["token"], native_seed["csrf_token"]))
# Require native issuance wire fields with no CORS, cookies, or credentials wildcard.
assert native_rotated["status"] == "200 OK" and not header_values(native_rotated, "Access-Control-Allow-Origin") and not header_values(native_rotated, "Access-Control-Allow-Credentials") and not header_values(native_rotated, "Set-Cookie")
# Retain only the disposable successor for stale/lost-response/revoke evidence.
native_successor = decoded(native_rotated)["data"]["session"]
# Require one atomic server generation and distinct bearer/CSRF pair.
assert native_successor["generation"] == native_seed["generation"] + 1 and native_successor["token"] != native_seed["token"] and native_successor["csrf_token"] != native_seed["csrf_token"]
# Model a lost rotation response by retrying the predecessor, which must never leave two reusable credentials.
native_lost_response_retry = request("POST", "/api/v2/auth/mobile/session/rotate", {"expected_generation": native_seed["generation"]}, native_headers(native_seed["token"], native_seed["csrf_token"]))
# Require forced reauthentication rather than duplicate issuance or replay.
assert native_lost_response_retry["status"] == "401 Unauthorized"
# Revoke the successor through the matching bearer/CSRF boundary.
native_revoked = request("POST", "/api/v2/auth/mobile/session/revoke", {}, native_headers(native_successor["token"], native_successor["csrf_token"]))
# Require one cookie-free terminal revocation.
assert native_revoked["status"] == "200 OK" and decoded(native_revoked)["data"] == {"revoked": True} and not header_values(native_revoked, "Set-Cookie")
# Prove the revoked successor cannot probe or replay.
native_after_revoke = request("GET", "/api/v2/auth/mobile/session", headers=native_headers(native_successor["token"]))
# Require the same generic unauthorized boundary.
assert native_after_revoke["status"] == "401 Unauthorized"

# Reject browser-CSRF bootstrap when requested through the native no-cookie authority.
native_csrf_bootstrap = request("GET", "/api/v2/auth/csrf", headers=native_headers())
# Require a fixed forbidden result with no CORS or Set-Cookie emission.
assert native_csrf_bootstrap["status"] == "403 Forbidden" and not header_values(native_csrf_bootstrap, "Access-Control-Allow-Origin") and not header_values(native_csrf_bootstrap, "Set-Cookie")

# Create one native guest session without browser cookies or bootstrap CSRF authority.
native_guest_started = request("POST", "/api/v2/auth/guest", {"accepted": True, "terms_version": "private-beta-1", "locale": "en-US", "device": "mobile"}, native_headers())
# Require the issuance-only guest credential pair and nonce with no Set-Cookie authority.
assert native_guest_started["status"] == "200 OK" and not header_values(native_guest_started, "Set-Cookie") and not header_values(native_guest_started, "Access-Control-Allow-Origin")
# Retain the disposable guest wire material only inside this isolated child process.
native_guest = decoded(native_guest_started)["data"]
# Require the native guest issuance envelope to carry all OS-vault and guest-integrity inputs.
assert native_guest["session"]["token"] and native_guest["session"]["csrf_token"] and native_guest["guest_browser_nonce"]
# End the guest with exact bearer, CSRF, nonce, native marker, and configured Origin.
native_guest_end = request("POST", "/api/v2/auth/guest/end", {}, native_headers(native_guest["session"]["token"], native_guest["session"]["csrf_token"], guest_nonce=native_guest["guest_browser_nonce"]))
# Require cookie-free terminal success so the native bridge can atomically clear its vault.
assert native_guest_end["status"] == "200 OK" and decoded(native_guest_end)["data"] == {"ended": True} and not header_values(native_guest_end, "Set-Cookie")
# Prove the ended bearer cannot revalidate after terminal OS-vault clear semantics.
native_guest_after_end = request("GET", "/api/v2/auth/mobile/session", headers=native_headers(native_guest["session"]["token"]))
# Require the fixed unauthorized result with no cookie residue.
assert native_guest_after_end["status"] == "401 Unauthorized" and not header_values(native_guest_after_end, "Set-Cookie")
# Preserve browser cookie authentication and omit native CORS from ordinary same-origin current-user reads.
browser_cookie_regression = request("GET", "/api/v2/me", headers={"Cookie": f"casino_session={admin_token}", "Origin": ORIGIN})
# Require unchanged browser authority and no reflected Capacitor CORS metadata.
assert browser_cookie_regression["status"] == "200 OK" and not header_values(browser_cookie_regression, "Access-Control-Allow-Origin")

# Reject a protected mutation when Origin is absent.
no_origin = request("POST", "/api/v2/me/tokens/add", {"amount": 1}, {"Authorization": f"Bearer {admin_token}", "X-CSRF-Token": admin_csrf})
# Require a fixed forbidden result.
assert no_origin["status"] == "403 Forbidden"
# Reject bearer reuse as CSRF proof.
bearer_as_csrf = request("POST", "/api/v2/me/tokens/add", {"amount": 1}, {"Authorization": f"Bearer {admin_token}", "Origin": ORIGIN, "X-CSRF-Token": admin_token})
# Require the fixed forbidden result without reflecting either value.
assert bearer_as_csrf["status"] == "403 Forbidden" and admin_token.encode("utf-8") not in bearer_as_csrf["body"]
# Accept the exact distinct session CSRF proof.
credited = request("POST", "/api/v2/me/tokens/add", {"amount": 1}, mutation_headers(admin_csrf, admin_token))
# Require successful same-origin production-adapter mutation.
assert credited["status"] == "200 OK"

# Require anonymous liveness and authenticated readiness to retain #72 semantics.
health = request("GET", "/healthz")
# Require only the sanitized liveness payload.
assert health["status"] == "200 OK" and decoded(health) == {"ok": True, "data": {"status": "live"}}
# Reject anonymous detailed readiness.
anonymous_ready = request("GET", "/readyz")
# Require authentication without dependency detail.
assert anonymous_ready["status"] == "401 Unauthorized" and decoded(anonymous_ready)["error"]["details"] == {}
# Accept authenticated readiness.
ready = request("GET", "/readyz", headers={"Authorization": f"Bearer {admin_token}"})
# Require a healthy trusted readiness response.
assert ready["status"] == "200 OK" and decoded(ready)["data"]["ready"] is True

# Reject an oversized body before reading or reflecting it.
oversized = request("POST", "/api/v2/me/tokens/add", headers=mutation_headers(admin_csrf, admin_token), content_length=4097)
# Require the fixed 413 response.
assert oversized["status"] == "413 Request Entity Too Large" and decoded(oversized)["error"]["code"] == "REQUEST_TOO_LARGE"

# Create one normal manually provisioned invite through the Admin-only API.
invite_created = request("POST", "/api/v2/admin/users", {"username": "preview-invite@example.invalid", "display_name": "Preview Invite", "password": "synthetic-invite-password", "roles": ["player"], "initial_tokens": 0}, mutation_headers(admin_csrf, admin_token))
# Require successful invite creation without signup.
assert invite_created["status"] == "200 OK"
# Authenticate the invite using the current browser double-submit value.
invite_login = request("POST", "/api/v2/auth/login", {"email": "preview-invite@example.invalid", "password": "synthetic-invite-password"}, mutation_headers(admin_csrf))
# Require successful local invite login.
assert invite_login["status"] == "200 OK"
# Retain invite credential material only in memory.
invite_session = decoded(invite_login)["data"]["session"]
# Require normal invite users to be denied the Admin HTML shell.
invite_admin = request("GET", "/admin", headers={"Cookie": f"casino_session={invite_session['token']}"})
# Require no Admin bytes in the forbidden response.
assert invite_admin["status"] == "403 Forbidden" and b"adminView" not in invite_admin["body"]
# Require normal invite users to be denied the packaged Admin JavaScript.
invite_admin_js = request("GET", "/admin.js", headers={"Cookie": f"casino_session={invite_session['token']}"})
# Require no Admin source in the forbidden response.
assert invite_admin_js["status"] == "403 Forbidden" and b"adminView" not in invite_admin_js["body"]
# Require the Admin session to receive the protected Admin shell.
admin_html = request("GET", "/admin", headers={"Cookie": f"casino_session={admin_token}"})
# Require the immutable Admin document only after application authorization.
assert admin_html["status"] == "200 OK" and b"adminView" in admin_html["body"]

# Preserve the production limiter before exercising an isolated one-request budget. (SEC-010, issue #570)
original_application_limiter = application.rate_limiter
# Preserve the live-policy reader before installing one deterministic request allowance.
original_rate_policy_reader = rate_settings.rate_limits
# Preserve the provider-backed policy so the focused live update cannot affect later matrix cases.
original_stored_rate_policy = original_rate_policy_reader()
# Install one fresh limiter so prior matrix traffic cannot affect the accounting proof.
application.rate_limiter = RateLimiter(replace(application.policy, rate_requests=1))
# Return one exact one-request live policy for this listener-free adapter proof.
rate_settings.rate_limits = lambda: {"schema_version": 2, "requests_per_window": 1, "window_seconds": 60}
# Start protected restoration so later security cases retain their original generous allowance.
try:
    # Load one real packaged browser asset that must not consume application/API capacity.
    static_asset = request("GET", "/app.js")
    # Require normal static delivery through the production adapter.
    assert static_asset["status"] == "200 OK" and b"updateShellStatus" in static_asset["body"]
    # Consume the one configured application allowance through a public API read.
    first_bounded_api = request("GET", "/api/v2/auth/enrollment-policy")
    # Require the API call to succeed because static delivery consumed no API allowance.
    assert first_bounded_api["status"] == "200 OK"
    # Repeat the same API read inside the unchanged fixed window.
    limited_api = request("GET", "/api/v2/auth/enrollment-policy")
    # Require the second application request to retain the standard 429 boundary.
    assert limited_api["status"] == "429 Too Many Requests" and decoded(limited_api)["error"]["code"] == "RATE_LIMITED"
    # Read the owner-only recovery policy through its independent bounded bucket after application exhaustion.
    recovery_policy = request("GET", "/api/v2/admin/rate-limits", headers={"Authorization": f"Bearer {admin_token}"})
    # Require the recovery control to remain reachable only through a valid owner session while the focused reader seam stays exact.
    assert recovery_policy["status"] == "200 OK" and decoded(recovery_policy)["data"]["settings"]["requests_per_window"] == 1
    # Persist a larger allowance through the real owner mutation while the application bucket remains exhausted.
    raised_policy = request("POST", "/api/v2/admin/rate-limits", {"requests_per_window": 900, "window_seconds": 60}, mutation_headers(admin_csrf, admin_token))
    # Require the recovery bucket, owner authorization, CSRF boundary, clamp, and provider write to succeed together.
    assert raised_policy["status"] == "200 OK" and decoded(raised_policy)["data"]["settings"]["requests_per_window"] == 900
    # Restore the production reader so the freshly persisted policy governs the next ordinary API request.
    rate_settings.rate_limits = original_rate_policy_reader
    # Reuse the existing limiter state to prove the live allowance activates without reconstruction or restart.
    recovered_api = request("GET", "/api/v2/auth/enrollment-policy")
    # Require the same client to recover immediately under the raised live allowance.
    assert recovered_api["status"] == "200 OK"
# Restore the original limiter even when the focused accounting proof fails.
finally:
    # Return the complete security matrix to its original configured allowance.
    application.rate_limiter = original_application_limiter
    # Restore the provider-backed live-policy reader for later matrix cases.
    rate_settings.rate_limits = original_rate_policy_reader
    # Restore the exact provider-backed policy that preceded this focused live-update proof.
    rate_settings.save_rate_limits(original_stored_rate_policy)

# Prove signup remains present only as a disabled enrollment endpoint even for an authenticated Admin request.
signup = request("POST", "/api/v2/auth/signup", {"email": "held@example.invalid", "password": "held"}, mutation_headers(admin_csrf, admin_token))
# Require the disabled route to fail closed rather than creating account state.
assert signup["status"] == "403 Forbidden" and decoded(signup)["error"]["code"] == "FORBIDDEN"
# Read the public enrollment policy without authenticating a user.
signup_policy = request("GET", "/api/v2/auth/enrollment-policy")
# Require the enrollment surface to publish disabled signup and passkeys while retaining conversion availability.
assert signup_policy["status"] == "200 OK" and decoded(signup_policy)["data"]["signup_enabled"] is False and decoded(signup_policy)["data"]["passkeys_enabled"] is False and decoded(signup_policy)["data"]["guest_conversion_enabled"] is True
# Prove the wrong HTTP method remains absent on the exact OAuth start path.
oauth_start = request("GET", "/api/v2/auth/oauth/google/start", headers={"Authorization": f"Bearer {admin_token}"})
# Require method-level route absence without treating it as provider readiness.
assert oauth_start["status"] == "404 Not Found"
# Prove the registered start mutation remains provider-inaccessible under repository defaults.
oauth_start_held = request("POST", "/api/v2/auth/oauth/google/start", {"action": "signin", "return_to": "/"}, mutation_headers(admin_csrf, admin_token))
# Require the same non-enumerating unavailable result without provider network or account mutation.
assert oauth_start_held["status"] == "404 Not Found"

# Require direct cleartext loopback to omit HSTS even though other headers remain.
direct = request("GET", "/healthz", proxied=False)
# Require liveness without Strict-Transport-Security on an unverified scheme.
assert direct["status"] == "200 OK" and not header_values(direct, "Strict-Transport-Security")
# Reject a foreign Host before application dispatch.
foreign_host = request("GET", "/healthz", headers={"Host": "foreign.example.invalid"})
# Require the fixed authority failure.
assert foreign_host["status"] == "403 Forbidden"
# Reject nginx metadata from a non-configured direct peer.
wrong_peer = request("GET", "/healthz", remote="127.0.0.2")
# Require proxy trust to fail closed.
assert wrong_peer["status"] == "403 Forbidden"
# Reject forwarding host metadata even from the configured peer.
forwarded_host = request("GET", "/healthz", headers={"X-Forwarded-Host": AUTHORITY})
# Require the strict nginx header contract.
assert forwarded_host["status"] == "403 Forbidden"

# Exercise path, query, header, cookie, Origin, and body sentinels through one rejected request.
secret_rejected = request("POST", f"/api/v2/unknown/{SENTINEL}?q={SENTINEL}", {"password": SENTINEL, "token": SENTINEL}, {"Authorization": f"Bearer {SENTINEL}", "Cookie": f"casino_session={SENTINEL}; casino_csrf={SENTINEL}", "Origin": f"https://{SENTINEL}.invalid", "X-CSRF-Token": SENTINEL})
# Require a bounded rejection without reflected material.
assert secret_rejected["status"].startswith(("401", "403")) and SENTINEL.encode("utf-8") not in secret_rejected["body"]
# Read every external application log only after requests complete.
log_root = pathlib.Path(os.environ["CASINO_LOG_DIR"])
# Join all log text for one fail-closed sentinel scan.
log_text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in log_root.rglob("*") if path.is_file())
# Require no supplied path, query, header, cookie, Origin, body, bearer, or CSRF value in logs.
assert SENTINEL not in log_text and admin_token not in log_text and admin_csrf not in log_text and bootstrap_csrf not in log_text and native_seed["token"] not in log_text and native_successor["token"] not in log_text and native_successor["csrf_token"] not in log_text

# Logout through exact Origin and session CSRF proof.
logout = request("POST", "/api/v2/auth/logout", {}, mutation_headers(admin_csrf, admin_token))
# Require successful revocation with one session expiry plus one CSRF rotation.
assert logout["status"] == "200 OK"
# Collect both ordered logout cookie headers.
cleared = header_values(logout, "Set-Cookie")
# Require exactly the session expiration and the double-submit replacement.
assert len(cleared) == 2
# Read the expiring host-only session credential.
session_cleared = next(value for value in cleared if value.startswith("casino_session="))
# Require the session cookie to clear with Secure, Strict, Max-Age, and epoch expiry.
assert "Secure" in session_cleared and "SameSite=Strict" in session_cleared and "Max-Age=0" in session_cleared and "Expires=Thu, 01 Jan 1970" in session_cleared
# Read the rotated anonymous double-submit replacement issued by logout. (issue #438)
rotated_csrf = response_cookie(logout, "casino_csrf")
# Read the complete rotated cookie attributes for boundary assertions.
rotated_attributes = next(value for value in cleared if value.startswith("casino_csrf="))
# Require rotation rather than removal so the still-open sign-in view keeps a valid double-submit pair.
assert 32 <= len(rotated_csrf) <= 128 and rotated_csrf != admin_csrf and "Max-Age=0" not in rotated_attributes
# Require the rotated companion to stay browser-readable, Secure, Strict, and host-only.
assert "HttpOnly" not in rotated_attributes and "Secure" in rotated_attributes and "SameSite=Strict" in rotated_attributes and "Domain=" not in rotated_attributes
# Authenticate again immediately with the rotated anonymous pair exactly like the still-open sign-in form. (issue #438)
relogin = request("POST", "/api/v2/auth/login", {"email": "preview-admin@example.invalid", "password": "synthetic-preview-password"}, mutation_headers(rotated_csrf))
# Require login after logout to succeed without reloading the application shell.
assert relogin["status"] == "200 OK"
# Read the recovered session summary from the relogin envelope.
relogin_session = decoded(relogin)["data"]["session"]
# Require the recovered session to rotate onto its own distinct per-session CSRF proof.
assert relogin_session["csrf_token"] != rotated_csrf and relogin_session["token"] != admin_token

# Start one disposable guest trial from the anonymous sign-in surface with explicit terms acceptance. (issue #317)
guest_started = request("POST", "/api/v2/auth/guest", {"accepted": True, "terms_version": "private-beta-1", "locale": "en-US", "device": "desktop"}, mutation_headers(relogin_session["csrf_token"]))
# Require the anonymous guest creation to succeed under the browser integrity contract.
assert guest_started["status"] == "200 OK"
# Read the guest browser-session credential from its host-only cookie.
guest_token = response_cookie(guest_started, "casino_session")
# Read the guest session-bound double-submit value.
guest_csrf = response_cookie(guest_started, "casino_csrf")
# Read the one-time browser-context proof from the creation envelope.
guest_nonce = decoded(guest_started)["data"]["guest_browser_nonce"]
# End the trial through its authenticated lifecycle route with complete browser proofs. (issue #317)
guest_end = request("POST", "/api/v2/auth/guest/end", {}, {"Origin": ORIGIN, "Cookie": f"casino_session={guest_token}; casino_csrf={guest_csrf}", "X-CSRF-Token": guest_csrf, "X-Guest-Browser-Nonce": guest_nonce})
# Require the irreversible guest teardown to succeed.
assert guest_end["status"] == "200 OK" and decoded(guest_end)["data"]["ended"] is True
# Read the rotated anonymous double-submit replacement issued by trial end. (issue #438)
guest_rotated = response_cookie(guest_end, "casino_csrf")
# Read the complete rotated cookie attributes for boundary assertions.
guest_rotated_attributes = next(value for value in header_values(guest_end, "Set-Cookie") if value.startswith("casino_csrf="))
# Require trial end to rotate rather than remove the double-submit pair exactly like logout.
assert 32 <= len(guest_rotated) <= 128 and guest_rotated != guest_csrf and "Max-Age=0" not in guest_rotated_attributes and "HttpOnly" not in guest_rotated_attributes
# Authenticate a registered account immediately with the rotated pair exactly like the post-trial sign-in form. (issue #438)
post_guest_login = request("POST", "/api/v2/auth/login", {"email": "preview-admin@example.invalid", "password": "synthetic-preview-password"}, mutation_headers(guest_rotated))
# Require login after guest trial end to succeed without reloading the application shell.
assert post_guest_login["status"] == "200 OK"
