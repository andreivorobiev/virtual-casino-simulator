# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Session isolation and exactly-once service tests for integrated Plinko."""

# Import deep-copy support so fake persistence matches JSON document boundaries.
import copy
# Import the standard dependency-free test runner.
import unittest

# Import the real router to exercise authenticated player replacement.
from casino.router import Router
# Import public conflict and validation errors for route assertions.
from casino.errors import ConflictError, ValidationError
# Import the isolated route adapter and pure engine under test.
from casino.games.plinko import api, engine
# Import the isolated service orchestration under test.
from casino.games.plinko.service import PlinkoService


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

    # Find one committed game action for the requested player.
    def find(self, player_id, action_id):
        # Search newest-first using the same game-owned details key.
        return next((event for event in reversed(self.events) if event["player_id"] == player_id and event["game"] == engine.GAME_ID and event["details"]["plinko_action_id"] == action_id), None)

    # Apply or recover one signed movement exactly once.
    def apply_once(self, *, player_id, signed_amount, transaction_type, drop_id, action_id, fingerprint, details):
        # Resolve any prior committed action before changing the fake balance.
        existing = self.find(player_id, action_id)
        # Reuse an exact matching event.
        if existing is not None:
            # Reject semantic conflicts like the production gateway.
            if existing["amount"] != signed_amount or existing["transaction_type"] != transaction_type or existing["round_id"] != drop_id or existing["details"]["request_fingerprint"] != fingerprint:
                # Fail before a second movement.
                raise ConflictError("fake action identity conflict")
            # Return immutable proof and replay evidence.
            return copy.deepcopy(existing), True
        # Calculate the candidate balance after the signed movement.
        new_balance = round(self.balances[player_id] + signed_amount, 2)
        # Reject overdrafts like the shared ledger provider.
        if new_balance < 0:
            # Keep the fake state unchanged on rejected debit.
            raise ValidationError("Insufficient fake balance")
        # Commit the fake balance only through this ledger adapter.
        self.balances[player_id] = new_balance
        # Build the public ledger fields used by service recovery and assertions.
        event = {"ledger_id": f"ledger-{len(self.events) + 1}", "player_id": player_id, "amount": signed_amount, "transaction_type": transaction_type, "game": engine.GAME_ID, "round_id": drop_id, "details": {**copy.deepcopy(details), "plinko_action_id": action_id, "request_fingerprint": fingerprint}}
        # Append the event once.
        self.events.append(event)
        # Return detached proof and non-replay evidence.
        return copy.deepcopy(event), False


# Verify route binding, retries, recovery, and ledger audit dimensions.
class PlinkoApiTests(unittest.TestCase):
    # Build isolated state, ledger, service, and router before every test.
    def setUp(self):
        # Create fresh player-scoped state storage.
        self.repository = MemoryRepository()
        # Create fresh fake balances and append-only ledger events.
        self.ledger = RecordingLedger()
        # Build a deterministic service without filesystem or ambient randomness.
        self.service = PlinkoService(ledger_gateway=self.ledger, state_loader=self.repository.load, state_saver=self.repository.save, get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:00Z", seed_factory=lambda action_id: f"api:{action_id}")
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

    # Confirm hostile body and query player ids cannot override the session.
    def test_session_binding_and_idempotent_drop(self):
        # Start one drop with two competing hostile caller identities.
        first = self.call("/api/v1/games/plinko/drops?player_id=other-player", {"player_id": "other-player", "action_id": "drop-retry-1", "wager": 7})
        # Replay the exact action through the same hostile inputs.
        second = self.call("/api/v1/games/plinko/drops?player_id=other-player", {"player_id": "other-player", "action_id": "drop-retry-1", "wager": 7})
        # Verify drop ownership follows only the authenticated session.
        self.assertEqual("session-player", first["drop"]["player_id"])
        # Verify another player's balance remains untouched.
        self.assertEqual(100.0, self.ledger.balances["other-player"])
        # Verify the same stable drop is returned on replay.
        self.assertEqual(first["drop"]["drop_id"], second["drop"]["drop_id"])
        # Verify exactly one wager debit and one payout credit exist.
        debits = [event for event in self.ledger.events if event["transaction_type"] == "PLINKO_WAGER_DEBIT"]
        # Verify count and signed debit amount.
        self.assertEqual((1, -7.0), (len(debits), debits[0]["amount"]))
        # Verify the public payload includes committed replay facts.
        self.assertEqual(engine.ROWS, len(first["drop"]["path"]))
        # Verify rules disclosure exactly matches the server settlement table.
        self.assertEqual(list(engine.MULTIPLIERS), first["rules"]["multipliers"])
        # Verify the internal request fingerprint stays private.
        self.assertNotIn("request_fingerprint", first["drop"])
        # Read state through a different authenticated session.
        other_context = {"bound_player_id": "other-player", "user": {"player_id": "other-player"}}
        # Request the other player's isolated state while spoofing the first player in the query.
        other_state = self.call("/api/v1/games/plinko/state?player_id=session-player", method="GET", context=other_context)
        # Verify the other session cannot read the first player's drops.
        self.assertEqual([], other_state["state"]["recent_drops"])

    # Confirm conflicting retries and insufficient funds fail without extra state.
    def test_drop_conflict_and_rejected_debit_cleanup(self):
        # Commit one valid wager action.
        self.call("/api/v1/games/plinko/drops", {"action_id": "drop-conflict", "wager": 3})
        # Reject reuse of the same identity with a changed wager.
        with self.assertRaises(ConflictError):
            # Exercise the conflicting semantic fingerprint.
            self.call("/api/v1/games/plinko/drops", {"action_id": "drop-conflict", "wager": 4})
        # Build a separate empty-balance service for rollback behavior.
        empty_ledger = RecordingLedger({"session-player": 0.0})
        # Build fresh storage for the rejected action.
        empty_repository = MemoryRepository()
        # Create the isolated empty-balance service.
        empty_service = PlinkoService(ledger_gateway=empty_ledger, state_loader=empty_repository.load, state_saver=empty_repository.save, get_player=lambda player_id: {"player_id": player_id, "balance": empty_ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:00Z", seed_factory=lambda action_id: action_id)
        # Reject the debit without committing a ledger row.
        with self.assertRaises(ValidationError):
            # Attempt one unaffordable drop.
            empty_service.drop("session-player", {"action_id": "drop-no-funds", "wager": 1})
        # Verify no drop history is stranded after a non-committed debit.
        self.assertEqual([], empty_repository.documents["session-player"]["recent_drops"])
        # Verify no ledger event exists for the rejected action.
        self.assertEqual([], empty_ledger.events)

    # Confirm a payout marker recovers after a reload without duplicate movement.
    def test_settlement_marker_recovery_after_reload(self):
        # Commit one deterministic drop.
        first = self.call("/api/v1/games/plinko/drops", {"action_id": "drop-recover", "wager": 8})
        # Simulate a crash after credit but before the completion marker save.
        self.repository.documents["session-player"]["recent_drops"][-1]["settlement_status"] = "pending"
        # Remove cached ledger id so reload must recover it from append-only proof.
        self.repository.documents["session-player"]["recent_drops"][-1].pop("settlement_ledger_id", None)
        # Recreate service state behavior through a normal GET reload.
        reloaded = self.call("/api/v1/games/plinko/state", method="GET")
        # Replay the same drop after reload.
        second = self.call("/api/v1/games/plinko/drops", {"action_id": "drop-recover", "wager": 8})
        # Verify deterministic result and explicit replay behavior.
        self.assertEqual((first["drop"]["drop_id"], True), (second["drop"]["drop_id"], second["replayed"]))
        # Verify reload restored a complete settlement marker.
        self.assertEqual("complete", reloaded["state"]["recent_drops"][-1]["settlement_status"])
        # Verify exactly one payout credit exists after recovery and replay.
        credits = [event for event in self.ledger.events if event["transaction_type"] == "PLINKO_PAYOUT_CREDIT"]
        # Verify the returned amount and complete audit dimensions.
        self.assertEqual((1, first["drop"]["payout"], "session-player", engine.GAME_ID, first["drop"]["drop_id"]), (len(credits), credits[0]["amount"], credits[0]["player_id"], credits[0]["game"], credits[0]["round_id"]))

    # Confirm durable receipts prevent action reuse after bounded history pruning.
    def test_action_receipt_survives_history_pruning(self):
        # Commit one ordinary drop and its durable action receipt.
        self.call("/api/v1/games/plinko/drops", {"action_id": "drop-old", "wager": 2})
        # Simulate the normal bounded-history pruning of an old public drop.
        self.repository.documents["session-player"]["recent_drops"] = []
        # Reject reuse of the pruned identity instead of debiting again.
        with self.assertRaises(ConflictError):
            # Attempt the same semantic drop after its drop body is absent.
            self.call("/api/v1/games/plinko/drops", {"action_id": "drop-old", "wager": 2})
        # Verify exactly one wager debit remains committed for that action.
        self.assertEqual(1, len([event for event in self.ledger.events if event["transaction_type"] == "PLINKO_WAGER_DEBIT"]))


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
