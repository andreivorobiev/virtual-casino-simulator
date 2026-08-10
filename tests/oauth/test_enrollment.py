"""Focused recoverable social-enrollment tests without provider traffic. (OAUTH-013, TEST-168)"""

# Import temporary directories for isolated provider-backed documents.
import tempfile
# Import threads for same-subject callback overlap evidence.
import threading
# Import unittest and exact dependency patching.
import unittest
# Import paths for isolated JSON provider construction.
from pathlib import Path
# Import mock patching for canonical user/player activation seams.
from unittest.mock import patch

# Import the recoverable enrollment service under test.
from casino.core.oauth.enrollment import SocialEnrollmentService
# Import the strict compound link model for existing-account collision evidence.
from casino.core.oauth.identity_links import ExternalIdentityLink
# Import synthetic provider-neutral verified identities.
from casino.core.oauth.models import VerifiedIdentity
# Import the isolated JSON storage provider.
from casino.core.storage import JsonStorageProvider
# Import stable conflict behavior for revocation and link ownership.
from casino.errors import ConflictError

# Define one strong synthetic digest key that is never used outside temporary tests.
DIGEST_KEY = "synthetic-social-enrollment-digest-key-32-bytes"


# Prove deterministic allocation, no email matching, recovery, revocation, and concurrency.
class SocialEnrollmentTests(unittest.TestCase):
    # Create one isolated provider and canonical-seam capture before each test.
    def setUp(self):
        # Retain the temporary root until teardown.
        self.temporary = tempfile.TemporaryDirectory()
        # Build one provider beneath the test-owned root.
        self.storage = JsonStorageProvider(Path(self.temporary.name) / "data")
        # Create provider directories before document operations.
        self.storage.ensure_ready()
        # Retain every deterministic provisioning call for uniqueness assertions.
        self.provisioned = []
        # Retain canonical user state by server-owned user id.
        self.users = {}
        # Protect test-local canonical state during the concurrency case.
        self.lock = threading.Lock()

    # Remove only test-owned temporary state.
    def tearDown(self):
        # Delete the isolated provider root.
        self.temporary.cleanup()

    # Build a verified identity whose email is presentation metadata only.
    @staticmethod
    def identity(provider="google", subject="subject-one", email="same@example.invalid"):
        # Return one provider-neutral synthetic claim projection.
        return VerifiedIdentity(provider=provider, subject=subject, email=email, email_verified=True, display_name="Synthetic player")

    # Emulate idempotent inactive canonical provisioning with no filesystem or wallet side effect.
    def provision(self, provider, enrollment_id, user_id, player_id, display_name, provider_email, email_verified, locale, terms_version):
        # Serialize test-local canonical state updates.
        with self.lock:
            # Retain the deterministic binding and presentation email independently.
            self.provisioned.append((provider, enrollment_id, user_id, player_id, provider_email, terms_version, locale))
            # Create or replay one inactive canonical record by server-owned user id.
            user = self.users.setdefault(user_id, {"user_id": user_id, "player_id": player_id, "status": "provisioning", "identity_provider": provider, "display_name": display_name, "provider_email": provider_email, "provider_email_verified": email_verified})
            # Return a detached user record.
            return dict(user)

    # Emulate the one externally visible canonical activation transaction.
    def activate(self, provider, enrollment_id, user_id, player_id):
        # Serialize test-local activation.
        with self.lock:
            # Read the exact prior deterministic user.
            user = self.users[user_id]
            # Require provider and wallet bindings to remain unchanged.
            if user["identity_provider"] != provider or user["player_id"] != player_id or not enrollment_id.startswith("social_enrollment_"):
                # Fail the test double on drift.
                raise AssertionError("canonical binding drifted")
            # Publish the account as active.
            user["status"] = "active"
            # Return a detached active record.
            return dict(user)

    # Construct the service under patched canonical seams.
    def service(self):
        # Return one provider-neutral enrollment service.
        return SocialEnrollmentService(self.storage, DIGEST_KEY)

    # Prove two providers or subjects sharing an email never select the same account.
    def test_email_metadata_never_links_or_selects_account(self):
        # Patch only canonical persistence while using real pending and link repositories.
        with patch("casino.core.oauth.enrollment.auth.provision_social_user", side_effect=self.provision), patch("casino.core.oauth.enrollment.auth.activate_social_user", side_effect=self.activate):
            # Enroll one Google subject with the shared presentation email.
            first = self.service().provision(self.identity("google", "subject-one"), "private-beta-1", "en-US")
            # Enroll one Facebook subject with the identical presentation email.
            second = self.service().provision(self.identity("facebook", "subject-two"), "private-beta-1", "ru-RU")
        # Require distinct canonical users and wallets despite identical email metadata.
        self.assertNotEqual((first.user["user_id"], first.user["player_id"]), (second.user["user_id"], second.user["player_id"]))
        # Require both first activations to report creation.
        self.assertEqual((first.created, second.created), (True, True))

    # Prove simultaneous callbacks allocate only one user, wallet, and identity link.
    def test_concurrent_same_subject_callbacks_share_one_allocation(self):
        # Build one shared service and result collectors.
        service = self.service()
        # Retain successful thread results.
        results = []
        # Retain unexpected thread failures.
        errors = []

        # Execute one identical provider callback result.
        def worker():
            # Capture any failure without losing thread context.
            try:
                # Provision the exact same provider subject and acknowledgement.
                results.append(service.provision(self.identity(), "private-beta-1", "en-US"))
            # Retain unexpected failures for the parent assertion.
            except Exception as error:
                # Append only the exception object inside the test process.
                errors.append(error)

        # Patch canonical operations while both threads use real transactional documents.
        with patch("casino.core.oauth.enrollment.auth.provision_social_user", side_effect=self.provision), patch("casino.core.oauth.enrollment.auth.activate_social_user", side_effect=self.activate):
            # Construct two overlapping callback workers.
            threads = [threading.Thread(target=worker) for _ in range(2)]
            # Start both workers before joining either.
            for thread in threads:
                # Start one callback worker.
                thread.start()
            # Wait for both bounded local workers.
            for thread in threads:
                # Join one completed worker.
                thread.join()
        # Require both calls to succeed through idempotent recovery.
        self.assertEqual(errors, [])
        # Require one canonical identity and wallet across both outcomes.
        self.assertEqual(len({(result.user["user_id"], result.user["player_id"]) for result in results}), 1)
        # Require exactly one first allocation decision.
        self.assertEqual(sorted(result.created for result in results), [False, True])
        # Require exactly one durable provider-subject link.
        self.assertEqual(len(self.storage.read_document("auth/oauth_identity_links", lambda: {"links": []})["links"]), 1)

    # Prove a post-link activation failure is resumable with the same deterministic resources.
    def test_activation_failure_resumes_without_duplicates(self):
        # Count activation attempts inside the isolated seam.
        attempts = {"count": 0}

        # Fail only the first activation after pending user, wallet, and link persistence.
        def flaky_activate(provider, enrollment_id, user_id, player_id):
            # Advance one bounded local attempt counter.
            attempts["count"] += 1
            # Stop the first attempt at the final publication boundary.
            if attempts["count"] == 1:
                # Simulate one recoverable local persistence interruption.
                raise RuntimeError("synthetic activation stop")
            # Resume through the deterministic test activation seam.
            return self.activate(provider, enrollment_id, user_id, player_id)

        # Construct one service over retained pending state.
        service = self.service()
        # Patch canonical operations while preserving real pending and link documents.
        with patch("casino.core.oauth.enrollment.auth.provision_social_user", side_effect=self.provision), patch("casino.core.oauth.enrollment.auth.activate_social_user", side_effect=flaky_activate):
            # Require the first post-link activation to fail without another account.
            with self.assertRaises(RuntimeError):
                # Attempt the first recoverable signup.
                service.provision(self.identity(), "private-beta-1", "en-US")
            # Retry through a fresh verified provider flow for the same subject.
            recovered = service.provision(self.identity(), "private-beta-1", "en-US")
        # Require the resumed account to be active and not a second allocation.
        self.assertEqual((recovered.user["status"], recovered.created), ("active", False))
        # Require every provisioning replay to preserve one user and wallet binding.
        self.assertEqual(len({(row[2], row[3]) for row in self.provisioned}), 1)

    # Prove explicit link deletion cannot be silently reversed by another signup intent.
    def test_completed_link_revocation_requires_separate_recovery(self):
        # Construct one service over retained state.
        service = self.service()
        # Complete the first signup through real pending and link documents.
        with patch("casino.core.oauth.enrollment.auth.provision_social_user", side_effect=self.provision), patch("casino.core.oauth.enrollment.auth.activate_social_user", side_effect=self.activate):
            # Create the social account once.
            created = service.provision(self.identity(), "private-beta-1", "en-US")
            # Remove only the exact provider-user link to model revocation or deletion.
            self.assertTrue(service.links.delete_for_user("google", created.user["user_id"]))
            # Refuse signup as a way to resurrect the revoked authentication authority.
            with self.assertRaises(ConflictError):
                # Attempt a new explicit signup for the revoked subject.
                service.provision(self.identity(), "private-beta-1", "en-US")

    # Prove an identity linked through an existing account cannot silently become a new account.
    def test_existing_link_without_signup_allocation_conflicts(self):
        # Construct one service over isolated storage.
        service = self.service()
        # Seed a subject link that belongs to an existing local account.
        service.links.save(ExternalIdentityLink(provider="google", subject="subject-one", user_id="user-local", created_at="2026-08-10T00:00:00.000Z", updated_at="2026-08-10T00:00:00.000Z"))
        # Reject provider email or signup intent as an account-merge path.
        with self.assertRaises(ConflictError):
            # Attempt no pending allocation or canonical user creation.
            service.provision(self.identity(), "private-beta-1", "en-US")

    # Prove a verified provider email owned by a local account requires explicit authenticated linking.
    def test_existing_local_email_requires_explicit_link_without_account_selection(self):
        # Construct one service over isolated storage.
        service = self.service()
        # Return only a synthetic existing local owner from the eligibility lookup.
        with patch("casino.core.oauth.enrollment.auth.find_user_by_email", return_value={"user_id": "user-local", "identity_provider": "local"}):
            # Reject social creation without returning or selecting the matching account.
            with self.assertRaisesRegex(ConflictError, "explicit provider linking"):
                # Attempt one verified provider signup using the occupied display email.
                service.provision(self.identity(email="owned@example.invalid"), "private-beta-1", "en-US")
        # Require no pending enrollment or identity link after the eligibility conflict.
        self.assertEqual(self.storage.read_document("auth/oauth_social_enrollments", lambda: {"enrollments": []})["enrollments"], [])
        # Require no compound link to be created from an email match.
        self.assertEqual(self.storage.read_document("auth/oauth_identity_links", lambda: {"links": []})["links"], [])


# Run focused tests when this module is invoked directly.
if __name__ == "__main__":
    # Delegate process status and reporting to unittest.
    unittest.main()
