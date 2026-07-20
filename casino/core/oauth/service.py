"""Invite-only OAuth orchestration with one-time browser-bound flows.

Requirements: AUTH-002, OAUTH-003, OAUTH-004, OAUTH-005, OAUTH-007,
OAUTH-008, OAUTH-009, OAUTH-010, SESSION-006, and SEC-010.
"""

# Import hashing for one-way browser-owner and limiter keys.
import hashlib
# Import constant-time comparison for retained authenticated ownership.
import hmac
# Import threading so focused OAuth throttling is safe inside one worker.
import threading
# Import time and UTC date helpers for expiring flow and limiter records.
import time
# Import UTC-aware timestamps for durable one-time flow expiration.
from datetime import datetime, timedelta, timezone
# Import regular expressions for an explicit same-origin return-path allowlist.
import re
# Import mapping and callable types for dependency-injected provider tests.
from typing import Callable, Mapping
# Import query encoding for bounded same-origin completion redirects.
from urllib.parse import urlencode

# Import canonical authentication without creating or mutating users.
from casino.core import auth, logger
# Import canonical timestamps and random identifiers for durable audit records.
from casino.core.clock import utc_now
# Import random prefixed identifiers for flow persistence.
from casino.core.ids import new_id
# Import strict callback, URL, state, nonce, and PKCE helpers.
from casino.core.oauth.callbacks import build_callback_url, callback_state, new_flow_secrets, pkce_s256_challenge, validate_callback_query
# Import secret-safe configuration snapshots and readiness diagnostics.
from casino.core.oauth.configuration import OAuthConfiguration, load_oauth_configuration, oauth_diagnostics
# Import the provider-neutral identity link policy.
from casino.core.oauth.identity_links import IdentityLinkService
# Import provider adapter construction through an injectable boundary.
from casino.core.oauth.adapters import build_provider_adapter
# Import durable flow and identity-link repositories.
from casino.core.oauth.persistence import OAuthFlowRecord, OAuthFlowRepository, PersistentIdentityLinkRepository
# Import browser-cookie parsing without retaining raw cookie headers.
from casino.core.security import CSRF_COOKIE, CSRF_HEADER, cookie_value
# Import the configured JSON or MySQL provider through the shared storage port.
from casino.core.storage import StorageProvider, get_storage_provider
# Import fixed public error types without request-derived values.
from casino.errors import ForbiddenError, NotFoundError, RateLimitError, UnauthorizedError, ValidationError

# Expire authorization attempts quickly enough to constrain intercepted browser state.
FLOW_TTL_SECONDS = 300
# Permit only the lobby and canonical game routes as post-authentication destinations.
RETURN_PATH_RE = re.compile(r"^/(?:$|games/[a-z0-9][a-z0-9_-]{0,63})$")
# Bound repeated provider starts and callbacks independently from the application limiter.
RATE_LIMIT_COUNT = 8
# Forget limiter events after five minutes.
RATE_LIMIT_WINDOW_SECONDS = 300
# Bound retained in-worker limiter identities to prevent unbounded hostile-key growth.
MAX_RATE_KEYS = 2_000


# Render a canonical millisecond UTC timestamp for persistence.
def _timestamp(value: datetime) -> str:
    # Normalize the UTC suffix to the repository's canonical Z form.
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


# Validate a same-origin relative completion target without accepting query or fragments.
def _safe_return_to(value: object) -> str:
    # Default an omitted destination to the same-origin lobby.
    if value is None or value == "":
        # Keep the completion target local and predictable.
        return "/"
    # Require an exact bounded string accepted by the reviewed route allowlist.
    if not isinstance(value, str) or len(value) > 96 or not RETURN_PATH_RE.fullmatch(value):
        # Reject absolute, scheme-relative, encoded, query-bearing, and unknown destinations.
        raise ValidationError("OAuth return path is invalid")
    # Return the exact allowlisted local path.
    return value


# Append only server-owned completion metadata to an already validated local path.
def _completion_location(return_to: str, provider: str, outcome: str) -> str:
    # Encode fixed keys and allowlisted values without accepting caller query data.
    return return_to + "?" + urlencode({"oauth_provider": provider, "oauth_status": outcome})


# Return whether one canonical record remains an active private-invite local-password user.
def _is_authorized_invite_user(user: Mapping[str, object]) -> bool:
    # Require active canonical status, local identity authority, and retained password recovery.
    return user.get("status") == "active" and user.get("identity_provider", "local") == "local" and isinstance(user.get("user_id"), str) and bool(user.get("user_id")) and isinstance(user.get("password_hash"), str) and bool(user.get("password_hash"))


# Bind a flow to the browser's existing anonymous or session CSRF cookie without storing it.
def _browser_binding(headers: Mapping[str, object]) -> str:
    # Read only the named host cookie through the hardened cookie parser.
    csrf_value = cookie_value(headers, CSRF_COOKIE)
    # Require the token length produced by the application bootstrap or session rotation.
    if not isinstance(csrf_value, str) or not 32 <= len(csrf_value) <= 128:
        # Prevent starts or callbacks that cannot be bound to an initiating browser.
        raise ForbiddenError("OAuth browser binding is required")
    # Hash the cookie into a stable storage-safe binding and discard the raw value.
    return hashlib.sha256(("casino-oauth-owner\0" + csrf_value).encode("utf-8")).hexdigest()


# Require linking consent to carry the exact authenticated session's CSRF proof.
def _require_session_csrf(headers: Mapping[str, object], session: Mapping[str, object]) -> None:
    # Read the supplied proof and durable expected proof without logging either value.
    supplied = headers.get(CSRF_HEADER)
    # Read only the current authenticated session's independent CSRF value.
    expected = session.get("csrf_token")
    # Require bounded non-empty text before constant-time comparison.
    if not isinstance(supplied, str) or not isinstance(expected, str) or not supplied or not expected or len(supplied) > 128 or len(expected) > 128 or not hmac.compare_digest(supplied, expected):
        # Reject bearer-plus-anonymous-cookie substitution on the public start route.
        raise ForbiddenError("CSRF validation failed")


# Resolve one exact ready external provider configuration or fail closed as unavailable.
def _ready_provider(configuration: OAuthConfiguration, provider: str):
    # Reject local and unknown identifiers without reflecting the supplied path value.
    if provider not in {"google", "facebook"}:
        # Keep provider discovery limited to the published catalog.
        raise NotFoundError("Identity provider is unavailable")
    # Find the exact immutable provider configuration.
    selected = next((item for item in configuration.providers if item.spec.provider_id == provider), None)
    # Find the corresponding secret-safe readiness decision.
    diagnostic = next((item for item in oauth_diagnostics(configuration) if item.provider == provider), None)
    # Require an explicit enabled flag, complete credentials, valid callback, and integrated runtime.
    if selected is None or diagnostic is None or diagnostic.status != "ready" or not diagnostic.runtime_available:
        # Return the same not-found response for disabled and incomplete providers.
        raise NotFoundError("Identity provider is unavailable")
    # Return credentials only to the request-local adapter constructor.
    return selected


# Apply an OAuth-specific in-worker throttle keyed by one-way browser binding.
class OAuthRateLimiter:
    # Initialize bounded event buckets and a mutex.
    def __init__(self, clock: Callable[[], float] | None = None):
        # Use an injectable monotonic clock for deterministic unit tests.
        self.clock = time.monotonic if clock is None else clock
        # Store only hashed owner/action/provider keys.
        self.events: dict[str, list[float]] = {}
        # Serialize event pruning and append operations.
        self.lock = threading.Lock()

    # Consume one allowance without retaining raw cookies, users, IPs, or provider data.
    def check(self, owner_binding: str, provider: str, action: str) -> None:
        # Hash all bounded dimensions so even internal diagnostics cannot expose them.
        key = hashlib.sha256(f"{owner_binding}\0{provider}\0{action}".encode("utf-8")).hexdigest()
        # Read the current monotonic instant once.
        now = float(self.clock())
        # Serialize the complete prune, check, and append decision.
        with self.lock:
            # Drop expired timestamps from every retained bucket.
            self.events = {bucket_key: [seen for seen in seen_values if now - seen < RATE_LIMIT_WINDOW_SECONDS] for bucket_key, seen_values in self.events.items() if any(now - seen < RATE_LIMIT_WINDOW_SECONDS for seen in seen_values)}
            # Bound unique keys by evicting the oldest insertion-ordered entries.
            while len(self.events) >= MAX_RATE_KEYS and key not in self.events:
                # Remove the oldest key without exposing it.
                self.events.pop(next(iter(self.events)))
            # Read the current request bucket after pruning.
            bucket = self.events.setdefault(key, [])
            # Reject requests beyond the reviewed short-window allowance.
            if len(bucket) >= RATE_LIMIT_COUNT:
                # Return only the stable application rate-limit envelope.
                raise RateLimitError()
            # Record the accepted attempt for this provider action.
            bucket.append(now)


# Coordinate provider adapters, one-time flows, canonical users, links, and sessions.
class OAuthService:
    # Initialize production dependencies while retaining complete test injection.
    def __init__(self, *, environ: Mapping[str, object] | None = None, storage: StorageProvider | None = None, adapter_factory=None, limiter: OAuthRateLimiter | None = None):
        # Retain an injected environment snapshot or defer live reads until each request.
        self.environ = environ
        # Select the shared configured storage provider once for transactional repositories.
        self.storage = get_storage_provider() if storage is None else storage
        # Bind durable one-time flows to the shared provider.
        self.flows = OAuthFlowRepository(self.storage)
        # Bind durable compound identity links to the same provider.
        self.links = PersistentIdentityLinkRepository(self.storage)
        # Use concrete secure adapters only when tests did not inject a mock factory.
        self.adapter_factory = build_provider_adapter if adapter_factory is None else adapter_factory
        # Apply an independent bounded throttle to every provider operation.
        self.limiter = OAuthRateLimiter() if limiter is None else limiter

    # Load the current flag and credential snapshot so rollback takes effect without restart.
    def _configuration(self) -> OAuthConfiguration:
        # Read live process settings or the isolated test mapping without logging them.
        return load_oauth_configuration(self.environ)

    # Build one request-local provider adapter without storing it in service representations.
    def _adapter(self, provider: str):
        # Require a currently ready provider before credential access.
        selected = _ready_provider(self._configuration(), provider)
        # Construct the adapter with the exact public id and confidential secret.
        return self.adapter_factory(provider, selected.credentials.client_id, selected.credentials.client_secret)

    # Publish boolean-only provider availability for the anonymous login surface.
    def public_provider_status(self) -> dict:
        # Build secret-safe diagnostics from the current configuration.
        diagnostics = oauth_diagnostics(self._configuration())
        # Return only external provider ids and whether their complete runtime is ready.
        return {"providers": [{"provider": item.provider, "available": item.status == "ready" and item.runtime_available} for item in diagnostics if item.provider in {"google", "facebook"}]}

    # Start one sign-in or explicit authenticated link operation.
    def start(self, provider: str, body: Mapping[str, object], context: dict) -> dict:
        # Require an object-shaped body before reading bounded intent fields.
        if not isinstance(body, Mapping):
            # Reject arbitrary input without serialization.
            raise ValidationError("OAuth start request is invalid")
        # Reject every field outside the versioned start contract, including identity targets.
        if any(name not in {"action", "return_to", "confirm_link"} for name in body):
            # Prevent account selection, email hints, or future unreviewed intent from reaching a flow.
            raise ValidationError("OAuth start request contains unsupported fields")
        # Require the explicit operation named by the versioned request contract.
        action = body.get("action")
        # Reject unknown operations before provider or storage access.
        if action not in {"signin", "link"}:
            # Preserve a stable validation response.
            raise ValidationError("OAuth action is invalid")
        # Resolve a strict same-origin completion path before generating secrets.
        return_to = _safe_return_to(body.get("return_to"))
        # Require current provider readiness before writing a flow.
        adapter = self._adapter(provider)
        # Require browser binding material and consume one focused rate allowance.
        owner_binding = _browser_binding(context.get("headers") or {})
        # Apply a provider/action-specific attempt bound.
        self.limiter.check(owner_binding, provider, str(action))
        # Initialize linking ownership as absent for provider-only sign-in.
        user_id = None
        # Initialize session ownership as absent for provider-only sign-in.
        session_id = None
        # Require current canonical authentication and explicit confirmation for first linking.
        if action == "link":
            # Require the exact JSON boolean rather than truthy strings or numbers.
            if body.get("confirm_link") is not True:
                # Stop before provider navigation when consent is absent.
                raise ValidationError("Explicit identity-link confirmation is required")
            # Authenticate the canonical local session directly because start is also a public sign-in route.
            session, user = auth.authenticate_headers(context.get("headers") or {})
            # Bind the public start request to the authenticated session proof as well as the browser cookie.
            _require_session_csrf(context.get("headers") or {}, session)
            # Preserve private-invite recovery by requiring an active local-password account.
            if not _is_authorized_invite_user(user):
                # Reject identities without the canonical local recovery authority.
                raise ForbiddenError("An active local-password account is required")
            # Bind the callback to the exact authenticated durable user.
            user_id = user.get("user_id")
            # Bind the callback to the exact initiating session as well as browser cookie.
            session_id = session.get("session_id")
        # Generate independent state, nonce, and PKCE values after every early validation succeeds.
        secrets = new_flow_secrets()
        # Build the exact registered callback URI for this provider.
        callback_uri = build_callback_url(next(item for item in self._configuration().providers if item.spec.provider_id == provider).public_base_url, provider)
        # Record one canonical creation instant.
        created = datetime.now(timezone.utc)
        # Construct the complete expiring one-time record without claims or tokens.
        record = OAuthFlowRecord(flow_id=new_id("oauth_flow"), provider=provider, state=secrets.state, nonce=secrets.nonce, pkce_verifier=secrets.pkce_verifier, callback_uri=callback_uri, owner_binding=owner_binding, action=str(action), return_to=return_to, user_id=user_id, session_id=session_id, status="pending", created_at=_timestamp(created), expires_at=_timestamp(created + timedelta(seconds=FLOW_TTL_SECONDS)))
        # Persist state and every binding before returning a provider navigation URL.
        self.flows.create(record)
        # Build the authorization URL from only the just-persisted request-local secrets.
        authorization_url = adapter.authorization_url(redirect_uri=callback_uri, state=secrets.state, nonce=secrets.nonce, pkce_challenge=pkce_s256_challenge(secrets.pkce_verifier))
        # Record only the bounded provider and action, never a URL, secret, user, or flow id.
        logger.info("oauth_flow_started", provider=provider, action=action)
        # Return the sensitive navigation URL only to the initiating browser response.
        return {"provider": provider, "action": action, "authorization_url": authorization_url, "expires_in": FLOW_TTL_SECONDS}

    # Complete one provider callback after durable one-time flow consumption.
    def callback(self, provider: str, query: Mapping[str, object], context: dict) -> dict:
        # Require the provider to remain enabled before a callback can authenticate.
        adapter = self._adapter(provider)
        # Require and hash the initiating browser's retained owner cookie.
        owner_binding = _browser_binding(context.get("headers") or {})
        # Extract a single syntactically valid state before storage lookup.
        state_value = callback_state(query)
        # Apply an independent callback allowance without retaining state or browser values.
        self.limiter.check(owner_binding, provider, "callback")
        # Build the exact current callback so base/provider drift cannot consume another flow.
        selected = _ready_provider(self._configuration(), provider)
        # Canonicalize the configured callback URI before atomic flow claim.
        callback_uri = build_callback_url(selected.public_base_url, provider)
        # Consume the record atomically before validation or any external token exchange.
        record = self.flows.consume(provider, state_value, callback_uri, owner_binding)
        # Validate duplicates, state, ambiguity, authorization code, and provider error outcome.
        parameters = validate_callback_query(provider, query, record.state)
        # Return a safe same-origin cancellation outcome without contacting the provider token endpoint.
        if not parameters.succeeded:
            # Set a 303 redirect instead of reflecting provider error text in an API envelope.
            context["redirect"] = _completion_location(record.return_to, provider, "cancelled")
            # Record only the bounded provider, action, and sanitized outcome.
            logger.info("oauth_flow_cancelled", provider=provider, action=record.action)
            # Return a non-sensitive route result for direct router tests.
            return {"provider": provider, "status": "cancelled"}
        # Exchange the one-time code using the exact retained callback, nonce, and PKCE verifier.
        identity = adapter.exchange_code(code=parameters.code, redirect_uri=record.callback_uri, expected_nonce=record.nonce, pkce_verifier=record.pkce_verifier)
        # Apply canonical link and active-user policy without consulting identity email.
        link_service = IdentityLinkService(self.links, auth.find_user_by_id)
        # Complete explicit authenticated linking without replacing the current session.
        if record.action == "link":
            # Reauthenticate the session retained by the callback browser.
            session, user = auth.authenticate_headers(context.get("headers") or {})
            # Require exact initiating session and user ownership before the link transaction.
            if not isinstance(record.session_id, str) or not isinstance(record.user_id, str) or not hmac.compare_digest(str(session.get("session_id") or ""), record.session_id) or not hmac.compare_digest(str(user.get("user_id") or ""), record.user_id):
                # Prevent stolen linking state from binding to a different signed-in account.
                raise UnauthorizedError("OAuth linking session is invalid")
            # Require the canonical local password to remain a recovery path at completion time.
            if not _is_authorized_invite_user(user):
                # Reject accounts outside the private-invite password model.
                raise ForbiddenError("An active local-password account is required")
            # Atomically create or idempotently retain the provider-subject binding.
            resolution = link_service.link(identity, record.user_id)
            # Redirect only to the prevalidated same-origin path.
            context["redirect"] = _completion_location(record.return_to, provider, "linked")
            # Record a meaningful secret-free audit outcome.
            logger.info("oauth_identity_linked", provider=provider, created=resolution.link_created)
            # Return only non-sensitive completion facts for direct router tests.
            return {"provider": provider, "status": "linked", "created": resolution.link_created}
        # Resolve sign-in only through a prior provider-subject link and current active user.
        resolution = link_service.resolve(identity)
        # Re-read the active canonical user used for the new local session.
        user = auth.find_user_by_id(resolution.user_id)
        # Fail closed if canonical state changed after resolution.
        if not user or not _is_authorized_invite_user(user):
            # Reuse the active-user authorization boundary.
            raise ForbiddenError("User is inactive")
        # Create a normal Casino session tagged with its provider authentication method.
        session = auth.create_session(user, str(context.get("client") or ""), auth_method=provider)
        # Set the same hardened session and CSRF cookies as local-password login.
        context.setdefault("response_headers", []).extend(auth.session_cookie_headers(session, context.get("session_samesite", "Lax"), bool(context.get("secure_cookie")), bool(context.get("include_csrf_cookie"))))
        # Redirect only to the original prevalidated same-origin path.
        context["redirect"] = _completion_location(record.return_to, provider, "signed_in")
        # Record only the provider and successful action, never identity fields.
        logger.info("oauth_signin_completed", provider=provider)
        # Return only non-sensitive completion facts for direct router tests.
        return {"provider": provider, "status": "signed_in"}

    # Return authenticated user's boolean link status without provider subjects.
    def link_status(self, context: dict) -> dict:
        # Require the canonical session and active user supplied by central authorization.
        user = context.get("user") or {}
        # Reject direct route dispatch without authenticated ownership.
        if not _is_authorized_invite_user(user):
            # Preserve the standard authentication failure.
            raise UnauthorizedError()
        # Build current public availability for the same two providers.
        public = {row["provider"]: row["available"] for row in self.public_provider_status()["providers"]}
        # Read compound-link booleans without returning subjects or user ids.
        linked = self.links.provider_status_for_user(user["user_id"], ("google", "facebook"))
        # Combine readiness and ownership in stable display order.
        return {"providers": [{**row, "available": bool(public.get(row["provider"]))} for row in linked]}

    # Unlink one provider from the authenticated canonical user after explicit confirmation.
    def unlink(self, provider: str, body: Mapping[str, object], context: dict) -> dict:
        # Require the exact one-field confirmation contract before any persistent mutation.
        if not isinstance(body, Mapping) or set(body) != {"confirm_unlink"} or body.get("confirm_unlink") is not True:
            # Prevent accidental or forged generic POST requests from unlinking identity.
            raise ValidationError("Explicit identity-unlink confirmation is required")
        # Reject unknown provider paths before user or storage access.
        if provider not in {"google", "facebook"}:
            # Preserve the published provider catalog.
            raise NotFoundError("Identity provider is unavailable")
        # Read the centrally authenticated active canonical user.
        user = context.get("user") or {}
        # Require the retained local-password recovery authority before unlinking.
        if not _is_authorized_invite_user(user):
            # Never leave an account without the approved local recovery path.
            raise ForbiddenError("An active local-password account is required")
        # Revoke provider-authenticated sessions first so a later storage failure cannot revive them after relinking.
        revoked = auth.revoke_sessions_for_user_method(user["user_id"], provider)
        # Delete only this provider's exact authenticated-user binding transactionally after safe session rollback.
        deleted = self.links.delete_for_user(provider, user["user_id"])
        # Record only provider and boolean/count audit facts.
        logger.info("oauth_identity_unlinked", provider=provider, deleted=deleted, sessions_revoked=revoked)
        # Return idempotent non-sensitive unlink state.
        return {"provider": provider, "linked": False, "deleted": deleted}


# Return whether a provider-authenticated session remains enabled, linked, and active.
def provider_session_is_authorized(session: Mapping[str, object], user: Mapping[str, object], *, environ: Mapping[str, object] | None = None, storage: StorageProvider | None = None) -> bool:
    # Preserve local-password sessions without external configuration or storage access.
    method = session.get("auth_method", "local")
    # Accept only the canonical local marker for legacy and password sessions.
    if method == "local":
        # Keep local-password access unchanged.
        return True
    # Reject unknown external session markers immediately.
    if method not in {"google", "facebook"}:
        # Fail closed on damaged or unreviewed methods.
        return False
    # Require the canonical user to remain active.
    if not _is_authorized_invite_user(user):
        # Prevent disabled accounts from retaining provider sessions.
        return False
    # Require the provider's live flag and complete configuration to remain ready.
    try:
        # Reuse the exact readiness policy used for starts and callbacks.
        _ready_provider(load_oauth_configuration(environ), str(method))
    # Treat disabled or invalid provider settings as immediate rollback.
    except NotFoundError:
        # Invalidate only externally authenticated sessions.
        return False
    # Read the current link through the configured transactional provider.
    repository = PersistentIdentityLinkRepository(get_storage_provider() if storage is None else storage)
    # Require the exact provider-user link to remain present.
    return repository.find_by_user(str(method), user["user_id"]) is not None
