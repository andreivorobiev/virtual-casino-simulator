# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused issue-86 tests for Big Six rules, settlement, and exactly-once service behavior."""

# Import the standard dependency-free unit-test runner.
import unittest
# Import the project conflict error used for idempotency misuse.
from casino.errors import ConflictError
# Import the pure game engine under direct test.
from casino.games.big_six_wheel import engine
# Import the immutable wheel profile under direct test.
from casino.games.big_six_wheel.rules import NET_ODDS, SEGMENT_COUNTS, WHEEL_SEGMENTS
# Import the orchestration service with injectable storage, entropy, and ledger seams.
from casino.games.big_six_wheel.service import BigSixWheelService


# Provide an in-memory ledger gateway that enforces the same action-key contract.
class FakeLedgerGateway:
    # Initialize stable event storage and call evidence.
    def __init__(self):
        # Store committed events by deterministic action key.
        self.events = {}
        # Store every gateway invocation so replay behavior is observable.
        self.calls = []

    # Apply or replay one event without touching any real player balance.
    def apply_once(self, *, player_id, amount, transaction_type, round_id, action_key, details):
        # Record each requested action for exact call-count assertions.
        self.calls.append(action_key)
        # Return an existing event when the action key already committed.
        if action_key in self.events:
            # Reuse the original event as exactly-once evidence.
            return self.events[action_key], True
        # Build a minimal shared-ledger-shaped event for service recovery logic.
        event = {"player_id": player_id, "amount": amount, "transaction_type": transaction_type, "round_id": round_id, "ts": "2026-07-13T00:00:00Z", "details": {**details, "idempotency_key": action_key}}
        # Commit the event under its deterministic identity.
        self.events[action_key] = event
        # Return the new event and non-replay evidence.
        return event, False


# Verify the regulated profile and pure settlement calculations.
class BigSixWheelEngineTests(unittest.TestCase):
    # Confirm the wheel has exactly the documented distribution.
    def test_regulated_wheel_profile_counts(self):
        # Verify the physical profile contains exactly 54 ordered segments.
        self.assertEqual(54, len(WHEEL_SEGMENTS))
        # Verify each outcome count against immutable rule metadata.
        self.assertEqual(dict(SEGMENT_COUNTS), {outcome: WHEEL_SEGMENTS.count(outcome) for outcome in SEGMENT_COUNTS})
        # Verify the two unique symbols use the selected 45-to-1 profile.
        self.assertEqual((45, 45), (NET_ODDS["joker"], NET_ODDS["crest"]))

    # Confirm an injected index produces deterministic multi-wager settlement.
    def test_settlement_is_deterministic_for_selected_index(self):
        # Normalize two outcome wagers through the public validation path.
        wagers = engine.normalize_wagers({"one": 3, "joker": 2})
        # Select the first Joker segment deterministically.
        result = engine.settle(wagers, 0)
        # Verify the canonical outcome and total wager.
        self.assertEqual(("joker", 5.0), (result["outcome"], result["total_wager"]))
        # Verify a two-token Joker wager returns stake plus 45-to-1 net winnings.
        self.assertEqual(92.0, result["total_return"])
        # Verify losing covered outcomes remain visible in the result rows.
        self.assertEqual(-3.0, next(row["net"] for row in result["settlements"] if row["outcome"] == "one"))

    # Confirm equal client actions produce one stable round id without exposing raw identity.
    def test_round_id_is_stable_and_player_scoped(self):
        # Derive the same round twice for retry identity.
        first = engine.round_id_for("player-a", "request-17")
        # Repeat the derivation through the same public helper.
        second = engine.round_id_for("player-a", "request-17")
        # Verify deterministic replay identity.
        self.assertEqual(first, second)
        # Verify another authenticated player cannot collide with this round.
        self.assertNotEqual(first, engine.round_id_for("player-b", "request-17"))
        # Verify free-form request text is not included in the persisted round id.
        self.assertNotIn("request", first)


# Verify ledger-only orchestration and crash/retry recovery.
class BigSixWheelServiceTests(unittest.TestCase):
    # Build an isolated service and its mutable test seams.
    def setUp(self):
        # Store player documents in memory by player id.
        self.states = {}
        # Create the fake apply-once ledger adapter.
        self.ledger = FakeLedgerGateway()
        # Build the service with deterministic Joker selection and pinned time.
        self.service = BigSixWheelService(ledger_gateway=self.ledger, state_loader=lambda player_id: self.states.setdefault(player_id, engine.default_state()), state_saver=lambda player_id, state: self.states.__setitem__(player_id, state), randbelow=lambda size: 0, clock=lambda: "2026-07-13T00:00:00Z")

    # Confirm a normal retry returns one debit and one credit only.
    def test_retry_reuses_settled_round_without_new_ledger_actions(self):
        # Define one complete retry-safe request.
        request = {"client_request_id": "retry-1", "wagers": {"joker": 2}}
        # Execute the original atomic spin.
        first = self.service.spin("player-a", request)
        # Repeat the identical action identity.
        second = self.service.spin("player-a", request)
        # Verify both responses identify the same settled round.
        self.assertEqual(first["round"], second["round"])
        # Verify the state-cache retry is explicitly reported.
        self.assertTrue(second["replayed"])
        # Verify exactly one debit and one settlement credit were requested.
        self.assertEqual(2, len(self.ledger.calls))

    # Confirm a crash after ledger commit reconstructs the committed result and credits once.
    def test_post_debit_crash_retry_recovers_committed_index(self):
        # Define one complete retry-safe request.
        request = {"client_request_id": "crash-1", "wagers": {"joker": 2}}
        # Derive the stable round and request identity used by the service.
        round_id = engine.round_id_for("player-a", "crash-1")
        # Normalize and fingerprint the original wagers.
        wagers = engine.normalize_wagers(request["wagers"])
        # Precommit only the debit to simulate a crash before settlement and state save.
        self.ledger.apply_once(player_id="player-a", amount=-2.0, transaction_type="BIG_SIX_WAGER_DEBIT", round_id=round_id, action_key=f"{round_id}:wager", details={"client_request_id": "crash-1", "request_fingerprint": engine.wager_fingerprint(wagers), "wagers": wagers, "result_index": 0})
        # Retry with an entropy source that would choose another segment if recovery failed.
        recovering = BigSixWheelService(ledger_gateway=self.ledger, state_loader=lambda player_id: self.states.setdefault(player_id, engine.default_state()), state_saver=lambda player_id, state: self.states.__setitem__(player_id, state), randbelow=lambda size: 1, clock=lambda: "later")
        # Resume the interrupted action.
        result = recovering.spin("player-a", request)
        # Verify the committed Joker result wins instead of the new index-one proposal.
        self.assertEqual((0, "joker", 92.0), (result["round"]["result_index"], result["round"]["outcome"], result["round"]["total_return"]))
        # Verify the fake ledger contains only one debit and one credit identity.
        self.assertEqual(2, len(self.ledger.events))

    # Confirm one idempotency identity cannot represent different wager content.
    def test_conflicting_request_identity_fails_closed(self):
        # Commit one settled request identity.
        self.service.spin("player-a", {"client_request_id": "same-id", "wagers": {"joker": 1}})
        # Reject a different wager map under the same client identity.
        with self.assertRaises(ConflictError):
            # Exercise the conflicting replay boundary.
            self.service.spin("player-a", {"client_request_id": "same-id", "wagers": {"one": 1}})


# Run the focused suite directly without central runner registration.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
