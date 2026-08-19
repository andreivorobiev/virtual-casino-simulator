# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Provider-free acceptance for verified-email pending enrollment. (TEST-171)"""

# Import JSON for exact durable-state inspection.
import json
# Import regular expressions to extract only an ephemeral synthetic bearer from fake mail.
import re
# Import timezone-aware arithmetic for crash-window and retention tests.
from datetime import datetime, timedelta, timezone
# Import temporary directories so tests never touch repository runtime data.
import tempfile
# Import unittest for repository-standard focused assertions.
import unittest
# Import patching for deterministic post-credit recovery simulation.
from unittest.mock import patch
# Import portable paths for isolated provider documents.
from pathlib import Path

# Import configuration only for current terms and configured starting-balance assertions.
from casino import config
# Import canonical identity, ledger, enrollment, storage, and token services under test.
from casino.core import auth, ledger, one_time_tokens, pending_enrollment, players, storage
# Import the approved transactional-mail boundary with an injected transport.
from casino.core.mail import MailService
# Import generic verification and fixed abuse-control rejections.
from casino.errors import ConflictError, RateLimitError, ValidationError

# Use synthetic digest material unrelated to deployment credentials.
TEST_TOKEN_KEY = "verified-email-token-test-key-" + ("t" * 32)
# Use independent synthetic mail and enrollment digest material.
TEST_MAIL_KEY = "verified-email-mail-test-key-" + ("m" * 32)
# Use a reserved non-routable mailbox only inside isolated test state.
TEST_EMAIL = "verified@example.invalid"
# Use one policy-compliant synthetic password that never enters fixtures.
TEST_PASSWORD = "Verified-Email-2026!"


# Capture transient verification mail without network or provider access.
class _Transport:
    # Initialize one in-memory message list.
    def __init__(self):
        # Retain synthetic messages only for the current test.
        self.messages = []

    # Accept one transient provider payload.
    def send(self, message: dict) -> None:
        # Store a detached test-only copy for bearer extraction.
        self.messages.append(dict(message))


# Model abrupt process termination without running ordinary exception cleanup blocks.
class _Crash(BaseException):
    # Carry no recipient, bearer, or durable identifier in the synthetic stop.
    pass


# Provide one mutable repository-format UTC clock for crash and retention boundaries.
class _Clock:
    # Initialize one deterministic synthetic instant.
    def __init__(self):
        # Retain an aware UTC datetime for exact duration arithmetic.
        self.current = datetime(2031, 2, 3, 4, 5, 6, tzinfo=timezone.utc)

    # Return the repository timestamp format expected by provider documents.
    def __call__(self):
        # Serialize milliseconds and the shared UTC suffix.
        return self.current.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    # Advance by one bounded test-owned duration.
    def advance(self, seconds: int) -> None:
        # Replace the current instant without relying on wall-clock sleeps.
        self.current += timedelta(seconds=seconds)


# Exercise identity absence, exactly-once funding, replay, cancellation, and recovery.
class VerifiedEmailEnrollmentTests(unittest.TestCase):
    # Build isolated canonical and supporting state before each case.
    def setUp(self):
        # Allocate one automatically cleaned test root.
        self.temp_directory = tempfile.TemporaryDirectory()
        # Resolve the portable root path once.
        self.root = Path(self.temp_directory.name)
        # Preserve production path seams before isolated mutation.
        self.original_users_path = auth.USERS_PATH
        # Preserve the canonical session path before isolated mutation.
        self.original_sessions_path = auth.SESSIONS_PATH
        # Redirect user state into the isolated root.
        auth.USERS_PATH = self.root / "auth" / "users.json"
        # Redirect session state into the isolated root.
        auth.SESSIONS_PATH = self.root / "auth" / "sessions.json"
        # Install an isolated JSON provider for players and ledger events.
        storage.set_provider_for_tests(storage.JsonStorageProvider(self.root / "provider"))
        # Capture provider-free mail in memory.
        self.transport = _Transport()
        # Freeze enrollment and token lifecycle time for deterministic recovery tests.
        self.clock = _Clock()
        # Build the approved mail service with explicit test-only ready gates.
        self.mail_service = MailService(state_path=self.root / "mail.json", enabled=True, network_enabled=True, provider="postmark", digest_key=TEST_MAIL_KEY, canonical_origin="https://casino.example.invalid", from_address="security@casino.example.invalid", sending_domain="casino.example.invalid", provider_token="synthetic-provider-token", transport=self.transport)
        # Build the purpose-bound token service over isolated state.
        self.token_service = one_time_tokens.TokenService(store_path=self.root / "tokens.json", digest_key=TEST_TOKEN_KEY, clock=self.clock, audit_sink=lambda level, event, fields: None)
        # Build the enabled test service without changing production defaults.
        self.service = pending_enrollment.PendingEnrollmentService(store_path=self.root / "pending.json", enabled=True, digest_key=TEST_MAIL_KEY, token_service=self.token_service, mail_service=self.mail_service, clock=self.clock, audit_sink=lambda event, **fields: None)

    # Restore global seams and remove isolated state after each case.
    def tearDown(self):
        # Restore the canonical user path.
        auth.USERS_PATH = self.original_users_path
        # Restore the canonical session path.
        auth.SESSIONS_PATH = self.original_sessions_path
        # Clear the injected player provider.
        storage.set_provider_for_tests(None)
        # Delete only the test-owned temporary root.
        self.temp_directory.cleanup()

    # Initiate one signup and return the ephemeral bearer from fake mail.
    def initiate(self, key: str = "verified-initiate-key-0001", client_reference: str = "verified-test-client") -> str:
        # Begin one pending signup through the complete provider-free composition.
        result = self.service.initiate(TEST_EMAIL, TEST_PASSWORD, "Verified Player", "en-US", config.GUEST_TERMS_VERSION, True, key, client_reference)
        # Require the fixed account-free public acknowledgement.
        self.assertEqual(result, {"status": "verification_pending"})
        # Require exactly one verification delivery.
        self.assertEqual(len(self.transport.messages), 1)
        # Extract the bearer only from transient fake mail.
        match = re.search(r"[?&]token=([^\s<]+)", self.transport.messages[0]["text_body"])
        # Require one canonical same-origin link.
        self.assertIsNotNone(match)
        # Return the bearer without writing it to a fixture.
        return match.group(1)

    # Extract one transient bearer by synthetic message index.
    def bearer(self, index: int) -> str:
        # Resolve the requested test-owned message.
        message = self.transport.messages[index]
        # Parse only its same-origin query bearer.
        match = re.search(r"[?&]token=([^\s<]+)", message["text_body"])
        # Require one bearer before returning it to the test.
        self.assertIsNotNone(match)
        # Return the ephemeral value without writing it to durable state.
        return match.group(1)

    # Prove verification is the first identity boundary and funding is exactly once.
    def test_pending_then_verified_activation_has_one_ledger_credit_and_no_session(self):
        # Begin one pending enrollment and capture its transient bearer.
        bearer = self.initiate()
        # Require no user account before verification.
        self.assertEqual(auth.load_users()["users"], [])
        # Require no email-enrollment player before verification.
        self.assertFalse(any(row.get("player_id", "").startswith("player_email_") for row in players.list_players()))
        # Require no session before verification.
        self.assertEqual(auth.load_sessions()["sessions"], [])
        # Consume the bearer and complete the recoverable activation.
        result = self.service.verify(bearer, TEST_EMAIL, "verified-complete-key-0001")
        # Require one identifier-free success receipt.
        self.assertEqual(result, {"status": "enrolled"})
        # Require one active first-party identity.
        user = auth.find_user_by_email(TEST_EMAIL)
        # Require verified active status and local ownership.
        self.assertEqual((user["status"], user["identity_provider"]), ("active", "local"))
        # Require the configured initial funds to be present after ledger credit.
        player = players.get_player(user["player_id"])
        # Require exact active funded wallet state.
        self.assertEqual((player["status"], player["balance"]), ("active", float(config.ACCOUNT_STARTING_BALANCE)))
        # Require one and only one funding ledger event.
        funding = [row for row in ledger.read_recent(user["player_id"], 20) if row.get("transaction_type") == "ACCOUNT_STARTING_BALANCE"]
        # Require the exact configured credit.
        self.assertEqual((len(funding), funding[0]["amount"]), (1, float(config.ACCOUNT_STARTING_BALANCE)))
        # Replay the lost response under the exact caller key.
        self.assertEqual(self.service.verify(bearer, TEST_EMAIL, "verified-complete-key-0001"), result)
        # Require replay not to duplicate funding.
        self.assertEqual(len([row for row in ledger.read_recent(user["player_id"], 20) if row.get("transaction_type") == "ACCOUNT_STARTING_BALANCE"]), 1)
        # Require verification never to create an implicit session.
        self.assertEqual(auth.load_sessions()["sessions"], [])
        # Read the terminal pending row only to prove credential and profile residue was removed.
        terminal = json.loads((self.root / "pending.json").read_text(encoding="utf-8"))["enrollments"][0]
        # Require terminal complete replay metadata to retain no raw recipient, password verifier, or profile fields.
        self.assertFalse({"email", "password_hash", "display_name", "locale", "terms_version"} & set(terminal))

    # Prove different-key initiation cannot enumerate an already-pending mailbox.
    def test_pending_recipient_lookup_returns_generic_without_second_delivery(self):
        # Begin one real pending enrollment and retain its sole transient delivery.
        self.initiate("verified-initiate-key-enumeration-0001")
        # Repeat the recipient lookup under a different key and otherwise changed valid request details.
        repeated = self.service.initiate(TEST_EMAIL, "Different-Verified-Email-2026!", "Different Player", "ru-RU", config.GUEST_TERMS_VERSION, True, "verified-initiate-key-enumeration-0002")
        # Require the exact same public acknowledgement rather than a pending-address conflict.
        self.assertEqual(repeated, {"status": "verification_pending"})
        # Require no second bearer delivery or parallel pending row.
        self.assertEqual((len(self.transport.messages), len(json.loads((self.root / "pending.json").read_text(encoding="utf-8"))["enrollments"])), (1, 1))

    # Prove resend suppression and provider throttling never replace the current valid bearer.
    def test_resend_suppression_is_generic_and_preserves_current_bearer(self):
        # Begin one pending enrollment and retain its delivered bearer.
        bearer = self.initiate("verified-initiate-key-resend-0001", "resend-initiate-client")
        # Reduce the source allowance only for this deterministic abuse-control test.
        with patch.object(config, "EMAIL_ENROLLMENT_RESEND_RATE_LIMIT", 1):
            # Suppress immediate address-only replacement inside the recipient cooldown.
            first = self.service.resend(TEST_EMAIL, "en-US", "verified-resend-key-0001", "resend-source-client")
            # Require the ordinary acknowledgement and no second delivery.
            self.assertEqual((first, len(self.transport.messages)), ({"status": "verification_pending"}, 1))
            # Require the same trusted source to consume its independent resend allowance.
            with self.assertRaises(RateLimitError):
                # Attempt another well-formed resend from the same source.
                self.service.resend(TEST_EMAIL, "en-US", "verified-resend-key-0002", "resend-source-client")
        # Force the existing mail boundary to reject any new recipient submission.
        self.mail_service.rate_limit = 1
        # Remove only the test cooldown so the provider-rate rollback path executes.
        with patch.object(config, "EMAIL_ENROLLMENT_RESEND_COOLDOWN_SECONDS", 0):
            # Request from a separate source so only provider throttling suppresses replacement.
            held = self.service.resend(TEST_EMAIL, "en-US", "verified-resend-key-0003", "resend-provider-client")
        # Require the same generic receipt and no second provider transport attempt.
        self.assertEqual((held, len(self.transport.messages)), ({"status": "verification_pending"}, 1))
        # Require the original bearer to remain valid and complete exactly once.
        self.assertEqual(self.service.verify(bearer, TEST_EMAIL, "verified-complete-key-resend-0001", "resend-verify-client"), {"status": "enrolled"})

    # Prove initiation and verification spraying consume independent trusted-source allowances.
    def test_initiate_and_verify_have_durable_source_rate_limits(self):
        # Reduce initiation allowance to one request for a deterministic test.
        with patch.object(config, "EMAIL_ENROLLMENT_INITIATE_RATE_LIMIT", 1):
            # Begin one valid pending enrollment under the bounded source.
            bearer = self.initiate("verified-initiate-key-rate-0001", "bounded-initiate-client")
            # Reject a second valid address from the same source without delivery.
            with self.assertRaises(RateLimitError):
                # Attempt a distinct recipient and caller key under the exhausted allowance.
                self.service.initiate("other@example.invalid", TEST_PASSWORD, "Other Player", "en-US", config.GUEST_TERMS_VERSION, True, "verified-initiate-key-rate-0002", "bounded-initiate-client")
        # Reduce verification allowance to one attempt for a deterministic token-spray test.
        with patch.object(config, "EMAIL_ENROLLMENT_VERIFY_RATE_LIMIT", 1):
            # Consume the sole allowance with an invalid bearer through the generic rejection.
            with self.assertRaises(ValidationError):
                # Submit a well-shaped invalid token against the real pending recipient.
                self.service.verify("invalid-verification-bearer", TEST_EMAIL, "verified-complete-key-rate-0001", "bounded-verify-client")
            # Reject a later attempt from the same trusted source before token classification.
            with self.assertRaises(RateLimitError):
                # Submit the real bearer only to prove the independent allowance is enforced.
                self.service.verify(bearer, TEST_EMAIL, "verified-complete-key-rate-0002", "bounded-verify-client")

    # Prove exact accepted replays bypass rate charging while distinct attempts remain bounded.
    def test_exact_replays_survive_rate_ceiling_and_successful_resend_replaces_once(self):
        # Limit each action to one distinct request for a strong replay proof.
        with patch.object(config, "EMAIL_ENROLLMENT_INITIATE_RATE_LIMIT", 1), patch.object(config, "EMAIL_ENROLLMENT_RESEND_RATE_LIMIT", 1), patch.object(config, "EMAIL_ENROLLMENT_VERIFY_RATE_LIMIT", 1), patch.object(config, "EMAIL_ENROLLMENT_RESEND_COOLDOWN_SECONDS", 0):
            # Create the sole pending enrollment and retain its predecessor bearer.
            predecessor = self.initiate("verified-initiate-key-replay-0001", "exact-initiate-source")
            # Replay the exact initiate request beyond its distinct-source ceiling.
            for _ in range(3):
                # Require stable acknowledgement without another delivery or allowance.
                self.assertEqual(self.service.initiate(TEST_EMAIL, TEST_PASSWORD, "Verified Player", "en-US", config.GUEST_TERMS_VERSION, True, "verified-initiate-key-replay-0001", "exact-initiate-source"), {"status": "verification_pending"})
            # Deliver one successful replacement after the zero-duration test cooldown.
            self.assertEqual(self.service.resend(TEST_EMAIL, "en-US", "verified-resend-key-replay-0001", "exact-resend-source"), {"status": "verification_pending"})
            # Capture the delivered promoted replacement.
            replacement = self.bearer(1)
            # Replay the exact resend beyond the source ceiling without another provider call.
            for _ in range(3):
                # Require the generic stable receipt on every replay.
                self.assertEqual(self.service.resend(TEST_EMAIL, "en-US", "verified-resend-key-replay-0001", "exact-resend-source"), {"status": "verification_pending"})
            # Require exactly the initial and one replacement delivery.
            self.assertEqual(len(self.transport.messages), 2)
            # Reject the predecessor only after the replacement was successfully promoted.
            with self.assertRaises(ValidationError):
                # Consume through the token boundary without mutating the enrollment claim.
                self.token_service.consume(pending_enrollment.PURPOSE, predecessor, subject=TEST_EMAIL)
            # Complete signup with the promoted bearer under the sole distinct verify allowance.
            self.assertEqual(self.service.verify(replacement, TEST_EMAIL, "verified-complete-key-replay-0001", "exact-verify-source"), {"status": "enrolled"})
            # Replay the completed response beyond the source ceiling without another side effect.
            for _ in range(3):
                # Require one stable identifier-free terminal receipt.
                self.assertEqual(self.service.verify(replacement, TEST_EMAIL, "verified-complete-key-replay-0001", "exact-verify-source"), {"status": "enrolled"})

    # Prove every durable delivery checkpoint can recover without duplicate mail or unusable bearer state.
    def test_delivery_crash_boundaries_reconcile_and_keep_emailed_bearer_usable(self):
        # Exercise the five governed boundaries independently.
        for index, phase in enumerate(("delivery_prepared", "candidate_prepared", "provider_recorded", "candidate_promoted", "delivery_finalized")):
            # Label failures by the exact durable boundary.
            with self.subTest(phase=phase):
                # Allocate isolated state and transport for this crash boundary.
                root = self.root / f"crash-{index}"
                # Freeze an independent lifecycle clock.
                clock = _Clock()
                # Capture only this boundary's transient delivery.
                transport = _Transport()
                # Build an isolated provider-free mail boundary.
                mail_service = MailService(state_path=root / "mail.json", enabled=True, network_enabled=True, provider="postmark", digest_key=TEST_MAIL_KEY, canonical_origin="https://casino.example.invalid", from_address="security@casino.example.invalid", sending_domain="casino.example.invalid", provider_token="synthetic-provider-token", transport=transport)
                # Build an isolated token boundary on the same deterministic clock.
                token_service = one_time_tokens.TokenService(store_path=root / "tokens.json", digest_key=TEST_TOKEN_KEY, clock=clock, audit_sink=lambda level, event, fields: None)
                # Arm one abrupt stop at the selected durable checkpoint.
                armed = {"value": True}

                # Raise outside ordinary Exception cleanup exactly once.
                def crash_hook(observed: str) -> None:
                    # Stop only at the selected phase and leave later recovery unhooked.
                    if armed["value"] and observed == phase:
                        # Disarm before modelling process loss.
                        armed["value"] = False
                        # Abort without executing ordinary cleanup handlers.
                        raise _Crash()

                # Compose the crash-injected enrollment service.
                service = pending_enrollment.PendingEnrollmentService(store_path=root / "pending.json", enabled=True, digest_key=TEST_MAIL_KEY, token_service=token_service, mail_service=mail_service, clock=clock, audit_sink=lambda event, **fields: None, phase_hook=crash_hook)
                # Use one unique synthetic mailbox and exact caller key.
                email = f"crash-{index}@example.invalid"
                # Stop at the exact selected durable boundary.
                with self.assertRaises(_Crash):
                    # Begin the pending enrollment without catching abrupt process loss.
                    service.initiate(email, TEST_PASSWORD, "Crash Player", "en-US", config.GUEST_TERMS_VERSION, True, f"verified-initiate-crash-key-{index:04d}", f"crash-source-{index}")
                # Replay immediately while a fresh pre-provider generation may still be owned elsewhere.
                self.assertEqual(service.initiate(email, TEST_PASSWORD, "Crash Player", "en-US", config.GUEST_TERMS_VERSION, True, f"verified-initiate-crash-key-{index:04d}", f"crash-source-{index}"), {"status": "verification_pending"})
                # Expire only ambiguous pre-provider ownership before another recovery attempt.
                if phase in {"delivery_prepared", "candidate_prepared"}:
                    # Cross the bounded recovery window deterministically.
                    clock.advance(config.EMAIL_ENROLLMENT_DELIVERY_RECOVERY_SECONDS + 1)
                    # Resume the exact request, which safely creates the first provider delivery.
                    self.assertEqual(service.initiate(email, TEST_PASSWORD, "Crash Player", "en-US", config.GUEST_TERMS_VERSION, True, f"verified-initiate-crash-key-{index:04d}", f"crash-source-{index}"), {"status": "verification_pending"})
                # Require exactly one provider delivery across crash and recovery.
                self.assertEqual(len(transport.messages), 1)
                # Extract the only emailed bearer from transient fake mail.
                match = re.search(r"[?&]token=([^\s<]+)", transport.messages[0]["text_body"])
                # Require a usable same-origin bearer after reconciliation.
                self.assertIsNotNone(match)
                # Complete activation with the emailed bearer after any delivered/promoted lost response.
                self.assertEqual(service.verify(match.group(1), email, f"verified-complete-crash-key-{index:04d}", f"crash-verify-{index}"), {"status": "enrolled"})

    # Prove cancellation requires the exact current delivered bearer and bounds every distinct probe.
    def test_cancel_ownership_rejects_malformed_wrong_candidate_stale_absent_and_cross_recipient(self):
        # Deliver one pending bearer for the target recipient.
        predecessor = self.initiate("verified-initiate-cancel-owner-0001", "cancel-owner-initiate-a")
        # Create a second pending recipient and capture its independent bearer.
        self.service.initiate("other-cancel@example.invalid", TEST_PASSWORD, "Other Cancel", "en-US", config.GUEST_TERMS_VERSION, True, "verified-initiate-cancel-owner-0002", "cancel-owner-initiate-b")
        # Extract the second recipient's transient bearer.
        cross_recipient = self.bearer(1)
        # Prepare one non-consumable candidate directly to prove it grants no cancellation ownership.
        current_row = json.loads((self.root / "pending.json").read_text(encoding="utf-8"))["enrollments"][0]
        # Bind the candidate to the target's exact active predecessor.
        candidate = self.token_service.prepare_candidate(pending_enrollment.PURPOSE, TEST_EMAIL, current_row["token_id"])
        # Reject the unpromoted candidate through the generic cancellation envelope.
        with self.assertRaises(ValidationError):
            # Attempt cancellation without provider delivery or promotion.
            self.service.cancel(candidate["token"], TEST_EMAIL, "verified-cancel-candidate-0001", "cancel-candidate-source")
        # Discard only the test-owned candidate so normal resend can proceed.
        self.assertTrue(self.token_service.discard_candidate(candidate["token_id"]))
        # Charge malformed, wrong, absent, and cross-recipient attempts against one bounded source.
        with patch.object(config, "EMAIL_ENROLLMENT_CANCEL_RATE_LIMIT", 4):
            # Submit four distinct ownership failures under the same trusted source.
            for token, email, key in (("", TEST_EMAIL, "verified-cancel-probe-key-0001"), ("wrong-cancel-bearer", TEST_EMAIL, "verified-cancel-probe-key-0002"), (predecessor, "absent-cancel@example.invalid", "verified-cancel-probe-key-0003"), (cross_recipient, TEST_EMAIL, "verified-cancel-probe-key-0004")):
                # Require each lookup class to remain generic.
                with self.assertRaises(ValidationError):
                    # Submit the distinct bounded probe.
                    self.service.cancel(token, email, key, "cancel-probe-source")
            # Reject the next attempt at the shared rate boundary before token classification.
            with self.assertRaises(RateLimitError):
                # Reuse the actual current bearer only to prove rate enforcement is prior to ownership result.
                self.service.cancel(predecessor, TEST_EMAIL, "verified-cancel-probe-key-0005", "cancel-probe-source")
        # Deliver and promote one replacement under an independent source.
        with patch.object(config, "EMAIL_ENROLLMENT_RESEND_COOLDOWN_SECONDS", 0):
            # Replace only after provider acceptance.
            self.assertEqual(self.service.resend(TEST_EMAIL, "en-US", "verified-cancel-owner-resend-0001", "cancel-owner-resend"), {"status": "verification_pending"})
        # Extract the replacement current bearer.
        replacement = self.bearer(2)
        # Reject the stale predecessor after successful replacement.
        with self.assertRaises(ValidationError):
            # Attempt terminalization with the superseded ownership proof.
            self.service.cancel(predecessor, TEST_EMAIL, "verified-cancel-stale-key-0001", "cancel-stale-source")
        # Cancel with the exact current bearer under a one-attempt ceiling.
        with patch.object(config, "EMAIL_ENROLLMENT_CANCEL_RATE_LIMIT", 1):
            # Complete terminal cancellation exactly once.
            self.assertEqual(self.service.cancel(replacement, TEST_EMAIL, "verified-cancel-current-key-0001", "cancel-current-source"), {"status": "cancelled"})
            # Replay the exact terminal request beyond the ceiling without requiring the revoked bearer active.
            for _ in range(3):
                # Require the stable terminal receipt and no additional rate charge.
                self.assertEqual(self.service.cancel(replacement, TEST_EMAIL, "verified-cancel-current-key-0001", "cancel-current-source"), {"status": "cancelled"})

    # Prove a predecessor authorized before concurrent resend cannot cancel the promoted replacement.
    def test_cancel_authorization_rechecks_generation_after_concurrent_resend(self):
        # Deliver the initial ownership bearer.
        predecessor = self.initiate("verified-initiate-cancel-race-0001", "cancel-race-initiate")
        # Arm one nested replacement exactly after cancellation authorizes the predecessor.
        armed = {"value": True}

        # Advance the delivery generation inside the test-only cancellation race boundary.
        def race_hook(phase: str) -> None:
            # Trigger exactly once after active-bearer authorization.
            if armed["value"] and phase == "cancel_authorized":
                # Disarm before nested delivery checkpoints execute.
                armed["value"] = False
                # Promote one replacement while the outer cancel still holds its old generation snapshot.
                with patch.object(config, "EMAIL_ENROLLMENT_RESEND_COOLDOWN_SECONDS", 0):
                    # Complete the nested replacement through normal service boundaries.
                    self.service.resend(TEST_EMAIL, "en-US", "verified-cancel-race-resend-0001", "cancel-race-resend")

        # Install the provider-free race hook after initial delivery.
        self.service.phase_hook = race_hook
        # Reject the predecessor because the terminal transaction observes the advanced generation/token.
        with self.assertRaises(ValidationError):
            # Attempt cancellation with the stale but initially authorized predecessor.
            self.service.cancel(predecessor, TEST_EMAIL, "verified-cancel-race-key-0001", "cancel-race-source")
        # Extract the replacement promoted during the authorization race.
        replacement = self.bearer(1)
        # Require the enrollment to remain pending on the replacement generation.
        row = json.loads((self.root / "pending.json").read_text(encoding="utf-8"))["enrollments"][0]
        # Bind non-resurrection and exact generation advancement.
        self.assertEqual((row["status"], row["delivery_generation"]), ("pending", 2))
        # Cancel successfully only with the current replacement bearer.
        self.assertEqual(self.service.cancel(replacement, TEST_EMAIL, "verified-cancel-race-key-0002", "cancel-race-source-current"), {"status": "cancelled"})

    # Prove the browser exposes cancellation only with a bearer and reuses its exact lost-response key.
    def test_cancel_frontend_requires_bearer_and_stable_action_key(self):
        # Read the governed frontend source without launching a browser listener.
        source = (Path(__file__).resolve().parents[1] / "web" / "views" / "verification.js").read_text(encoding="utf-8")
        # Require the cancel control to stay disabled before an email-link bearer arrives.
        self.assertIn("const disabled = emailVerificationBearer ? '' : 'disabled';", source)
        self.assertIn('data-testid="email-verification-cancel" type="button" ${disabled}', source)
        # Require the exact bearer in the cancellation request body.
        self.assertIn("api('/api/v2/auth/signup/cancel'", source)
        self.assertIn("token: emailVerificationBearer,", source)
        # Require a domain-separated stable caller key rather than a fresh click UUID.
        self.assertIn("emailVerificationIdempotency(emailVerificationBearer, 'cancel')", source)
        # Require the replay key to clear only after acknowledged terminal success.
        self.assertIn("await emailVerificationStorageKey(emailVerificationBearer, 'cancel'),", source)
        # Require successful verification to remove its independent terminal replay key too.
        self.assertIn("sessionStorageRef.removeItem(await emailVerificationStorageKey(emailVerificationBearer));", source)

    # Prove cancellation wins against every delivery phase and cannot be resurrected by a stale callback.
    def test_cancel_at_each_delivery_phase_is_terminal_and_revokes_every_token(self):
        # Cover replacement prepare, candidate, provider-confirmed, promoted, and finalized states.
        for index, phase in enumerate(("delivery_prepared", "candidate_prepared", "provider_recorded", "candidate_promoted", "delivery_finalized")):
            # Label any lifecycle regression by exact checkpoint.
            with self.subTest(phase=phase):
                # Allocate independent provider documents.
                root = self.root / f"cancel-{index}"
                # Freeze lifecycle time for deterministic phase ownership.
                clock = _Clock()
                # Capture any transient mail locally.
                transport = _Transport()
                # Compose isolated mail and token boundaries.
                mail_service = MailService(state_path=root / "mail.json", enabled=True, network_enabled=True, provider="postmark", digest_key=TEST_MAIL_KEY, canonical_origin="https://casino.example.invalid", from_address="security@casino.example.invalid", sending_domain="casino.example.invalid", provider_token="synthetic-provider-token", transport=transport)
                # Build an isolated purpose-bound token service.
                token_service = one_time_tokens.TokenService(store_path=root / "tokens.json", digest_key=TEST_TOKEN_KEY, clock=clock, audit_sink=lambda level, event, fields: None)
                # Compose the service without a crash hook for its initial delivered ownership bearer.
                service = pending_enrollment.PendingEnrollmentService(store_path=root / "pending.json", enabled=True, digest_key=TEST_MAIL_KEY, token_service=token_service, mail_service=mail_service, clock=clock, audit_sink=lambda event, **fields: None)
                # Use one unique non-routable recipient.
                email = f"cancel-{index}@example.invalid"
                # Deliver the predecessor bearer that proves mailbox ownership during replacement races.
                self.assertEqual(service.initiate(email, TEST_PASSWORD, "Cancel Player", "en-US", config.GUEST_TERMS_VERSION, True, f"verified-initiate-cancel-key-{index:04d}", f"cancel-source-{index}"), {"status": "verification_pending"})
                # Extract the predecessor from transient fake mail only.
                predecessor_match = re.search(r"[?&]token=([^\s<]+)", transport.messages[0]["text_body"])
                # Require one current delivered predecessor.
                self.assertIsNotNone(predecessor_match)
                # Arm one abrupt stop for the replacement delivery only.
                armed = {"value": True}

                # Stop exactly once without ordinary stack cleanup.
                def crash_hook(observed: str) -> None:
                    # Match only the selected phase.
                    if armed["value"] and observed == phase:
                        # Prevent a second synthetic stop during recovery.
                        armed["value"] = False
                        # Model abrupt process termination.
                        raise _Crash()

                # Install the test-only hook only after the predecessor is delivered.
                service.phase_hook = crash_hook
                # Stop at the requested replacement-delivery phase.
                with patch.object(config, "EMAIL_ENROLLMENT_RESEND_COOLDOWN_SECONDS", 0), self.assertRaises(_Crash):
                    # Begin one replacement while the predecessor remains valid through provider acceptance.
                    service.resend(email, "en-US", f"verified-resend-cancel-key-{index:04d}", f"cancel-resend-source-{index}")
                # Capture the stale callback binding before cancellation removes it.
                before = json.loads((root / "pending.json").read_text(encoding="utf-8"))["enrollments"][0]
                # Use the candidate only after provider delivery; otherwise the predecessor remains current.
                ownership_bearer = predecessor_match.group(1)
                # Resolve the delivered candidate for provider-confirmed and later phases.
                if phase in {"provider_recorded", "candidate_promoted", "delivery_finalized"}:
                    # Extract the replacement from the second transient fake message.
                    candidate_match = re.search(r"[?&]token=([^\s<]+)", transport.messages[1]["text_body"])
                    # Require one delivered ownership bearer.
                    self.assertIsNotNone(candidate_match)
                    # Cancel only with the now-current candidate after reconciliation.
                    ownership_bearer = candidate_match.group(1)
                # Cancel through the ownership-bound terminal state machine.
                self.assertEqual(service.cancel(ownership_bearer, email, f"verified-cancel-key-{index:04d}", f"cancel-owner-source-{index}"), {"status": "cancelled"})
                # Require terminal state, credential scrubbing, and no replacement residue.
                cancelled = json.loads((root / "pending.json").read_text(encoding="utf-8"))["enrollments"][0]
                # Bind all cancellation invariants in one assertion.
                self.assertEqual((cancelled["status"], "replacement" in cancelled, token_service.active_count(pending_enrollment.PURPOSE, email)), ("cancelled", False, 0))
                # Simulate a stale delivery finalizer arriving after terminal cancellation.
                with self.assertRaises(ConflictError):
                    # Require generation and lifecycle guards to reject resurrection.
                    service._finish_delivery(before["enrollment_id"], int(before["delivery_generation"]), (before.get("replacement") or {}).get("candidate_token_id"), True)
                # Re-read state after the rejected callback.
                stable = json.loads((root / "pending.json").read_text(encoding="utf-8"))["enrollments"][0]
                # Require cancellation to remain terminal with no delivery recovery packet.
                self.assertEqual((stable["status"], "replacement" in stable), ("cancelled", False))
                # Require no canonical identity or session for the cancelled recipient.
                self.assertIsNone(auth.find_user_by_email(email))
                # Require no deterministic email-enrollment wallet was created.
                self.assertFalse(any(row.get("display_name") == "Cancel Player" for row in players.list_players()))

    # Prove scrubbed terminal replay metadata expires while every active lifecycle row is retained.
    def test_terminal_metadata_retention_prunes_complete_and_cancelled_only(self):
        # Complete one enrollment so its scrubbed replay metadata becomes terminal.
        bearer = self.initiate("verified-initiate-key-retention-0001", "retention-source-1")
        # Finish activation without creating a session.
        self.assertEqual(self.service.verify(bearer, TEST_EMAIL, "verified-complete-key-retention-0001", "retention-verify-1"), {"status": "enrolled"})
        # Create and cancel a second terminal enrollment.
        self.service.initiate("cancel-retention@example.invalid", TEST_PASSWORD, "Cancel Retention", "en-US", config.GUEST_TERMS_VERSION, True, "verified-initiate-key-retention-0002", "retention-source-2")
        # Extract the second enrollment's current delivered ownership bearer.
        cancel_bearer = self.bearer(1)
        # Terminalize its scrubbed pending metadata.
        self.assertEqual(self.service.cancel(cancel_bearer, "cancel-retention@example.invalid", "verified-cancel-key-retention-0002", "retention-cancel-2"), {"status": "cancelled"})
        # Create one active pending row that must survive regardless of age.
        self.service.initiate("active-retention@example.invalid", TEST_PASSWORD, "Active Retention", "en-US", config.GUEST_TERMS_VERSION, True, "verified-initiate-key-retention-0003", "retention-source-3")
        # Move beyond the governed terminal replay window without wall-clock delay.
        self.clock.advance(config.EMAIL_ENROLLMENT_TERMINAL_RETENTION_SECONDS + 1)
        # Trigger provider-atomic cleanup with one new distinct initiation.
        self.service.initiate("cleanup-trigger@example.invalid", TEST_PASSWORD, "Cleanup Trigger", "en-US", config.GUEST_TERMS_VERSION, True, "verified-initiate-key-retention-0004", "retention-source-4")
        # Read the provider document after cleanup.
        rows = json.loads((self.root / "pending.json").read_text(encoding="utf-8"))["enrollments"]
        # Require both old terminal rows gone and both nonterminal rows preserved.
        self.assertEqual(sorted(row["status"] for row in rows), ["pending", "pending"])

    # Prove a post-credit failure resumes safely without duplicating money.
    def test_post_credit_activation_failure_recovers_exactly_once(self):
        # Begin one pending enrollment.
        bearer = self.initiate("verified-initiate-key-0002")
        # Preserve the real final activation boundary.
        real_activate = auth.activate_verified_email_user
        # Fail exactly once after the deterministic ledger credit.
        with patch.object(auth, "activate_verified_email_user", side_effect=RuntimeError("synthetic activation stop")):
            # Require the public generic failure while recoverable state remains.
            with self.assertRaises(ValidationError):
                # Start the first consumed-token attempt.
                self.service.verify(bearer, TEST_EMAIL, "verified-complete-key-0002")
        # Restore and replay the exact same caller request.
        with patch.object(auth, "activate_verified_email_user", side_effect=real_activate):
            # Complete the retained saga without another bearer.
            self.assertEqual(self.service.verify(bearer, TEST_EMAIL, "verified-complete-key-0002"), {"status": "enrolled"})
        # Resolve the active canonical identity.
        user = auth.find_user_by_email(TEST_EMAIL)
        # Require one deterministic starting-balance ledger event after recovery.
        funding = [row for row in ledger.read_recent(user["player_id"], 20) if row.get("transaction_type") == "ACCOUNT_STARTING_BALANCE"]
        # Require no duplicate credit and exact final balance.
        self.assertEqual((len(funding), players.get_player(user["player_id"])["balance"]), (1, float(config.ACCOUNT_STARTING_BALANCE)))

    # Prove cancellation removes the active bearer without provisioning resources.
    def test_cancel_is_generic_and_prevents_verification(self):
        # Begin one pending signup.
        bearer = self.initiate("verified-initiate-key-0003")
        # Cancel through the recipient-independent public receipt.
        self.assertEqual(self.service.cancel(bearer, TEST_EMAIL, "verified-cancel-key-0001", "cancel-source-1"), {"status": "cancelled"})
        # Replay the exact completed cancellation after its bearer is revoked.
        self.assertEqual(self.service.cancel(bearer, TEST_EMAIL, "verified-cancel-key-0001", "cancel-source-1"), {"status": "cancelled"})
        # Require the bearer to be unusable through the generic boundary.
        with self.assertRaises(ValidationError):
            # Attempt verification after terminal cancellation.
            self.service.verify(bearer, TEST_EMAIL, "verified-complete-key-0003")
        # Require no canonical user, email player, or session after cancellation.
        self.assertEqual((auth.load_users()["users"], auth.load_sessions()["sessions"]), ([], []))
        # Require no deterministic wallet residue.
        self.assertFalse(any(row.get("player_id", "").startswith("player_email_") for row in players.list_players()))
        # Read the cancelled row only to prove terminal cleanup was atomic with revocation state.
        cancelled = json.loads((self.root / "pending.json").read_text(encoding="utf-8"))["enrollments"][0]
        # Require no raw recipient, password verifier, or profile values after cancellation.
        self.assertFalse({"email", "password_hash", "display_name", "locale", "terms_version"} & set(cancelled))
        # Replay the exact initiation key without restoring or needing scrubbed credential fields.
        self.assertEqual(self.service.initiate(TEST_EMAIL, TEST_PASSWORD, "Verified Player", "en-US", config.GUEST_TERMS_VERSION, True, "verified-initiate-key-0003"), {"status": "verification_pending"})
        # Reject an absent mailbox through the same generic ownership failure as a wrong bearer.
        with self.assertRaises(ValidationError):
            # Reuse only a revoked synthetic bearer against an absent recipient.
            self.service.cancel(bearer, "absent@example.invalid", "verified-cancel-key-0002", "cancel-source-2")

    # Prove disabled production defaults reject before pending state or delivery.
    def test_disabled_default_is_inert(self):
        # Build one explicitly disabled service over isolated state.
        disabled = pending_enrollment.PendingEnrollmentService(store_path=self.root / "disabled.json", enabled=False, digest_key=TEST_MAIL_KEY, token_service=self.token_service, mail_service=self.mail_service, audit_sink=lambda event, **fields: None)
        # Reject initiation before any state or mail side effect.
        with self.assertRaises(Exception):
            # Attempt a fully shaped disabled signup.
            disabled.initiate(TEST_EMAIL, TEST_PASSWORD, "Verified Player", "en-US", config.GUEST_TERMS_VERSION, True, "verified-disabled-key-0001")
        # Require no disabled pending document and no new message.
        self.assertFalse((self.root / "disabled.json").exists())


# Run the focused module directly under repository validators.
if __name__ == "__main__":
    # Exit through unittest's standard result code.
    unittest.main()
