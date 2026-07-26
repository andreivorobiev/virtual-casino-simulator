"""Production WSGI adapter for CORE-023 without invoking the development HTTP server."""

# Import JSON encoding for the repository-standard API envelope.
import json
# Import MIME discovery for packaged frontend assets.
import mimetypes
# Import operating-system entropy for bounded request correlation identifiers.
import os
# Import regular expressions for the established player-resource authorization boundary.
import re
# Import standard status phrases for valid WSGI response lines.
from http import HTTPStatus
# Import portable paths for traversal-safe static asset resolution.
from pathlib import Path

# Reuse the canonical route registry and cache contract without starting casino.app's development server.
from casino.app import CACHE_CONTROL_NO_STORE, ROUTER
# Import production runtime and packaged-static configuration.
from casino.config import APP_VERSION, WEB_DIR, validate_bootstrap_for_startup, validate_production_runtime
# Import standard application errors for stable public envelopes.
from casino.errors import CasinoError, ForbiddenError, RequestTooLargeError, ValidationError
# Import strict JSON-number handling shared with the development HTTP adapter.
from casino.core.validation import reject_nonfinite_json_constant
# Import authentication and application logging through the existing core boundaries.
from casino.core import auth, logger, players
# Import the complete restricted-preview request and response policy.
from casino.core.security import CSRF_COOKIE, RateLimiter, SecurityPolicy, cookie_value, csrf_cookie_header, effective_request, new_csrf_token, response_security_headers, validate_request_integrity
# Import provider-neutral bootstrap behavior for a fresh external runtime root.
from casino.core.storage import bootstrap_players
# Import persistent-directory initialization and legacy local-state migration.
from casino.core.state_store import ensure_dirs, migrate_from_v7_if_needed

# Enumerate request methods whose WSGI bodies may carry JSON input.
BODY_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
# Preserve the accepted probe paths outside the versioned API prefix.
PROBE_PATHS = frozenset({"/healthz", "/readyz"})
# Enumerate packaged Admin assets that share the Admin API authorization boundary.
ADMIN_STATIC_PATHS = frozenset({"/admin", "/admin.html", "/admin.js", "/web/admin.js"})
# Name the exact credential-free worker request marker for cookie-free public shell bytes. (PWA-002)
PWA_PUBLIC_SHELL_HEADER = "X-Casino-Public-Shell"


# Classify one request for secret-safe diagnostics without retaining path identifiers.
def _route_class(method: str, path: str) -> str:
    # Group both accepted probe paths under one bounded class.
    if path in PROBE_PATHS:
        # Return no probe name or path value.
        return "probe"
    # Group Admin API and packaged Admin assets under their shared authority boundary.
    if path in ADMIN_STATIC_PATHS or path.startswith("/api/v1/admin/") or path.startswith("/api/v2/admin/"):
        # Return only the fixed privilege class.
        return "admin"
    # Group all remaining versioned API paths without logging resource identifiers.
    if path.startswith("/api/"):
        # Return only the fixed API class.
        return "api"
    # Treat GET browser routes as packaged or shell-fallback static requests.
    if method == "GET":
        # Return only the fixed browser asset class.
        return "static"
    # Preserve a final fixed class for malformed non-GET routes.
    return "unknown"


# Convert one WSGI environment into the minimal case-preserving header mapping auth expects.
def _request_headers(environ: dict) -> dict:
    # Start with content headers because WSGI stores them outside the HTTP_ namespace.
    headers = {}
    # Carry a supplied request content type through the existing application context.
    if environ.get("CONTENT_TYPE"):
        # Use conventional title casing for compatibility with auth header lookups.
        headers["Content-Type"] = str(environ["CONTENT_TYPE"])
    # Carry a supplied request content length without coercing its value.
    if environ.get("CONTENT_LENGTH"):
        # Preserve the WSGI server's validated scalar header value.
        headers["Content-Length"] = str(environ["CONTENT_LENGTH"])
    # Translate every remaining HTTP request header deterministically.
    for key, value in environ.items():
        # Ignore server metadata and already handled content headers.
        if not key.startswith("HTTP_"):
            # Continue scanning the bounded WSGI environment mapping.
            continue
        # Convert upper snake case into the conventional header spelling used by core auth.
        name = "-".join(part.capitalize() for part in key[5:].split("_"))
        # Retain the server-provided string value without trusting proxy identity headers.
        headers[name] = str(value)
    # Return an ordinary mapping that supports the existing case-specific get calls.
    return headers


# Read one bounded-by-server JSON request body using the WSGI input stream.
def _request_body(environ: dict, method: str, max_body_bytes: int) -> dict:
    # Preserve empty bodies for read-only methods and bodyless mutations.
    if method not in BODY_METHODS:
        # Return a fresh mapping so route handlers may normalize it safely.
        return {}
    # Start protected length parsing because a nonconforming server value must remain a bounded client error.
    try:
        # Parse the WSGI content length while treating an absent value as an empty body.
        length = int(environ.get("CONTENT_LENGTH") or 0)
    # Convert malformed server input into the standard validation envelope rather than a traceback response.
    except (TypeError, ValueError) as exc:
        # Raise a value-free error that cannot echo a hostile or private header value.
        raise ValidationError("Content-Length must be a non-negative integer") from exc
    # Reject negative lengths rather than treating them as an empty mutation body.
    if length < 0:
        # Preserve the same bounded public diagnostic used for non-numeric lengths.
        raise ValidationError("Content-Length must be a non-negative integer")
    # Reject an oversized declaration before reading any client-controlled bytes.
    if length > max_body_bytes:
        # Return a fixed 413 response that does not disclose the declared size.
        raise RequestTooLargeError()
    # Avoid reading from the server stream when no bytes were declared.
    if length == 0:
        # Return the same empty-body representation as the development adapter.
        return {}
    # Read exactly the declared request bytes from the WSGI server-owned stream.
    raw = environ["wsgi.input"].read(length)
    # Preserve an empty stream as an empty JSON object.
    if not raw:
        # Return without creating an artificial parse error.
        return {}
    # Start protected parsing so malformed client input reaches existing validation behavior.
    try:
        # Decode UTF-8 JSON into the same route body shape used by casino.app.
        return json.loads(raw.decode("utf-8"), parse_constant=reject_nonfinite_json_constant)
    # Preserve compatibility with the development adapter's raw-input fallback.
    except (UnicodeDecodeError, json.JSONDecodeError):
        # Decode replacement characters only into request-local data, never logs.
        return {"_raw": raw.decode("utf-8", errors="replace")}


# Construct one complete WSGI response with deterministic length and cache semantics.
def _respond(start_response, status: int, payload: bytes, content_type: str, extra_headers=None, effective_scheme="http"):
    # Resolve the registered HTTP phrase or a generic fallback for a custom status.
    phrase = HTTPStatus(status).phrase if status in HTTPStatus._value2member_map_ else "Response"
    # Start with transport headers shared by static and API responses.
    headers = [("Content-Type", content_type), ("Content-Length", str(len(payload))), ("Cache-Control", CACHE_CONTROL_NO_STORE)]
    # Add the fixed browser policy, with HSTS only for trusted effective HTTPS requests.
    headers.extend(response_security_headers(effective_scheme))
    # Append application-owned response headers such as session cookies unchanged.
    headers.extend(list(extra_headers or []))
    # Commit status and headers through the WSGI server before yielding bytes.
    start_response(f"{status} {phrase}", headers)
    # Return exactly one byte chunk for predictable server and test behavior.
    return [payload]


# Serialize one API envelope with stable formatting for parity with the local adapter.
def _json_response(start_response, status: int, payload: dict, extra_headers=None, effective_scheme="http"):
    # Encode deterministic JSON bytes without exposing Python object representations.
    raw = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    # Return the response through the shared WSGI header builder.
    return _respond(start_response, status, raw, "application/json; charset=utf-8", extra_headers, effective_scheme)


# Initialize provider-neutral state once during production worker boot.
def _validate_restricted_preview_routes() -> None:
    # Require exactly the reviewed anonymous fixed routes plus separately matched OAuth paths. (issues #317, #326, #332, #378)
    if auth.PUBLIC_API_PATHS != {"/api/v2/auth/login", "/api/v2/auth/guest", "/api/v2/auth/redeem-invitation", "/api/v2/auth/enrollment-policy", "/api/v2/auth/signup", "/api/v2/auth/oauth/providers", "/healthz"}:
        # Fail startup rather than allowing compatibility metadata to broaden public access.
        raise RuntimeError("Restricted preview public routes do not match the accepted allowlist")
    # Inspect registered method and pattern pairs without invoking any route.
    for route in ROUTER.routes:
        # Normalize the pattern only for fixed forbidden-route detection.
        pattern = str(route.pattern).lower()
        # Reject any unreviewed signup or public registration route during restricted preview.
        if (("signup" in pattern and pattern != "/api/v2/auth/signup") or ("/register" in pattern and pattern != "/api/v2/me/passkeys/register")):
            # Keep the diagnostic free of private route or configuration details.
            raise RuntimeError("Restricted preview does not permit signup routes")
        # Reject every OAuth action route outside the exact reviewed disabled-by-default v2 shapes.
        if "/auth/oauth/" in pattern and "/admin/" not in pattern and not any(fragment in pattern for fragment in ("/api/v2/auth/oauth/providers", "/api/v2/auth/oauth/(?p<provider>google|facebook)/start", "/api/v2/auth/oauth/(?p<provider>google|facebook)/callback")):
            # Fail startup instead of accepting an unreviewed provider or action route.
            raise RuntimeError("Restricted preview OAuth routes do not match the accepted allowlist")


# Initialize provider-neutral state and return the validated production security policy.
def _initialize_runtime() -> SecurityPolicy:
    # Require explicit production mode and mutable roots outside the immutable release.
    validate_production_runtime()
    # Apply the existing public bootstrap guard while the service remains loopback-bound.
    validate_bootstrap_for_startup("127.0.0.1")
    # Validate bounded session lifetime before any identity or session state is created.
    auth.validate_session_bounds()
    # Require the explicit canonical origin, proxy, cookie, body, and rate policy.
    policy = SecurityPolicy.from_environment()
    # Prove signup remains disabled and every disabled-by-default OAuth route matches the reviewed v2 allowlist.
    _validate_restricted_preview_routes()
    # Create only the configured external data and log directories.
    ensure_dirs()
    # Preserve the existing best-effort local JSON migration behavior outside release paths.
    migrate_from_v7_if_needed()
    # Bootstrap default players through the active storage provider when it is fresh.
    bootstrap_players(players.default_players)
    # Bootstrap the configured Admin after player persistence is available.
    auth.bootstrap_admin_from_env()
    # Record sanitized process readiness without a host, address, or configuration value.
    logger.info("production_adapter_ready", version=APP_VERSION)
    # Return the immutable policy for request handling after successful initialization.
    return policy


# Enforce the established authentication and player-resource boundary before route dispatch.
def _authorize_request(method: str, path: str, body: dict, headers: dict, client: str, policy: SecurityPolicy) -> dict:
    # Create the route context without accepting proxy-authored client identity.
    context = {"headers": headers, "client": client, "response_headers": [], "secure_cookie": True, "include_csrf_cookie": True, "session_samesite": policy.same_site}
    # Leave only the centrally declared public API and liveness routes anonymous.
    if auth.is_public_api_path(path):
        # Require exact Origin plus the bootstrap double-submit token for every anonymous mutation.
        validate_request_integrity(method, headers, policy)
        # Return the anonymous context before session lookup.
        return context
    # Authenticate the direct request headers through the canonical session service.
    session, user = auth.authenticate_headers(headers)
    # Require a distinct per-session CSRF secret for every authenticated mutation.
    validate_request_integrity(method, headers, policy, str(session.get("csrf_token") or ""))
    # Keep restricted-preview access on manually provisioned local identities and disposable guests only.
    if str(user.get("identity_provider") or "local").lower() not in ("local", "guest"):
        # Reject linked providers until the separately held public-launch gate while permitting #317 guests.
        raise ForbiddenError("Local invite or guest-trial access is required")
    # Publish the durable session to context-aware route handlers.
    context["session"] = session
    # Publish the authenticated user to authorization-aware route handlers.
    context["user"] = user
    # Enforce Admin authorization centrally for both supported Admin API versions.
    if path.startswith("/api/v1/admin/") or path.startswith("/api/v2/admin/"):
        # Reject non-Admin identities before route handlers can read or mutate Admin state.
        auth.require_admin(user)
    # Apply player and terms boundaries only to non-Admin identities.
    if not auth.is_admin(user):
        # Bind all player-aware route behavior to the authenticated user's player.
        context["bound_player_id"] = user["player_id"]
        # Block play and wallet mutation until the canonical terms requirement is satisfied.
        if auth.terms_status(user)["required"] and (path.startswith("/api/v1/games/") or path.startswith("/api/v1/autoplay/") or path == "/api/v2/me/tokens/add"):
            # Reuse the stable forbidden envelope without disclosing account details.
            raise ForbiddenError("Terms acceptance is required before play")
        # Reserve shared bot mutation for Admin while allowing non-mutating reads.
        if method != "GET" and path.startswith("/api/v1/bots/"):
            # Reject the request before any shared bot configuration changes.
            raise ForbiddenError("Admin role is required for bot account configuration")
        # Replace caller-authored autoplay player identity with the session binding.
        if path.startswith("/api/v1/autoplay/"):
            # Mutate only the request-local body passed to the router.
            body["player_id"] = user["player_id"]
        # Match player resource routes without interpreting other path segments.
        player_match = re.match(r"^/api/v1/players/([^/]+)", path)
        # Reject cross-player resource access without confirming whether the target exists.
        if player_match and player_match.group(1) != user["player_id"]:
            # Preserve the existing privacy-safe forbidden message.
            raise ForbiddenError("Player resource is outside the authenticated session")
    # Return the authenticated and authorized context for route dispatch.
    return context


# Serve the complete Casino frontend and API through a production WSGI server.
class CasinoWSGIApplication:
    # Initialize runtime state during worker boot so invalid service configuration fails closed.
    def __init__(self):
        # Complete all provider-neutral startup work before accepting the first request.
        self.policy = _initialize_runtime()
        # Create one thread-safe in-worker limiter for non-probe preview traffic.
        self.rate_limiter = RateLimiter(self.policy)
        # Isolate bounded probe traffic so public clients cannot consume application allowances.
        self.probe_rate_limiter = RateLimiter(self.policy)

    # Dispatch one API or probe request through the canonical router and envelope policy.
    def _api(self, environ: dict, start_response, method: str, raw_path: str, path: str, client: str, effective_scheme: str):
        # Decode only mutation bodies within the externally configured bound.
        body = _request_body(environ, method, self.policy.max_body_bytes)
        # Convert request headers without assigning forwarding trust here.
        headers = _request_headers(environ)
        # Apply authentication, request integrity, invite, and Admin boundaries.
        context = _authorize_request(method, path, body, headers, client, self.policy)
        # Dispatch the request through the single canonical route registry.
        data = ROUTER.dispatch(method, raw_path, body, context)
        # Return one same-origin OAuth completion redirect without a callback JSON body.
        if context.get("redirect"):
            # Prepend the reviewed Location to application-owned hardened cookie headers.
            redirect_headers = [("Location", str(context["redirect"])), *list(context.get("response_headers") or [])]
            # Publish an empty 303 response under the same cache and security policy.
            return _respond(start_response, 303, b"", "text/plain; charset=utf-8", redirect_headers, effective_scheme)
        # Return the standard successful envelope with hardened cookies and response policy.
        return _json_response(start_response, 200, {"ok": True, "data": data}, context.get("response_headers"), effective_scheme)

    # Serve one traversal-safe frontend asset from the extracted immutable release.
    def _static(self, environ: dict, start_response, path: str, effective_scheme: str):
        # Convert request headers once for optional session and Admin checks.
        headers = _request_headers(environ)
        # Accept the public-shell marker only when no cookie or authorization proof accompanies it.
        public_pwa_shell = headers.get(PWA_PUBLIC_SHELL_HEADER) == "1" and not headers.get("Cookie") and not headers.get("Authorization")
        # Collect only application-owned cookie response headers.
        extra_headers = []
        # Require the same application Admin authority for HTML and JavaScript assets.
        if path in ADMIN_STATIC_PATHS:
            # Authenticate the host-only session cookie before reading an Admin asset.
            session, user = auth.authenticate_headers(headers)
            # Reject normal invite users before any Admin bytes are read.
            auth.require_admin(user)
            # Keep the Admin browser's double-submit value synchronized with its session.
            extra_headers.append(csrf_cookie_header(session["csrf_token"], self.policy.same_site, True))
        # Map the same-origin application root to its packaged entry document.
        if path in ("", "/"):
            # Select the public frontend shell.
            path = "/index.html"
        # Map the stable Admin route to its separate packaged entry document.
        elif path == "/admin":
            # Select the Admin frontend shell without a redirect.
            path = "/admin.html"
        # Convert the URL path into a relative filesystem path.
        relative = Path(path.lstrip("/"))
        # Accept the existing optional /web prefix without duplicating the on-disk root.
        if relative.parts and relative.parts[0] == "web":
            # Remove only the explicit packaged-static prefix.
            relative = Path(*relative.parts[1:])
        # Resolve the candidate beneath the immutable web root.
        target = (WEB_DIR / relative).resolve()
        # Start protected containment handling for traversal attempts.
        try:
            # Require the resolved target to remain within packaged static content.
            target.relative_to(WEB_DIR.resolve())
        # Return a generic forbidden response for any escape attempt.
        except ValueError:
            # Avoid disclosing filesystem structure in the response.
            return _respond(start_response, 403, b"Forbidden\n", "text/plain; charset=utf-8")
        # Fall back to the same-origin application shell for client-side routes.
        if not target.is_file():
            # Select only the known packaged entry document.
            target = WEB_DIR / "index.html"
        # Bootstrap a host-only CSRF cookie on every non-Admin HTML shell response.
        if target.name == "index.html" and not extra_headers and not public_pwa_shell:
            # Reuse an active session's distinct CSRF value without authenticating a context-bound guest cookie.
            bootstrap_token = auth.csrf_token_for_session_cookie(headers)
            # Reuse a bounded anonymous double-submit cookie when no session is active.
            if not bootstrap_token:
                # Read only the named cookie rather than reflecting the complete Cookie header.
                existing = cookie_value(headers, CSRF_COOKIE)
                # Accept only token-url-safe lengths generated by this application.
                bootstrap_token = existing if 32 <= len(existing) <= 128 else new_csrf_token()
            # Set or refresh the production Secure host-only double-submit cookie.
            extra_headers.append(csrf_cookie_header(bootstrap_token, self.policy.same_site, True))
        # Read immutable asset bytes after containment and existence checks.
        content = target.read_bytes()
        # Derive a content type from the packaged asset name with a safe binary fallback.
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        # Return the static asset without adding security policy owned by issue #203.
        return _respond(start_response, 200, content, content_type, extra_headers, effective_scheme)

    # Implement the WSGI callable consumed by the supervised Gunicorn process.
    def __call__(self, environ: dict, start_response):
        # Normalize the server-supplied request method once for policy and routing.
        method = str(environ.get("REQUEST_METHOD") or "GET").upper()
        # Read the decoded WSGI path while preserving a leading slash.
        path = str(environ.get("PATH_INFO") or "/")
        # Read the raw query string without accepting a second path source.
        query = str(environ.get("QUERY_STRING") or "")
        # Reconstruct the router path exactly once using the WSGI query component.
        raw_path = path + ("?" + query if query else "")
        # Create a short correlation id without embedding process, host, or user identity.
        request_id = os.urandom(4).hex()
        # Classify the route before logging so raw client paths never enter diagnostics.
        route_class = _route_class(method, path)
        # Default to direct cleartext response policy until effective transport is validated.
        effective_scheme = "http"
        # Start protected dispatch so all security failures use stable secret-safe envelopes.
        try:
            # Resolve scheme and client only through server metadata and exact proxy policy.
            effective = effective_request(environ, self.policy)
            # Preserve trusted effective scheme for HSTS gating on every subsequent response.
            effective_scheme = effective.scheme
            # Apply a separate bounded probe policy with rotating client capacity for monitor availability.
            if path in PROBE_PATHS:
                # Bound each trusted effective client without consuming application allowances.
                self.probe_rate_limiter.check(effective.client, rotate_capacity=True)
            # Bound all application and browser traffic independently from probes.
            else:
                # Consume one application allowance keyed only by the trusted effective client.
                self.rate_limiter.check(effective.client)
            # Record only method and route class, never path, query, headers, body, or credentials.
            logger.info("request_accepted", request_id=request_id, method=method, route_class=route_class)
            # Route APIs, probes, and every non-GET request through application dispatch.
            if path.startswith("/api/") or path in PROBE_PATHS or method != "GET":
                # Return the canonical API response iterable.
                return self._api(environ, start_response, method, raw_path, path, effective.client, effective.scheme)
            # Serve browser assets only for GET requests outside the API and probe namespaces.
            return self._static(environ, start_response, path, effective.scheme)
        # Convert every declared application or security error into its stable public response.
        except CasinoError as exc:
            # Record only fixed request metadata and the bounded error code.
            logger.warning("request_rejected", request_id=request_id, method=method, route_class=route_class, code=exc.code)
            # Preserve the standard error envelope without request-derived details.
            return _json_response(start_response, exc.status, {"ok": False, "error": {"code": exc.code, "message": exc.message, "details": {}}}, effective_scheme=effective_scheme)
        # Prevent unexpected exception text, traceback values, or configuration from entering logs or responses.
        except Exception:
            # Record only the bounded correlation and normalized route identity.
            logger.error("request_exception", request_id=request_id, method=method, route_class=route_class)
            # Return a generic message plus the bounded request id to the client.
            return _json_response(start_response, 500, {"ok": False, "error": {"code": "INTERNAL_ERROR", "message": "Internal server error", "details": {"request_id": request_id}}}, effective_scheme=effective_scheme)


# Construct the single WSGI application object during Gunicorn worker import.
application = CasinoWSGIApplication()
