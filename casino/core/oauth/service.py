# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Invite-only OAuth orchestration with one-time browser-bound flows.

Requirements: AUTH-002, OAUTH-003, OAUTH-004, OAUTH-005, OAUTH-007,
OAUTH-008, OAUTH-009, OAUTH-010, SESSION-006, and SEC-010.
"""

# Import hashing for one-way browser-owner and limiter keys.
import hashlib
# Import constant-time comparison for retained authenticated ownership.
import hmac
# Import UTC-aware timestamps for durable one-time flow expiration.
from datetime import datetime, timedelta, timezone
# Import regular expressions for an explicit same-origin return-path allowlist.
import re
# Import mapping types for dependency-injected provider tests.
from typing import Mapping
# Import query encoding for bounded same-origin completion redirects.
from urllib.parse import urlencode

# Import canonical authentication without creating or mutating users.
from casino import config
# Import canonical auth, bounded audit, enrollment policy, and operational provider controls.
from casino.core import auth, enrollment_policy, logger, oauth_controls
# Import random prefixed identifiers for flow persistence.
from casino.core.ids import new_id
# Import strict callback, URL, state, nonce, and PKCE helpers.
from casino.core.oauth.callbacks import build_callback_url, callback_state, new_flow_secrets, pkce_s256_challenge, validate_callback_query
# Import secret-safe configuration snapshots and readiness diagnostics.
from casino.core.oauth.configuration import OAuthConfiguration, load_oauth_configuration, oauth_diagnostics
# Import the provider-neutral identity link policy.
from casino.core.oauth.identity_links import IdentityLinkService
# Import recoverable provider-subject enrollment without broadening sign-in/link semantics.
from casino.core.oauth.enrollment import SocialEnrollmentService
# Import provider adapter construction through an injectable boundary.
from casino.core.oauth.adapters import build_provider_adapter
# Import durable flow and identity-link repositories.
from casino.core.oauth.persistence import OAuthFlowRecord, OAuthFlowRepository, OAuthRateLimiter, PersistentIdentityLinkRepository
# Import browser-cookie parsing without retaining raw cookie headers.
from casino.core.security import CSRF_COOKIE, CSRF_HEADER, cookie_value
# Import the configured JSON or MySQL provider through the shared storage port.
from casino.core.storage import StorageProvider, get_storage_provider
# Import fixed public error types without request-derived values.
from casino.errors import ForbiddenError, NotFoundError, ProviderUnavailableError, UnauthorizedError, ValidationError

# Expire authorization attempts quickly enough to constrain intercepted browser state.
FLOW_TTL_SECONDS = 300
# Permit only the lobby and canonical game routes as post-authentication destinations.
RETURN_PATH_RE = re.compile(r"^/(?:$|games/[a-z0-9][a-z0-9_-]{0,63})$")
# Bound repeated provider starts and callbacks independently from the application limiter.
RATE_LIMIT_COUNT = 8
# Forget limiter events after five minutes.
RATE_LIMIT_WINDOW_SECONDS = 300
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


# Return whether one record remains an active canonical account with a bound wallet.
def _is_active_canonical_user(user: Mapping[str, object]) -> bool:
    # Require the common active identity and wallet invariants without requiring a local password.
    return user.get("status") == "active" and isinstance(user.get("user_id"), str) and bool(user.get("user_id")) and isinstance(user.get("player_id"), str) and bool(user.get("player_id")) and user.get("identity_provider", "local") in {"local", "google", "facebook"}


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


# Coordinate provider adapters, one-time flows, canonical users, links, and sessions.
class OAuthService:
    # Initialize production dependencies while retaining complete test injection.
    def __init__(self, *, environ: Mapping[str, object] | None = None, storage: StorageProvider | None = None, adapter_factory=None, limiter: OAuthRateLimiter | None = None, operational_gate=None, enrollment_factory=None):
        # Retain an injected environment snapshot or defer live reads until each request.
        self.environ = environ
        # Select the shared configured storage provider once for transactional repositories.
        self.storage = get_storage_provider() if storage is None else storage
        # Bind durable compound identity links to the same provider.
        self.links = PersistentIdentityLinkRepository(self.storage)
        # Use concrete secure adapters only when tests did not inject a mock factory.
        self.adapter_factory = build_provider_adapter if adapter_factory is None else adapter_factory
        # Retain an optional injected limiter while production constructs a key-bound durable limiter lazily.
        self.limiter = limiter
        # Resolve the durable owner kill switch on every production request while permitting isolated tests to inject a fixed decision.
        self.operational_gate = oauth_controls.enabled if operational_gate is None else operational_gate
        # Retain an injectable recovery boundary while production constructs the audited implementation per callback.
        self.enrollment_factory = (lambda storage, digest_key, links: SocialEnrollmentService(storage, digest_key, links)) if enrollment_factory is None else enrollment_factory

    # Load the current flag and credential snapshot so rollback takes effect without restart.
    def _configuration(self) -> OAuthConfiguration:
        # Read live process settings or the isolated test mapping without logging them.
        return load_oauth_configuration(self.environ)

    # Construct the flow repository only after complete provider readiness proves a strong digest key.
    def _flows(self, configuration: OAuthConfiguration) -> OAuthFlowRepository:
        # Bind digested metadata and physically separate proofs to the current server key.
        return OAuthFlowRepository(self.storage, configuration.digest_key)

    # Construct the durable cross-process limiter under the same current digest key.
    def _limiter(self, configuration: OAuthConfiguration):
        # Preserve focused test injection while production uses provider-backed atomic buckets.
        return self.limiter if self.limiter is not None else OAuthRateLimiter(self.storage, configuration.digest_key)

    # Build one request-local provider adapter without storing it in service representations.
    def _adapter(self, configuration: OAuthConfiguration, provider: str):
        # Require the independently governed operational switch before credentials or network adapters are available.
        if self.operational_gate(provider) is not True:
            # Collapse disabled operational state into the same unavailable response as incomplete configuration.
            raise NotFoundError("Identity provider is unavailable")
        # Require a currently ready provider before credential access.
        selected = _ready_provider(configuration, provider)
        # Construct the adapter with the exact public id and confidential secret.
        return self.adapter_factory(provider, selected.credentials.client_id, selected.credentials.client_secret)

    # Publish boolean-only provider availability for the anonymous login surface.
    def public_provider_status(self) -> dict:
        # Build secret-safe diagnostics from the current configuration.
        diagnostics = oauth_diagnostics(self._configuration())
        # Resolve signup capabilities without operational decision logging or provider transport.
        try:
            # Read one coherent policy snapshot for both external providers.
            capabilities = enrollment_policy.capabilities()
        # Fail closed when policy storage requires recovery.
        except Exception:
            # Publish no signup method as available while retaining sign-in diagnostics.
            capabilities = {"mode": enrollment_policy.MODE_CLOSED, "methods": {"google": False, "facebook": False}}
        # Build boolean-only rows without credential, policy revision, or provider subject data.
        rows = []
        # Inspect the two reviewed external providers in diagnostic order.
        for item in diagnostics:
            # Skip local password and any future unreviewed provider.
            if item.provider not in {"google", "facebook"}:
                # Continue to the next diagnostic row.
                continue
            # Require operational release plus complete safe runtime readiness for any provider navigation.
            available = self.operational_gate(item.provider) is True and item.status == "ready" and item.runtime_available
            # Require the independent self-signup mode and method flag in addition to provider readiness.
            signup_available = available and capabilities.get("mode") == enrollment_policy.MODE_SELF_SIGNUP and capabilities.get("methods", {}).get(item.provider) is True
            # Publish only the reviewed boolean availability projection.
            rows.append({"provider": item.provider, "available": available, "signup_available": signup_available})
        # Return the stable provider collection.
        return {"providers": rows}

    # Start one sign-in or explicit authenticated link operation.
    def start(self, provider: str, body: Mapping[str, object], context: dict) -> dict:
        # Require an object-shaped body before reading bounded intent fields.
        if not isinstance(body, Mapping):
            # Reject arbitrary input without serialization.
            raise ValidationError("OAuth start request is invalid")
        # Require the explicit operation named by the versioned request contract.
        action = body.get("action")
        # Reject unknown operations before provider or storage access.
        if action not in {"signin", "link", "signup"}:
            # Preserve a stable validation response.
            raise ValidationError("OAuth action is invalid")
        # Select the exact field allowlist for this explicit operation.
        allowed_fields = {"action", "return_to", "confirm_link"} if action == "link" else ({"action", "return_to", "terms_version", "accepted_terms", "accepted_privacy", "accepted_fake_money", "locale"} if action == "signup" else {"action", "return_to"})
        # Reject every field outside the selected versioned contract, including identity targets.
        if any(name not in allowed_fields for name in body):
            # Prevent account selection, email hints, roles, or future unreviewed intent from reaching a flow.
            raise ValidationError("OAuth start request contains unsupported fields")
        # Resolve a strict same-origin completion path before generating secrets.
        return_to = _safe_return_to(body.get("return_to"))
        # Initialize signup acknowledgement metadata as absent for sign-in or linking.
        terms_version = None
        # Initialize signup locale as absent for sign-in or linking.
        locale = None
        # Require current explicit terms, privacy, and fake-money acknowledgement for signup.
        if action == "signup":
            # Require all three exact JSON booleans before policy, provider, or storage access.
            if body.get("accepted_terms") is not True or body.get("accepted_privacy") is not True or body.get("accepted_fake_money") is not True:
                # Reject implied or partial consent.
                raise ValidationError("Explicit enrollment acknowledgements are required")
            # Require the current server-reviewed terms version.
            if body.get("terms_version") != config.GUEST_TERMS_VERSION:
                # Reject stale or caller-selected terms versions.
                raise ValidationError("Current enrollment acknowledgement is required")
            # Require one translated locale without silently coercing arbitrary input.
            if body.get("locale") not in {"en-US", "ru-RU"}:
                # Reject unsupported presentation state before flow persistence.
                raise ValidationError("Enrollment locale is invalid")
            # Enforce and operationally log the provider-specific signup method before navigation.
            signup_decision = enrollment_policy.evaluate(enrollment_policy.ROUTE_SIGNUP, str(provider))
            # Stop while mode or method remains disabled.
            if signup_decision["allowed"] is not True:
                # Preserve a generic gate response without exposing stored policy.
                raise ForbiddenError("Social account signup is disabled")
            # Retain only the accepted current terms version in flow metadata.
            terms_version = str(body["terms_version"])
            # Retain only the reviewed translated locale.
            locale = str(body["locale"])
        # Require current provider readiness before writing a flow.
        configuration = self._configuration()
        # Require the independent network-release latch before constructing any transport adapter.
        adapter = self._adapter(configuration, provider)
        # Require browser binding material and consume one focused rate allowance.
        owner_binding = _browser_binding(context.get("headers") or {})
        # Apply a provider/action-specific attempt bound.
        self._limiter(configuration).check(owner_binding, provider, str(action))
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
        callback_uri = build_callback_url(next(item for item in configuration.providers if item.spec.provider_id == provider).public_base_url, provider)
        # Record one canonical creation instant.
        created = datetime.now(timezone.utc)
        # Construct the complete expiring one-time record without claims or tokens.
        record = OAuthFlowRecord(flow_id=new_id("oauth_flow"), provider=provider, state=secrets.state, nonce=secrets.nonce, pkce_verifier=secrets.pkce_verifier, callback_uri=callback_uri, owner_binding=owner_binding, action=str(action), return_to=return_to, terms_version=terms_version, locale=locale, user_id=user_id, session_id=session_id, status="pending", created_at=_timestamp(created), expires_at=_timestamp(created + timedelta(seconds=FLOW_TTL_SECONDS)))
        # Persist state and every binding before returning a provider navigation URL.
        self._flows(configuration).create(record)
        # Build the authorization URL from only the just-persisted request-local secrets.
        authorization_url = adapter.authorization_url(redirect_uri=callback_uri, state=secrets.state, nonce=secrets.nonce, pkce_challenge=pkce_s256_challenge(secrets.pkce_verifier))
        # Record only the bounded provider and action, never a URL, secret, user, or flow id.
        logger.info("oauth_flow_started", provider=provider, action=action)
        # Return the sensitive navigation URL only to the initiating browser response.
        return {"provider": provider, "action": action, "authorization_url": authorization_url, "expires_in": FLOW_TTL_SECONDS}

    # Complete one provider callback after durable one-time flow consumption.
    def callback(self, provider: str, query: Mapping[str, object], context: dict) -> dict:
        # Require the provider to remain enabled before a callback can authenticate.
        configuration = self._configuration()
        # Require both provider enablement and the separate network-release latch before any adapter exists.
        adapter = self._adapter(configuration, provider)
        # Require and hash the initiating browser's retained owner cookie.
        owner_binding = _browser_binding(context.get("headers") or {})
        # Extract a single syntactically valid state before storage lookup.
        state_value = callback_state(query)
        # Apply an independent callback allowance without retaining state or browser values.
        self._limiter(configuration).check(owner_binding, provider, "callback")
        # Build the exact current callback so base/provider drift cannot consume another flow.
        selected = _ready_provider(configuration, provider)
        # Canonicalize the configured callback URI before atomic flow claim.
        callback_uri = build_callback_url(selected.public_base_url, provider)
        # Validate duplicates, state, ambiguity, authorization code, and provider error outcome.
        parameters = validate_callback_query(provider, query, state_value)
        # Bind the current digest key to one recoverable flow repository instance.
        flows = self._flows(configuration)
        # Lease the flow atomically; transient exchange failures can return this same state to pending.
        record = flows.claim(provider, state_value, callback_uri, owner_binding)
        # Return a safe same-origin cancellation outcome without contacting the provider token endpoint.
        if not parameters.succeeded:
            # Commit a cancellation replay tombstone and remove exchange proof material.
            flows.complete(record)
            # Set a 303 redirect instead of reflecting provider error text in an API envelope.
            context["redirect"] = _completion_location(record.return_to, provider, "cancelled")
            # Record only the bounded provider, action, and sanitized outcome.
            logger.info("oauth_flow_cancelled", provider=provider, action=record.action)
            # Return a non-sensitive route result for direct router tests.
            return {"provider": provider, "status": "cancelled"}
        # Start protected exchange so transport ambiguity returns the same flow to pending.
        try:
            # Exchange the code using the exact retained callback, nonce, and PKCE verifier.
            identity = adapter.exchange_code(code=parameters.code, redirect_uri=record.callback_uri, expected_nonce=record.nonce, pkce_verifier=record.pkce_verifier)
        # Preserve a bounded same-flow retry only for fixed retryable transport failures.
        except ProviderUnavailableError:
            # Release the exchange lease without deleting nonce or PKCE proof material.
            flows.release(record)
            # Record no URL, code, state, browser, or provider response details.
            logger.info("oauth_exchange_retryable", provider=provider, action=record.action)
            # Return the standard retryable 503 envelope to the initiating browser.
            raise
        # Treat cryptographic, issuer, audience, app-binding, and claim failures as terminal.
        except Exception:
            # Prevent replay of a terminally rejected provider response.
            flows.complete(record)
            # Preserve the original safe exception class and message.
            raise
        # Apply canonical link and active-user policy without consulting identity email.
        link_service = IdentityLinkService(self.links, auth.find_user_by_id)
        # Complete explicit authenticated linking without replacing the current session.
        if record.action == "link":
            # Reauthenticate the session retained by the callback browser.
            session, user = auth.authenticate_headers(context.get("headers") or {})
            # Require exact initiating session and user ownership before the link transaction.
            if not flows.link_owner_matches(record, str(user.get("user_id") or ""), str(session.get("session_id") or "")):
                # Commit terminal replay protection because the provider code has already been exchanged.
                flows.complete(record)
                # Prevent stolen linking state from binding to a different signed-in account.
                raise UnauthorizedError("OAuth linking session is invalid")
            # Require the canonical local password to remain a recovery path at completion time.
            if not _is_authorized_invite_user(user):
                # Commit terminal replay protection because the canonical owner changed after exchange.
                flows.complete(record)
                # Reject accounts outside the private-invite password model.
                raise ForbiddenError("An active local-password account is required")
            # Start protected link persistence because the provider code cannot be safely exchanged again.
            try:
                # Atomically create or idempotently retain the provider-subject binding.
                resolution = link_service.link(identity, str(user.get("user_id")))
            # Convert every post-exchange linking failure into a terminal restart boundary.
            except Exception:
                # Commit replay protection while preserving any idempotent link already published.
                flows.complete(record)
                # Preserve the original safe application or storage failure.
                raise
            # Commit replay protection only after the idempotent durable link exists.
            flows.complete(record)
            # Redirect only to the prevalidated same-origin path.
            context["redirect"] = _completion_location(record.return_to, provider, "linked")
            # Record a meaningful secret-free audit outcome.
            logger.info("oauth_identity_linked", provider=provider, created=resolution.link_created)
            # Return only non-sensitive completion facts for direct router tests.
            return {"provider": provider, "status": "linked", "created": resolution.link_created}
        # Complete explicit provider-subject signup through the recoverable canonical provisioning boundary.
        if record.action == "signup":
            # Re-evaluate and log the provider-specific method at mutation time so rollback is immediate.
            signup_decision = enrollment_policy.evaluate(enrollment_policy.ROUTE_SIGNUP, provider)
            # Deny a callback when the owner disabled signup after start.
            if signup_decision["allowed"] is not True:
                # Commit terminal replay protection because the provider code was already exchanged.
                flows.complete(record)
                # Preserve existing linked sign-in while refusing new enrollment.
                raise ForbiddenError("Social account signup is disabled")
            # Require the consumed flow to carry complete start-time acknowledgement metadata.
            if not isinstance(record.terms_version, str) or record.terms_version != config.GUEST_TERMS_VERSION or record.locale not in {"en-US", "ru-RU"}:
                # Commit terminal replay protection for malformed durable flow state.
                flows.complete(record)
                # Return one fixed acknowledgement failure.
                raise ValidationError("Current enrollment acknowledgement is required")
            # Start protected local provisioning because the provider code cannot be safely exchanged again.
            try:
                # Construct the recovery service with the same provider, digest key, and link repository.
                enrollment = self.enrollment_factory(self.storage, configuration.digest_key, self.links)
                # Provision or recover the exact provider-subject canonical account.
                enrolled = enrollment.provision(identity, record.terms_version, record.locale)
                # Create a normal local session tagged with the verified provider method.
                session = auth.create_session(enrolled.user, str(context.get("client") or ""), auth_method=provider)
            # Convert every post-exchange persistence failure into a terminal restart boundary.
            except Exception:
                # Commit replay protection while the deterministic pending record remains recoverable by a new flow.
                flows.complete(record)
                # Preserve the original safe application or storage failure.
                raise
            # Commit replay protection only after canonical account and session are durable.
            flows.complete(record)
            # Set the same hardened session and CSRF cookies as every other authentication method.
            context.setdefault("response_headers", []).extend(auth.session_cookie_headers(session, context.get("session_samesite", "Lax"), bool(context.get("secure_cookie")), bool(context.get("include_csrf_cookie"))))
            # Redirect only to the original prevalidated same-origin path.
            context["redirect"] = _completion_location(record.return_to, provider, "signed_up")
            # Record only provider and bounded lifecycle booleans, never identity metadata.
            logger.info("oauth_signup_completed", provider=provider, created=enrolled.created, recovered=enrolled.recovered)
            # Return only non-sensitive completion facts for direct router tests.
            return {"provider": provider, "status": "signed_up", "created": enrolled.created, "recovered": enrolled.recovered}
        # Resolve sign-in only through a prior provider-subject link and current active user.
        # Start protected resolution because the provider code cannot be safely exchanged again.
        try:
            # Resolve sign-in only through a prior durable provider-subject link.
            resolution = link_service.resolve(identity)
        # Convert every post-exchange resolution failure into a terminal restart boundary.
        except Exception:
            # Commit replay protection without creating any local session.
            flows.complete(record)
            # Preserve the original safe application or storage failure.
            raise
        # Re-read the active canonical user used for the new local session.
        user = auth.find_user_by_id(resolution.user_id)
        # Fail closed if canonical state changed after resolution.
        if not user or not _is_active_canonical_user(user):
            # Commit replay protection because the linked account is no longer authorized.
            flows.complete(record)
            # Reuse the active-user authorization boundary.
            raise ForbiddenError("User is inactive")
        # Start protected local session creation after successful provider verification.
        try:
            # Create a normal Casino session tagged with its provider authentication method.
            session = auth.create_session(user, str(context.get("client") or ""), auth_method=provider)
        # Convert local session persistence failure into a terminal restart boundary.
        except Exception:
            # Commit replay protection without returning a credential.
            flows.complete(record)
            # Preserve the original safe application or storage failure.
            raise
        # Commit replay protection only after the local session exists durably.
        flows.complete(record)
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
        if not _is_active_canonical_user(user):
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
    if not _is_active_canonical_user(user):
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
