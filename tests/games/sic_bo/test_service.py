# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Reload and exactly-once Sic Bo service tests for LEDGER-005/006/007/009."""

# Import deep-copy support so fake persistence matches JSON document boundaries.
import copy
# Import repository paths for exact source-topology evidence.
from pathlib import Path
# Import the dependency-free standard unit-test runner.
import unittest

# Import public errors used by validation, failure, and conflict assertions.
from casino.errors import ConflictError, InsufficientFundsError, ValidationError
# Import the one shared compatibility gateway used by every helper-backed game.
from casino.core.settlement import GameSettlementGateway
# Import the isolated engine for default player-state fixtures.
from casino.games.sic_bo import engine
# Import only the game-owned orchestration service under focused tests.
from casino.games.sic_bo.service import SicBoService


# Provide deep-copied player state with injectable write-failure points.
class FakeStateStore:
    # Initialize one empty player-document collection.
    def __init__(self):
        # Store persisted state by authenticated player id.
        self.states = {}
        # Count writes so tests can fail exact crash windows.
        self.save_calls = 0
        # Store write numbers that should raise before persistence.
        self.fail_on = set()

    # Load one detached player state or a fresh game default.
    def load(self, player_id):
        # Return a deep copy so mutations require an explicit save.
        return copy.deepcopy(self.states.get(player_id, engine.default_state()))

    # Apply one provider-current mutation unless this publication simulates a crash.
    def update(self, player_id, mutator):
        # Advance the deterministic write counter.
        self.save_calls += 1
        # Evaluate the callback against exact current provider state.
        updated = mutator(self.load(player_id))
        # Raise before persistence at configured crash windows.
        if self.save_calls in self.fail_on:
            # Simulate abrupt storage failure without altering prior durable state.
            raise RuntimeError(f"simulated save failure {self.save_calls}")
        # Persist a deep copy under only the authenticated player.
        self.states[player_id] = copy.deepcopy(updated)
        # Return a detached authoritative result like shared storage.
        return copy.deepcopy(updated)


# Provide an in-memory apply-once ledger with real signed-balance semantics.
class FakeLedgerGateway:
    # Initialize one player balance and empty append-only event list.
    def __init__(self, balance=1000.0):
        # Store fake balances only inside this ledger adapter.
        self.balances = {"session-player": balance}
        # Store committed events in chronological order.
        self.events = []
        # Allocate stable event identifiers.
        self.sequence = 0
        # Name transaction types whose first committed response should be lost.
        self.fail_after_types = set()

    # Find one committed action for the authenticated player.
    def find(self, player_id, action_key=None, **dimensions):
        # Scan newest-first while preserving player isolation.
        event = next((row for row in reversed(self.events) if row["player_id"] == player_id and (row["details"].get("game_action_key") == action_key or row["details"].get("sic_bo_action_id") == action_key)), None)
        # Report an absent committed action without validating optional dimensions.
        if event is None:
            # Preserve the shared gateway's nullable lookup contract.
            return None
        # Reject a mismatched round, transaction type, or semantic fingerprint.
        if dimensions.get("round_id") is not None and event["round_id"] != dimensions["round_id"] or dimensions.get("transaction_type") is not None and event["transaction_type"] != dimensions["transaction_type"] or dimensions.get("request_fingerprint") is not None and event["details"].get("request_fingerprint") != dimensions["request_fingerprint"]:
            # Match the production gateway's fail-closed recovery behavior.
            raise ConflictError("fake ledger proof conflict")
        # Return the immutable fake provider event.
        return event

    # Apply one signed movement once using deterministic action identity.
    def apply_once(self, *, player_id, amount, transaction_type, round_id, action_key, request_fingerprint=None, details):
        # Resolve an earlier event before changing the fake balance.
        existing = self.find(player_id, action_key)
        # Reuse a semantically identical event on retry.
        if existing is not None:
            # Reject different fingerprints behind one action key.
            if existing["details"].get("request_fingerprint") != details.get("request_fingerprint"):
                # Match production conflict behavior.
                raise ConflictError("fake ledger fingerprint conflict")
            # Return original event and replay evidence.
            return existing, True
        # Read the balance before applying the signed movement.
        before = self.balances[player_id]
        # Calculate the candidate balance at shared precision.
        after = round(before + amount, 2)
        # Reject overdrafts through the same public error category as production.
        if after < 0:
            # Preserve the pre-movement fake balance.
            raise InsufficientFundsError()
        # Commit the new balance inside the ledger fake only.
        self.balances[player_id] = after
        # Allocate the next stable event id.
        self.sequence += 1
        # Build the audit dimensions consumed by service recovery.
        event = {"ledger_id": f"led_{self.sequence}", "player_id": player_id, "amount": round(amount, 2), "transaction_type": transaction_type, "game": "sic_bo", "round_id": round_id, "details": {**details, "game_action_key": action_key, "sic_bo_action_id": action_key, "request_fingerprint": request_fingerprint or details.get("request_fingerprint")}, "balance_before": before, "balance_after": after}
        # Append the committed event exactly once.
        self.events.append(event)
        # Simulate one transport failure after immutable movement publication.
        if transaction_type in self.fail_after_types:
            # Consume the one-shot failure so an explicit retry can recover proof.
            self.fail_after_types.remove(transaction_type)
            # Surface an ambiguous response after the balance and event already committed.
            raise RuntimeError("simulated lost ledger response")
        # Return new-event evidence.
        return event, False


# Verify the production adapter's read-before-write conflict checks directly.
class SharedLedgerGatewayTests(unittest.TestCase):
    # Confirm an exact replay reuses one shared-ledger event and changed semantics fail closed.
    def test_production_gateway_replays_only_identical_debits(self):
        # Store fake shared-ledger events in chronological order.
        events = []

        # Return the requested player's committed events like ledger.read_recent.
        def read_recent(player_id, limit):
            # Preserve player isolation and the requested upper bound.
            return [event for event in events if event["player_id"] == player_id][-limit:]

        # Append one signed event like the real ledger.debit helper.
        def debit(player_id, amount, transaction_type, game, round_id, details):
            # Build the exact fields inspected by apply-once recovery.
            event = {"ledger_id": "led_core_1", "player_id": player_id, "amount": -abs(float(amount)), "transaction_type": transaction_type, "game": game, "round_id": round_id, "details": dict(details)}
            # Commit the one fake provider event.
            events.append(event)
            # Return provider evidence to the adapter.
            return event

        # Build the shared adapter against explicit focused-test seams.
        gateway = GameSettlementGateway("sic_bo", "sic_bo_action_id", read_recent=read_recent, debit=debit)
        # Preserve one semantic request fingerprint in ledger details.
        details = {"request_fingerprint": "a" * 64, "dice": [1, 2, 3]}
        # Commit the original aggregate wager debit.
        first, first_replayed = gateway.apply_once(player_id="session-player", amount=-3, transaction_type="SIC_BO_WAGER_DEBIT", round_id="sb_core", action_key="sb_core:wager", details=details)
        # Retry the exact same movement and action identity.
        replay, replayed = gateway.apply_once(player_id="session-player", amount=-3, transaction_type="SIC_BO_WAGER_DEBIT", round_id="sb_core", action_key="sb_core:wager", details=details)
        # Verify only one event exists and its original identity is returned.
        self.assertEqual((1, first, False, True), (len(events), replay, first_replayed, replayed))
        # Reject a different signed amount behind the committed action identity.
        with self.assertRaises(ConflictError):
            # Attempt to enlarge the already committed wager.
            gateway.apply_once(player_id="session-player", amount=-4, transaction_type="SIC_BO_WAGER_DEBIT", round_id="sb_core", action_key="sb_core:wager", details=details)
        # Reject the same key when a different round dimension is supplied.
        with self.assertRaises(ConflictError):
            # Attempt to transplant the action key into another round.
            gateway.apply_once(player_id="session-player", amount=-3, transaction_type="SIC_BO_WAGER_DEBIT", round_id="sb_other", action_key="sb_core:wager", details=details)


# Build deterministic service dependencies for each recovery scenario.
class SicBoServiceTests(unittest.TestCase):
    # Initialize isolated player state and ledger before every test.
    def setUp(self):
        # Create fresh deep-copy persistence.
        self.store = FakeStateStore()
        # Create a fresh ledger with ample play tokens.
        self.ledger = FakeLedgerGateway()
        # Start deterministic entropy with a specific triple of threes.
        self.rolls = iter([2, 2, 2])
        # Build the service through only injected test seams.
        self.service = SicBoService(ledger_gateway=self.ledger, state_loader=self.store.load, state_updater=self.store.update, get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, randbelow=lambda upper: next(self.rolls), clock=lambda: "2026-07-14T00:00:00.000Z")

    # Return one winning specific-triple request with a stable action id.
    def winning_request(self):
        # Cover the deterministic triple at one play token.
        return {"action_id": "issue-88-retry", "wagers": {"triple:3": 1}}

    # Confirm an exact retry returns one round and one movement of each kind.
    def test_exact_retry_and_conflict_detection(self):
        # Execute the original deterministic winning round.
        first = self.service.play("session-player", self.winning_request())
        # Repeat the identical public action identity and wager snapshot.
        second = self.service.play("session-player", self.winning_request())
        # Verify both responses preserve the same server round and dice.
        self.assertEqual(first["round"], second["round"])
        # Verify the repeated response is explicitly marked as replayed.
        self.assertTrue(second["replayed"])
        # Verify one aggregate debit and one returned-credit event exist.
        self.assertEqual(["SIC_BO_WAGER_DEBIT", "SIC_BO_PAYOUT_CREDIT"], [event["transaction_type"] for event in self.ledger.events])
        # Reject one action identity reused with different wager content.
        with self.assertRaises(ConflictError):
            # Attempt a semantically conflicting retry.
            self.service.play("session-player", {"action_id": "issue-88-retry", "wagers": {"small": 1}})

    # Confirm a ledger conflict after bounded history eviction cannot strand active state.
    def test_aged_action_conflict_clears_new_preparation(self):
        # Supply enough deterministic faces for the original, conflicting, and next actions.
        self.rolls = iter([2] * 9)
        # Settle the original action so its durable ledger identity exists.
        self.service.play("session-player", self.winning_request())
        # Simulate the original action aging out of the bounded state history.
        self.store.states["session-player"]["recent_rounds"] = []
        # Reject the reused identity with different wager semantics from ledger proof.
        with self.assertRaises(ConflictError):
            # Attempt a new preparation behind the aged action identity.
            self.service.play("session-player", {"action_id": "issue-88-retry", "wagers": {"small": 1}})
        # Verify the non-resumable proposal was removed despite the older ledger event.
        self.assertIsNone(self.store.states["session-player"]["active_round"])
        # Prove the player can immediately start a genuinely new action.
        next_round = self.service.play("session-player", {"action_id": "issue-88-next", "wagers": {"small": 1}})
        # Verify the following action reaches normal settlement instead of permanent conflict.
        self.assertEqual("settled", next_round["round"]["phase"])

    # Confirm runtime request validation matches the closed OpenAPI schema.
    def test_unknown_request_field_is_rejected(self):
        # Reject an arbitrary field before entropy, state, or ledger work begins.
        with self.assertRaises(ValidationError):
            # Attempt an otherwise valid request with contract-forbidden content.
            self.service.play("session-player", {**self.winning_request(), "future_option": True})
        # Verify schema rejection created no player recovery document.
        self.assertEqual({}, self.store.states)
        # Verify schema rejection created no token movement.
        self.assertEqual([], self.ledger.events)

    # Confirm a crash after debit recovers dice without a duplicate debit.
    def test_post_debit_crash_recovers_one_wager_event(self):
        # Fail the write that would mark the already committed wager complete.
        self.store.fail_on = {2}
        # Execute until the simulated post-debit storage crash.
        with self.assertRaises(RuntimeError):
            # Start the crash-interrupted round.
            self.service.play("session-player", self.winning_request())
        # Verify only the wager event committed before the crash.
        self.assertEqual(["SIC_BO_WAGER_DEBIT"], [event["transaction_type"] for event in self.ledger.events])
        # Verify reload-visible prepared state hides the private dice.
        self.assertNotIn("dice", self.service.payload("session-player")["state"]["active_round"])
        # Disable further simulated failures for recovery.
        self.store.fail_on.clear()
        # Retry the identical action through the same persisted state and ledger.
        recovered = self.service.play("session-player", self.winning_request())
        # Verify recovery returns the originally committed triple.
        self.assertEqual([3, 3, 3], recovered["round"]["dice"])
        # Verify exactly one debit and one payout exist after recovery.
        self.assertEqual(1, len([event for event in self.ledger.events if event["transaction_type"] == "SIC_BO_WAGER_DEBIT"]))
        # Verify the recovered winning action creates one payout only.
        self.assertEqual(1, len([event for event in self.ledger.events if event["transaction_type"] == "SIC_BO_PAYOUT_CREDIT"]))

    # Confirm a lost wager response preserves preparation and recovers exact committed dice.
    def test_lost_wager_response_recovers_without_second_debit(self):
        # Lose the first debit response only after the fake provider commits it.
        self.ledger.fail_after_types = {"SIC_BO_WAGER_DEBIT"}
        # Surface the ambiguous response through the established service boundary.
        with self.assertRaises(RuntimeError):
            # Start the deterministic winning action.
            self.service.play("session-player", self.winning_request())
        # Require one debit and retained private preparation after the lost response.
        self.assertEqual((1, "prepared"), (len(self.ledger.events), self.store.states["session-player"]["active_round"]["phase"]))
        # Retry the exact action and recover immutable wager proof.
        recovered = self.service.play("session-player", self.winning_request())
        # Require original dice, one debit, and one payout only.
        self.assertEqual(([3, 3, 3], 1, 1), (recovered["round"]["dice"], len([event for event in self.ledger.events if event["transaction_type"] == "SIC_BO_WAGER_DEBIT"]), len([event for event in self.ledger.events if event["transaction_type"] == "SIC_BO_PAYOUT_CREDIT"])))

    # Confirm a crash before result persistence exposes recovery rather than partial metrics.
    def test_post_wager_marker_crash_exposes_incomplete_settling_state(self):
        # Fail the result-intent write after committed dice and wager proof were saved.
        self.store.fail_on = {3}
        # Execute until the simulated pre-result storage crash.
        with self.assertRaises(RuntimeError):
            # Start the deterministic winning round through the normal service path.
            self.service.play("session-player", self.winning_request())
        # Read the exact reload-visible public recovery state.
        active = self.service.payload("session-player")["state"]["active_round"]
        # Verify committed dice are visible while lifecycle remains nonterminal.
        self.assertEqual(("settling", [3, 3, 3]), (active["phase"], active["dice"]))
        # Verify incomplete result fields cannot be mistaken for a settled summary.
        self.assertNotIn("outcome", active)
        # Verify no payout was attempted before result intent became durable.
        self.assertEqual(["SIC_BO_WAGER_DEBIT"], [event["transaction_type"] for event in self.ledger.events])
        # Disable the simulated failure for exact-action recovery.
        self.store.fail_on.clear()
        # Resume the same action from committed wager proof.
        recovered = self.service.play("session-player", self.winning_request())
        # Verify recovery reaches one complete result and one payout without duplication.
        self.assertEqual(("settled", 2), (recovered["round"]["phase"], len(self.ledger.events)))

    # Confirm a crash after payout recovers the original credit without duplication.
    def test_post_payout_crash_recovers_one_credit_event(self):
        # Fail the write immediately after a payout event has committed.
        self.store.fail_on = {4}
        # Execute until the simulated post-credit crash.
        with self.assertRaises(RuntimeError):
            # Start the winning crash-interrupted round.
            self.service.play("session-player", self.winning_request())
        # Verify both movement events committed before the marker failure.
        self.assertEqual(2, len(self.ledger.events))
        # Disable further simulated failures for recovery.
        self.store.fail_on.clear()
        # Retry and archive the action from ledger proof.
        recovered = self.service.play("session-player", self.winning_request())
        # Verify the action is reported as a replay.
        self.assertTrue(recovered["replayed"])
        # Verify recovery created no third ledger event.
        self.assertEqual(2, len(self.ledger.events))
        # Verify active recovery state is cleared after archival.
        self.assertIsNone(recovered["state"]["active_round"])

    # Confirm a lost payout response recovers the committed credit without duplication.
    def test_lost_payout_response_recovers_without_second_credit(self):
        # Lose the first payout response only after the fake provider commits it.
        self.ledger.fail_after_types = {"SIC_BO_PAYOUT_CREDIT"}
        # Surface the ambiguous positive-movement response.
        with self.assertRaises(RuntimeError):
            # Start the deterministic winning action.
            self.service.play("session-player", self.winning_request())
        # Require both movements and a durable pending payout marker.
        self.assertEqual((2, "pending"), (len(self.ledger.events), self.store.states["session-player"]["active_round"]["payout_status"]))
        # Retry from deterministic settlement intent and immutable payout proof.
        recovered = self.service.play("session-player", self.winning_request())
        # Require one credit total and terminal recovery cleanup.
        self.assertEqual((1, None), (len([event for event in self.ledger.events if event["transaction_type"] == "SIC_BO_PAYOUT_CREDIT"]), recovered["state"]["active_round"]))

    # Confirm a crash before terminal lifecycle proof recovers without another movement.
    def test_prefinalize_crash_recovers_completed_payout(self):
        # Fail the terminal lifecycle write after both ledger movements and payout proof persist.
        self.store.fail_on = {5}
        # Execute until the simulated pre-finalization storage crash.
        with self.assertRaises(RuntimeError):
            # Start the deterministic winning action.
            self.service.play("session-player", self.winning_request())
        # Verify exactly one wager and one payout committed before the failure.
        self.assertEqual(2, len(self.ledger.events))
        # Disable later simulated failures for action-owned recovery.
        self.store.fail_on.clear()
        # Resume from provider lifecycle and immutable ledger proof.
        recovered = self.service.play("session-player", self.winning_request())
        # Require one settled round, no third movement, and no active residue.
        self.assertEqual(("settled", 2, None), (recovered["round"]["phase"], len(self.ledger.events), recovered["state"]["active_round"]))

    # Confirm a crash during terminal history publication recovers the exact finalized round.
    def test_prearchive_crash_recovers_finalized_round(self):
        # Fail the provider-current history write after lifecycle finalization persisted.
        self.store.fail_on = {6}
        # Execute until the simulated archival publication crash.
        with self.assertRaises(RuntimeError):
            # Start the deterministic winning action.
            self.service.play("session-player", self.winning_request())
        # Capture the authoritative finalized active record for exact replay comparison.
        finalized = copy.deepcopy(self.store.states["session-player"]["active_round"])
        # Require both movements and terminal lifecycle proof before the failed archive.
        self.assertEqual((2, "settled"), (len(self.ledger.events), finalized["phase"]))
        # Disable later simulated failures for terminal publication recovery.
        self.store.fail_on.clear()
        # Resume and archive the already-finalized action.
        recovered = self.service.play("session-player", self.winning_request())
        # Require the exact public round, no duplicate movement, and one direct history row.
        self.assertEqual((engine.public_round(finalized), 2, 1), (recovered["round"], len(self.ledger.events), len(self.store.states["session-player"]["recent_rounds"])))

    # Confirm a losing result emits no zero-value credit event.
    def test_losing_round_has_no_payout_event(self):
        # Replace deterministic entropy with faces one, two, and four.
        rolls = iter([0, 1, 3])
        # Build a fresh service that covers a losing specific triple.
        service = SicBoService(ledger_gateway=self.ledger, state_loader=self.store.load, state_updater=self.store.update, get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, randbelow=lambda upper: next(rolls), clock=lambda: "2026-07-14T00:00:00.000Z")
        # Execute the losing action.
        result = service.play("session-player", {"action_id": "loss-1", "wagers": {"triple:6": 2}})
        # Verify the public settlement is a loss with zero returned credits.
        self.assertEqual(("loss", 0.0), (result["round"]["outcome"], result["round"]["total_return"]))
        # Verify only the aggregate wager debit exists.
        self.assertEqual(["SIC_BO_WAGER_DEBIT"], [event["transaction_type"] for event in self.ledger.events])

    # Confirm insufficient funds removes uncommitted prepared state.
    def test_insufficient_funds_cleans_uncommitted_recovery(self):
        # Replace the fake ledger with an empty wallet.
        empty_ledger = FakeLedgerGateway(balance=0.0)
        # Build a service against the same isolated state store.
        service = SicBoService(ledger_gateway=empty_ledger, state_loader=self.store.load, state_updater=self.store.update, get_player=lambda player_id: {"player_id": player_id, "balance": empty_ledger.balances[player_id]}, randbelow=lambda upper: 0, clock=lambda: "2026-07-14T00:00:00.000Z")
        # Reject the aggregate debit through the ledger adapter.
        with self.assertRaises(InsufficientFundsError):
            # Attempt a positive wager with no available play tokens.
            service.play("session-player", {"action_id": "no-funds", "wagers": {"small": 1}})
        # Verify no ledger event was created.
        self.assertEqual([], empty_ledger.events)
        # Verify the safe-to-edit active state was cleared.
        self.assertIsNone(self.store.states["session-player"]["active_round"])

    # Confirm bounded history remains direct, oldest-to-newest, and free of helper wrappers.
    def test_history_retains_fifty_direct_terminal_rounds(self):
        # Build a deterministic losing service so 51 actions create only wager movements.
        service = SicBoService(ledger_gateway=self.ledger, state_loader=self.store.load, state_updater=self.store.update, get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, randbelow=lambda _upper: 0, clock=lambda: "2026-07-14T00:00:00.000Z")
        # Execute one action beyond the established history capacity.
        for index in range(engine.RECENT_ROUND_LIMIT + 1):
            # Use a distinct stable action id with the same losing wager semantics.
            service.play("session-player", {"action_id": f"history-{index}", "wagers": {"triple:6": 1}})
        # Read the exact direct persisted history after bounded truncation.
        history = self.store.states["session-player"]["recent_rounds"]
        # Require fifty oldest-to-newest direct rows with the first action evicted.
        self.assertEqual((engine.RECENT_ROUND_LIMIT, "history-1", "history-50"), (len(history), history[0]["action_id"], history[-1]["action_id"]))
        # Reject shared-helper wrapper metadata from the frozen Sic Bo state shape.
        self.assertFalse(any("public" in row or "request_id" in row for row in history))
        # Require no recovery slot after every terminal publication.
        self.assertIsNone(self.store.states["session-player"]["active_round"])

    # Confirm the game owns one helper instance and no direct money-mutation boundary.
    def test_source_uses_one_shared_helper_without_local_gateway(self):
        # Read the exact production service source under test.
        source = (Path(__file__).resolve().parents[3] / "casino" / "games" / "sic_bo" / "service.py").read_text(encoding="utf-8")
        # Bind one coordinator and forbid bespoke gateway or raw movement calls.
        self.assertEqual((1, False, False, False), (source.count("SimpleWagerGame("), "CoreLedgerGateway" in source, ".apply_once(" in source, "GameSettlementGateway" in source))


# Run the focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
