# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused OAuth canonical user/player identity-link tests for issue #70.

Requirements: OAUTH-004, USER-001, and TEST-045.
"""

# Import unittest and patching support for isolated dependency injection.
import unittest
# Import Mock so malformed repository adapters can be exercised without persistence.
from unittest.mock import Mock

# Import the identity-link models and injected service under test.
from casino.core.oauth.identity_links import ExternalIdentityLink, IdentityLinkService
# Import the provider-neutral external identity model.
from casino.core.oauth.models import VerifiedIdentity
# Import standard errors for conflict and fail-closed assertions.
from casino.errors import ConflictError, ForbiddenError, UnauthorizedError, ValidationError


# Provide an in-memory repository that enforces the same compound uniqueness contract.
class InMemoryIdentityLinkRepository:
    # Initialize an empty isolated link collection.
    def __init__(self):
        # Store links only in this test instance.
        self.links = []

    # Find an exact provider-subject link.
    def find_by_subject(self, provider: str, subject: str):
        # Scan isolated links deterministically.
        for link in self.links:
            # Return the exact compound-key match.
            if link.provider == provider and link.subject == subject:
                # Return the stored immutable link.
                return link
        # Return no link when absent.
        return None

    # Find an exact provider-user link.
    def find_by_user(self, provider: str, user_id: str):
        # Scan isolated links deterministically.
        for link in self.links:
            # Return the exact provider-owner match.
            if link.provider == provider and link.user_id == user_id:
                # Return the stored immutable link.
                return link
        # Return no link when absent.
        return None

    # Save a link with idempotency and one-to-one uniqueness.
    def save(self, link: ExternalIdentityLink):
        # Check every isolated existing link.
        for existing in self.links:
            # Handle the same external compound key.
            if existing.provider == link.provider and existing.subject == link.subject:
                # Return an idempotent same-user link.
                if existing.user_id == link.user_id:
                    # Return the existing link without creation.
                    return existing, False
                # Reject cross-user reassignment.
                raise ConflictError("External identity is already linked to another user")
            # Reject a second subject for the same provider and user.
            if existing.provider == link.provider and existing.user_id == link.user_id:
                # Preserve one-to-one provider ownership.
                raise ConflictError("User already has a different identity for this provider")
        # Append the new immutable link.
        self.links.append(link)
        # Return the created link and marker.
        return link, True


# Validate explicit linking, resolution, collision handling, and persistence allowlisting.
class IdentityLinkTests(unittest.TestCase):
    # Create isolated canonical users and an in-memory repository before each test.
    def setUp(self):
        # Define two active canonical users with distinct bound players.
        self.users = {"user-1": {"user_id": "user-1", "status": "active", "player_id": "player-1", "email": "same@example.test"}, "user-2": {"user_id": "user-2", "status": "active", "player_id": "player-2", "email": "same@example.test"}, "inactive": {"user_id": "inactive", "status": "inactive", "player_id": "player-3"}, "broken": {"user_id": "broken", "status": "active", "player_id": ""}}
        # Create an isolated in-memory link repository.
        self.repository = InMemoryIdentityLinkRepository()
        # Create the service with injected users and storage so repository data is untouched.
        self.service = IdentityLinkService(repository=self.repository, user_lookup=self.users.get)
        # Create one external identity whose optional email matches multiple users.
        self.identity = VerifiedIdentity(provider="google", subject="google-subject-1", email="same@example.test", email_verified=True, display_name="Synthetic User")

    # Verify explicit linking resolves the canonical current player binding.
    def test_explicit_link_and_resolution_preserve_canonical_binding(self):
        # Link only after supplying an explicit canonical user id.
        created = self.service.link(self.identity, "user-1")
        # Assert the canonical user and player binding are returned.
        self.assertEqual((created.user_id, created.player_id), ("user-1", "player-1"))
        # Assert the first operation created a durable link.
        self.assertTrue(created.link_created)
        # Resolve the same identity without email matching.
        resolved = self.service.resolve(self.identity)
        # Assert resolution returns the same canonical binding.
        self.assertEqual((resolved.user_id, resolved.player_id), ("user-1", "player-1"))
        # Assert resolution did not create another link.
        self.assertFalse(resolved.link_created)

    # Verify repeated same-user links are idempotent.
    def test_same_link_is_idempotent(self):
        # Create the first explicit link.
        self.service.link(self.identity, "user-1")
        # Repeat the exact link.
        repeated = self.service.link(self.identity, "user-1")
        # Assert no second link was created.
        self.assertFalse(repeated.link_created)
        # Assert one durable row remains.
        self.assertEqual(len(self.repository.links), 1)

    # Verify external-subject and provider-user collision rules fail closed.
    def test_link_collisions_are_rejected(self):
        # Create the first explicit link.
        self.service.link(self.identity, "user-1")
        # Assert the same external subject cannot move to another user.
        with self.assertRaises(ConflictError):
            # Attempt a cross-user reassignment.
            self.service.link(self.identity, "user-2")
        # Create a different subject for the same provider.
        other_identity = VerifiedIdentity(provider="google", subject="google-subject-2")
        # Assert one user cannot own a second identity for the same provider.
        with self.assertRaises(ConflictError):
            # Attempt a second provider subject for the same user.
            self.service.link(other_identity, "user-1")

    # Verify repository adapters cannot cross provider or subject partitions.
    def test_repository_results_must_match_requested_compound_keys(self):
        # Create a repository mock that returns controlled malformed bindings.
        repository = Mock()
        # Create a service over the same isolated canonical-user fixtures.
        service = IdentityLinkService(repository=repository, user_lookup=self.users.get)
        # Return another provider's row for the requested Google subject and a different user.
        repository.find_by_subject.return_value = ExternalIdentityLink(provider="facebook", subject=self.identity.subject, user_id="user-2", created_at="2026-07-14T00:00:00Z", updated_at="2026-07-14T00:00:00Z")
        # Assert cross-provider repository drift cannot authenticate the other canonical user.
        with self.assertRaises(ConflictError):
            # Resolve no canonical binding from the mismatched provider partition.
            service.resolve(self.identity)
        # Return a same-provider row for a different opaque subject but the requested user.
        repository.find_by_subject.return_value = ExternalIdentityLink(provider="google", subject="different-subject", user_id="user-1", created_at="2026-07-14T00:00:00Z", updated_at="2026-07-14T00:00:00Z")
        # Assert a subject-keyed lookup cannot be treated as an idempotent same-user link.
        with self.assertRaises(ConflictError):
            # Link no identity through a mismatched subject partition.
            service.link(self.identity, "user-1")

    # Verify malformed repository save responses fail closed without attribute errors.
    def test_repository_save_results_require_exact_model_and_boolean(self):
        # Create a repository mock with no existing identity or user bindings.
        repository = Mock()
        # Return no subject-keyed binding before the proposed save.
        repository.find_by_subject.return_value = None
        # Return no user-keyed binding before the proposed save.
        repository.find_by_user.return_value = None
        # Return a mapping and a non-boolean marker instead of the strict repository contract.
        repository.save.return_value = ({"provider": "google"}, "created")
        # Create a service over the same isolated canonical-user fixtures.
        service = IdentityLinkService(repository=repository, user_lookup=self.users.get)
        # Assert malformed adapter output becomes one stable conflict.
        with self.assertRaises(ConflictError):
            # Persist no link from a non-model repository response.
            service.link(self.identity, "user-1")

    # Verify verified email never triggers implicit user matching or signup.
    def test_unlinked_verified_email_does_not_auto_link(self):
        # Attempt to resolve a first-use identity with a verified matching email.
        with self.assertRaises(UnauthorizedError):
            # Resolve without an explicit link or canonical user id.
            self.service.resolve(self.identity)
        # Assert no link was created from email.
        self.assertEqual(self.repository.links, [])

    # Verify missing, inactive, and broken canonical users cannot be linked.
    def test_canonical_user_invariants_are_required(self):
        # Define invalid canonical user ids and expected public errors.
        cases = (("missing", ValidationError), ("inactive", ForbiddenError), ("broken", ValidationError))
        # Validate each canonical invariant failure independently.
        for user_id, error_class in cases:
            # Label only the safe fixture user id.
            with self.subTest(user=user_id):
                # Assert the expected public error class.
                with self.assertRaises(error_class):
                    # Attempt no persistence after invariant failure.
                    self.service.link(self.identity, user_id)
        # Assert no invalid link reached the repository.
        self.assertEqual(self.repository.links, [])

    # Verify local password identities and absent explicit user ids stay outside this service.
    def test_link_requires_external_identity_and_explicit_user(self):
        # Create a synthetic local identity that must remain in existing local-login code.
        local_identity = VerifiedIdentity(provider="local", subject="local-subject")
        # Assert local identities cannot enter the external-link store.
        with self.assertRaises(ValidationError):
            # Attempt no local provider link.
            self.service.link(local_identity, "user-1")
        # Assert an explicit canonical user id is mandatory.
        with self.assertRaises(ValidationError):
            # Attempt no email-derived or auto-created link.
            self.service.link(self.identity, "")
        # Assert authenticated context identifiers are preserved rather than trimmed.
        with self.assertRaises(ValidationError):
            # Attempt a whitespace-altered identifier that does not match the canonical record.
            self.service.link(self.identity, " user-1 ")

    # Verify resolution and link objects suppress identity and canonical identifiers in repr output.
    def test_link_models_are_repr_and_diagnostic_safe(self):
        # Create one explicit external link.
        resolution = self.service.link(self.identity, "user-1")
        # Read the stored immutable link fixture.
        stored_link = self.repository.links[0]
        # Assert the provider subject is absent from link repr output.
        self.assertNotIn(self.identity.subject, repr(stored_link))
        # Assert the canonical user id is absent from link repr output.
        self.assertNotIn("user-1", repr(stored_link))
        # Assert canonical identifiers are absent from resolution repr output.
        self.assertNotIn("player-1", repr(resolution))
        # Assert diagnostics contain presence booleans rather than identifiers.
        self.assertNotIn("user-1", repr(resolution.diagnostic()))

# Run focused tests when this file is invoked directly.
if __name__ == "__main__":
    # Delegate process status and reporting to unittest.
    unittest.main()
