# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Recoverable provider-subject enrollment into canonical Casino accounts. (OAUTH-013)

The provider subject is the only external identity key. Provider email and display name are optional
presentation metadata and never select, merge, or authenticate a Casino account. A provider-backed
pending record allocates deterministic canonical identifiers once; identity and wallet provisioning
remain inactive until the exact compound identity link is durable, then one user-document mutation
publishes the account as active. Retries resume the same identifiers and cannot duplicate wallets.
"""

# Import keyed hashing for a non-reversible pending-enrollment subject index.
import hashlib
# Import constant-time keyed hashing without retaining the server digest key.
import hmac
# Import immutable result helpers while suppressing canonical identifiers from representations.
from dataclasses import dataclass, field

# Import canonical user and wallet provisioning boundaries.
from casino.core import auth
# Import canonical timestamps for pending and activation audit fields.
from casino.core.clock import utc_now
# Import server-owned opaque identifiers for deterministic recoverable resources.
from casino.core.ids import new_id
# Import strict external identity and link models.
from casino.core.oauth.identity_links import ExternalIdentityLink
# Import the allowlisted provider-neutral identity projection.
from casino.core.oauth.models import VerifiedIdentity
# Import exact supported provider metadata for validation.
from casino.core.oauth.providers import get_provider_spec
# Import the durable link repository and configured provider abstraction.
from casino.core.oauth.persistence import PersistentIdentityLinkRepository
# Import shared JSON/MySQL provider typing.
from casino.core.storage import StorageProvider
# Import fixed conflict and validation envelopes without reflecting claim values.
from casino.errors import ConflictError, ValidationError

# Name the provider-backed pending-enrollment document.
ENROLLMENT_DOCUMENT_KEY = "auth/oauth_social_enrollments"
# Version the strict pending record independently from global application schema.
ENROLLMENT_SCHEMA_VERSION = 1
# Bound durable pending and completed recovery records without evicting identity authority.
MAX_ENROLLMENT_RECORDS = 10_000
# Accept only the two translated enrollment locales.
ENROLLMENT_LOCALES = frozenset({"en-US", "ru-RU"})
# Accept only recoverable pending or terminal active lifecycle values.
ENROLLMENT_STATUSES = frozenset({"pending", "active"})


# Return a fresh provider-owned social-enrollment document.
def _default_enrollments() -> dict:
    # Preserve one independent schema marker and bounded record collection.
    return {"schema_version": ENROLLMENT_SCHEMA_VERSION, "enrollments": []}


# Represent one completed or recovered canonical social enrollment.
@dataclass(frozen=True)
class SocialEnrollmentResult:
    # Suppress the canonical user record from diagnostic representations.
    user: dict = field(repr=False)
    # Report whether this provider subject activated a new canonical account in this call.
    created: bool
    # Report whether a prior active signup was safely recovered after a lost browser response.
    recovered: bool


# Coordinate one provider subject through pending allocation, provisioning, linking, and activation.
class SocialEnrollmentService:
    # Bind the provider and keyed subject index while permitting an isolated link repository in tests.
    def __init__(self, storage: StorageProvider, digest_key: str, links: PersistentIdentityLinkRepository | None = None):
        # Require the same strong server-owned key already accepted by OAuth flow persistence.
        if not isinstance(digest_key, str) or len(digest_key.encode("utf-8")) < 32:
            # Reject enrollment before retaining any provider claim.
            raise ValidationError("OAuth digest configuration is unavailable")
        # Retain the shared provider for one JSON/MySQL-neutral pending document.
        self.storage = storage
        # Retain only key bytes for domain-separated HMAC operations.
        self._digest_key = digest_key.encode("utf-8")
        # Bind compound identity links to the same provider unless tests inject the exact repository.
        self.links = PersistentIdentityLinkRepository(storage) if links is None else links

    # Derive the pending-record identity without storing the provider subject twice.
    def _subject_digest(self, provider: str, subject: str) -> str:
        # Return one domain-separated HMAC that cannot be reversed without the server key.
        return hmac.new(self._digest_key, f"social-enrollment\0{provider}\0{subject}".encode("utf-8"), hashlib.sha256).hexdigest()

    # Strictly validate one durable pending record before it can drive provisioning.
    @staticmethod
    def _record(row: object) -> dict:
        # Require the exact mapping shape and no unreviewed stored fields.
        fields = {"enrollment_id", "provider", "subject_digest", "user_id", "player_id", "terms_version", "locale", "status", "created_at", "updated_at"}
        # Reject missing, extra, or nonmapping state without rewriting it.
        if not isinstance(row, dict) or set(row) != fields:
            # Preserve malformed enrollment evidence for operator recovery.
            raise RuntimeError("OAuth social-enrollment storage requires operator recovery")
        # Require bounded printable text for every durable scalar.
        if any(not isinstance(row[name], str) or not row[name] or len(row[name]) > 512 or any(not character.isprintable() for character in row[name]) for name in fields):
            # Preserve the complete malformed document for operator recovery.
            raise RuntimeError("OAuth social-enrollment storage requires operator recovery")
        # Require server-owned namespaces, provider partition, locale, and lifecycle.
        if not row["enrollment_id"].startswith("social_enrollment_") or not row["user_id"].startswith("user_social_") or not row["player_id"].startswith("player_social_") or row["provider"] not in {"google", "facebook"} or row["locale"] not in ENROLLMENT_LOCALES or row["status"] not in ENROLLMENT_STATUSES:
            # Reject structurally drifted records before canonical state access.
            raise RuntimeError("OAuth social-enrollment storage requires operator recovery")
        # Return a detached strict record so callers cannot alias provider state.
        return dict(row)

    # Read one strict record by keyed provider subject without mutating provider state.
    def _find(self, subject_digest: str) -> dict | None:
        # Read a missing document through the explicit empty default.
        document = self.storage.read_document(ENROLLMENT_DOCUMENT_KEY, _default_enrollments)
        # Require the exact root shape and independent schema marker.
        if not isinstance(document, dict) or set(document) != {"schema_version", "enrollments"} or document.get("schema_version") != ENROLLMENT_SCHEMA_VERSION or not isinstance(document.get("enrollments"), list):
            # Preserve malformed state for operator recovery.
            raise RuntimeError("OAuth social-enrollment storage requires operator recovery")
        # Strictly validate every row before trusting the selected digest.
        rows = [self._record(row) for row in document["enrollments"]]
        # Select only the exact constant-time digest match.
        return next((row for row in rows if hmac.compare_digest(row["subject_digest"], subject_digest)), None)

    # Allocate one stable pending enrollment or replay the exact existing record transactionally.
    def _reserve(self, provider: str, subject_digest: str, terms_version: str, locale: str) -> tuple[dict, bool]:
        # Capture the committed record and creation decision outside the provider mutator.
        result = {"record": None, "created": False}

        # Define one complete allocation under the named-document transaction.
        def mutate(document: object) -> dict:
            # Require the exact root before any append can replace recoverable state.
            if not isinstance(document, dict) or set(document) != {"schema_version", "enrollments"} or document.get("schema_version") != ENROLLMENT_SCHEMA_VERSION or not isinstance(document.get("enrollments"), list):
                # Preserve malformed state for operator recovery.
                raise RuntimeError("OAuth social-enrollment storage requires operator recovery")
            # Strictly validate all existing rows before selecting one.
            rows = [self._record(row) for row in document["enrollments"]]
            # Find an exact existing provider-subject recovery record.
            existing = next((row for row in rows if hmac.compare_digest(row["subject_digest"], subject_digest)), None)
            # Replay compatible pending or terminal state without allocating another identity.
            if existing is not None:
                # Reject impossible digest partition drift or changed pending consent semantics.
                if existing["provider"] != provider or (existing["status"] == "pending" and (existing["terms_version"] != terms_version or existing["locale"] != locale)):
                    # Preserve the prior enrollment under a stable conflict.
                    raise ConflictError("Social enrollment replay conflicts with existing state")
                # Publish the existing compatible record without mutation.
                result.update({"record": existing, "created": False})
                # Return the exact original document.
                return document
            # Reject capacity rather than evicting authentication recovery authority.
            if len(rows) >= MAX_ENROLLMENT_RECORDS:
                # Fail closed until explicit lifecycle policy archives records.
                raise ConflictError("Social enrollment capacity is reached")
            # Capture one server timestamp for every first-allocation field.
            now = utc_now()
            # Allocate all canonical identifiers exactly once inside this provider transaction.
            record = {"enrollment_id": new_id("social_enrollment"), "provider": provider, "subject_digest": subject_digest, "user_id": new_id("user_social"), "player_id": new_id("player_social"), "terms_version": terms_version, "locale": locale, "status": "pending", "created_at": now, "updated_at": now}
            # Append the strict recoverable record.
            document["enrollments"].append(record)
            # Preserve the independent schema marker on commit.
            document["schema_version"] = ENROLLMENT_SCHEMA_VERSION
            # Publish a detached committed result.
            result.update({"record": dict(record), "created": True})
            # Return the complete provider document.
            return document

        # Commit allocation through the provider's cross-process transaction boundary.
        self.storage.update_document(ENROLLMENT_DOCUMENT_KEY, mutate, _default_enrollments)
        # Return the strict record and first-allocation decision.
        return result["record"], result["created"]

    # Mark one exact pending record active only after canonical account activation succeeds.
    def _complete(self, subject_digest: str, enrollment_id: str, user_id: str) -> None:
        # Define the exact lifecycle transition under the provider transaction.
        def mutate(document: object) -> dict:
            # Require the exact root and strict rows before mutation.
            if not isinstance(document, dict) or set(document) != {"schema_version", "enrollments"} or document.get("schema_version") != ENROLLMENT_SCHEMA_VERSION or not isinstance(document.get("enrollments"), list):
                # Preserve malformed state for operator recovery.
                raise RuntimeError("OAuth social-enrollment storage requires operator recovery")
            # Validate every row before selecting the target.
            rows = [self._record(row) for row in document["enrollments"]]
            # Select the exact digest-bound allocation.
            index = next((index for index, row in enumerate(rows) if hmac.compare_digest(row["subject_digest"], subject_digest)), None)
            # Refuse absent or drifted canonical bindings.
            if index is None or rows[index]["enrollment_id"] != enrollment_id or rows[index]["user_id"] != user_id:
                # Preserve every enrollment record unchanged.
                raise ConflictError("Social enrollment completion is unavailable")
            # Transition pending or idempotent active state to active.
            document["enrollments"][index]["status"] = "active"
            # Refresh the recovery timestamp without changing any identity binding.
            document["enrollments"][index]["updated_at"] = utc_now()
            # Return the complete document for commit.
            return document

        # Commit only the final pending-record lifecycle marker.
        self.storage.update_document(ENROLLMENT_DOCUMENT_KEY, mutate, _default_enrollments)

    # Provision, link, and activate one provider subject without consulting provider email for identity.
    def provision(self, identity: VerifiedIdentity, terms_version: str, locale: str) -> SocialEnrollmentResult:
        # Require the provider-neutral verified identity model.
        if not isinstance(identity, VerifiedIdentity):
            # Reject arbitrary provider response objects.
            raise ValidationError("External identity is invalid")
        # Require one supported external provider and exact opaque subject.
        specification = get_provider_spec(identity.provider)
        # Reject local-password authorities or malformed provider subjects.
        if specification.flow == "password" or not isinstance(identity.subject, str) or not identity.subject or len(identity.subject) > 255 or any(not character.isprintable() for character in identity.subject):
            # Return one value-free provider identity error.
            raise ValidationError("External identity subject is invalid")
        # Require explicit current terms and one translated locale from the consumed start intent.
        if not isinstance(terms_version, str) or not terms_version or locale not in ENROLLMENT_LOCALES:
            # Reject missing consent metadata before any pending allocation.
            raise ValidationError("Current enrollment acknowledgement is required")
        # Derive the non-reversible pending-record key.
        subject_digest = self._subject_digest(identity.provider, identity.subject)
        # Read prior recovery state before interpreting an existing compound link.
        prior = self._find(subject_digest)
        # Read the exact provider-subject identity authority.
        existing_link = self.links.find_by_subject(identity.provider, identity.subject)
        # Reject a link that was created outside this social-enrollment allocation.
        if existing_link is not None and (prior is None or existing_link.user_id != prior["user_id"]):
            # Require the existing canonical owner to authenticate and use explicit linking/sign-in.
            raise ConflictError("External identity is already linked to a canonical account")
        # Refuse resurrection after an active enrollment's link was explicitly revoked or deleted.
        if prior is not None and prior["status"] == "active" and existing_link is None:
            # Preserve revocation until a separately authenticated recovery flow acts.
            raise ConflictError("Social identity requires account recovery")
        # Use a verified provider email only as an eligibility guard, never as an account selector.
        local_email_owner = auth.find_user_by_email(identity.email) if identity.email_verified is True and isinstance(identity.email, str) and identity.email.strip() else None
        # Require an existing email/password account owner to authenticate and explicitly link instead.
        if local_email_owner is not None:
            # Return one fixed conflict without disclosing the matching canonical account.
            raise ConflictError("Existing account requires explicit provider linking")
        # Allocate or replay the exact pending record.
        record, allocated = self._reserve(identity.provider, subject_digest, terms_version, locale)
        # Create or replay the inactive canonical user and deterministic wallet.
        user = auth.provision_social_user(identity.provider, record["enrollment_id"], record["user_id"], record["player_id"], identity.display_name or "", identity.email, identity.email_verified, record["locale"], record["terms_version"])
        # Preserve one timestamp for the first or idempotent identity-link proposal.
        now = utc_now()
        # Build the exact provider-subject to allocated-user link without email metadata.
        proposed = ExternalIdentityLink(provider=identity.provider, subject=identity.subject, user_id=record["user_id"], created_at=now, updated_at=now)
        # Atomically create or replay both compound uniqueness constraints.
        stored_link, _created_link = self.links.save(proposed)
        # Reject any repository result that drifted from the pending allocation.
        if stored_link.provider != identity.provider or stored_link.subject != identity.subject or stored_link.user_id != record["user_id"]:
            # Preserve inactive state for operator-safe recovery.
            raise ConflictError("Identity link repository returned a conflicting binding")
        # Publish the account only after user, wallet, consent, and identity link are all durable.
        active_user = auth.activate_social_user(identity.provider, record["enrollment_id"], record["user_id"], record["player_id"])
        # Mark the pending record complete for lost-response recovery.
        self._complete(subject_digest, record["enrollment_id"], record["user_id"])
        # Report first activation versus safe replay without exposing identifiers.
        return SocialEnrollmentResult(user=active_user, created=allocated, recovered=not allocated and prior is not None and prior["status"] == "active")
