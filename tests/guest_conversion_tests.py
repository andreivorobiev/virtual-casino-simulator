# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused guest-to-account conversion tests. (#378, CONVERT-001/002)"""

# Import a bounded thread pool for deterministic concurrent wallet-ownership proof.
from concurrent.futures import ThreadPoolExecutor
# Import JSON serialization for exact privacy assertions over de-identified analytics rows.
import json
# Import a barrier so both account claims reach the atomic identity transaction together.
import threading
# Import the standard unittest framework used by the repository's focused suites.
import unittest
# Import patching so the concurrent test synchronizes only the account-creation boundary.
from unittest.mock import patch

# Import the canonical identity, guest, and session boundary under test.
from casino.core import auth
# Import the authoritative ledger for wallet-preservation fixtures.
from casino.core import ledger
# Import the conversion and de-identified lifecycle services under test.
from casino.core import guest_analytics, guest_conversion
# Import the player boundary for balance assertions.
from casino.core import players
# Import the standard bounded application errors every rejection uses.
from casino.errors import ConflictError, ValidationError


# Verify explicit, idempotent, wallet-preserving guest conversion.
class GuestConversionTests(unittest.TestCase):
    # Seed one active guest trial with a distinguishable wallet for each test.
    def setUp(self) -> None:
        # Derive a per-test suffix so seeded accounts never collide across the shared store.
        self.unique = self.id().rsplit(".", 1)[1]
        # Reset the identity document so accumulated guests never exhaust the active-guest capacity between tests.
        from casino.core.state_store import write_json
        # Restore the canonical empty identity store before seeding this test's guest.
        write_json(auth.USERS_PATH, auth.default_users())
        # Reset the independent source-rate document so prior API cases cannot exhaust this focused fixture.
        write_json(auth.GUEST_CREATION_LOG_PATH, auth.default_guest_creation_log())
        # Create a real guest trial through the identity boundary.
        self.guest = auth.create_guest(accepted=True, terms_version=auth.GUEST_TERMS_VERSION, locale="en-US")["user"]

    # Reload the guest record fresh so a conversion marker written by the service is visible.
    def _reload_guest(self) -> dict:
        # Read the current guest identity by its durable id.
        for user in auth.load_users().get("users", []):
            # Match the seeded guest.
            if user.get("user_id") == self.guest["user_id"]:
                # Return the freshly loaded guest record.
                return user
        # Fail loudly if the guest vanished.
        raise AssertionError("guest record disappeared")

    # Build a valid conversion payload for this test's unique mailbox.
    def _payload(self, **overrides) -> dict:
        # Start from a complete, valid payload.
        base = {"email": f"converted.{self.unique}@example.test", "password": "ConvertPassw0rd!23", "display_name": "Converted Player", "terms_version": "v1", "accepted": True, "idempotency_key": f"guest-conversion-{self.unique}-key"}
        # Apply any per-test overrides.
        base.update(overrides)
        # Return the payload.
        return base

    # Read the exact de-identified lifecycle row created with this guest.
    def _trial(self) -> dict:
        # Resolve through the production Admin-detail projection rather than inspecting raw storage.
        trial = guest_analytics.detail(self.guest["guest_analytics_id"])
        # Fail clearly when a lifecycle row disappeared instead of weakening later assertions.
        if trial is None:
            # Surface one fixture-only failure without identity or credential content.
            raise AssertionError("guest analytics row disappeared")
        # Return the detached analytics-only row.
        return trial

    # Require a successful conversion to preserve the exact guest wallet.
    def test_conversion_preserves_the_wallet(self) -> None:
        # Commit a distinguishable movement so the guest wallet is not its default value.
        ledger.debit(self.guest["player_id"], 250, "GUEST_PLAY", game="roulette")
        # Read the guest balance before conversion.
        before = players.get_player(self.guest["player_id"])["balance"]
        # Convert the guest into a full account.
        result = guest_conversion.convert(self.guest, **self._payload())
        # Require the conversion to report success and wallet preservation.
        self.assertEqual((result["status"], result["player_preserved"]), ("converted", True))
        # Require the preserved balance to equal the pre-conversion balance exactly.
        self.assertEqual(result["balance"], before)
        # Require the new account to own the very same player as the guest.
        account = auth.find_user_by_email(f"converted.{self.unique}@example.test")
        self.assertEqual(account["player_id"], self.guest["player_id"])

    # Require self-service conversion to close one de-identified Admin analytics row. (GUEST-007, TEST-195)
    def test_self_service_conversion_closes_analytics_without_identity_data(self) -> None:
        # Commit a distinguishable legitimate movement before the account adopts this wallet.
        ledger.debit(self.guest["player_id"], 375, "GUEST_PLAY", game="roulette")
        # Convert through the ordinary authenticated self-service authority.
        result = guest_conversion.convert(self.guest, **self._payload())
        # Read the terminal analytics-only projection after identity ownership commits.
        trial = self._trial()
        # Require exact terminal reason, ending balance, milestone, and one lifecycle event.
        self.assertEqual((trial["end_reason"], trial["ending_balance"], trial["milestones"]["trial_terminal"], len([event for event in trial["events"] if event.get("event") == "trial_terminal"])), ("converted", result["balance"], True, 1))
        # Serialize only the de-identified row for an exact forbidden-content scan.
        serialized = json.dumps(trial, sort_keys=True)
        # Require no mailbox, password, account id, player id, or guest user id in analytics storage.
        self.assertNotIn(result["email"], serialized)
        # Bind every server identity and credential marker independently for clear failures.
        for forbidden in (self.guest["user_id"], self.guest["player_id"], "ConvertPassw0rd!23", "password_hash", "session_id"):
            # Reject any raw identity or credential content from the product analytics row.
            self.assertNotIn(forbidden, serialized)
        # Require the converted row to disappear from the Admin active-trial action source.
        active_ids = {row["analytics_id"] for row in guest_analytics.summary(status="active")["recent"]}
        # Prove Admin cannot offer active-trial actions for the terminal row.
        self.assertNotIn(self.guest["guest_analytics_id"], active_ids)

    # Require the new account to be a real password login, not a guest.
    def test_converted_account_can_authenticate(self) -> None:
        # Convert the guest.
        guest_conversion.convert(self.guest, **self._payload())
        # Log in as the new account with the chosen password.
        login = auth.login(f"converted.{self.unique}@example.test", "ConvertPassw0rd!23")
        # Require a session to be issued and the account not to be a guest.
        self.assertTrue(login["session"]["token"])
        self.assertFalse(auth.is_guest(login["user"]))

    # Require the guest record to become terminal and leave the trial lifecycle.
    def test_guest_becomes_terminal(self) -> None:
        # Convert the guest.
        guest_conversion.convert(self.guest, **self._payload())
        # Reload the guest record.
        terminal = self._reload_guest()
        # Require the guest to be marked converted and linked to the new account.
        self.assertEqual(terminal["status"], "converted")
        self.assertTrue(terminal["converted_to_user_id"])

    # Require a retry after completion to replay the same account with no second wallet.
    def test_conversion_is_idempotent(self) -> None:
        # Perform the first conversion.
        first = guest_conversion.convert(self.guest, **self._payload())
        # Retry with the freshly reloaded, now-terminal guest record.
        second = guest_conversion.convert(self._reload_guest(), **self._payload())
        # Require the retry to be reported as a replay of the same account.
        self.assertTrue(second["replayed"])
        # Require both results to name the same account email.
        self.assertEqual(first["email"], second["email"])
        # Require exactly one account to own the guest's player.
        owners = [u for u in auth.load_users().get("users", []) if u.get("player_id") == self.guest["player_id"] and not auth.is_guest(u)]
        self.assertEqual(len(owners), 1)
        # Capture the complete terminal analytics row after the first completed conversion.
        terminal_trial = self._trial()
        # Replay once more with the canonical terminal guest to prove analytics fields stay byte-stable.
        third = guest_conversion.convert(self._reload_guest(), **self._payload())
        # Require the public replay marker and exact original terminal analytics projection.
        self.assertTrue(third["replayed"])
        # Prove record_ended never duplicates or restamps the terminal row.
        self.assertEqual(self._trial(), terminal_trial)

    # Require pre-commit failure to leave analytics active and committed conversion to recover its projection.
    def test_analytics_failure_is_deferred_and_exact_replay_converges(self) -> None:
        # Fail before identity completion and require no terminal analytics side effect.
        with patch.object(guest_conversion, "_complete_conversion", side_effect=RuntimeError("identity commit unavailable")):
            # Attempt one otherwise-valid first conversion.
            with self.assertRaisesRegex(RuntimeError, "identity commit unavailable"):
                # Submit the exact production request up to the failed commit boundary.
                guest_conversion.convert(self.guest, **self._payload())
        # Require the analytics row to remain active before any durable conversion marker exists.
        self.assertIsNone(self._trial().get("ended_at"))
        # Remove the account created before the synthetic completion failure by resetting this case's identities.
        auth.save_users({"schema_version": 1, "users": [self.guest], "reservations": []})
        # Preserve the exact wallet and ledger projections before the successful conversion attempt.
        player_before = dict(players.get_player(self.guest["player_id"]))
        # Capture authoritative money history so telemetry failure cannot add an effect.
        ledger_before = ledger.read_recent(self.guest["player_id"], 100)
        # Fail only the de-identified analytics close after identity conversion commits.
        with patch.object(guest_conversion.guest_analytics, "record_ended", side_effect=RuntimeError("analytics unavailable")):
            # Require conversion success even though its recoverable projection is temporarily unavailable.
            first = guest_conversion.convert(self.guest, **self._payload())
        # Require the durable guest marker and account owner despite the telemetry failure.
        terminal_guest = self._reload_guest()
        # Bind committed identity and still-active analytics before recovery.
        self.assertEqual((first["status"], terminal_guest["status"], self._trial().get("ended_at")), ("converted", "converted", None))
        # Run the bounded Admin-read recovery without invoking identity conversion again.
        with patch.object(guest_conversion, "_complete_conversion", side_effect=AssertionError("conversion repeated during analytics recovery")):
            # Require one committed marker to converge through analytics-only reconciliation.
            self.assertEqual(guest_conversion.reconcile_conversion_analytics(), 1)
        # Capture the recovered terminal row before exercising ordinary exact replay.
        recovered_trial = self._trial()
        # Require analytics-only recovery to publish the expected reason and preserved balance.
        self.assertEqual((recovered_trial["end_reason"], recovered_trial["ending_balance"]), ("converted", first["balance"]))
        # Replay the already-converted service request after recovery.
        second = guest_conversion.convert(terminal_guest, **self._payload())
        # Require the public replay marker without changing recovered terminal analytics fields.
        self.assertEqual((second["replayed"], self._trial()), (True, recovered_trial))
        # Prove wallet and ledger stayed exact across both the deferred close and recovery replay.
        self.assertEqual((players.get_player(self.guest["player_id"]), ledger.read_recent(self.guest["player_id"], 100)), (player_before, ledger_before))

    # Require completed conversion replay to reject a different caller operation identity.
    def test_completed_conversion_rejects_conflicting_idempotency_key(self) -> None:
        # Complete one conversion with the fixture's stable operation key.
        guest_conversion.convert(self.guest, **self._payload())
        # Reload the terminal guest so the persisted operation fingerprint is available.
        terminal = self._reload_guest()
        # Reject another key rather than treating a new operation as the original replay.
        with self.assertRaises(ConflictError):
            # Attempt the conflicting operation against the same completed guest.
            guest_conversion.convert(terminal, **self._payload(idempotency_key=f"guest-conversion-{self.unique}-other-key"))

    # Require two concurrent account claims to converge on exactly one owner for the guest wallet.
    def test_concurrent_conversion_keeps_one_durable_wallet_owner(self) -> None:
        # Synchronize both callers immediately before the atomic account claim.
        claim_barrier = threading.Barrier(2)
        # Retain the production account creator behind the synchronization seam.
        create_user = auth.create_user
        # Define one synchronized account creation call used only by this test.
        def synchronized_create(*args, **kwargs):
            # Release both contenders only after each passed the pre-claim recovery read.
            claim_barrier.wait(timeout=5)
            # Delegate the actual uniqueness decision to the production provider transaction.
            return create_user(*args, **kwargs)
        # Define one contender that reports only a completed conversion or bounded conflict.
        def attempt(index: int):
            # Start one distinct account claim for the same guest wallet.
            try:
                # Return the service result when this contender wins.
                return ("converted", guest_conversion.convert(self.guest, **self._payload(email=f"concurrent-{index}.{self.unique}@example.test", idempotency_key=f"guest-conversion-{self.unique}-concurrent-{index}")))
            # Treat the losing different-content claim as the required bounded conflict.
            except ConflictError:
                # Return no result payload for the rejected contender.
                return ("conflict", None)
        # Patch only the guest-conversion module's shared auth creator during both claims.
        with patch.object(auth, "create_user", side_effect=synchronized_create):
            # Execute both contenders through independent threads over the same JSON transaction.
            with ThreadPoolExecutor(max_workers=2) as pool:
                # Materialize both outcomes before leaving the patched boundary.
                outcomes = list(pool.map(attempt, range(2)))
        # Require exactly one completed account and one rejected conflicting claim.
        self.assertEqual(sorted(outcome for outcome, _ in outcomes), ["conflict", "converted"])
        # Read every durable non-guest account attached to the preserved player.
        owners = [user for user in auth.load_users().get("users", []) if user.get("player_id") == self.guest["player_id"] and not auth.is_guest(user)]
        # Require the provider transaction to retain exactly one account owner.
        self.assertEqual(len(owners), 1)

    # Require an interrupted conversion (account created, guest unmarked) to recover on retry.
    def test_interrupted_conversion_recovers(self) -> None:
        # Simulate a prior attempt that created the account but never wrote the terminal guest marker.
        auth.create_user(f"converted.{self.unique}@example.test", "ConvertPassw0rd!23", "Converted Player", role="player", player_id=self.guest["player_id"], terms_required=False)
        # Retry conversion with the still-active guest and the matching mailbox.
        result = guest_conversion.convert(self.guest, **self._payload())
        # Require the retry to recover the existing account as a replay.
        self.assertTrue(result["replayed"])
        # Reload the recovered account so accepted terms are proven in the same identity transaction.
        account = auth.find_user_by_email(f"converted.{self.unique}@example.test")
        # Require explicit accepted terms metadata on the recovered durable account.
        self.assertEqual((account["terms_required"], account["terms_accepted_version"], account["terms_acceptance_source"]), (False, "v1", "guest_conversion"))
        # Require the guest to now be marked terminal.
        self.assertEqual(self._reload_guest()["status"], "converted")

    # Require a retry that names a different mailbox for an already-bound wallet to fail closed.
    def test_conflicting_retry_is_rejected(self) -> None:
        # Simulate a prior attempt that bound the guest wallet to one account.
        auth.create_user(f"converted.{self.unique}@example.test", "ConvertPassw0rd!23", "Converted Player", role="player", player_id=self.guest["player_id"], terms_required=False)
        # Require a retry naming a different mailbox to conflict rather than create a second account.
        with self.assertRaises(ConflictError):
            # Attempt the conflicting conversion.
            guest_conversion.convert(self.guest, **self._payload(email=f"different.{self.unique}@example.test"))

    # Require conversion to refuse a non-guest principal.
    def test_only_a_guest_can_convert(self) -> None:
        # Create a full account that is not a guest.
        auth.create_user(f"account.{self.unique}@example.test", "AccountPassw0rd!23", "Account")
        account = auth.find_user_by_email(f"account.{self.unique}@example.test")
        # Require conversion of a non-guest to fail closed.
        with self.assertRaises(ValidationError) as raised:
            # Attempt to convert a full account.
            guest_conversion.convert(account, **self._payload(email=f"other.{self.unique}@example.test"))
        # Require the not-a-guest reason.
        self.assertEqual(raised.exception.details.get("reason"), "not_a_guest")

    # Require conversion to refuse silent or non-compliant enrollment inputs.
    def test_enrollment_inputs_are_validated(self) -> None:
        # Enumerate rejected payloads with their reason.
        cases = [({"accepted": False}, "terms_required"), ({"password": "short"}, "weak_password"), ({"email": "not-an-email"}, "invalid_email")]
        # Check every rejected payload.
        for overrides, reason in cases:
            # Isolate each case so a failure names the payload.
            with self.subTest(overrides=overrides):
                # Require the bounded validation error.
                with self.assertRaises(ValidationError) as raised:
                    # Attempt the rejected conversion; each case fails before conversion so the guest stays reusable.
                    guest_conversion.convert(self.guest, **self._payload(**overrides))
                # Require the exact reason.
                self.assertEqual(raised.exception.details.get("reason"), reason)

    # Require the contract's caller-stable idempotency key before any identity mutation.
    def test_idempotency_key_is_required_and_bounded(self) -> None:
        # Enumerate missing, short, oversized, and non-token operation keys.
        for idempotency_key in ("", "short", "x" * 101, "contains spaces and symbols!"):
            # Isolate each rejected key so a failure names its shape without echoing secrets.
            with self.subTest(length=len(idempotency_key)):
                # Require the bounded validation result.
                with self.assertRaises(ValidationError) as raised:
                    # Attempt conversion with the invalid operation key.
                    guest_conversion.convert(self.guest, **self._payload(idempotency_key=idempotency_key))
                # Require the exact contract reason and no account side effect.
                self.assertEqual(raised.exception.details.get("reason"), "invalid_idempotency_key")

    # Require a duplicate mailbox already owned by a different account to be rejected.
    def test_duplicate_email_is_rejected(self) -> None:
        # Seed an unrelated account holding the target mailbox.
        auth.create_user(f"taken.{self.unique}@example.test", "TakenPassw0rd!23", "Taken")
        # Require conversion onto the taken mailbox to fail rather than duplicate identity.
        with self.assertRaises(ValidationError):
            # Attempt the conversion onto a taken mailbox.
            guest_conversion.convert(self.guest, **self._payload(email=f"taken.{self.unique}@example.test"))
