"""Listener-free hostile-client proof for the restricted-preview WSGI boundary."""

# Import in-memory request streams for direct WSGI calls.
import io
# Import JSON encoding and decoding for standard API envelopes.
import json
# Import environment access for the disposable external log scan.
import os
# Import portable paths for exact checkout and external logs.
import pathlib
# Import interpreter path control for exact checkout module resolution.
import sys

# Resolve the exact repository root independently of the caller.
ROOT = pathlib.Path(__file__).resolve().parents[2]
# Prepend the exact checkout so direct script execution imports its casino package.
sys.path.insert(0, str(ROOT))

# Import the already environment-validated production application.
from casino.wsgi import application

# Preserve the synthetic exact origin supplied by the parent test.
ORIGIN = os.environ["CASINO_CANONICAL_ORIGIN"]
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

# Rotate login using the current browser CSRF cookie value.
rotated_login = request("POST", "/api/v2/auth/login", {"email": "preview-admin@example.invalid", "password": "synthetic-preview-password"}, mutation_headers(first_csrf))
# Require successful predecessor rotation.
assert rotated_login["status"] == "200 OK"
# Read the replacement session summary.
rotated_session = decoded(rotated_login)["data"]["session"]
# Retain the new disposable bearer.
admin_token = rotated_session["token"]
# Retain the new distinct CSRF proof.
admin_csrf = rotated_session["csrf_token"]
# Require both credential classes to rotate.
assert admin_token != first_token and admin_csrf != first_csrf and admin_token != admin_csrf
# Prove the predecessor bearer no longer authenticates.
old_session = request("GET", "/api/v2/me", headers={"Authorization": f"Bearer {first_token}"})
# Require the standard invalid-session result.
assert old_session["status"] == "401 Unauthorized"
# Prove the replacement bearer authenticates current-user reads.
current = request("GET", "/api/v2/me", headers={"Authorization": f"Bearer {admin_token}"})
# Require the expected synthetic identity without client metadata.
assert current["status"] == "200 OK" and "client" not in decoded(current)["data"]["session"] and "token" not in decoded(current)["data"]["session"] and decoded(current)["data"]["session"]["csrf_token"] == admin_csrf

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

# Prove signup remains absent even for an authenticated Admin request.
signup = request("POST", "/api/v2/auth/signup", {"email": "held@example.invalid", "password": "held"}, mutation_headers(admin_csrf, admin_token))
# Require route absence rather than provider or account mutation.
assert signup["status"] == "404 Not Found"
# Prove live OAuth start remains absent.
oauth_start = request("GET", "/api/v2/auth/oauth/google/start", headers={"Authorization": f"Bearer {admin_token}"})
# Require route absence while Admin diagnostic OAuth remains separate.
assert oauth_start["status"] == "404 Not Found"

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
assert SENTINEL not in log_text and admin_token not in log_text and admin_csrf not in log_text and bootstrap_csrf not in log_text

# Logout through exact Origin and session CSRF proof.
logout = request("POST", "/api/v2/auth/logout", {}, mutation_headers(admin_csrf, admin_token))
# Require successful revocation and both cookie expirations.
assert logout["status"] == "200 OK"
# Collect both ordered cookie clear headers.
cleared = header_values(logout, "Set-Cookie")
# Require session and CSRF cookies to clear with Secure, Strict, Max-Age, and epoch expiry.
assert len(cleared) == 2 and all("Secure" in value and "SameSite=Strict" in value and "Max-Age=0" in value and "Expires=Thu, 01 Jan 1970" in value for value in cleared)
