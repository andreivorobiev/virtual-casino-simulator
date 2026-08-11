# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Cross-process OAuth flow, proof, rate, and identity-link persistence.

Requirements: OAUTH-003, OAUTH-004, OAUTH-008, OAUTH-009, STORAGE-001,
STORAGE-002, and SESSION-007. Raw state, callback, browser, user, and session
bindings never share a durable document with nonce or PKCE material.
"""

# Import keyed hashing for non-reversible durable binding indexes.
import hashlib
# Import constant-time comparison for every opaque durable verifier.
import hmac
# Import cryptographic randomness for one-attempt exchange claim tokens.
import secrets
# Import immutable record helpers while suppressing proof material from representations.
from dataclasses import dataclass, field
# Import UTC timestamp helpers for expiry and recoverable claim leases.
from datetime import datetime, timedelta, timezone

# Import the application schema marker used by provider-backed documents.
from casino.config import SCHEMA_VERSION
# Import canonical timestamps for durable lifecycle fields.
from casino.core.clock import utc_now
# Import the existing allowlisted identity-link model.
from casino.core.oauth.identity_links import ExternalIdentityLink
# Import the shared JSON/MySQL provider transaction contract.
from casino.core.storage import StorageProvider
# Import stable public failures without reflecting proof values.
from casino.errors import ConflictError, RateLimitError, UnauthorizedError, ValidationError

# Name the metadata document containing only proof digests and lifecycle fields.
FLOW_DOCUMENT_KEY = "auth/oauth_flows"
# Name the separate document containing only nonce and PKCE exchange material.
FLOW_SECRET_DOCUMENT_KEY = "auth/oauth_flow_secrets"
# Name the durable cross-process OAuth limiter document.
RATE_DOCUMENT_KEY = "auth/oauth_rate_limits"
# Name the durable provider-subject link document.
LINK_DOCUMENT_KEY = "auth/oauth_identity_links"
# Bound retained pending and terminal flow metadata.
MAX_FLOW_RECORDS = 2_000
# Bound retained flow-secret rows independently from metadata.
MAX_SECRET_RECORDS = 2_000
# Bound durable identity links without evicting authentication authority.
MAX_LINK_RECORDS = 10_000
# Bound distinct rate buckets retained in durable state.
MAX_RATE_BUCKETS = 2_000
# Keep an in-flight exchange claim bounded so a crashed worker can recover.
EXCHANGE_CLAIM_SECONDS = 60
# Accept only the three reviewed OAuth actions.
FLOW_ACTIONS = frozenset({"signin", "link", "signup"})
# Accept only reviewed flow lifecycle states.
FLOW_STATUSES = frozenset({"pending", "exchanging", "consumed"})


# Parse one canonical UTC timestamp while treating malformed persistence as invalid.
def _parse_timestamp(value: str) -> datetime:
    # Require exact text so arbitrary persisted objects are never stringified.
    if not isinstance(value, str):
        # Raise a value-free storage validation failure.
        raise ValidationError("OAuth persistence timestamp is invalid")
    # Start protected ISO parsing so damaged rows fail closed.
    try:
        # Parse the canonical Z suffix as an explicit UTC offset.
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    # Replace parser details with a fixed public message.
    except ValueError:
        # Suppress the persisted value and parser exception chain.
        raise ValidationError("OAuth persistence timestamp is invalid") from None
    # Require an offset-aware timestamp before comparing expiry.
    if parsed.tzinfo is None:
        # Reject ambiguous local time values from damaged persistence.
        raise ValidationError("OAuth persistence timestamp is invalid")
    # Normalize valid offsets to UTC for deterministic comparisons.
    return parsed.astimezone(timezone.utc)


# Render one canonical millisecond UTC timestamp.
def _timestamp(value: datetime) -> str:
    # Normalize the UTC suffix to the repository's canonical Z form.
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


# Represent one request-local OAuth flow while suppressing all proof fields from repr.
@dataclass(frozen=True)
class OAuthFlowRecord:
    # Store an opaque internal flow identifier.
    flow_id: str = field(repr=False)
    # Store the reviewed provider partition.
    provider: str
    # Retain returned state only in the active request.
    state: str = field(repr=False)
    # Retain OIDC nonce only in the active request.
    nonce: str = field(repr=False)
    # Retain PKCE verifier only in the active request.
    pkce_verifier: str = field(repr=False)
    # Retain the canonical callback only in the active request.
    callback_uri: str = field(repr=False)
    # Retain the one-way browser binding only in the active request.
    owner_binding: str = field(repr=False)
    # Store signin or link as the reviewed operation.
    action: str
    # Store one prevalidated same-origin completion path.
    return_to: str
    # Retain the exact reviewed terms version only for an explicit signup intent.
    terms_version: str | None = None
    # Retain the translated enrollment locale only for an explicit signup intent.
    locale: str | None = None
    # Carry only a durable HMAC verifier for a linking user after claim.
    user_id: str | None = field(default=None, repr=False)
    # Carry only a durable HMAC verifier for a linking session after claim.
    session_id: str | None = field(default=None, repr=False)
    # Store the current durable lifecycle state.
    status: str = "pending"
    # Store the canonical creation timestamp.
    created_at: str = ""
    # Store the exclusive expiry timestamp.
    expires_at: str = ""
    # Carry the raw exchange claim token only in the claiming request.
    exchange_token: str | None = field(default=None, repr=False)


# Return a fresh flow metadata document.
def _default_flows() -> dict:
    # Preserve the schema marker and one bounded metadata collection.
    return {"schema_version": SCHEMA_VERSION, "flows": []}


# Return a fresh flow-secret document.
def _default_secrets() -> dict:
    # Preserve the schema marker and a physically separate proof collection.
    return {"schema_version": SCHEMA_VERSION, "secrets": []}


# Return a fresh limiter document.
def _default_rates() -> dict:
    # Preserve the schema marker and bounded cross-process buckets.
    return {"schema_version": SCHEMA_VERSION, "buckets": []}


# Return a fresh identity-link document.
def _default_links() -> dict:
    # Preserve the schema marker and one durable link collection.
    return {"schema_version": SCHEMA_VERSION, "links": []}


# Require one exact document collection without destructively normalizing malformed state.
def _collection(document: object, name: str, message: str) -> list:
    # Reject malformed roots or collections before any mutation can replace them.
    if not isinstance(document, dict) or not isinstance(document.get(name), list):
        # Preserve the original provider document for operator recovery.
        raise RuntimeError(message)
    # Reject malformed rows rather than silently dropping recoverable evidence.
    if any(not isinstance(row, dict) for row in document[name]):
        # Abort the provider transaction without rewriting any row.
        raise RuntimeError(message)
    # Return the exact mutable collection under the provider transaction.
    return document[name]


# Validate one request-local flow before its digested metadata and proofs can be stored.
def _validate_flow(record: OAuthFlowRecord) -> None:
    # Require the immutable record type so callers cannot smuggle fields.
    if not isinstance(record, OAuthFlowRecord):
        # Reject arbitrary flow objects before storage access.
        raise ValidationError("OAuth flow record is invalid")
    # Collect bounded request-local text fields.
    scalar_values = (record.flow_id, record.provider, record.state, record.nonce, record.pkce_verifier, record.callback_uri, record.owner_binding, record.return_to, record.created_at, record.expires_at)
    # Reject missing, overlong, or control-bearing proof values.
    if any(not isinstance(value, str) or not value or len(value) > 4096 or any(not character.isprintable() for character in value) for value in scalar_values):
        # Return one stable validation class for every malformed field.
        raise ValidationError("OAuth flow record is invalid")
    # Require a reviewed action and a newly pending lifecycle.
    if record.action not in FLOW_ACTIONS or record.status != "pending" or record.exchange_token is not None:
        # Reject action or lifecycle drift before persistence.
        raise ValidationError("OAuth flow record is invalid")
    # Require a usable exclusive expiry.
    if _parse_timestamp(record.expires_at) <= _parse_timestamp(record.created_at):
        # Reject unusable retention bounds.
        raise ValidationError("OAuth flow record is invalid")
    # Require raw authenticated owner ids only for the request-local link start.
    if record.action == "link" and (not isinstance(record.user_id, str) or not record.user_id or not isinstance(record.session_id, str) or not record.session_id):
        # Prevent a provider callback from selecting a linking target.
        raise ValidationError("OAuth linking flow owner is invalid")
    # Require sign-in and signup flows to carry no canonical target.
    if record.action in {"signin", "signup"} and (record.user_id is not None or record.session_id is not None):
        # Reject preselected users so email or a caller id cannot become a target.
        raise ValidationError("OAuth provider flow owner is invalid")
    # Require signup-only consent metadata to be complete and bounded.
    if record.action == "signup" and (not isinstance(record.terms_version, str) or not record.terms_version or len(record.terms_version) > 64 or record.locale not in {"en-US", "ru-RU"}):
        # Reject missing or stale signup acknowledgement metadata.
        raise ValidationError("OAuth signup acknowledgement is invalid")
    # Require sign-in and link flows to carry no signup acknowledgement metadata.
    if record.action != "signup" and (record.terms_version is not None or record.locale is not None):
        # Prevent one flow intent from smuggling enrollment meaning.
        raise ValidationError("OAuth flow acknowledgement is invalid")


# Persist and recoverably claim OAuth flows across JSON and MySQL processes.
class OAuthFlowRepository:
    # Bind one repository to the shared provider and server-owned HMAC key.
    def __init__(self, provider: StorageProvider, digest_key: str):
        # Reject missing or weak digest material before any proof persistence.
        if not isinstance(digest_key, str) or len(digest_key.encode("utf-8")) < 32:
            # Preserve one value-free readiness failure.
            raise ValidationError("OAuth digest configuration is unavailable")
        # Store the provider interface without branching on JSON or MySQL.
        self.provider = provider
        # Store key bytes without exposing them through repository representations.
        self._digest_key = digest_key.encode("utf-8")

    # Compute one domain-separated durable verifier.
    def _digest(self, domain: str, value: str) -> str:
        # Require exact bounded text before keyed hashing.
        if not isinstance(value, str) or not value or len(value) > 4096:
            # Reject malformed proof inputs without persistence access.
            raise ValidationError("OAuth flow binding is invalid")
        # Compute a non-reversible verifier under the server-owned key.
        return hmac.new(self._digest_key, f"{domain}\0{value}".encode("utf-8"), hashlib.sha256).hexdigest()

    # Create one pending flow with metadata and proofs in separate durable documents.
    def create(self, record: OAuthFlowRecord) -> OAuthFlowRecord:
        # Validate every request-local binding before opening provider transactions.
        _validate_flow(record)
        # Read current UTC once for deterministic pruning.
        now = datetime.now(timezone.utc)

        # Define the separate proof-document transaction.
        def store_secret(document: object) -> dict:
            # Require recognizable existing state or the explicit absent default.
            rows = _collection(document, "secrets", "OAuth proof storage requires operator recovery")
            # Retain unexpired proof rows while preserving their exact fields.
            retained = [row for row in rows if _parse_timestamp(row.get("expires_at")) > now]
            # Reject duplicate internal ids without replacing proof material.
            if any(hmac.compare_digest(str(row.get("flow_id", "")), record.flow_id) for row in retained):
                # Preserve the existing proof row under a stable conflict.
                raise ConflictError("OAuth flow already exists")
            # Reject capacity pressure instead of evicting an active exchange proof.
            if len(retained) >= MAX_SECRET_RECORDS:
                # Fail closed until bounded retention removes expired rows.
                raise ConflictError("OAuth flow capacity is reached")
            # Store nonce and PKCE only, never state, callback, browser, user, or session bindings.
            retained.append({"flow_id": record.flow_id, "nonce": record.nonce, "pkce_verifier": record.pkce_verifier, "expires_at": record.expires_at})
            # Return the complete separate proof document.
            return {"schema_version": SCHEMA_VERSION, "secrets": retained}

        # Persist proof material before publishing any discoverable state index.
        self.provider.update_document(FLOW_SECRET_DOCUMENT_KEY, store_secret, _default_secrets)

        # Define the metadata-document transaction.
        def store_metadata(document: object) -> dict:
            # Require recognizable existing metadata without normalizing corruption.
            rows = _collection(document, "flows", "OAuth flow storage requires operator recovery")
            # Retain unexpired metadata, including terminal replay tombstones.
            retained = [row for row in rows if _parse_timestamp(row.get("expires_at")) > now]
            # Compute the state verifier once inside the transaction.
            state_digest = self._digest("state", record.state)
            # Reject duplicate state under constant-time comparison.
            if any(hmac.compare_digest(str(row.get("state_digest", "")), state_digest) for row in retained):
                # Preserve every existing flow under a stable conflict.
                raise ConflictError("OAuth flow state already exists")
            # Reject capacity pressure instead of discarding replay tombstones.
            if len(retained) >= MAX_FLOW_RECORDS:
                # Fail closed until bounded expiry makes room.
                raise ConflictError("OAuth flow capacity is reached")
            # Persist only digests for state, callback, browser, user, and session bindings.
            retained.append({"flow_id": record.flow_id, "provider": record.provider, "state_digest": state_digest, "callback_digest": self._digest("callback", record.callback_uri), "owner_digest": self._digest("owner", record.owner_binding), "action": record.action, "return_to": record.return_to, "terms_version": record.terms_version, "locale": record.locale, "user_digest": self._digest("user", record.user_id) if record.user_id else None, "session_digest": self._digest("session", record.session_id) if record.session_id else None, "status": "pending", "created_at": record.created_at, "expires_at": record.expires_at, "attempts": 0, "exchange_digest": None, "claim_until": None, "consumed_at": None})
            # Return the complete metadata document for atomic commit.
            return {"schema_version": SCHEMA_VERSION, "flows": retained}

        # Publish the state index only after the separate proof row is durable.
        self.provider.update_document(FLOW_DOCUMENT_KEY, store_metadata, _default_flows)
        # Return the unchanged request-local flow.
        return record

    # Recoverably claim one exact flow for a provider exchange attempt.
    def claim(self, provider: str, state_value: str, callback_uri: str, owner_binding: str) -> OAuthFlowRecord:
        # Compute all callback binding verifiers before provider mutation.
        state_digest = self._digest("state", state_value)
        # Compute the canonical callback verifier.
        callback_digest = self._digest("callback", callback_uri)
        # Compute the browser-owner verifier.
        owner_digest = self._digest("owner", owner_binding)
        # Generate a request-local exchange claim and retain only its digest.
        exchange_token = secrets.token_urlsafe(32)
        # Compute the claim verifier before entering the transaction.
        exchange_digest = self._digest("exchange", exchange_token)
        # Read current UTC once for expiry and claim lease decisions.
        now = datetime.now(timezone.utc)
        # Capture selected metadata outside the provider mutator.
        selected = {"row": None}

        # Define one atomic metadata claim transaction.
        def claim_metadata(document: object) -> dict:
            # Require recognizable metadata to prove a prior start.
            rows = _collection(document, "flows", "OAuth flow storage requires operator recovery")
            # Search every retained row without exposing the returned state.
            for row in rows:
                # Continue until constant-time state lookup finds the exact metadata row.
                if not hmac.compare_digest(str(row.get("state_digest", "")), state_digest):
                    # Preserve unrelated flows unchanged.
                    continue
                # Validate bounded lifecycle fields before trusting the match.
                if row.get("provider") != provider or row.get("action") not in FLOW_ACTIONS or row.get("status") not in FLOW_STATUSES:
                    # Fail without revealing whether the state existed for another partition.
                    raise UnauthorizedError("OAuth flow is invalid or expired")
                # Require callback and browser bindings under constant-time comparison.
                if not hmac.compare_digest(str(row.get("callback_digest", "")), callback_digest) or not hmac.compare_digest(str(row.get("owner_digest", "")), owner_digest):
                    # Reject callback or browser drift without consuming the flow.
                    raise UnauthorizedError("OAuth flow is invalid or expired")
                # Reject expired or terminal flows identically.
                if _parse_timestamp(row.get("expires_at")) <= now or row.get("status") == "consumed":
                    # Preserve one fixed replay/expiry response.
                    raise UnauthorizedError("OAuth flow is invalid or expired")
                # Reject a still-live exchange claim so only one worker contacts the provider.
                if row.get("status") == "exchanging" and _parse_timestamp(row.get("claim_until")) > now:
                    # Preserve one fixed concurrent/replay response.
                    raise UnauthorizedError("OAuth flow is already being processed")
                # Lease this flow for one bounded exchange attempt.
                row["status"] = "exchanging"
                # Store only the exchange claim digest.
                row["exchange_digest"] = exchange_digest
                # Store the bounded recovery lease expiry.
                row["claim_until"] = _timestamp(now + timedelta(seconds=EXCHANGE_CLAIM_SECONDS))
                # Count attempts for bounded audit and test evidence.
                row["attempts"] = int(row.get("attempts", 0)) + 1
                # Copy only secret-free metadata for post-commit proof lookup.
                selected["row"] = dict(row)
                # Stamp the schema marker while preserving every row.
                document["schema_version"] = SCHEMA_VERSION
                # Return the complete claimed metadata document.
                return document
            # Reject unknown state with the same authentication failure.
            raise UnauthorizedError("OAuth flow is invalid or expired")

        # Commit the exchange lease atomically across JSON or MySQL processes.
        self.provider.update_document(FLOW_DOCUMENT_KEY, claim_metadata, _default_flows)
        # Read the physically separate proof document after the claim commits.
        proof_document = self.provider.read_document(FLOW_SECRET_DOCUMENT_KEY, _default_secrets)
        # Require recognizable proof storage without rewriting it.
        proof_rows = _collection(proof_document, "secrets", "OAuth proof storage requires operator recovery")
        # Select the exact internal proof row without state or callback lookup.
        proof = next((row for row in proof_rows if hmac.compare_digest(str(row.get("flow_id", "")), str(selected["row"].get("flow_id", "")))), None)
        # Release the recoverable claim when proof storage is incomplete or expired.
        if proof is None or _parse_timestamp(proof.get("expires_at")) <= now:
            # Return the metadata row to pending so a repaired store can be retried.
            self._transition(selected["row"], exchange_token, "pending")
            # Fail closed without consuming the state.
            raise UnauthorizedError("OAuth flow proof is unavailable")
        # Return a request-local record combining callback inputs with the separate proofs.
        return OAuthFlowRecord(flow_id=str(selected["row"]["flow_id"]), provider=provider, state=state_value, nonce=str(proof.get("nonce", "")), pkce_verifier=str(proof.get("pkce_verifier", "")), callback_uri=callback_uri, owner_binding=owner_binding, action=str(selected["row"]["action"]), return_to=str(selected["row"]["return_to"]), terms_version=selected["row"].get("terms_version"), locale=selected["row"].get("locale"), user_id=selected["row"].get("user_digest"), session_id=selected["row"].get("session_digest"), status="exchanging", created_at=str(selected["row"]["created_at"]), expires_at=str(selected["row"]["expires_at"]), exchange_token=exchange_token)

    # Transition an exact claimed metadata row to pending or consumed.
    def _transition(self, record_or_row: object, exchange_token: str, target: str) -> None:
        # Accept request-local records and internal metadata copies without exposing either.
        row = record_or_row.__dict__ if isinstance(record_or_row, OAuthFlowRecord) else record_or_row
        # Require the two reviewed transition targets.
        if target not in {"pending", "consumed"} or not isinstance(row, dict):
            # Reject arbitrary lifecycle mutation before provider access.
            raise ValidationError("OAuth flow transition is invalid")
        # Compute the claim verifier from the request-local token.
        exchange_digest = self._digest("exchange", exchange_token)

        # Define one exact claim-owned transition.
        def mutate(document: object) -> dict:
            # Require recognizable metadata without normalizing corruption.
            rows = _collection(document, "flows", "OAuth flow storage requires operator recovery")
            # Select only the exact internal flow id.
            selected = next((item for item in rows if hmac.compare_digest(str(item.get("flow_id", "")), str(row.get("flow_id", "")))), None)
            # Require the same active exchange claim before any transition.
            if selected is None or selected.get("status") != "exchanging" or not hmac.compare_digest(str(selected.get("exchange_digest", "")), exchange_digest):
                # Reject stale workers and concurrent callbacks.
                raise UnauthorizedError("OAuth flow claim is invalid")
            # Publish the reviewed target state.
            selected["status"] = target
            # Clear the temporary exchange lease and verifier.
            selected["exchange_digest"] = None
            # Clear the temporary claim expiry.
            selected["claim_until"] = None
            # Record a terminal timestamp only for consumed flows.
            selected["consumed_at"] = utc_now() if target == "consumed" else None
            # Preserve the schema marker on commit.
            document["schema_version"] = SCHEMA_VERSION
            # Return the complete metadata document.
            return document

        # Commit the exact claim-owned transition.
        self.provider.update_document(FLOW_DOCUMENT_KEY, mutate, _default_flows)

    # Release a transient/ambiguous provider exchange for bounded same-flow retry.
    def release(self, record: OAuthFlowRecord) -> None:
        # Require the request-local claim token before returning to pending.
        if not isinstance(record.exchange_token, str):
            # Reject unclaimed records without provider access.
            raise ValidationError("OAuth flow claim is invalid")
        # Return the exact flow to pending without deleting nonce or PKCE proof.
        self._transition(record, record.exchange_token, "pending")

    # Complete one successful, cancelled, or terminally rejected flow.
    def complete(self, record: OAuthFlowRecord) -> None:
        # Require the request-local claim token before terminal transition.
        if not isinstance(record.exchange_token, str):
            # Reject unclaimed records without provider access.
            raise ValidationError("OAuth flow claim is invalid")
        # Mark metadata consumed before removing reusable proof material.
        self._transition(record, record.exchange_token, "consumed")

        # Define bounded proof removal after the replay tombstone is durable.
        def remove_proof(document: object) -> dict:
            # Require recognizable proof storage without destructive normalization.
            rows = _collection(document, "secrets", "OAuth proof storage requires operator recovery")
            # Remove only the exact completed flow proof row.
            retained = [row for row in rows if not hmac.compare_digest(str(row.get("flow_id", "")), record.flow_id)]
            # Return the complete separate proof document.
            return {"schema_version": SCHEMA_VERSION, "secrets": retained}

        # Remove nonce and PKCE only after terminal replay protection is committed.
        self.provider.update_document(FLOW_SECRET_DOCUMENT_KEY, remove_proof, _default_secrets)

    # Verify the current authenticated user/session against digests retained for a link flow.
    def link_owner_matches(self, record: OAuthFlowRecord, user_id: str, session_id: str) -> bool:
        # Reject sign-in records or missing durable owner verifiers.
        if record.action != "link" or not isinstance(record.user_id, str) or not isinstance(record.session_id, str):
            # Return false without exposing lifecycle or identifier values.
            return False
        # Compare both current identifiers under their domain-separated HMACs.
        return hmac.compare_digest(record.user_id, self._digest("user", user_id)) and hmac.compare_digest(record.session_id, self._digest("session", session_id))


# Apply a durable cross-process rate limiter keyed only by HMAC verifiers.
class OAuthRateLimiter:
    # Bind limiter policy to one provider and server-owned digest key.
    def __init__(self, provider: StorageProvider, digest_key: str, clock=None, limit: int = 8, window_seconds: int = 300):
        # Reuse the flow repository's strict digest-key validation.
        self._digests = OAuthFlowRepository(provider, digest_key)
        # Retain the provider for one atomic limiter transaction.
        self.provider = provider
        # Use an injectable UTC clock for deterministic tests.
        self.clock = (lambda: datetime.now(timezone.utc)) if clock is None else clock
        # Store the positive bounded allowance.
        self.limit = int(limit)
        # Store the positive bounded window.
        self.window_seconds = int(window_seconds)
        # Reject unsafe limiter policy before persistence.
        if self.limit < 1 or self.limit > 100 or self.window_seconds < 1 or self.window_seconds > 3600:
            # Preserve a value-free policy failure.
            raise ValidationError("OAuth rate policy is invalid")

    # Consume one allowance without retaining browser, provider, or action values.
    def check(self, owner_binding: str, provider: str, action: str) -> None:
        # Compute one HMAC bucket identity from already bounded dimensions.
        bucket_digest = self._digests._digest("rate", f"{owner_binding}\0{provider}\0{action}")
        # Read current UTC once for pruning and append.
        now = self.clock()
        # Require an aware datetime from injected or production clocks.
        if not isinstance(now, datetime) or now.tzinfo is None:
            # Reject invalid clocks before durable mutation.
            raise ValidationError("OAuth rate clock is invalid")
        # Compute the inclusive retention boundary.
        boundary = now - timedelta(seconds=self.window_seconds)

        # Define one complete rate decision under the provider transaction.
        def mutate(document: object) -> dict:
            # Require recognizable rate storage without normalizing corruption.
            rows = _collection(document, "buckets", "OAuth rate storage requires operator recovery")
            # Retain only valid nonempty buckets with at least one in-window timestamp.
            retained = []
            # Track the selected bucket under the same transaction.
            selected = None
            # Inspect every strict bucket row.
            for row in rows:
                # Require a digest and list of timestamps before the row can affect limits.
                if not isinstance(row.get("digest"), str) or not isinstance(row.get("events"), list):
                    # Preserve malformed limiter evidence for operator recovery.
                    raise RuntimeError("OAuth rate storage requires operator recovery")
                # Keep only parseable in-window event timestamps.
                events = [value for value in row["events"] if _parse_timestamp(value) >= boundary]
                # Skip empty expired buckets during bounded retention.
                if not events:
                    # Continue without retaining an expired row.
                    continue
                # Build the strict retained row.
                candidate = {"digest": row["digest"], "events": events}
                # Select the exact bucket under constant-time comparison.
                if hmac.compare_digest(row["digest"], bucket_digest):
                    # Retain the selected bucket for limit evaluation.
                    selected = candidate
                # Preserve the strict in-window bucket.
                retained.append(candidate)
            # Create a fresh selected bucket when none remains.
            if selected is None:
                # Reject distinct-key capacity instead of evicting a live abuse signal.
                if len(retained) >= MAX_RATE_BUCKETS:
                    # Fail closed under sustained hostile key growth.
                    raise RateLimitError()
                # Create the HMAC-only bucket.
                selected = {"digest": bucket_digest, "events": []}
                # Append the selected bucket to retained state.
                retained.append(selected)
            # Reject the request when the in-window allowance is exhausted.
            if len(selected["events"]) >= self.limit:
                # Return the stable application rate-limit envelope.
                raise RateLimitError()
            # Record the accepted attempt at the current canonical instant.
            selected["events"].append(_timestamp(now))
            # Return the complete bounded limiter document.
            return {"schema_version": SCHEMA_VERSION, "buckets": retained}

        # Commit prune, check, and append as one JSON/MySQL transaction.
        self.provider.update_document(RATE_DOCUMENT_KEY, mutate, _default_rates)


# Provide atomic one-to-one external identity links on shared provider documents.
class PersistentIdentityLinkRepository:
    # Bind one repository instance to the configured shared storage provider.
    def __init__(self, provider: StorageProvider):
        # Store the provider interface for JSON/MySQL-neutral operations.
        self.provider = provider

    # Convert one persisted row into the strict immutable public link model.
    @staticmethod
    def _link_from_row(row: object) -> ExternalIdentityLink:
        # Reject anything outside the exact persisted mapping shape.
        if not isinstance(row, dict):
            # Preserve malformed durable state for operator recovery.
            raise RuntimeError("OAuth identity-link storage requires operator recovery")
        # Construct only allowlisted identity-link fields.
        link = ExternalIdentityLink(provider=row.get("provider"), subject=row.get("subject"), user_id=row.get("user_id"), created_at=row.get("created_at"), updated_at=row.get("updated_at"))
        # Collect bounded key and audit fields.
        values = (link.provider, link.subject, link.user_id, link.created_at, link.updated_at)
        # Reject absent, overlong, or control-bearing fields.
        if any(not isinstance(value, str) or not value or len(value) > 4096 or any(not character.isprintable() for character in value) for value in values):
            # Preserve the malformed row without rewriting the document.
            raise RuntimeError("OAuth identity-link storage requires operator recovery")
        # Validate both audit timestamps before the link can authenticate.
        _parse_timestamp(link.created_at)
        # Validate the update timestamp separately for explicit traceability.
        _parse_timestamp(link.updated_at)
        # Return the strict immutable link.
        return link

    # Read a strict link collection without mutating provider state.
    def _links(self) -> list[ExternalIdentityLink]:
        # Load the provider document using a fresh default only when absent.
        document = self.provider.read_document(LINK_DOCUMENT_KEY, _default_links)
        # Require recognizable state so malformed evidence never authenticates.
        rows = _collection(document, "links", "OAuth identity-link storage requires operator recovery")
        # Convert every row strictly; one malformed row fails the complete read.
        return [self._link_from_row(row) for row in rows]

    # Find one exact provider-owned subject binding.
    def find_by_subject(self, provider: str, subject: str) -> ExternalIdentityLink | None:
        # Search strict rows without consulting email or provider metadata.
        return next((link for link in self._links() if link.provider == provider and hmac.compare_digest(link.subject, subject)), None)

    # Find one provider link owned by a canonical Casino user.
    def find_by_user(self, provider: str, user_id: str) -> ExternalIdentityLink | None:
        # Search strict rows by provider and authenticated canonical user id.
        return next((link for link in self._links() if link.provider == provider and hmac.compare_digest(link.user_id, user_id)), None)

    # Atomically create one link or return the exact idempotent binding.
    def save(self, link: ExternalIdentityLink) -> tuple[ExternalIdentityLink, bool]:
        # Require the strict link model before provider mutation.
        if not isinstance(link, ExternalIdentityLink):
            # Reject arbitrary persistence objects without serialization.
            raise ValidationError("Identity link is invalid")
        # Capture the committed result outside the provider mutator.
        result = {"link": None, "created": False}

        # Define the complete compound-uniqueness transaction.
        def mutate(document: object) -> dict:
            # Require recognizable state and every strict row.
            rows = _collection(document, "links", "OAuth identity-link storage requires operator recovery")
            # Convert every row before any mutation can occur.
            links = [self._link_from_row(row) for row in rows]
            # Find an existing provider-subject binding.
            subject_link = next((stored for stored in links if stored.provider == link.provider and hmac.compare_digest(stored.subject, link.subject)), None)
            # Preserve an exact existing binding as idempotent.
            if subject_link is not None and hmac.compare_digest(subject_link.user_id, link.user_id):
                # Publish the accepted existing row without mutation.
                result.update({"link": subject_link, "created": False})
                # Return the original valid document.
                return document
            # Reject an existing subject owned by another user.
            if subject_link is not None:
                # Fail under the transaction that observed the conflict.
                raise ConflictError("External identity is already linked to another user")
            # Find an existing provider-user binding under the same lock.
            user_link = next((stored for stored in links if stored.provider == link.provider and hmac.compare_digest(stored.user_id, link.user_id)), None)
            # Reject a second subject for the same provider and user.
            if user_link is not None:
                # Preserve one-to-one ownership without revealing either subject.
                raise ConflictError("User already has a different identity for this provider")
            # Reject capacity instead of evicting authentication authority.
            if len(rows) >= MAX_LINK_RECORDS:
                # Fail closed until an explicit lifecycle removes a link.
                raise ConflictError("Identity link capacity is reached")
            # Append only the strict allowlisted record.
            rows.append(link.to_record())
            # Publish the committed binding and creation flag.
            result.update({"link": link, "created": True})
            # Preserve the schema marker on commit.
            document["schema_version"] = SCHEMA_VERSION
            # Return the complete link document.
            return document

        # Commit both compound uniqueness checks and append atomically.
        self.provider.update_document(LINK_DOCUMENT_KEY, mutate, _default_links)
        # Return the exact committed or idempotent link and decision.
        return result["link"], result["created"]

    # Atomically unlink one provider from the authenticated owner.
    def delete_for_user(self, provider: str, user_id: str) -> bool:
        # Capture the deletion decision outside the provider mutator.
        deleted = {"value": False}

        # Define the exact provider-user deletion transaction.
        def mutate(document: object) -> dict:
            # Require recognizable state and strict rows before deletion.
            rows = _collection(document, "links", "OAuth identity-link storage requires operator recovery")
            # Validate every row before selecting one for removal.
            links = [self._link_from_row(row) for row in rows]
            # Build the retained strict rows.
            retained = []
            # Inspect each row with its validated model.
            for row, stored in zip(rows, links):
                # Remove only the exact provider-user binding.
                if stored.provider == provider and hmac.compare_digest(stored.user_id, user_id):
                    # Record the exact deletion without retaining its subject.
                    deleted["value"] = True
                    # Continue without preserving the selected row.
                    continue
                # Preserve every unrelated strict row.
                retained.append(row)
            # Return the complete retained link document.
            return {"schema_version": SCHEMA_VERSION, "links": retained}

        # Commit lookup and deletion atomically across providers.
        self.provider.update_document(LINK_DOCUMENT_KEY, mutate, _default_links)
        # Return only whether the authenticated binding existed.
        return deleted["value"]

    # Return provider-level link status without subjects or canonical identifiers.
    def provider_status_for_user(self, user_id: str, providers: tuple[str, ...]) -> list[dict]:
        # Read strict links once so the projection stays consistent.
        links = self._links()
        # Project stable provider and boolean-only ownership fields.
        return [{"provider": provider, "linked": any(link.provider == provider and hmac.compare_digest(link.user_id, user_id) for link in links)} for provider in providers]
