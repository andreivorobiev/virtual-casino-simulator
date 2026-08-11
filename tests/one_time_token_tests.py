# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused deterministic and cross-process acceptance for inert one-time-token infrastructure."""

# Import process and thread executors for bounded exactly-once race evidence.
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
# Import mutable UTC timestamp arithmetic for deterministic expiry and retention.
from datetime import datetime, timedelta, timezone
# Import SHA-256 so the component contract can be pinned to the checked digest inventory.
import hashlib
# Import JSON parsing so durable state can be inspected without exposing secrets.
import json
# Import temporary directories so tests never touch user or repository token state.
import tempfile
# Import the standard unittest framework used by the central test runner.
import unittest
# Import portable paths for isolated token documents shared across processes.
from pathlib import Path

# Import the inert service under test and its canonical public error envelope.
from casino.core import one_time_tokens
# Import the standard validation error used by the service facade.
from casino.errors import ValidationError

# Use a synthetic high-entropy test key that is unrelated to deployment credentials.
TEST_DIGEST_KEY = "synthetic-one-time-token-test-key-material-2026"
# Resolve repository contract artifacts without depending on the process working directory.
ROOT = Path(__file__).resolve().parents[1]


# Provide one serializable process worker for JSON exactly-once consumption.
def _json_consume_worker(arguments):
    # Unpack only synthetic test fields passed by the parent process.
    store_path, digest_key, now, purpose, token, subject = arguments
    # Build an independent process-local service over the shared isolated document.
    service = one_time_tokens.TokenService(
        # Point both workers at the same temporary JSON document.
        store_path=Path(store_path),
        # Use the synthetic keyed digest material shared by this isolated test.
        digest_key=digest_key,
        # Freeze the worker clock at the parent issue instant.
        clock=lambda: now,
        # Suppress application logging while returning only a boolean outcome.
        audit_sink=lambda level, event, fields: None,
    )
    # Start protected consumption so the expected losing process returns a stable result.
    try:
        # Attempt the exact same consume operation from this independent process.
        service.consume(purpose, token, subject=subject)
        # Report the single successful winner.
        return True
    # Convert the generic losing result into a serializable false value.
    except ValidationError as error:
        # Require the losing process to receive only the generic public reason.
        assert error.details == one_time_tokens.INVALID_TOKEN_DETAILS
        # Report a safely rejected replay or race loser.
        return False


# Provide a mutable injected clock with repository-compatible UTC strings.
class _Clock:
    # Initialize the clock at one deterministic synthetic instant.
    def __init__(self):
        # Store an aware UTC datetime so expiry arithmetic remains deterministic.
        self.current = datetime(2031, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

    # Return the current repository timestamp string.
    def __call__(self):
        # Format the aware instant with milliseconds and the shared Z suffix.
        return self.current.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    # Advance the deterministic instant by a bounded number of seconds.
    def advance(self, seconds):
        # Replace the current instant with the advanced aware timestamp.
        self.current += timedelta(seconds=seconds)


# Exercise purpose binding, generic errors, lifecycle, and atomicity without any route or listener.
class OneTimeTokenTests(unittest.TestCase):
    # Build one isolated deterministic service before each test.
    def setUp(self):
        # Allocate an automatically cleaned temporary directory outside repository state.
        self.temp_directory = tempfile.TemporaryDirectory()
        # Place the isolated durable document beneath the temporary directory.
        self.store_path = Path(self.temp_directory.name) / "auth" / "one_time_tokens.json"
        # Create the mutable deterministic clock used by this test.
        self.clock = _Clock()
        # Count deterministic bearer and opaque identifier requests locally.
        self.sequence = {"token": 0, "id": 0}
        # Collect only sanitized audit events emitted by the service.
        self.audit_events = []

        # Return one unique deterministic bearer without using a fixture or checked-in secret.
        def token_factory():
            # Increment the local bearer sequence.
            self.sequence["token"] += 1
            # Return an ephemeral synthetic bearer that exists only in this test process.
            return f"ephemeral-test-bearer-{self.sequence['token']:04d}-not-a-secret"

        # Return one unique deterministic opaque identifier for assertions.
        def id_factory(prefix):
            # Increment the local identifier sequence.
            self.sequence["id"] += 1
            # Return a stable non-secret identifier with the requested prefix.
            return f"{prefix}_test_{self.sequence['id']:04d}"

        # Capture sanitized audit fields without forwarding them to repository logs.
        def audit_sink(level, event, fields):
            # Append an immutable copy so later mutation cannot hide leaked fields.
            self.audit_events.append((level, event, dict(fields)))

        # Construct the deterministic service over the isolated document.
        self.service = one_time_tokens.TokenService(
            # Use only the temporary token document.
            store_path=self.store_path,
            # Use synthetic keyed digest material unrelated to any credential.
            digest_key=TEST_DIGEST_KEY,
            # Inject the deterministic mutable clock.
            clock=self.clock,
            # Inject the ephemeral deterministic bearer factory.
            token_factory=token_factory,
            # Inject deterministic opaque identifier generation.
            id_factory=id_factory,
            # Capture only sanitized audit events.
            audit_sink=audit_sink,
        )

    # Remove the isolated temporary directory after each test.
    def tearDown(self):
        # Close and delete only the test-owned temporary directory.
        self.temp_directory.cleanup()

    # Assert one call fails with the exact generic consumption envelope.
    def assert_generic_token_error(self, operation):
        # Capture the standard validation error raised by the rejected operation.
        with self.assertRaises(ValidationError) as context:
            # Invoke the abuse or terminal-state operation.
            operation()
        # Require the one generic public reason without internal state detail.
        self.assertEqual(context.exception.details, one_time_tokens.INVALID_TOKEN_DETAILS)

    # Assert one call fails with the exact generic initiation envelope.
    def assert_generic_request_error(self, operation):
        # Capture the standard validation error raised by the malformed request.
        with self.assertRaises(ValidationError) as context:
            # Invoke the malformed or conflicting initiation operation.
            operation()
        # Require the one generic public initiation reason.
        self.assertEqual(context.exception.details, one_time_tokens.INVALID_REQUEST_DETAILS)

    # Prove deterministic issuance, strict bindings, exactly-once consume, and data minimization.
    def test_lifecycle_bindings_generic_errors_and_minimization(self):
        # Issue one session-bound verification token.
        issued = self.service.issue("email_verification", "Owner@Example.invalid", session_binding="ephemeral-browser-binding")
        # Require the documented one-time issuance receipt fields exactly.
        self.assertEqual(set(issued), {"expires_at", "purpose", "token", "token_id"})
        # Reject missing subject binding through the same public token envelope.
        self.assert_generic_token_error(lambda: self.service.consume("email_verification", issued["token"]))
        # Reject the wrong purpose without revealing cross-purpose state.
        self.assert_generic_token_error(lambda: self.service.consume("password_reset", issued["token"], subject="owner@example.invalid"))
        # Reject the wrong subject without revealing binding state.
        self.assert_generic_token_error(lambda: self.service.consume("email_verification", issued["token"], subject="other@example.invalid", session_binding="ephemeral-browser-binding"))
        # Reject the wrong session without revealing binding state.
        self.assert_generic_token_error(lambda: self.service.consume("email_verification", issued["token"], subject="owner@example.invalid", session_binding="wrong-binding"))
        # Reject an inactive bound subject through the same generic envelope.
        self.assert_generic_token_error(lambda: self.service.consume("email_verification", issued["token"], subject="owner@example.invalid", session_binding="ephemeral-browser-binding", subject_active=False))
        # Consume successfully with normalized subject and exact session binding.
        consumed = self.service.consume("email_verification", issued["token"], subject="owner@example.invalid", session_binding="ephemeral-browser-binding")
        # Require only opaque success fields and the fixed purpose.
        self.assertEqual(set(consumed), {"audit_id", "purpose", "token_id"})
        # Reject replay without exposing the consumed state.
        self.assert_generic_token_error(lambda: self.service.consume("email_verification", issued["token"], subject="owner@example.invalid", session_binding="ephemeral-browser-binding"))
        # Read the isolated durable document as text for raw-material absence checks.
        stored_text = self.store_path.read_text(encoding="utf-8")
        # Require no raw bearer, subject, or session binding in durable state.
        self.assertNotIn(issued["token"], stored_text)
        # Require the raw subject to be absent regardless of input casing.
        self.assertNotIn("owner@example.invalid", stored_text.casefold())
        # Require the raw browser/session binding to be absent.
        self.assertNotIn("ephemeral-browser-binding", stored_text)
        # Serialize captured audit data for raw-material absence checks.
        audit_text = json.dumps(self.audit_events, sort_keys=True)
        # Require audit events to contain none of the ephemeral raw material.
        self.assertNotIn(issued["token"], audit_text)
        # Require audit events to contain no raw subject or session binding.
        self.assertNotIn("owner@example.invalid", audit_text.casefold())
        # Require audit events to contain no raw session binding.
        self.assertNotIn("ephemeral-browser-binding", audit_text)

    # Prove active uniqueness plus atomic revoke-and-reissue semantics.
    def test_active_uniqueness_and_atomic_reissue(self):
        # Issue the first active invitation token for one bound subject.
        first = self.service.issue("invitation", "invitee@example.invalid")
        # Reject a second active issue for the same purpose and subject generically.
        self.assert_generic_request_error(lambda: self.service.issue("invitation", "invitee@example.invalid"))
        # Replace the active token through one atomic revoke-and-append operation.
        replacement = self.service.reissue("invitation", "invitee@example.invalid")
        # Require exactly one active replacement after reissue.
        self.assertEqual(self.service.active_count("invitation", "invitee@example.invalid"), 1)
        # Reject the superseded bearer through the generic token envelope.
        self.assert_generic_token_error(lambda: self.service.consume("invitation", first["token"], subject="invitee@example.invalid"))
        # Consume the replacement successfully.
        result = self.service.consume("invitation", replacement["token"], subject="invitee@example.invalid")
        # Require the replacement opaque identifier to match the successful result.
        self.assertEqual(result["token_id"], replacement["token_id"])

    # Prove an approved recoverable consumer may replay only the exact caller idempotency binding. (INVITE-003)
    def test_caller_idempotent_consume_replays_only_same_binding(self):
        # Issue one invitation bearer for a synthetic non-routable recipient.
        issued = self.service.issue("invitation", "recoverable@example.invalid")
        # Consume the bearer with an explicit caller-owned recovery key.
        first = self.service.consume("invitation", issued["token"], subject="recoverable@example.invalid", idempotency_key="invitation-recovery-key-0001")
        # Replay the exact request after a simulated lost response.
        replay = self.service.consume("invitation", issued["token"], subject="recoverable@example.invalid", idempotency_key="invitation-recovery-key-0001")
        # Require the same opaque receipt without another attempt counter transition.
        self.assertEqual(replay, first)
        # Reject a changed caller key through the unchanged one-time public envelope.
        self.assert_generic_token_error(lambda: self.service.consume("invitation", issued["token"], subject="recoverable@example.invalid", idempotency_key="invitation-recovery-key-0002"))
        # Reject the original key when the subject binding changes.
        self.assert_generic_token_error(lambda: self.service.consume("invitation", issued["token"], subject="other@example.invalid", idempotency_key="invitation-recovery-key-0001"))
        # Inspect durable state without printing any digest value.
        durable = json.loads(self.store_path.read_text(encoding="utf-8"))
        # Require one keyed replay verifier and no raw caller key.
        self.assertTrue(durable["tokens"][0].get("consume_idempotency_digest"))
        # Require raw caller replay material to remain absent from storage.
        self.assertNotIn("invitation-recovery-key-0001", self.store_path.read_text(encoding="utf-8"))

    # Prove bounded attempts, expiry, explicit revocation, and retention cleanup.
    def test_attempt_expiry_revocation_and_cleanup(self):
        # Issue a reset token with a deliberately smaller bounded attempt budget.
        throttled = self.service.issue("password_reset", "bounded@example.invalid", max_attempts=2)
        # Charge the first subject mismatch without exposing the internal class.
        self.assert_generic_token_error(lambda: self.service.consume("password_reset", throttled["token"], subject="wrong@example.invalid"))
        # Charge the second subject mismatch without exposing the internal class.
        self.assert_generic_token_error(lambda: self.service.consume("password_reset", throttled["token"], subject="wrong@example.invalid"))
        # Reject the correct subject after the bounded budget is exhausted.
        self.assert_generic_token_error(lambda: self.service.consume("password_reset", throttled["token"], subject="bounded@example.invalid"))
        # Issue a short-lived magic-link token below the configured purpose ceiling.
        expiring = self.service.issue("magic_link", "expiring@example.invalid", ttl_seconds=1)
        # Advance beyond the absolute expiry.
        self.clock.advance(2)
        # Reject the expired bearer through the generic envelope.
        self.assert_generic_token_error(lambda: self.service.consume("magic_link", expiring["token"], subject="expiring@example.invalid"))
        # Issue an independent invitation token for explicit revocation.
        revoked = self.service.issue("invitation", "revoked@example.invalid")
        # Revoke the active opaque record exactly once.
        self.assertTrue(self.service.revoke(revoked["token_id"]))
        # Reject the revoked bearer through the generic envelope.
        self.assert_generic_token_error(lambda: self.service.consume("invitation", revoked["token"], subject="revoked@example.invalid"))
        # Advance beyond the fixed retention window after every terminal reference.
        self.clock.advance(one_time_tokens.TOKEN_RETENTION_SECONDS + one_time_tokens.TOKEN_PURPOSE_TTL_SECONDS["password_reset"] + 2)
        # Prune at least the expired, revoked, and exhausted historical rows.
        self.assertGreaterEqual(self.service.cleanup(), 2)

    # Prove concurrent callers observe one JSON winner across threads and processes.
    def test_json_exactly_once_across_threads_and_processes(self):
        # Issue one bearer for the bounded in-process thread race.
        threaded = self.service.issue("password_reset", "threaded@example.invalid")

        # Attempt one thread-local consume and return only whether it won.
        def consume_thread(_index):
            # Start protected consumption so losing threads return false.
            try:
                # Attempt the exact same consume operation.
                self.service.consume("password_reset", threaded["token"], subject="threaded@example.invalid")
                # Report the single successful thread.
                return True
            # Convert the generic losing result into false.
            except ValidationError as error:
                # Require every loser to receive only the generic public reason.
                self.assertEqual(error.details, one_time_tokens.INVALID_TOKEN_DETAILS)
                # Report a safely rejected replay or race loser.
                return False

        # Run eight bounded concurrent attempts against the same JSON document.
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Materialize every result so worker exceptions fail the test.
            thread_results = list(executor.map(consume_thread, range(8)))
        # Require exactly one successful thread.
        self.assertEqual(sum(thread_results), 1)
        # Issue one independent bearer for the cross-process JSON race.
        process_issued = self.service.issue("invitation", "process@example.invalid")
        # Build one synthetic serializable worker packet.
        worker_packet = (str(self.store_path), TEST_DIGEST_KEY, self.clock(), "invitation", process_issued["token"], "process@example.invalid")
        # Run six attempts through two independent operating-system processes.
        with ProcessPoolExecutor(max_workers=2) as executor:
            # Materialize every process result so cross-process exceptions surface.
            process_results = list(executor.map(_json_consume_worker, [worker_packet] * 6))
        # Require exactly one successful process and five generic rejections.
        self.assertEqual(sum(process_results), 1)

    # Prove malformed initiation and weak service configuration fail closed without values.
    def test_malformed_inputs_and_weak_key_fail_closed(self):
        # Reject unknown purpose through the generic initiation envelope.
        self.assert_generic_request_error(lambda: self.service.issue("unknown", "subject@example.invalid"))
        # Reject an absent subject through the same initiation envelope.
        self.assert_generic_request_error(lambda: self.service.issue("invitation", "   "))
        # Reject an attempt policy above the configured ceiling.
        self.assert_generic_request_error(lambda: self.service.issue("invitation", "attempts@example.invalid", max_attempts=one_time_tokens.TOKEN_MAX_ATTEMPTS + 1))
        # Reject a lifetime above the fixed purpose policy.
        self.assert_generic_request_error(lambda: self.service.issue("magic_link", "ttl@example.invalid", ttl_seconds=one_time_tokens.TOKEN_PURPOSE_TTL_SECONDS["magic_link"] + 1))
        # Reject a weak keyed-digest configuration before any operation can mint a bearer.
        with self.assertRaises(RuntimeError):
            # Construct an isolated service with deliberately weak synthetic material.
            one_time_tokens.TokenService(store_path=self.store_path, digest_key="too-short")

    # Prove the inert v2 component and compatibility policy publish no consuming route.
    def test_inert_contract_and_compatibility_boundary(self):
        # Resolve the checked compatibility policy.
        policy_path = ROOT / "contracts" / "compatibility" / "one-time-tokens-infrastructure.json"
        # Resolve the component-only OpenAPI artifact.
        component_path = ROOT / "contracts" / "openapi" / "one-time-tokens.v2.yaml"
        # Parse the policy as inert checked data.
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        # Require every consuming or live authority to remain denied.
        self.assertTrue(policy["authorization"]["repository_merge_requires_separate_owner_approval"])
        # Require every capability other than the approval flag to remain false.
        self.assertTrue(all(value is False for key, value in policy["authorization"].items() if key != "repository_merge_requires_separate_owner_approval"))
        # Require the fixed purpose vocabulary and frozen v1 boundary.
        self.assertEqual(policy["purposes"], ["invitation", "email_verification", "password_reset", "magic_link"])
        # Require one separate policy envelope for every fixed purpose.
        self.assertEqual(set(policy["purpose_policies"]), set(policy["purposes"]))
        # Require each separate policy to publish its fixed positive default lifetime.
        self.assertTrue(all(details["default_ttl_seconds"] > 0 for details in policy["purpose_policies"].values()))
        # Require compatibility to preserve the frozen v1 API.
        self.assertTrue(policy["compatibility"]["api_v1_frozen"])
        # Read the component artifact without parsing or activating it.
        component_text = component_path.read_text(encoding="utf-8")
        # Require an explicitly empty path map and no concrete API route.
        self.assertIn("paths: {}", component_text)
        # Require no route string anywhere in the component-only contract.
        self.assertNotIn("/api/", component_text)
        # Parse the checked contract digest inventory.
        digests = json.loads((ROOT / "contracts" / "compatibility" / "contract-digests.json").read_text(encoding="utf-8"))
        # Compute the exact current component digest.
        actual_digest = hashlib.sha256(component_path.read_bytes()).hexdigest()
        # Require the current component artifact to match its checked digest exactly.
        self.assertEqual(digests["contracts/openapi/one-time-tokens.v2.yaml"], actual_digest)
