# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Transactional OAuth persistence tests for issue #326.

Requirements: OAUTH-003, OAUTH-004, OAUTH-009, STORAGE-001, STORAGE-002,
SESSION-007, and TEST-045.
"""

# Import temporary directories for isolated JSON-provider persistence.
import tempfile
# Import threads so compound uniqueness is exercised concurrently.
import threading
# Import unittest for dependency-free focused execution.
import unittest
# Import UTC timestamps for deterministic lifecycle fixtures.
from datetime import datetime, timedelta, timezone
# Import paths for the isolated provider root.
from pathlib import Path

# Import immutable identity-link records.
from casino.core.oauth.identity_links import ExternalIdentityLink
# Import transactional flow and link repositories.
from casino.core.oauth.persistence import FLOW_DOCUMENT_KEY, FLOW_SECRET_DOCUMENT_KEY, OAuthFlowRecord, OAuthFlowRepository, OAuthRateLimiter, PersistentIdentityLinkRepository
# Import the JSON storage implementation through its public class.
from casino.core.storage import JsonStorageProvider
# Import stable conflict and authentication errors.
from casino.errors import ConflictError, UnauthorizedError

# Define one synthetic strong HMAC key that never reaches production configuration.
DIGEST_KEY = "synthetic-digest-key-with-at-least-32-bytes"


# Render canonical millisecond timestamps for persisted flow fixtures.
def stamp(value: datetime) -> str:
    # Convert UTC offset text to the repository's canonical Z suffix.
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


# Verify one-time claims, expiry, browser binding, and compound uniqueness.
class OAuthPersistenceTests(unittest.TestCase):
    # Create one isolated provider for each test.
    def setUp(self):
        # Retain the temporary directory until test cleanup.
        self.temporary = tempfile.TemporaryDirectory()
        # Build a JSON provider rooted outside repository application data.
        self.storage = JsonStorageProvider(Path(self.temporary.name) / "data")
        # Create the provider directories before repository use.
        self.storage.ensure_ready()

    # Remove the isolated filesystem after each test.
    def tearDown(self):
        # Delete only the TemporaryDirectory-owned test root.
        self.temporary.cleanup()

    # Build one fully bound pending flow around the current time.
    def flow(self, *, state="s" * 43, expires_delta=timedelta(minutes=5)):
        # Read one creation instant for consistent expiry math.
        created = datetime.now(timezone.utc)
        # Return a complete immutable pending record with synthetic opaque proofs.
        return OAuthFlowRecord(flow_id=f"flow-{state[:1]}", provider="google", state=state, nonce="n" * 43, pkce_verifier="v" * 64, callback_uri="https://casino.example.test/api/v2/auth/oauth/google/callback", owner_binding="b" * 64, action="signin", return_to="/", status="pending", created_at=stamp(created), expires_at=stamp(created + expires_delta))

    # Prove the first callback consumes a flow and every replay fails.
    def test_flow_consumption_is_atomic_and_one_time(self):
        # Create the repository over isolated persistent storage.
        repository = OAuthFlowRepository(self.storage, DIGEST_KEY)
        # Persist one pending flow before callback simulation.
        record = repository.create(self.flow())
        # Consume the exact provider, state, callback, and browser binding.
        claimed = repository.claim("google", record.state, record.callback_uri, record.owner_binding)
        # Assert the durable lifecycle is leased before provider exchange.
        self.assertEqual(claimed.status, "exchanging")
        # Commit a terminal replay tombstone only after the simulated exchange succeeds.
        repository.complete(claimed)
        # Reject a replay of the same callback after the durable transition.
        with self.assertRaises(UnauthorizedError):
            # Attempt a second claim of the same state.
            repository.claim("google", record.state, record.callback_uri, record.owner_binding)

    # Prove callback URI, provider, browser, and expiration bindings fail closed.
    def test_flow_rejects_binding_drift_and_expiry(self):
        # Create one repository for all independent cases.
        repository = OAuthFlowRepository(self.storage, DIGEST_KEY)
        # Define mismatched provider, callback, and owner attempts.
        cases = (("facebook", None, None), (None, "https://casino.example.test/api/v2/auth/oauth/facebook/callback", None), (None, None, "x" * 64))
        # Verify each mismatch against a fresh state so failed claims remain independent.
        for index, (provider, callback, owner) in enumerate(cases):
            # Label only the bounded numeric fixture case.
            with self.subTest(case=index):
                # Create a unique synthetic flow for this binding check.
                record = repository.create(self.flow(state=(str(index) + "s" * 42)))
                # Require the same indistinguishable authentication failure.
                with self.assertRaises(UnauthorizedError):
                    # Attempt the mismatched callback claim.
                    repository.claim(provider or record.provider, record.state, callback or record.callback_uri, owner or record.owner_binding)
        # Build a flow whose ordered creation and expiry are both in the past.
        past = datetime.now(timezone.utc) - timedelta(minutes=10)
        # Persist the already expired but structurally valid lifecycle record.
        expired = repository.create(OAuthFlowRecord(flow_id="flow-expired", provider="google", state="e" * 43, nonce="n" * 43, pkce_verifier="v" * 64, callback_uri="https://casino.example.test/api/v2/auth/oauth/google/callback", owner_binding="b" * 64, action="signin", return_to="/", status="pending", created_at=stamp(past), expires_at=stamp(past + timedelta(minutes=1))))
        # Reject expiry before any provider exchange can begin.
        with self.assertRaises(UnauthorizedError):
            # Attempt an expired flow claim.
            repository.claim(expired.provider, expired.state, expired.callback_uri, expired.owner_binding)

    # Prove raw browser and provider proofs are physically separated from durable metadata.
    def test_flow_metadata_and_exchange_proofs_are_separated_and_recoverable(self):
        # Create one strong-key repository over isolated persistent storage.
        repository = OAuthFlowRepository(self.storage, DIGEST_KEY)
        # Persist one complete request-local flow.
        record = repository.create(self.flow())
        # Read the two exact provider documents independently.
        metadata = self.storage.read_document(FLOW_DOCUMENT_KEY, {})
        # Read proof material from its physically separate document.
        secrets = self.storage.read_document(FLOW_SECRET_DOCUMENT_KEY, {})
        # Serialize only in test memory for secret-absence assertions.
        serialized_metadata = repr(metadata)
        # Require raw state, callback, browser binding, nonce, and PKCE to be absent from metadata.
        self.assertTrue(all(value not in serialized_metadata for value in (record.state, record.callback_uri, record.owner_binding, record.nonce, record.pkce_verifier)))
        # Require the proof document to contain nonce and PKCE but no state, callback, browser, user, or session fields.
        self.assertEqual(set(secrets["secrets"][0]), {"flow_id", "nonce", "pkce_verifier", "expires_at"})
        # Claim the exact flow once for provider exchange.
        claimed = repository.claim(record.provider, record.state, record.callback_uri, record.owner_binding)
        # Release a simulated retryable provider failure without burning state.
        repository.release(claimed)
        # Require the same callback to be claimable again after bounded release.
        retry = repository.claim(record.provider, record.state, record.callback_uri, record.owner_binding)
        # Complete the recovered attempt to preserve replay protection.
        repository.complete(retry)

    # Prove the provider-backed rate limiter is shared across repository instances.
    def test_rate_limit_is_durable_across_instances(self):
        # Construct two worker-like limiters over independent provider instances and one shared root.
        limiters = (OAuthRateLimiter(JsonStorageProvider(self.storage.data_dir), DIGEST_KEY, limit=1), OAuthRateLimiter(JsonStorageProvider(self.storage.data_dir), DIGEST_KEY, limit=1))
        # Consume the only allowance through the first worker-like instance.
        limiters[0].check("browser-binding", "google", "signin")
        # Require the second process-like instance to observe the same durable bucket.
        from casino.errors import RateLimitError
        # Reject a second attempt without process-local bypass.
        with self.assertRaises(RateLimitError):
            # Exercise the same compound limiter key through another instance.
            limiters[1].check("browser-binding", "google", "signin")

    # Prove provider-subject and provider-user uniqueness under concurrent writes.
    def test_identity_link_compound_uniqueness_is_concurrent(self):
        # Create two repository instances as separate worker-like callers.
        repositories = (PersistentIdentityLinkRepository(JsonStorageProvider(self.storage.data_dir)), PersistentIdentityLinkRepository(JsonStorageProvider(self.storage.data_dir)))
        # Use one barrier so both writes contend for the same transaction boundary.
        barrier = threading.Barrier(2)
        # Collect only stable success or error class outcomes.
        outcomes = []
        # Serialize result collection independently from storage locking.
        outcome_lock = threading.Lock()

        # Attempt one subject assignment to a selected canonical user.
        def save(repository, user_id):
            # Wait until both synthetic workers are ready.
            barrier.wait()
            # Start protected save handling so both threads report a bounded outcome.
            try:
                # Build a strict link without provider claims or user data.
                link = ExternalIdentityLink(provider="facebook", subject="subject-synthetic", user_id=user_id, created_at="2026-07-19T00:00:00.000Z", updated_at="2026-07-19T00:00:00.000Z")
                # Commit the one-to-one binding through the repository transaction.
                _stored, created = repository.save(link)
                # Record only the success marker.
                outcome = ("created", created)
            # Convert the expected losing transaction into a class-only marker.
            except ConflictError:
                # Avoid retaining identity values in results.
                outcome = ("conflict", False)
            # Append the stable outcome under a test-local mutex.
            with outcome_lock:
                # Preserve both thread results for exact assertions.
                outcomes.append(outcome)

        # Construct both competing writer threads.
        threads = [threading.Thread(target=save, args=(repositories[index], f"user-{index}")) for index in range(2)]
        # Start each writer after all fixtures exist.
        for thread in threads:
            # Begin the concurrent repository call.
            thread.start()
        # Wait for both bounded writes to complete.
        for thread in threads:
            # Join without leaving background mutation after the test.
            thread.join(timeout=5)
        # Require exactly one committed binding and one conflict.
        self.assertEqual(sorted(outcomes), [("conflict", False), ("created", True)])
        # Require exactly one durable strict link after the race.
        self.assertEqual(len(repositories[0]._links()), 1)


# Run focused tests when invoked directly.
if __name__ == "__main__":
    # Delegate reporting and status to unittest.
    unittest.main()
