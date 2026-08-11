# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Injected external-identity links to canonical users and bound players.

Requirements: OAUTH-004 and USER-001. This module never creates users, links by email, or
selects a persistence provider.
"""

# Import dataclass helpers so subjects and canonical identifiers stay out of repr output.
from dataclasses import dataclass, field
# Import protocol types so persistence and canonical users remain integration-injected.
from typing import Protocol

# Import the canonical timestamp helper for proposed durable link audit fields.
from casino.core.clock import utc_now
# Import the provider-neutral identity and canonical-user lookup models.
from casino.core.oauth.models import CanonicalUserLookup, VerifiedIdentity
# Import provider metadata so only supported external providers can be linked.
from casino.core.oauth.providers import get_provider_spec
# Import standard errors for future envelope-compatible route integration.
from casino.errors import ConflictError, ForbiddenError, UnauthorizedError, ValidationError


# Represent one compound provider-subject link to a canonical user.
@dataclass(frozen=True)
class ExternalIdentityLink:  # Keep one compound binding in an immutable allowlisted record.
    # Store the exact supported provider identifier.
    provider: str
    # Store the opaque provider subject without exposing it through repr output.
    subject: str = field(repr=False)
    # Store the canonical user id without exposing it through repr output.
    user_id: str = field(repr=False)
    # Store the creation timestamp for audit use.
    created_at: str
    # Store the latest persisted update timestamp for audit use.
    updated_at: str

    # Convert the link to the strict allowlist expected from an integration-owned repository.
    def to_record(self) -> dict:
        # Return no email, profile claim, code, token, state, nonce, or credential fields.
        return {"provider": self.provider, "subject": self.subject, "user_id": self.user_id, "created_at": self.created_at, "updated_at": self.updated_at}


# Return one canonical user/player resolution without provider claims or secrets.
@dataclass(frozen=True)
class IdentityResolution:  # Keep the canonical user/player outcome separate from claims.
    # Store the exact supported provider identifier.
    provider: str
    # Store the canonical user id without exposing it through repr output.
    user_id: str = field(repr=False)
    # Store the bound canonical player id without exposing it through repr output.
    player_id: str = field(repr=False)
    # Report whether this operation proposed a new repository link.
    link_created: bool

    # Return non-sensitive resolution facts for diagnostic testing.
    def diagnostic(self) -> dict:
        # Publish presence booleans instead of canonical identifiers.
        return {"provider": self.provider, "user_resolved": bool(self.user_id), "player_resolved": bool(self.player_id), "link_created": self.link_created}


# Define the repository port needed for deterministic link resolution and atomic uniqueness.
class IdentityLinkRepository(Protocol):
    # Find a link by the provider-owned compound identity key.
    def find_by_subject(self, provider: str, subject: str) -> ExternalIdentityLink | None:
        # Protocol methods have no implementation because persistence is shared-owner work.
        ...

    # Find a provider link already owned by one canonical user.
    def find_by_user(self, provider: str, user_id: str) -> ExternalIdentityLink | None:
        # Protocol methods have no implementation because persistence is shared-owner work.
        ...

    # Atomically save one new link or return the exact idempotent existing link.
    def save(self, link: ExternalIdentityLink) -> tuple[ExternalIdentityLink, bool]:
        # Protocol methods have no implementation because persistence is shared-owner work.
        ...


# Link and resolve external identities without user creation, email matching, or built-in persistence.
class IdentityLinkService:
    # Require explicit repository and canonical-user lookup ports.
    def __init__(self, repository: IdentityLinkRepository, user_lookup: CanonicalUserLookup):
        # Store the integration-owned repository without selecting JSON or MySQL behavior.
        self.repository = repository
        # Store the canonical lookup without importing or modifying local-login code.
        self.user_lookup = user_lookup

    # Validate one canonical user and return its current bound player id.
    def _canonical_player_id(self, user_id: str) -> str:
        # Resolve the durable user record through the injected canonical lookup.
        user = self.user_lookup(user_id)
        # Reject missing users before creating or resolving a link.
        if not user or user.get("user_id") != user_id:
            # Raise a generic error without exposing the requested identifier.
            raise ValidationError("Canonical user was not found")
        # Reject inactive users before external authentication can create a session.
        if user.get("status") != "active":
            # Raise the same inactive-user class used by local login.
            raise ForbiddenError("User is inactive")
        # Read the canonical bound player identifier from the durable user.
        player_id = user.get("player_id")
        # Reject broken canonical user/player bindings.
        if not isinstance(player_id, str) or not player_id:
            # Raise a generic invariant failure without serializing the user record.
            raise ValidationError("Canonical user has no bound player")
        # Return the current canonical player binding instead of persisting a duplicate copy.
        return player_id

    # Validate an external identity before compound-key repository use.
    def _validate_identity(self, identity: VerifiedIdentity) -> None:
        # Reject objects outside the provider-neutral allowlisted model.
        if not isinstance(identity, VerifiedIdentity):
            # Raise a generic error without serializing arbitrary claim payloads.
            raise ValidationError("External identity is invalid")
        # Resolve exact provider metadata without normalizing unknown identifiers.
        spec = get_provider_spec(identity.provider)
        # Reject local password identities because local login remains unchanged.
        if spec.flow == "password":
            # Raise a generic error for an unsupported linking flow.
            raise ValidationError("Local identities do not use external links")
        # Reject absent, overlong, or control-character subjects before lookup.
        if not identity.subject or len(identity.subject) > 255 or any(not character.isprintable() for character in identity.subject):
            # Raise a generic error without exposing the subject.
            raise ValidationError("External identity subject is invalid")

    # Validate one repository result before trusting any persisted binding fields.
    @staticmethod
    def _repository_link_matches(link: object, provider: str, *, subject: str | None = None, user_id: str | None = None) -> bool:  # Enforce exact repository partition keys.
        # Reject objects outside the strict immutable link model.
        if not isinstance(link, ExternalIdentityLink):
            # Report no match without serializing the repository result.
            return False
        # Reject provider drift before comparing optional compound-key components.
        if link.provider != provider:
            # Report no match for a row from another provider partition.
            return False
        # Reject malformed stored subjects even when an adapter returned the row.
        if not isinstance(link.subject, str) or not link.subject or len(link.subject) > 255 or any(not character.isprintable() for character in link.subject):
            # Report no match for an unusable persisted compound key.
            return False
        # Reject missing or non-text canonical user identifiers.
        if not isinstance(link.user_id, str) or not link.user_id:
            # Report no match for an unusable canonical binding.
            return False
        # Require an exact opaque subject when the lookup was subject-keyed.
        if subject is not None and link.subject != subject:
            # Report no match without reflecting either subject.
            return False
        # Require the exact canonical user when the lookup was user-keyed.
        if user_id is not None and link.user_id != user_id:
            # Report no match without reflecting either user identifier.
            return False
        # Accept only the exact requested repository binding.
        return True

    # Explicitly link one external identity to the authenticated canonical caller.
    def link(self, identity: VerifiedIdentity, authenticated_user_id: str) -> IdentityResolution:
        # Validate the provider and subject before any user or repository lookup.
        self._validate_identity(identity)
        # Require an exact text identifier from authenticated context, never a request-body target.
        if not isinstance(authenticated_user_id, str) or not authenticated_user_id:
            # Raise a generic error without inspecting optional identity email.
            raise ValidationError("Authenticated canonical user id is required for identity linking")
        # Preserve the authenticated canonical identifier exactly without normalization.
        canonical_user_id = authenticated_user_id
        # Validate the current canonical user/player invariant before repository use.
        player_id = self._canonical_player_id(canonical_user_id)
        # Resolve any existing external compound key before proposing a write.
        existing_subject_link = self.repository.find_by_subject(identity.provider, identity.subject)
        # Handle an existing external identity idempotently or as a cross-user conflict.
        if existing_subject_link is not None:
            # Reject adapter results outside the exact provider-subject partition.
            if not self._repository_link_matches(existing_subject_link, identity.provider, subject=identity.subject):
                # Raise a generic repository invariant error without exposing row contents.
                raise ConflictError("Identity link repository returned a conflicting binding")
            # Reject attempts to reassign one external identity to another canonical user.
            if existing_subject_link.user_id != canonical_user_id:
                # Raise a stable conflict without exposing either identifier.
                raise ConflictError("External identity is already linked to another user")
            # Return the exact existing canonical binding without another repository write.
            return IdentityResolution(provider=identity.provider, user_id=canonical_user_id, player_id=player_id, link_created=False)
        # Resolve any different subject already owned by this provider and canonical user.
        existing_user_link = self.repository.find_by_user(identity.provider, canonical_user_id)
        # Reject a second provider subject until an explicit unlink or replace flow exists.
        if existing_user_link is not None:
            # Reject adapter results outside the exact provider-user partition.
            if not self._repository_link_matches(existing_user_link, identity.provider, user_id=canonical_user_id):
                # Raise a generic repository invariant error without exposing row contents.
                raise ConflictError("Identity link repository returned a conflicting binding")
            # Raise a stable conflict without exposing either subject.
            raise ConflictError("User already has a different identity for this provider")
        # Preserve one timestamp for the proposed first durable record.
        now = utc_now()
        # Build the strict allowlisted proposal without email, claims, tokens, state, or nonce.
        proposed_link = ExternalIdentityLink(provider=identity.provider, subject=identity.subject, user_id=canonical_user_id, created_at=now, updated_at=now)
        # Require the integration-owned repository to enforce both uniqueness constraints atomically.
        save_result = self.repository.save(proposed_link)
        # Reject malformed adapter return shapes before tuple unpacking or attribute access.
        if not isinstance(save_result, tuple) or len(save_result) != 2:
            # Raise a generic repository invariant error without exposing return contents.
            raise ConflictError("Identity link repository returned a conflicting binding")
        # Unpack only the validated two-item repository response.
        stored_link, created = save_result
        # Reject a repository result that does not preserve the requested compound binding.
        if not self._repository_link_matches(stored_link, identity.provider, subject=identity.subject, user_id=canonical_user_id) or not isinstance(created, bool):
            # Raise a generic invariant failure without exposing repository contents.
            raise ConflictError("Identity link repository returned a conflicting binding")
        # Return the canonical resolution without exposing the provider subject.
        return IdentityResolution(provider=identity.provider, user_id=canonical_user_id, player_id=player_id, link_created=created)

    # Resolve a previously linked external identity to its canonical user and current player.
    def resolve(self, identity: VerifiedIdentity) -> IdentityResolution:
        # Validate the provider and subject before repository lookup.
        self._validate_identity(identity)
        # Find the compound external identity link.
        link = self.repository.find_by_subject(identity.provider, identity.subject)
        # Reject first-use identities because email auto-linking and signup are out of scope.
        if link is None:
            # Raise a generic authentication error without exposing identity claims.
            raise UnauthorizedError("External identity is not linked to a local account")
        # Reject adapter results outside the exact provider-subject partition.
        if not self._repository_link_matches(link, identity.provider, subject=identity.subject):
            # Raise a generic repository invariant error without exposing row contents.
            raise ConflictError("Identity link repository returned a conflicting binding")
        # Resolve the canonical user's current player binding and active status.
        player_id = self._canonical_player_id(link.user_id)
        # Return the canonical resolution without exposing the provider subject.
        return IdentityResolution(provider=identity.provider, user_id=link.user_id, player_id=player_id, link_created=False)
