# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Session isolation and exactly-once service tests for GitHub issue #85."""

# Import deep-copy support so fake persistence matches JSON document boundaries.
import copy
# Import the standard dependency-free test runner.
import unittest

# Import the real router to exercise authenticated player replacement.
from casino.router import Router
# Import public conflict, lookup, and validation errors for route assertions.
from casino.errors import ConflictError, NotFoundError, ValidationError
# Import the isolated route adapter and pure engine under test.
from casino.games.hi_lo import api, engine
# Import the isolated service orchestration under test.
from casino.games.hi_lo.service import HiLoService


# Simulate player-scoped state documents without touching repository data files.
class MemoryRepository:
    # Start with no persisted game documents.
    def __init__(self):
        # Store detached documents by authenticated player id.
        self.documents = {}

    # Load one detached state document or a fresh default.
    def load(self, player_id):
        # Copy state so every mutation requires an explicit save.
        return copy.deepcopy(self.documents.get(player_id, engine.default_state()))

    # Save one detached player document.
    def save(self, player_id, state):
        # Persist a deep copy to model the JSON/provider boundary.
        self.documents[player_id] = copy.deepcopy(state)


# Record signed ledger events and enforce action-id replay behavior in memory.
class RecordingLedger:
    # Seed deterministic balances for two isolated session players.
    def __init__(self, balances=None):
        # Store fake balances only inside this ledger adapter.
        self.balances = balances or {"session-player": 100.0, "other-player": 100.0}
        # Retain append-only committed event rows.
        self.events = []
        # Allow one focused test to simulate a pre-commit ledger failure.
        self.fail_next = False

    # Find one committed game action for the requested player.
    def find(self, player_id, action_id):
        # Search newest-first using the same game-owned details key.
        return next((event for event in reversed(self.events) if event["player_id"] == player_id and event["game"] == engine.GAME_ID and event["details"]["hi_lo_action_id"] == action_id), None)

    # Apply or recover one signed movement exactly once.
    def apply_once(self, *, player_id, signed_amount, transaction_type, round_id, action_id, fingerprint, details):
        # Resolve any prior committed action before changing the fake balance.
        existing = self.find(player_id, action_id)
        # Reuse an exact matching event.
        if existing is not None:
            # Reject semantic conflicts like the production gateway.
            if existing["amount"] != signed_amount or existing["transaction_type"] != transaction_type or existing["round_id"] != round_id or existing["details"]["request_fingerprint"] != fingerprint:
                # Fail before a second movement.
                raise ConflictError("fake action identity conflict")
            # Return immutable proof and replay evidence.
            return copy.deepcopy(existing), True
        # Simulate one failure before any append-only event exists.
        if self.fail_next:
            # Consume the one-shot failure flag.
            self.fail_next = False
            # Raise a public validation-shaped insufficient-funds error.
            raise ValidationError("Insufficient fake balance")
        # Calculate the candidate balance after the signed movement.
        new_balance = round(self.balances[player_id] + signed_amount, 2)
        # Reject overdrafts like the shared ledger provider.
        if new_balance < 0:
            # Keep the fake state unchanged on rejected debit.
            raise ValidationError("Insufficient fake balance")
        # Commit the fake balance only through this ledger adapter.
        self.balances[player_id] = new_balance
        # Build the public ledger fields used by service recovery and assertions.
        event = {"ledger_id": f"ledger-{len(self.events) + 1}", "player_id": player_id, "amount": signed_amount, "transaction_type": transaction_type, "game": engine.GAME_ID, "round_id": round_id, "details": {**copy.deepcopy(details), "hi_lo_action_id": action_id, "request_fingerprint": fingerprint}}
        # Append the event once.
        self.events.append(event)
        # Return detached proof and non-replay evidence.
        return copy.deepcopy(event), False


# Verify route binding, retries, crash markers, and ledger audit dimensions.
class HiLoApiTests(unittest.TestCase):
    # Build isolated state, ledger, service, and router before every test.
    def setUp(self):
        # Create fresh player-scoped state storage.
        self.repository = MemoryRepository()
        # Create fresh fake balances and append-only ledger events.
        self.ledger = RecordingLedger()
        # Build a deterministic service without filesystem or ambient randomness.
        self.service = HiLoService(ledger_gateway=self.ledger, state_loader=self.repository.load, state_saver=self.repository.save, get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:00Z", seed_factory=lambda action_id: f"api:{action_id}")
        # Register only the game-owned routes on the real shared router.
        self.router = Router()
        # Inject the focused service without changing global registration.
        api.register(self.router, service=self.service)
        # Store the authenticated request context that must override caller ids.
        self.context = {"bound_player_id": "session-player", "user": {"player_id": "session-player"}}

    # Dispatch one game action through the real shared resolver path.
    def call(self, path, body=None, method="POST", context=None):
        # Delegate with a copied context so router mutations remain request-local.
        return self.router.dispatch(method, path, body or {}, context=dict(context or self.context))

    # Prepare one active fixture round with a committed wager marker.
    def prepared_round(self, current_card, next_card, wager=5, action_id="deal-fixture"):
        # Compute the same deal fingerprint shape as production.
        from casino.games.hi_lo.service import request_fingerprint
        # Build the deterministic deal fingerprint.
        fingerprint = request_fingerprint({"stage": "deal", "wager": float(wager)})
        # Derive the stable round id from player and action identity.
        round_id = engine.round_id_for("session-player", action_id)
        # Create the prepared private state.
        round_state = engine.create_round("session-player", wager, action_id, current_card=current_card, next_card=next_card, round_id=round_id, created_at="2026-07-14T00:00:00Z", request_fingerprint=fingerprint)
        # Mark the fixture wager committed before testing settlement.
        round_state["wager_status"] = "complete"
        # Store the fake committed wager identifier.
        round_state["wager_ledger_id"] = "ledger-fixture"
        # Persist the active player document.
        self.repository.save("session-player", {"active_round": round_state, "recent_rounds": []})
        # Reflect the already-paid fixture wager in the fake balance.
        self.ledger.balances["session-player"] = round(100.0 - wager, 2)
        # Return the stable route id.
        return round_id

    # Confirm hostile body and query player ids cannot override the session.
    def test_session_binding_and_idempotent_deal(self):
        # Start one deal with two competing hostile caller identities.
        first = self.call("/api/v1/games/hi-lo/rounds?player_id=other-player", {"player_id": "other-player", "action_id": "deal-retry-1", "wager": 7})
        # Replay the exact action through the same hostile inputs.
        second = self.call("/api/v1/games/hi-lo/rounds?player_id=other-player", {"player_id": "other-player", "action_id": "deal-retry-1", "wager": 7})
        # Verify round ownership follows only the authenticated session.
        self.assertEqual("session-player", first["round"]["player_id"])
        # Verify another player's balance remains untouched.
        self.assertEqual(100.0, self.ledger.balances["other-player"])
        # Verify the same stable round is returned on replay.
        self.assertEqual(first["round"]["round_id"], second["round"]["round_id"])
        # Verify exactly one wager debit exists.
        debits = [event for event in self.ledger.events if event["transaction_type"] == "HI_LO_WAGER_DEBIT"]
        # Require the legacy scalar plus the exact additive server-owned rank table.
        self.assertEqual((2, engine.correct_paytable(), engine.HOUSE_EDGE), (first["rules"]["correct_return_multiplier"], first["rules"]["correct_paytable"], first["rules"]["house_edge"]))
        # Verify both count and signed amount.
        self.assertEqual((1, -7.0), (len(debits), debits[0]["amount"]))
        # Verify wager audit details never disclose the private reveal card.
        self.assertNotIn("next_card", debits[0]["details"])
        # Verify the hidden reveal card is absent from the public payload.
        self.assertNotIn("_next_card", first["round"])
        # Verify the private card remains reload-safe in persisted state.
        self.assertIn("_next_card", self.repository.documents["session-player"]["active_round"])
        # Read state through a different authenticated session.
        other_context = {"bound_player_id": "other-player", "user": {"player_id": "other-player"}}
        # Request the other player's isolated state while spoofing the first player in the query.
        other_state = self.call("/api/v1/games/hi-lo/state?player_id=session-player", method="GET", context=other_context)
        # Verify the other session cannot read the first player's active card.
        self.assertIsNone(other_state["state"]["active_round"])
        # Reject an attempt by the other session to guess the first player's round.
        with self.assertRaises(NotFoundError):
            # Exercise cross-session round lookup through the real router.
            self.call(f"/api/v1/games/hi-lo/rounds/{first['round']['round_id']}/guesses", {"action_id": "guess-cross-session", "guess": "higher", "player_id": "session-player"}, context=other_context)

    # Confirm conflicting deal retries and insufficient funds fail without extra state.
    def test_deal_conflict_and_rejected_debit_cleanup(self):
        # Commit one valid wager action.
        self.call("/api/v1/games/hi-lo/rounds", {"action_id": "deal-conflict", "wager": 3})
        # Reject reuse of the same identity with a changed wager.
        with self.assertRaises(ConflictError):
            # Exercise the conflicting semantic fingerprint.
            self.call("/api/v1/games/hi-lo/rounds", {"action_id": "deal-conflict", "wager": 4})
        # Build a separate empty-balance service for rollback behavior.
        empty_ledger = RecordingLedger({"session-player": 0.0})
        # Build fresh storage for the rejected action.
        empty_repository = MemoryRepository()
        # Create the isolated empty-balance service.
        empty_service = HiLoService(ledger_gateway=empty_ledger, state_loader=empty_repository.load, state_saver=empty_repository.save, get_player=lambda player_id: {"player_id": player_id, "balance": empty_ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:00Z", seed_factory=lambda action_id: action_id)
        # Reject the debit without committing a ledger row.
        with self.assertRaises(ValidationError):
            # Attempt one unaffordable round.
            empty_service.start_round("session-player", {"action_id": "deal-no-funds", "wager": 1})
        # Verify no active decision is stranded after a non-committed debit.
        self.assertIsNone(empty_repository.documents["session-player"]["active_round"])
        # Verify no ledger event exists for the rejected action.
        self.assertEqual([], empty_ledger.events)

    # Confirm a committed debit survives a lost state marker and service restart.
    def test_deal_marker_recovery_after_restart(self):
        # Commit one deterministic wagered deal.
        first = self.call("/api/v1/games/hi-lo/rounds", {"action_id": "deal-recover", "wager": 8})
        # Simulate a crash after debit commit but before its completion marker save.
        self.repository.documents["session-player"]["active_round"]["wager_status"] = "pending"
        # Remove the cached ledger id so recovery must scan append-only proof.
        self.repository.documents["session-player"]["active_round"].pop("wager_ledger_id", None)
        # Recreate the service to prove no process-local cache is required.
        restarted = HiLoService(ledger_gateway=self.ledger, state_loader=self.repository.load, state_saver=self.repository.save, get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:02Z", seed_factory=lambda action_id: f"restart:{action_id}")
        # Replay the exact deal through the restarted service.
        second = restarted.start_round("session-player", {"action_id": "deal-recover", "wager": 8})
        # Verify the original private card plan and round identity survive restart.
        self.assertEqual(first["round"], second["round"])
        # Verify the restarted replay reports idempotent recovery.
        self.assertTrue(second["replayed"])
        # Verify only one wager debit exists after recovery.
        self.assertEqual(1, len([event for event in self.ledger.events if event["transaction_type"] == "HI_LO_WAGER_DEBIT"]))

    # Confirm a prepared round without debit proof cannot reveal or receive a payout.
    def test_guess_cannot_settle_an_uncommitted_wager(self):
        # Build one private prepared round without a matching ledger event.
        round_id = self.prepared_round("2H", "AS", wager=5, action_id="deal-uncommitted")
        # Replace the fixture's committed marker with the exact pre-debit crash state.
        self.repository.documents["session-player"]["active_round"]["wager_status"] = "pending"
        # Remove the cached fixture ledger id.
        self.repository.documents["session-player"]["active_round"].pop("wager_ledger_id", None)
        # Restore the balance because no wager debit actually committed.
        self.ledger.balances["session-player"] = 100.0
        # Reject the reveal because recovery clears the non-wagered prepared round.
        with self.assertRaises(NotFoundError):
            # Attempt a guaranteed winning guess against the hidden card.
            self.service.guess("session-player", round_id, {"action_id": "guess-free", "guess": "higher"})
        # Verify no payout or refund ledger event was created.
        self.assertEqual([], self.ledger.events)
        # Verify the uncommitted active round was removed.
        self.assertIsNone(self.repository.documents["session-player"]["active_round"])

    # Confirm payout retry and post-credit marker recovery never duplicate movement.
    def test_correct_guess_replay_and_state_reload_recovery(self):
        # Prepare a guaranteed higher result.
        round_id = self.prepared_round("2H", "AS", wager=5)
        # Settle once through the public route.
        first = self.call(f"/api/v1/games/hi-lo/rounds/{round_id}/guesses", {"action_id": "guess-win", "guess": "higher"})
        # Simulate a crash after credit but before the completion marker save.
        self.repository.documents["session-player"]["recent_rounds"][-1]["settlement_status"] = "pending"
        # Remove cached ledger id so reload must recover it from append-only proof.
        self.repository.documents["session-player"]["recent_rounds"][-1].pop("settlement_ledger_id", None)
        # Recreate service state behavior through a normal GET reload.
        reloaded = self.call("/api/v1/games/hi-lo/state", method="GET")
        # Replay the same guess after reload.
        second = self.call(f"/api/v1/games/hi-lo/rounds/{round_id}/guesses", {"action_id": "guess-win", "guess": "higher"})
        # Derive the expected return from the visible 2 rank price (0.96 on a near-certain higher call). (issue #406)
        expected_payout = round(5 * engine.correct_return_multiplier("2H"), 2)
        # Verify deterministic result and explicit replay behavior.
        self.assertEqual(("correct", expected_payout, True), (first["round"]["outcome"], first["round"]["payout"], second["replayed"]))
        # Verify reload restored a complete settlement marker.
        self.assertEqual("complete", reloaded["state"]["recent_rounds"][-1]["settlement_status"])
        # Verify exactly one payout credit exists after recovery and replay.
        credits = [event for event in self.ledger.events if event["transaction_type"] == "HI_LO_PAYOUT_CREDIT"]
        # Verify the returned amount and complete audit dimensions.
        self.assertEqual((1, expected_payout, "session-player", engine.GAME_ID, round_id, "guess-win"), (len(credits), credits[0]["amount"], credits[0]["player_id"], credits[0]["game"], credits[0]["round_id"], credits[0]["details"]["hi_lo_action_id"]))
        # Require the ledger audit row to retain the exact authoritative rank price.
        self.assertEqual(engine.correct_return_multiplier("2H"), credits[0]["details"]["correct_return_multiplier"])

    # Confirm equal ranks refund once and a changed terminal retry fails closed.
    def test_tie_refund_and_conflicting_guess_retry(self):
        # Prepare equal ranks in different suits.
        round_id = self.prepared_round("7H", "7S", wager=6, action_id="deal-tie")
        # Settle the tie once.
        result = self.call(f"/api/v1/games/hi-lo/rounds/{round_id}/guesses", {"action_id": "guess-tie", "guess": "lower"})
        # Verify documented tie outcome and full stake refund.
        self.assertEqual(("tie", 6.0), (result["round"]["outcome"], result["round"]["payout"]))
        # Verify one distinct refund credit exists.
        refunds = [event for event in self.ledger.events if event["transaction_type"] == "HI_LO_REFUND_CREDIT"]
        # Verify count and returned amount.
        self.assertEqual((1, 6.0), (len(refunds), refunds[0]["amount"]))
        # Reject the same action id with a changed direction.
        with self.assertRaises(ConflictError):
            # Exercise the conflicting terminal fingerprint.
            self.call(f"/api/v1/games/hi-lo/rounds/{round_id}/guesses", {"action_id": "guess-tie", "guess": "higher"})
        # Verify the conflicting retry created no second refund.
        self.assertEqual(1, len([event for event in self.ledger.events if event["transaction_type"] == "HI_LO_REFUND_CREDIT"]))

    # Confirm an incorrect prediction records no zero-value credit.
    def test_incorrect_guess_creates_no_settlement_event(self):
        # Prepare a guaranteed incorrect higher prediction.
        round_id = self.prepared_round("KH", "3S", wager=4, action_id="deal-loss")
        # Settle the losing direction once.
        result = self.call(f"/api/v1/games/hi-lo/rounds/{round_id}/guesses", {"action_id": "guess-loss", "guess": "higher"})
        # Verify the documented losing result and zero returned tokens.
        self.assertEqual(("incorrect", 0.0, "complete"), (result["round"]["outcome"], result["round"]["payout"], result["round"]["settlement_status"]))
        # Verify the game never asks the shared ledger to append a zero credit.
        self.assertEqual([], self.ledger.events)
        # Verify only the already-paid fixture wager remains reflected in balance.
        self.assertEqual(96.0, self.ledger.balances["session-player"])

    # Confirm durable receipts prevent action reuse after bounded history pruning.
    def test_action_receipt_survives_round_history_pruning(self):
        # Commit one ordinary deal and its durable action receipt.
        started = self.call("/api/v1/games/hi-lo/rounds", {"action_id": "deal-old", "wager": 2})
        # Read the private test fixture card only to complete the round deterministically.
        hidden = self.repository.documents["session-player"]["active_round"]["_next_card"]
        # Read the visible card rank value.
        current_value = engine.RANK_VALUES[started["round"]["current_card"][:-1]]
        # Read the hidden card rank value.
        next_value = engine.RANK_VALUES[hidden[:-1]]
        # Choose one legal direction regardless of whether the cards tie.
        guess = "higher" if next_value >= current_value else "lower"
        # Settle the round so the active slot becomes free.
        self.call(f"/api/v1/games/hi-lo/rounds/{started['round']['round_id']}/guesses", {"action_id": "guess-old", "guess": guess})
        # Simulate the normal bounded-history pruning of an old public round.
        self.repository.documents["session-player"]["recent_rounds"] = []
        # Reject reuse of the pruned deal identity instead of debiting again.
        with self.assertRaises(ConflictError):
            # Attempt the same semantic deal after its round body is absent.
            self.call("/api/v1/games/hi-lo/rounds", {"action_id": "deal-old", "wager": 2})
        # Verify exactly one wager debit remains committed for that action.
        self.assertEqual(1, len([event for event in self.ledger.events if event["transaction_type"] == "HI_LO_WAGER_DEBIT"]))


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
