"""Focused provider-free tests for transactional-mail safety and lifecycle policy. (TEST-090)"""

# Import JSON parsing so tests can inspect persistence without application helpers.
import json
# Import hashing so the published v2 contract is pinned in the compatibility inventory.
import hashlib
# Import temporary directories so every case owns isolated provider state.
import tempfile
# Import threading so duplicate claims are proven under concurrent callers.
import threading
# Import unittest for repository-standard focused assertions.
import unittest
# Import paths for isolated state documents.
from pathlib import Path

# Import the public conflict error used for changed-meaning idempotency assertions.
from casino.errors import ConflictError, RateLimitError
# Import startup configuration for the public digest-key guard proof.
from casino import config
# Import the mail state machine and safe transport classifications under test.
from casino.core.mail import AmbiguousDeliveryError, BRAND_NAME, MailService, RetryableDeliveryError, TEMPLATES

# Supply a test-only key that exceeds the public strength floor and is never logged.
TEST_DIGEST_KEY = "mail-test-digest-key-" + ("x" * 32)
# Supply a synthetic non-routable recipient used only in process memory.
TEST_RECIPIENT = "mail-test@example.invalid"
# Supply a synthetic bearer that must never reach durable state or receipts.
TEST_TOKEN = "synthetic-bearer-value"


# Capture transient messages and optionally raise one safe provider classification.
class RecordingTransport:
    # Configure the optional failure and a thread-safe call counter.
    def __init__(self, failure=None):
        # Store the fixed failure object without provider content.
        self.failure = failure
        # Collect transient messages for rendering assertions only.
        self.messages = []
        # Protect the call collection during the concurrency test.
        self.lock = threading.Lock()

    # Record one invocation and produce the configured safe outcome.
    def send(self, message: dict) -> None:
        # Serialize collection so duplicate calls cannot be hidden by a race.
        with self.lock:
            # Retain one transient copy inside the test process only.
            self.messages.append(dict(message))
        # Raise the configured classification after recording the attempt.
        if self.failure is not None:
            # Preserve the exact safe exception type used by the service.
            raise self.failure


# Prove safety, idempotency, retry, suppression, rendering, and diagnostics without network access.
class MailServiceTests(unittest.TestCase):
    # Prove every governed locale uses the single reviewed TiltSeven subject identity.
    def test_subjects_use_the_active_brand_name(self):
        # Require the configured subject identity to match the browser application's active brand.
        self.assertEqual(BRAND_NAME, "TiltSeven")
        # Exercise both installed locale template collections.
        for locale, templates in TEMPLATES.items():
            # Require every authorized purpose to include the canonical brand and exclude the retired product label.
            for purpose, (subject, _copy) in templates.items():
                # Keep failures self-describing without exposing recipient, bearer, or provider material.
                self.assertIn(BRAND_NAME, subject, (locale, purpose, subject))
                # Reject stale subject identity after the coordinated browser and mail rebrand.
                self.assertNotIn("Casino Simulator", subject, (locale, purpose, subject))

    # Allocate one isolated state document and deterministic clock per test.
    def setUp(self):
        # Own a removable temporary root for the duration of the case.
        self.temp_dir = tempfile.TemporaryDirectory()
        # Place state below the isolated root.
        self.state_path = Path(self.temp_dir.name) / "mail.json"
        # Keep a mutable deterministic epoch for rate, retry, and retention transitions.
        self.now = [1_800_000_000.0]

    # Remove the isolated state root after each case.
    def tearDown(self):
        # Release every file created by the focused test.
        self.temp_dir.cleanup()

    # Build one explicitly configured service without a live provider adapter.
    def service(self, *, transport=None, enabled=True, network_enabled=True, **overrides):
        # Assemble secure test-only defaults that satisfy readiness.
        values = {
            "state_path": self.state_path,
            "enabled": enabled,
            "network_enabled": network_enabled,
            "provider": "postmark",
            "digest_key": TEST_DIGEST_KEY,
            "canonical_origin": "https://casino.example.invalid",
            "from_address": "security@casino.example.invalid",
            "sending_domain": "casino.example.invalid",
            "provider_token": "synthetic-provider-token",
            "transport": transport or RecordingTransport(),
            "epoch_clock": lambda: self.now[0],
        }
        # Apply the focused policy override requested by the case.
        values.update(overrides)
        # Return a fresh service instance over the shared isolated state path.
        return MailService(**values)

    # Prove disabled and release-held submissions cannot invoke a transport or leak content.
    def test_dual_gate_is_inert_and_receipt_is_secret_free(self):
        # Build an explicit disabled configuration with a transport that would reveal invocation.
        disabled_transport = RecordingTransport()
        # Submit through the repository feature-disabled state.
        disabled = self.service(transport=disabled_transport, enabled=False).submit("invitation", TEST_RECIPIENT, token=TEST_TOKEN, idempotency_key="disabled-idempotency-key")
        # Confirm no provider boundary was reached and the safe status is explicit.
        self.assertEqual((disabled["status"], len(disabled_transport.messages)), ("disabled", 0))
        # Build an enabled but independently release-held configuration.
        held_transport = RecordingTransport()
        # Submit through the separate network-release hold.
        held = self.service(transport=held_transport, network_enabled=False).submit("password_reset", TEST_RECIPIENT, token=TEST_TOKEN, idempotency_key="release-held-idempotency")
        # Confirm the second gate also prevents all provider access.
        self.assertEqual((held["status"], len(held_transport.messages)), ("release_held", 0))
        # Read the exact serialized state to detect accidental sensitive persistence.
        serialized = self.state_path.read_text(encoding="utf-8")
        # Require every raw sensitive value and tokened URL to remain absent.
        self.assertNotIn(TEST_RECIPIENT, serialized)
        # Require the bearer to remain absent from durable state.
        self.assertNotIn(TEST_TOKEN, serialized)
        # Require the receipt to omit links, recipients, tokens, digests, provider, and secrets.
        self.assertEqual(set(held), {"delivery_id", "purpose", "status", "attempts", "next_retry_at"})

    # Prove same-key replays and concurrent submissions make one provider attempt only.
    def test_atomic_idempotency_allows_one_transport_attempt(self):
        # Share one recording transport across service instances and threads.
        transport = RecordingTransport()
        # Build two services representing concurrent workers over one provider-backed document.
        services = [self.service(transport=transport), self.service(transport=transport)]
        # Collect safe receipts from each worker.
        receipts = []

        # Submit the exact same caller request from one worker.
        def submit(service):
            # Append the secret-free result after its atomic claim resolves.
            receipts.append(service.submit("email_verification", TEST_RECIPIENT, token=TEST_TOKEN, idempotency_key="concurrent-idempotency-key"))

        # Create both worker threads before starting either.
        threads = [threading.Thread(target=submit, args=(service,)) for service in services]
        # Start both callers against the same state document.
        for thread in threads:
            # Begin one concurrent claim.
            thread.start()
        # Wait for both bounded local calls to finish.
        for thread in threads:
            # Join without any external listener or provider wait.
            thread.join(timeout=5)
        # Require both callers to receive the same opaque delivery identifier.
        self.assertEqual(len({receipt["delivery_id"] for receipt in receipts}), 1)
        # Require exactly one transient provider invocation.
        self.assertEqual(len(transport.messages), 1)
        # Permit the losing concurrent caller to observe the in-flight claim without waiting.
        self.assertTrue({receipt["status"] for receipt in receipts}.issubset({"sending", "sent"}))
        # Replay after both workers finish to read the stable terminal result.
        terminal = services[0].submit("email_verification", TEST_RECIPIENT, token=TEST_TOKEN, idempotency_key="concurrent-idempotency-key")
        # Require the durable result to be sent with no additional provider call.
        self.assertEqual((terminal["status"], len(transport.messages)), ("sent", 1))

    # Prove one caller key cannot silently change request meaning.
    def test_changed_meaning_idempotency_is_rejected(self):
        # Build one ready provider-free service.
        service = self.service()
        # Establish the caller key with its first stable request.
        service.submit("magic_link", TEST_RECIPIENT, token=TEST_TOKEN, idempotency_key="stable-idempotency-key")
        # Reuse the key with a different purpose and require a conflict.
        with self.assertRaises(ConflictError):
            # Attempt a changed-meaning replay without a second provider call.
            service.submit("password_reset", TEST_RECIPIENT, token=TEST_TOKEN, idempotency_key="stable-idempotency-key")

    # Prove known retryable failures back off and do not attempt early.
    def test_retry_is_bounded_and_due_time_enforced(self):
        # Configure a transport that reports a known non-accepted transient failure.
        transport = RecordingTransport(RetryableDeliveryError("temporary"))
        # Limit the test to two attempts with a deterministic ten-second base.
        service = self.service(transport=transport, max_attempts=2, retry_base_seconds=10)
        # Submit the first attempt and capture its schedule.
        first = service.submit("password_reset", TEST_RECIPIENT, token=TEST_TOKEN, idempotency_key="retry-idempotency-key")
        # Require one provider call and a scheduled retry.
        self.assertEqual((first["status"], len(transport.messages)), ("retry_wait", 1))
        # Replay before due time without another provider attempt.
        early = service.submit("password_reset", TEST_RECIPIENT, token=TEST_TOKEN, idempotency_key="retry-idempotency-key")
        # Require the early replay to preserve the schedule and call count.
        self.assertEqual((early["next_retry_at"], len(transport.messages)), (first["next_retry_at"], 1))
        # Advance to the exact due time.
        self.now[0] = float(first["next_retry_at"])
        # Retry the exact stable request.
        final = service.submit("password_reset", TEST_RECIPIENT, token=TEST_TOKEN, idempotency_key="retry-idempotency-key")
        # Require retry exhaustion after the bounded second attempt.
        self.assertEqual((final["status"], final["attempts"], len(transport.messages)), ("failed", 2, 2))

    # Prove ambiguous provider results freeze against automatic duplicates.
    def test_ambiguous_result_never_retries(self):
        # Configure a transport whose acceptance outcome is unknown.
        transport = RecordingTransport(AmbiguousDeliveryError("unknown"))
        # Build one ready service with that test transport.
        service = self.service(transport=transport)
        # Submit once through the ambiguous boundary.
        first = service.submit("invitation", TEST_RECIPIENT, token=TEST_TOKEN, idempotency_key="ambiguous-idempotency")
        # Replay the exact caller request.
        replay = service.submit("invitation", TEST_RECIPIENT, token=TEST_TOKEN, idempotency_key="ambiguous-idempotency")
        # Require the operator-reconciliation state and exactly one provider attempt.
        self.assertEqual((first["status"], replay["status"], len(transport.messages)), ("uncertain", "uncertain", 1))

    # Prove suppressions block future delivery and expose counts only.
    def test_suppression_blocks_delivery_and_diagnostics_are_aggregate(self):
        # Create a ready service and record an internally verified bounce.
        transport = RecordingTransport()
        # Share the transport for the later no-call assertion.
        service = self.service(transport=transport)
        # Persist only the keyed suppression metadata.
        service.record_suppression(TEST_RECIPIENT, "bounced")
        # Submit a new purpose for the suppressed recipient.
        receipt = service.submit("email_verification", TEST_RECIPIENT, token=TEST_TOKEN, idempotency_key="suppressed-idempotency")
        # Require a terminal suppression without provider access.
        self.assertEqual((receipt["status"], len(transport.messages)), ("suppressed", 0))
        # Read the secret-free Admin readiness diagnostic.
        diagnostic = service.readiness()
        # Require one aggregate suppression and no identifiers.
        self.assertEqual(diagnostic["suppressed_recipients"], 1)
        # Serialize the response to prove no raw recipient or keyed digest appears.
        self.assertNotIn(TEST_RECIPIENT, json.dumps(diagnostic))

    # Prove the per-recipient window rejects excess first submissions.
    def test_per_recipient_rate_limit(self):
        # Build one service that allows one new submission per window.
        service = self.service(rate_limit=1)
        # Consume the permitted slot.
        service.submit("invitation", TEST_RECIPIENT, token=TEST_TOKEN, idempotency_key="rate-first-idempotency")
        # Require a different caller key for the same recipient to be rejected.
        with self.assertRaises(RateLimitError):
            # Attempt a second purpose inside the same window.
            service.submit("magic_link", TEST_RECIPIENT, token="second-synthetic-token", idempotency_key="rate-second-idempotency")

    # Prove malformed structural state is not normalized or overwritten.
    def test_malformed_state_is_preserved_for_recovery(self):
        # Write a structurally invalid but syntactically valid source document.
        original = '{"schema_version":"unexpected","deliveries":"do-not-discard"}'
        # Persist the exact malformed source for comparison.
        self.state_path.write_text(original, encoding="utf-8")
        # Require submission to fail before destructive normalization.
        with self.assertRaises(RuntimeError):
            # Attempt one submission through the malformed state.
            self.service().submit("invitation", TEST_RECIPIENT, token=TEST_TOKEN, idempotency_key="malformed-idempotency")
        # Require the original bytes to remain unchanged.
        self.assertEqual(self.state_path.read_text(encoding="utf-8"), original)

    # Prove fixed EN/RU semantic templates and secret-free receipts.
    def test_templates_are_accessible_bilingual_and_links_are_transient(self):
        # Capture both locale variants in process memory.
        transport = RecordingTransport()
        # Build one ready service with a two-message rate allowance.
        service = self.service(transport=transport, rate_limit=2)
        # Submit the English invitation.
        english = service.submit("invitation", TEST_RECIPIENT, token=TEST_TOKEN, idempotency_key="english-template-key", locale="en-US")
        # Submit the Russian reset message.
        russian = service.submit("password_reset", TEST_RECIPIENT, token="russian-synthetic-token", idempotency_key="russian-template-key", locale="ru-RU")
        # Require semantic HTML landmarks and a language declaration for both messages.
        self.assertTrue(all("<main>" in message["html_body"] and "<h1>" in message["html_body"] and "<a href=" in message["html_body"] for message in transport.messages))
        # Require both plain-text alternatives to carry their transient canonical link.
        self.assertTrue(all("https://casino.example.invalid/" in message["text_body"] for message in transport.messages))
        # Require the Russian message to retain its governed locale.
        self.assertIn('lang="ru-RU"', transport.messages[1]["html_body"])
        # Require both public receipts to omit bearer URLs.
        self.assertNotIn("link", english)
        # Require the second receipt to omit bearer URLs too.
        self.assertNotIn("link", russian)

    # Prove readiness differentiates disabled, misconfigured, release-held, and ready states.
    def test_readiness_states_are_distinct_and_secret_free(self):
        # Read the intentional disabled state.
        disabled = self.service(enabled=False).readiness()
        # Read an enabled configuration missing sender identity.
        misconfigured = self.service(from_address="").readiness()
        # Read a complete configuration held from network release.
        held = self.service(network_enabled=False).readiness()
        # Read a complete test configuration.
        ready = self.service().readiness()
        # Require exact distinct low-cardinality states.
        self.assertEqual([disabled["status"], misconfigured["status"], held["status"], ready["status"]], ["disabled", "misconfigured", "release_held", "ready"])
        # Serialize every diagnostic and require credential material to remain absent.
        self.assertNotIn("synthetic-provider-token", json.dumps([disabled, misconfigured, held, ready]))

    # Prove the additive v2 contract is checksum-pinned and publishes no consumer route.
    def test_contract_digest_and_route_boundary(self):
        # Resolve the repository root from this focused test module.
        root = Path(__file__).resolve().parents[1]
        # Read the checked digest inventory.
        digests = json.loads((root / "contracts" / "compatibility" / "contract-digests.json").read_text(encoding="utf-8"))
        # Resolve the exact additive Admin-only contract path.
        contract_path = root / "contracts" / "openapi" / "transactional-mail.v2.yaml"
        # Require the checked digest to match the exact current contract bytes.
        self.assertEqual(hashlib.sha256(contract_path.read_bytes()).hexdigest(), digests["contracts/openapi/transactional-mail.v2.yaml"])
        # Read contract text for explicit route-boundary assertions.
        contract_text = contract_path.read_text(encoding="utf-8")
        # Require the sole published path to be the Admin readiness diagnostic.
        self.assertEqual(contract_text.count("  /api/v2/"), 1)
        # Require no send, bounce, callback, invitation, or recovery consumer path.
        self.assertNotIn("/api/v2/mail/", contract_text)

    # Prove public startup rejects the committed mail digest default independently.
    def test_public_startup_rejects_known_mail_digest_key(self):
        # Build otherwise hardened synthetic public settings.
        environment = {
            "CASINO_BOOTSTRAP_ADMIN_EMAIL": "mail-startup@example.invalid",
            "CASINO_BOOTSTRAP_ADMIN_PASSWORD": "synthetic-mail-startup-password",
            "CASINO_TOKEN_DIGEST_KEY": "synthetic-startup-token-digest-key-material",
            "CASINO_MAIL_DIGEST_KEY": config.LOCAL_MAIL_DIGEST_KEY,
        }
        # Require the mail-key default alone to block a non-loopback startup.
        with self.assertRaises(RuntimeError):
            # Validate without mutating the actual process environment.
            config.validate_bootstrap_for_startup("0.0.0.0", environment)
        # Replace only the mail key with independent synthetic material.
        environment["CASINO_MAIL_DIGEST_KEY"] = "synthetic-startup-mail-digest-key-material"
        # Require the otherwise valid public mapping to pass the startup guard.
        config.validate_bootstrap_for_startup("0.0.0.0", environment)

    # Prove terminal delivery and suppression metadata is removed only after retention.
    def test_terminal_retention_cleanup_is_bounded(self):
        # Create one disabled terminal delivery without provider access.
        service = self.service(enabled=False, retention_seconds=86400)
        # Persist the first terminal record.
        service.submit("invitation", TEST_RECIPIENT, token=TEST_TOKEN, idempotency_key="retention-first-idempotency")
        # Persist one keyed suppression record at the same epoch.
        service.record_suppression("retention@example.invalid", "bounced")
        # Advance beyond the enforced one-day minimum retention.
        self.now[0] += 86401
        # Submit a different recipient to trigger cleanup inside an atomic mutation.
        service.submit("magic_link", "new-retention@example.invalid", token="new-retention-token", idempotency_key="retention-second-idempotency")
        # Read the resulting persistence document.
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        # Require only the newly created terminal delivery to remain.
        self.assertEqual(len(state["deliveries"]), 1)
        # Require the expired suppression metadata to be removed.
        self.assertEqual(state["suppressions"], {})


# Run the focused suite directly for local developer validation.
if __name__ == "__main__":
    # Exit nonzero through unittest when any safety assertion fails.
    unittest.main()
