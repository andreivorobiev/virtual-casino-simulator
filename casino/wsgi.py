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

# Reuse the canonical route registry without starting casino.app's development server.
from casino.app import ROUTER
# Import production runtime and packaged-static configuration.
from casino.config import APP_VERSION, WEB_DIR, validate_bootstrap_for_startup, validate_production_runtime
# Import standard application errors for stable public envelopes.
from casino.errors import CasinoError, ForbiddenError, ValidationError
# Import authentication and application logging through the existing core boundaries.
from casino.core import auth, logger, players
# Import provider-neutral bootstrap behavior for a fresh external runtime root.
from casino.core.storage import bootstrap_players
# Import persistent-directory initialization and legacy local-state migration.
from casino.core.state_store import ensure_dirs, migrate_from_v7_if_needed

# Enumerate request methods whose WSGI bodies may carry JSON input.
BODY_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
# Preserve the accepted probe paths outside the versioned API prefix.
PROBE_PATHS = frozenset({"/healthz", "/readyz"})


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
def _request_body(environ: dict, method: str) -> dict:
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
        return json.loads(raw.decode("utf-8"))
    # Preserve compatibility with the development adapter's raw-input fallback.
    except (UnicodeDecodeError, json.JSONDecodeError):
        # Decode replacement characters only into request-local data, never logs.
        return {"_raw": raw.decode("utf-8", errors="replace")}


# Construct one complete WSGI response with deterministic length and cache semantics.
def _respond(start_response, status: int, payload: bytes, content_type: str, extra_headers=None):
    # Resolve the registered HTTP phrase or a generic fallback for a custom status.
    phrase = HTTPStatus(status).phrase if status in HTTPStatus._value2member_map_ else "Response"
    # Start with transport headers shared by static and API responses.
    headers = [("Content-Type", content_type), ("Content-Length", str(len(payload)))]
    # Prevent API and probe responses from being cached by intermediaries.
    if content_type.startswith("application/json"):
        # Match the existing no-store API contract.
        headers.append(("Cache-Control", "no-store"))
    # Append application-owned response headers such as session cookies unchanged.
    headers.extend(list(extra_headers or []))
    # Commit status and headers through the WSGI server before yielding bytes.
    start_response(f"{status} {phrase}", headers)
    # Return exactly one byte chunk for predictable server and test behavior.
    return [payload]


# Serialize one API envelope with stable formatting for parity with the local adapter.
def _json_response(start_response, status: int, payload: dict, extra_headers=None):
    # Encode deterministic JSON bytes without exposing Python object representations.
    raw = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    # Return the response through the shared WSGI header builder.
    return _respond(start_response, status, raw, "application/json; charset=utf-8", extra_headers)


# Initialize provider-neutral state once during production worker boot.
def _initialize_runtime() -> None:
    # Require explicit production mode and mutable roots outside the immutable release.
    validate_production_runtime()
    # Apply the existing public bootstrap guard while the service remains loopback-bound.
    validate_bootstrap_for_startup("127.0.0.1")
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


# Enforce the established authentication and player-resource boundary before route dispatch.
def _authorize_request(method: str, path: str, body: dict, headers: dict, client: str) -> dict:
    # Create the route context without accepting proxy-authored client identity.
    context = {"headers": headers, "client": client, "response_headers": []}
    # Leave only the centrally declared public API and liveness routes anonymous.
    if auth.is_public_api_path(path):
        # Return the anonymous context before session lookup.
        return context
    # Authenticate the direct request headers through the canonical session service.
    session, user = auth.authenticate_headers(headers)
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
        _initialize_runtime()

    # Dispatch one API or probe request through the canonical router and envelope policy.
    def _api(self, environ: dict, start_response, method: str, raw_path: str, path: str):
        # Create a short correlation id without embedding process, host, or user identity.
        request_id = os.urandom(4).hex()
        # Start protected dispatch so all application failures become valid WSGI responses.
        try:
            # Decode only mutation bodies declared by the WSGI server.
            body = _request_body(environ, method)
            # Convert direct request headers without trusting forwarded client metadata.
            headers = _request_headers(environ)
            # Read the direct peer address supplied by the WSGI server.
            client = str(environ.get("REMOTE_ADDR") or "")
            # Apply the existing authentication and player-resource boundary.
            context = _authorize_request(method, path, body, headers, client)
            # Record only method and application path for bounded request diagnostics.
            logger.info("api_request", request_id=request_id, method=method, path=raw_path)
            # Dispatch the request through the single canonical route registry.
            data = ROUTER.dispatch(method, raw_path, body, context)
            # Return the standard successful API envelope and application response headers.
            return _json_response(start_response, 200, {"ok": True, "data": data}, context.get("response_headers"))
        # Convert every declared application error into its stable public response.
        except CasinoError as exc:
            # Record only the bounded application diagnostic already owned by the error type.
            logger.warning("api_error", request_id=request_id, code=exc.code, message=exc.message, path=raw_path, details=exc.details)
            # Preserve the current error envelope and status contract.
            return _json_response(start_response, exc.status, {"ok": False, "error": {"code": exc.code, "message": exc.message, "details": exc.details}})
        # Prevent unexpected exception text or configuration values from entering HTTP responses.
        except Exception as exc:
            # Retain the exception only in the external application log for operator diagnosis.
            logger.error("api_exception", exc, request_id=request_id, path=raw_path)
            # Return a generic message plus the bounded request id to the client.
            return _json_response(start_response, 500, {"ok": False, "error": {"code": "INTERNAL_ERROR", "message": "Internal server error", "details": {"request_id": request_id}}})

    # Serve one traversal-safe frontend asset from the extracted immutable release.
    def _static(self, start_response, path: str):
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
        # Read immutable asset bytes after containment and existence checks.
        content = target.read_bytes()
        # Derive a content type from the packaged asset name with a safe binary fallback.
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        # Return the static asset without adding security policy owned by issue #203.
        return _respond(start_response, 200, content, content_type)

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
        # Route APIs, probes, and every non-GET request through application dispatch.
        if path.startswith("/api/") or path in PROBE_PATHS or method != "GET":
            # Return the canonical API response iterable.
            return self._api(environ, start_response, method, raw_path, path)
        # Serve browser assets only for GET requests outside the API and probe namespaces.
        return self._static(start_response, path)


# Construct the single WSGI application object during Gunicorn worker import.
application = CasinoWSGIApplication()
