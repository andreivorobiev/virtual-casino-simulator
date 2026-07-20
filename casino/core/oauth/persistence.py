"""Transactional OAuth flow and identity-link persistence for issue #326.

Requirements: OAUTH-003, OAUTH-004, STORAGE-001, STORAGE-002, and SESSION-007.
"""

# Import constant-time comparison so opaque state and browser bindings never use early-exit equality.
import hmac
# Import immutable record helpers while keeping sensitive flow material out of representations.
from dataclasses import dataclass, field
# Import UTC timestamp parsing for strict flow expiration decisions.
from datetime import datetime, timezone

# Import the application schema marker used by every provider-backed JSON document.
from casino.config import SCHEMA_VERSION
# Import canonical timestamps for durable audit fields.
from casino.core.clock import utc_now
# Import the existing allowlisted identity-link record and repository contract.
from casino.core.oauth.identity_links import ExternalIdentityLink
# Import the shared provider interface so JSON and MySQL use the same repository code.
from casino.core.storage import StorageProvider
# Import stable public errors without reflecting provider or identity values.
from casino.errors import ConflictError, UnauthorizedError, ValidationError

# Name the provider document that contains bounded one-time authorization flows.
FLOW_DOCUMENT_KEY = "auth/oauth_flows"
# Name the provider document that contains durable provider-subject links.
LINK_DOCUMENT_KEY = "auth/oauth_identity_links"
# Bound retained pending and consumed flows for the single-node private preview.
MAX_FLOW_RECORDS = 2_000
# Bound durable links well beyond the current invite population without permitting unbounded corruption.
MAX_LINK_RECORDS = 10_000
# Accept only the two explicitly approved OAuth actions.
FLOW_ACTIONS = frozenset({"signin", "link"})


# Parse one canonical UTC timestamp while treating malformed persistence as invalid.
def _parse_timestamp(value: str) -> datetime:
    # Require text so arbitrary persisted objects are never stringified into diagnostics.
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
    # Require an offset-aware timestamp before comparing expiration.
    if parsed.tzinfo is None:
        # Reject ambiguous local time values from damaged persistence.
        raise ValidationError("OAuth persistence timestamp is invalid")
    # Normalize valid offsets to UTC for deterministic comparisons.
    return parsed.astimezone(timezone.utc)


# Represent one expiring authorization flow while suppressing every secret binding from repr.
@dataclass(frozen=True)
class OAuthFlowRecord:  # Keep a complete provider, browser, callback, and action binding immutable.
    # Store an internal random record identifier without exposing it through representations.
    flow_id: str = field(repr=False)
    # Store the exact supported provider partition.
    provider: str
    # Store the anti-forgery state used only for constant-time callback matching.
    state: str = field(repr=False)
    # Store the OIDC nonce retained until the one allowed exchange.
    nonce: str = field(repr=False)
    # Store the PKCE verifier retained until the one allowed exchange.
    pkce_verifier: str = field(repr=False)
    # Store the exact callback URI used at authorization and exchange.
    callback_uri: str = field(repr=False)
    # Store a one-way browser/session-owner binding without raw cookie material.
    owner_binding: str = field(repr=False)
    # Store signin or link as the only allowed intent.
    action: str
    # Store a same-origin relative redirect selected before provider navigation.
    return_to: str
    # Store the canonical user only for authenticated linking flows.
    user_id: str | None = field(default=None, repr=False)
    # Store the authenticated session only for linking-flow ownership checks.
    session_id: str | None = field(default=None, repr=False)
    # Store pending or consumed for durable replay rejection.
    status: str = "pending"
    # Store the creation timestamp for expiry and audit decisions.
    created_at: str = ""
    # Store the exclusive expiry timestamp for bounded retention.
    expires_at: str = ""
    # Store the first consumption timestamp without changing creation provenance.
    consumed_at: str | None = None

    # Convert the flow to its strict persistence allowlist.
    def to_record(self) -> dict:
        # Persist only fields needed for one exchange; never persist codes, tokens, claims, or email.
        return {"flow_id": self.flow_id, "provider": self.provider, "state": self.state, "nonce": self.nonce, "pkce_verifier": self.pkce_verifier, "callback_uri": self.callback_uri, "owner_binding": self.owner_binding, "action": self.action, "return_to": self.return_to, "user_id": self.user_id, "session_id": self.session_id, "status": self.status, "created_at": self.created_at, "expires_at": self.expires_at, "consumed_at": self.consumed_at}

    # Reconstruct one strict flow record without accepting extra persistence behavior.
    @classmethod
    def from_record(cls, record: object):
        # Require an ordinary mapping before allowlisted field extraction.
        if not isinstance(record, dict):
            # Reject damaged provider storage without serializing it.
            raise ValidationError("OAuth flow record is invalid")
        # Construct from exact known fields so unknown data never reaches service logic.
        return cls(flow_id=record.get("flow_id"), provider=record.get("provider"), state=record.get("state"), nonce=record.get("nonce"), pkce_verifier=record.get("pkce_verifier"), callback_uri=record.get("callback_uri"), owner_binding=record.get("owner_binding"), action=record.get("action"), return_to=record.get("return_to"), user_id=record.get("user_id"), session_id=record.get("session_id"), status=record.get("status"), created_at=record.get("created_at"), expires_at=record.get("expires_at"), consumed_at=record.get("consumed_at"))


# Return a fresh flow document for JSON and MySQL providers.
def _default_flows() -> dict:
    # Preserve the common schema marker and one bounded flow collection.
    return {"schema_version": SCHEMA_VERSION, "flows": []}


# Return a fresh identity-link document for JSON and MySQL providers.
def _default_links() -> dict:
    # Preserve the common schema marker and one durable link collection.
    return {"schema_version": SCHEMA_VERSION, "links": []}


# Validate one flow record before it can enter or leave persistence.
def _validate_flow(record: OAuthFlowRecord) -> None:
    # Require the immutable record type so callers cannot smuggle extra fields.
    if not isinstance(record, OAuthFlowRecord):
        # Reject arbitrary flow objects before storage access.
        raise ValidationError("OAuth flow record is invalid")
    # Require bounded printable identifiers and secrets without exposing their values.
    scalar_values = (record.flow_id, record.provider, record.state, record.nonce, record.pkce_verifier, record.callback_uri, record.owner_binding, record.return_to, record.created_at, record.expires_at)
    # Reject missing, overlong, or control-bearing persisted values.
    if any(not isinstance(value, str) or not value or len(value) > 4096 or any(not character.isprintable() for character in value) for value in scalar_values):
        # Return one stable validation class for every malformed field.
        raise ValidationError("OAuth flow record is invalid")
    # Require a known action and one of the two lifecycle states.
    if record.action not in FLOW_ACTIONS or record.status not in {"pending", "consumed"}:
        # Reject action or status drift without serializing it.
        raise ValidationError("OAuth flow record is invalid")
    # Parse both timestamps before the record can affect expiry decisions.
    _parse_timestamp(record.created_at)
    # Require an expiry strictly after creation.
    if _parse_timestamp(record.expires_at) <= _parse_timestamp(record.created_at):
        # Reject unusable retention bounds.
        raise ValidationError("OAuth flow record is invalid")
    # Require authenticated owner identifiers only for link actions.
    if record.action == "link" and (not isinstance(record.user_id, str) or not record.user_id or not isinstance(record.session_id, str) or not record.session_id):
        # Prevent a provider callback from selecting a linking target.
        raise ValidationError("OAuth linking flow owner is invalid")
    # Require signin flows to carry no canonical target before identity resolution.
    if record.action == "signin" and (record.user_id is not None or record.session_id is not None):
        # Reject preselected signin users so email or caller input cannot become a target.
        raise ValidationError("OAuth sign-in flow owner is invalid")


# Persist and atomically consume bounded OAuth authorization flows.
class OAuthFlowRepository:
    # Bind one repository instance to the configured shared storage provider.
    def __init__(self, provider: StorageProvider):
        # Store the provider interface without branching on JSON or MySQL.
        self.provider = provider

    # Create one pending flow while atomically rejecting state collisions.
    def create(self, record: OAuthFlowRecord) -> OAuthFlowRecord:
        # Validate every binding before opening the provider transaction.
        _validate_flow(record)
        # Require callers to create only pending, unconsumed records.
        if record.status != "pending" or record.consumed_at is not None:
            # Reject lifecycle drift before persistence.
            raise ValidationError("New OAuth flow must be pending")
        # Hold the exact stored result outside the provider-owned mutator return.
        stored = {"record": None}

        # Define one complete flow-document transaction.
        def mutate(document: object) -> dict:
            # Normalize a missing document while rejecting malformed collection types.
            state = document if isinstance(document, dict) else _default_flows()
            # Read the stored collection only when it is a list.
            rows = state.get("flows") if isinstance(state.get("flows"), list) else []
            # Read current time once for deterministic expiry pruning.
            now = datetime.now(timezone.utc)
            # Retain unexpired rows, including consumed rows needed for replay rejection.
            retained = [row for row in rows if isinstance(row, dict) and _parse_timestamp(row.get("expires_at")) > now]
            # Reject the astronomically unlikely duplicate state instead of replacing an existing flow.
            if any(isinstance(row.get("state"), str) and hmac.compare_digest(row["state"], record.state) for row in retained):
                # Preserve every existing flow under a stable conflict.
                raise ConflictError("OAuth flow state already exists")
            # Bound pending and consumed retention before appending the new record.
            retained = retained[-(MAX_FLOW_RECORDS - 1):]
            # Append the strict allowlisted persistence record.
            retained.append(record.to_record())
            # Publish the exact created record to the caller.
            stored["record"] = record
            # Return the complete normalized document for atomic commit.
            return {"schema_version": SCHEMA_VERSION, "flows": retained}

        # Commit the state-collision check and append as one provider transaction.
        self.provider.update_document(FLOW_DOCUMENT_KEY, mutate, _default_flows)
        # Return the immutable created record after provider commit.
        return stored["record"]

    # Atomically consume one exact callback flow before any provider exchange begins.
    def consume(self, provider: str, state_value: str, callback_uri: str, owner_binding: str) -> OAuthFlowRecord:
        # Reject missing or overlong callback inputs before provider storage access.
        if any(not isinstance(value, str) or not value or len(value) > 4096 for value in (provider, state_value, callback_uri, owner_binding)):
            # Use one authentication failure without naming the malformed field value.
            raise UnauthorizedError("OAuth flow is invalid or expired")
        # Hold the claimed immutable record outside the mutator closure.
        claimed = {"record": None}

        # Define one read-validate-consume transaction.
        def mutate(document: object) -> dict:
            # Require a recognizable flow document to prove a prior start operation.
            if not isinstance(document, dict) or not isinstance(document.get("flows"), list):
                # Reject absent or damaged persistence identically.
                raise UnauthorizedError("OAuth flow is invalid or expired")
            # Read current time once for expiry and consumption timestamps.
            now = datetime.now(timezone.utc)
            # Search every retained record without exposing any state value.
            for index, row in enumerate(document["flows"]):
                # Skip malformed rows so they cannot authenticate a callback.
                if not isinstance(row, dict) or not isinstance(row.get("state"), str):
                    # Continue looking for an exact valid record.
                    continue
                # Continue until constant-time state comparison finds the selected flow.
                if not hmac.compare_digest(row["state"], state_value):
                    # Preserve unrelated provider flows unchanged.
                    continue
                # Reconstruct and validate the exact selected flow.
                record = OAuthFlowRecord.from_record(row)
                # Validate persisted bindings before trusting lifecycle fields.
                _validate_flow(record)
                # Reject provider partition drift without revealing whether the state existed.
                if record.provider != provider:
                    # Preserve the flow for its intended provider callback.
                    raise UnauthorizedError("OAuth flow is invalid or expired")
                # Reject every replay once the first callback has claimed the flow.
                if record.status != "pending" or record.consumed_at is not None:
                    # Return the same fixed authentication failure for a replay.
                    raise UnauthorizedError("OAuth flow is invalid or expired")
                # Reject an expired record before code exchange or user lookup.
                if _parse_timestamp(record.expires_at) <= now:
                    # Prevent a stale browser callback from authenticating.
                    raise UnauthorizedError("OAuth flow is invalid or expired")
                # Bind the exchange to the exact callback URI used at start.
                if not hmac.compare_digest(record.callback_uri, callback_uri):
                    # Reject callback-origin drift without echoing either URI.
                    raise UnauthorizedError("OAuth flow is invalid or expired")
                # Bind the exchange to the initiating browser or session owner.
                if not hmac.compare_digest(record.owner_binding, owner_binding):
                    # Reject browser theft without disclosing either binding.
                    raise UnauthorizedError("OAuth flow is invalid or expired")
                # Mark the record consumed before any external provider request begins.
                consumed = OAuthFlowRecord(**{**record.__dict__, "status": "consumed", "consumed_at": utc_now()})
                # Replace only the selected row inside the atomic provider transaction.
                document["flows"][index] = consumed.to_record()
                # Publish the claimed secrets only to the request-local service caller.
                claimed["record"] = consumed
                # Stamp the schema marker while preserving every other flow.
                document["schema_version"] = SCHEMA_VERSION
                # Return the complete mutated document for commit.
                return document
            # Reject unknown state with the same failure used for expiry and replay.
            raise UnauthorizedError("OAuth flow is invalid or expired")

        # Commit the one-time status transition before returning any flow secret.
        self.provider.update_document(FLOW_DOCUMENT_KEY, mutate, _default_flows)
        # Return the exact consumed record to the current callback only.
        return claimed["record"]


# Provide atomic one-to-one external identity links on shared provider documents.
class PersistentIdentityLinkRepository:
    # Bind one repository instance to the configured shared storage provider.
    def __init__(self, provider: StorageProvider):
        # Store the provider interface for JSON/MySQL-neutral operations.
        self.provider = provider

    # Convert one persisted row into the strict immutable public link model.
    @staticmethod
    def _link_from_row(row: object) -> ExternalIdentityLink | None:
        # Reject anything outside the exact persisted mapping shape.
        if not isinstance(row, dict):
            # Return no trusted link for malformed persistence.
            return None
        # Read only allowlisted fields into the immutable link record.
        try:
            # Construct without serializing subject or canonical user values.
            link = ExternalIdentityLink(provider=row.get("provider"), subject=row.get("subject"), user_id=row.get("user_id"), created_at=row.get("created_at"), updated_at=row.get("updated_at"))
        # Treat unexpected dataclass construction failures as a malformed row.
        except (TypeError, ValueError):
            # Return no trusted link rather than exposing persistence contents.
            return None
        # Require bounded printable key fields and valid timestamps before use.
        values = (link.provider, link.subject, link.user_id, link.created_at, link.updated_at)
        # Reject absent, overlong, or control-bearing fields.
        if any(not isinstance(value, str) or not value or len(value) > 4096 or any(not character.isprintable() for character in value) for value in values):
            # Return no trusted identity binding for a damaged row.
            return None
        # Validate audit timestamps even though identity resolution does not compare them.
        _parse_timestamp(link.created_at)
        # Validate the latest update timestamp as part of the durable record.
        _parse_timestamp(link.updated_at)
        # Return the strict allowlisted identity link.
        return link

    # Read a stable link collection without mutating provider state.
    def _links(self) -> list[ExternalIdentityLink]:
        # Load the provider document using a fresh default for absent storage.
        document = self.provider.read_document(LINK_DOCUMENT_KEY, _default_links)
        # Reject malformed top-level persistence by returning no authenticating links.
        if not isinstance(document, dict) or not isinstance(document.get("links"), list):
            # Fail closed without rewriting potentially recoverable evidence.
            return []
        # Convert only valid rows into immutable identity links.
        return [link for row in document["links"] if (link := self._link_from_row(row)) is not None]

    # Find one exact provider-owned subject binding.
    def find_by_subject(self, provider: str, subject: str) -> ExternalIdentityLink | None:
        # Search strict rows without email or other provider metadata.
        return next((link for link in self._links() if link.provider == provider and hmac.compare_digest(link.subject, subject)), None)

    # Find the single provider link owned by one canonical Casino user.
    def find_by_user(self, provider: str, user_id: str) -> ExternalIdentityLink | None:
        # Search strict rows by provider and authenticated canonical user id.
        return next((link for link in self._links() if link.provider == provider and hmac.compare_digest(link.user_id, user_id)), None)

    # Atomically create one link or return the exact idempotent existing binding.
    def save(self, link: ExternalIdentityLink) -> tuple[ExternalIdentityLink, bool]:
        # Require the strict link model before provider mutation.
        if not isinstance(link, ExternalIdentityLink):
            # Reject arbitrary persistence objects without serialization.
            raise ValidationError("Identity link is invalid")
        # Hold the committed result outside the mutator closure.
        result = {"link": None, "created": False}

        # Define the compound uniqueness transaction.
        def mutate(document: object) -> dict:
            # Normalize only a missing document; malformed rows remain non-authenticating.
            state = document if isinstance(document, dict) else _default_links()
            # Read the collection only when its persisted type is valid.
            rows = state.get("links") if isinstance(state.get("links"), list) else []
            # Convert valid rows for exact compound-key comparisons.
            links = [stored for row in rows if (stored := self._link_from_row(row)) is not None]
            # Find an existing provider-subject binding under the transaction lock.
            subject_link = next((stored for stored in links if stored.provider == link.provider and hmac.compare_digest(stored.subject, link.subject)), None)
            # Preserve an exact existing binding as an idempotent save.
            if subject_link is not None and hmac.compare_digest(subject_link.user_id, link.user_id):
                # Return the accepted existing row without another append.
                result.update({"link": subject_link, "created": False})
                # Preserve the document byte-for-byte aside from provider serialization.
                return state
            # Reject attempts to assign an existing subject to another user.
            if subject_link is not None:
                # Fail under the same transaction that observed the conflict.
                raise ConflictError("External identity is already linked to another user")
            # Find an existing provider-user binding under the same lock.
            user_link = next((stored for stored in links if stored.provider == link.provider and hmac.compare_digest(stored.user_id, link.user_id)), None)
            # Reject a second subject for the same provider and canonical user.
            if user_link is not None:
                # Preserve one-to-one ownership without revealing either subject.
                raise ConflictError("User already has a different identity for this provider")
            # Reject unbounded growth before appending the new invite-user binding.
            if len(links) >= MAX_LINK_RECORDS:
                # Fail closed rather than evicting an authentication identity.
                raise ConflictError("Identity link capacity is reached")
            # Append the strict allowlisted record without provider claims or tokens.
            rows.append(link.to_record())
            # Publish the committed binding and creation flag to the caller.
            result.update({"link": link, "created": True})
            # Return a normalized complete document for atomic provider commit.
            return {"schema_version": SCHEMA_VERSION, "links": rows}

        # Commit both compound uniqueness checks and the append atomically.
        self.provider.update_document(LINK_DOCUMENT_KEY, mutate, _default_links)
        # Return the exact committed or idempotent link and its creation decision.
        return result["link"], result["created"]

    # Atomically unlink one provider only from the authenticated canonical owner.
    def delete_for_user(self, provider: str, user_id: str) -> bool:
        # Hold a deletion decision outside the provider mutator closure.
        deleted = {"value": False}

        # Define the exact provider-user deletion transaction.
        def mutate(document: object) -> dict:
            # Treat absent storage as an idempotent no-op.
            state = document if isinstance(document, dict) else _default_links()
            # Read only a list-shaped link collection.
            rows = state.get("links") if isinstance(state.get("links"), list) else []
            # Preserve rows unless they are the exact strict authenticated binding.
            retained = []
            # Inspect every persisted row under the provider transaction lock.
            for row in rows:
                # Convert valid identity rows without trusting malformed records.
                stored = self._link_from_row(row)
                # Remove only the requested provider and canonical user binding.
                if stored is not None and stored.provider == provider and hmac.compare_digest(stored.user_id, user_id):
                    # Record the exact deletion without retaining its subject.
                    deleted["value"] = True
                    # Continue without appending the selected row.
                    continue
                # Preserve every unrelated or malformed row for recovery review.
                retained.append(row)
            # Return the complete link document after the bounded deletion.
            return {"schema_version": SCHEMA_VERSION, "links": retained}

        # Commit lookup and deletion atomically across JSON or MySQL providers.
        self.provider.update_document(LINK_DOCUMENT_KEY, mutate, _default_links)
        # Return only whether the authenticated binding existed.
        return deleted["value"]

    # Return provider-level link status without subjects or canonical identifiers.
    def provider_status_for_user(self, user_id: str, providers: tuple[str, ...]) -> list[dict]:
        # Read strict links once so status projection stays consistent.
        links = self._links()
        # Return one boolean-only row per configured external provider.
        return [{"provider": provider, "linked": any(link.provider == provider and hmac.compare_digest(link.user_id, user_id) for link in links)} for provider in providers]
