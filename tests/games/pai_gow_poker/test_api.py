# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Session isolation and exactly-once service tests for GitHub issue #138."""

# Import deep-copy support so fake persistence matches JSON document boundaries.
import copy
# Import the standard dependency-free test runner.
import unittest

# Import the real router to exercise authenticated player replacement.
from casino.router import Router
# Import public conflict, lookup, and validation errors for route assertions.
from casino.errors import ConflictError, NotFoundError, ValidationError
# Import the isolated route adapter and pure engine under test.
from casino.games.pai_gow_poker import api, engine
# Import the isolated service orchestration under test.
from casino.games.pai_gow_poker.service import PaiGowPokerService


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
        self.balances = balances or {"session-player": 200.0, "other-player": 200.0}
        # Retain append-only committed event rows.
        self.events = []
        # Allow one focused test to simulate a pre-commit ledger failure.
        self.fail_next = False

    # Find one committed game action for the requested player.
    def find(self, player_id, action_id):
        # Search newest-first using the same game-owned details key.
        return next((event for event in reversed(self.events) if event["player_id"] == player_id and event["game"] == engine.GAME_ID and event["details"]["pai_gow_poker_action_id"] == action_id), None)

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
            raise ValidationError("Insufficient play-token balance")
        # Calculate the candidate balance after the signed movement.
        new_balance = round(self.balances[player_id] + signed_amount, 2)
        # Reject overdrafts like the shared ledger provider.
        if new_balance < 0:
            # Keep the fake state unchanged on rejected debit.
            raise ValidationError("Insufficient play-token balance")
        # Commit the fake balance only through this ledger adapter.
        self.balances[player_id] = new_balance
        # Build the public ledger fields used by service recovery and assertions.
        event = {"ledger_id": f"ledger-{len(self.events) + 1}", "player_id": player_id, "amount": signed_amount, "transaction_type": transaction_type, "game": engine.GAME_ID, "round_id": round_id, "details": {**copy.deepcopy(details), "pai_gow_poker_action_id": action_id, "request_fingerprint": fingerprint}}
        # Append the event once.
        self.events.append(event)
        # Return detached proof and non-replay evidence.
        return copy.deepcopy(event), False


# Verify route binding, retries, crash markers, and ledger audit dimensions.
class PaiGowPokerApiTests(unittest.TestCase):
    # Build isolated state, ledger, service, and router before every test.
    def setUp(self):
        # Create fresh player-scoped state storage.
        self.repository = MemoryRepository()
        # Create fresh fake balances and append-only ledger events.
        self.ledger = RecordingLedger()
        # Provide deterministic card fixtures by deal action id.
        self.fixtures = {
            # A player two-pair-plus hand that beats a weak dealer on both hands.
            "deal-win": {"player_cards": ["AS", "AD", "KS", "KD", "QS", "7C", "2H"], "dealer_cards": ["3C", "4D", "9H", "JS", "2C", "5D", "8H"]},
            # A player hand that loses both hands to a strong dealer.
            "deal-loss": {"player_cards": ["2S", "3D", "4H", "5C", "7S", "9D", "10H"], "dealer_cards": ["AS", "AD", "AH", "KD", "KS", "QS", "QD"]},
        }
        # Build a deterministic service without filesystem or ambient randomness.
        self.service = PaiGowPokerService(ledger_gateway=self.ledger, state_loader=self.repository.load, state_saver=self.repository.save, get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, clock=lambda: "2026-07-24T00:00:00Z", seed_factory=lambda action_id: f"api:{action_id}", fixture_factory=lambda action_id: self.fixtures.get(action_id))
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

    # Start one deterministic round through the public route.
    def start(self, action_id="deal-win", ante=10):
        # Deal through the API so ante settlement is exercised.
        return self.call("/api/v1/games/pai-gow-poker/rounds", {"action_id": action_id, "ante": ante})

    # Confirm hostile body and query player ids cannot override the session.
    def test_session_binding_and_idempotent_ante_deal(self):
        # Start one deal with two competing hostile caller identities.
        first = self.call("/api/v1/games/pai-gow-poker/rounds?player_id=other-player", {"player_id": "other-player", "action_id": "deal-win", "ante": 7})
        # Replay the exact action through the same hostile inputs.
        second = self.call("/api/v1/games/pai-gow-poker/rounds?player_id=other-player", {"player_id": "other-player", "action_id": "deal-win", "ante": 7})
        # Verify round ownership follows only the authenticated session.
        self.assertEqual("session-player", first["round"]["player_id"])
        # Verify another player's balance remains untouched.
        self.assertEqual(200.0, self.ledger.balances["other-player"])
        # Verify the same stable round is returned on replay.
        self.assertEqual(first["round"]["round_id"], second["round"]["round_id"])
        # Verify exactly one ante debit exists.
        debits = [event for event in self.ledger.events if event["transaction_type"] == "PAI_GOW_POKER_ANTE_DEBIT"]
        # Verify both count and signed amount.
        self.assertEqual((1, -7.0), (len(debits), debits[0]["amount"]))
        # Verify all seven player cards are public but dealer cards are absent.
        self.assertEqual(7, len(first["round"]["player_cards"]))
        # Verify dealer cards never appear in the public payload.
        self.assertNotIn("dealer_high", first["round"])
        # Verify the private dealer cards remain reload-safe in persisted state.
        self.assertIn("_dealer_cards", self.repository.documents["session-player"]["active_round"])
        # Read state through a different authenticated session.
        other_context = {"bound_player_id": "other-player", "user": {"player_id": "other-player"}}
        # Request the other player's isolated state while spoofing the first player in the query.
        other_state = self.call("/api/v1/games/pai-gow-poker/state?player_id=session-player", method="GET", context=other_context)
        # Verify the other session cannot read the first player's active hand.
        self.assertIsNone(other_state["state"]["active_round"])
        # Reject an attempt by the other session to decide the first player's round.
        with self.assertRaises(NotFoundError):
            # Exercise cross-session round lookup through the real router.
            self.call(f"/api/v1/games/pai-gow-poker/rounds/{first['round']['round_id']}/decisions", {"action_id": "decision-cross-session", "set": "house_way", "player_id": "session-player"}, context=other_context)

    # Confirm conflicting deal retries and insufficient funds fail without extra state.
    def test_deal_conflict_and_rejected_ante_cleanup(self):
        # Commit one valid ante action.
        self.start("deal-win", ante=3)
        # Reject reuse of the same identity with a changed ante.
        with self.assertRaises(ConflictError):
            # Exercise the conflicting semantic fingerprint.
            self.call("/api/v1/games/pai-gow-poker/rounds", {"action_id": "deal-win", "ante": 4})
        # Build a separate empty-balance service for rollback behavior.
        empty_ledger = RecordingLedger({"session-player": 0.0})
        # Build fresh storage for the rejected action.
        empty_repository = MemoryRepository()
        # Create the isolated empty-balance service.
        empty_service = PaiGowPokerService(ledger_gateway=empty_ledger, state_loader=empty_repository.load, state_saver=empty_repository.save, get_player=lambda player_id: {"player_id": player_id, "balance": empty_ledger.balances[player_id]}, clock=lambda: "2026-07-24T00:00:00Z", fixture_factory=lambda action_id: self.fixtures["deal-win"])
        # Reject the debit without committing a ledger row.
        with self.assertRaises(ValidationError):
            # Attempt one unaffordable round.
            empty_service.start_round("session-player", {"action_id": "deal-no-funds", "ante": 1})
        # Verify no active decision is stranded after a non-committed ante.
        self.assertIsNone(empty_repository.documents["session-player"]["active_round"])
        # Verify no ledger event exists for the rejected action.
        self.assertEqual([], empty_ledger.events)

    # Confirm the set decision settles once and the settlement credit is replay-safe.
    def test_set_replay_and_settlement_recovery(self):
        # Deal a deterministic player-win round.
        started = self.start("deal-win", ante=10)
        # Set by the house way once through the public route.
        first = self.call(f"/api/v1/games/pai-gow-poker/rounds/{started['round']['round_id']}/decisions", {"action_id": "decision-set", "set": "house_way"})
        # Simulate a crash after credit but before the completion marker save.
        self.repository.documents["session-player"]["recent_rounds"][-1]["settlement_status"] = "pending"
        # Remove cached ledger id so reload must recover it from append-only proof.
        self.repository.documents["session-player"]["recent_rounds"][-1].pop("settlement_ledger_id", None)
        # Recreate service state behavior through a normal GET reload.
        reloaded = self.call("/api/v1/games/pai-gow-poker/state", method="GET")
        # Replay the same decision after reload.
        second = self.call(f"/api/v1/games/pai-gow-poker/rounds/{started['round']['round_id']}/decisions", {"action_id": "decision-set", "set": "house_way"})
        # Verify the deterministic win pays the ante back plus even money minus commission.
        self.assertEqual(("win", 19.5, True), (first["round"]["outcome"], first["round"]["payout"], second["replayed"]))
        # Verify reload restored a complete settlement marker.
        self.assertEqual("complete", reloaded["state"]["recent_rounds"][-1]["settlement_status"])
        # Verify exactly one ante and one settlement event exist.
        self.assertEqual((1, 1), (len([event for event in self.ledger.events if event["transaction_type"] == "PAI_GOW_POKER_ANTE_DEBIT"]), len([event for event in self.ledger.events if event["transaction_type"] == "PAI_GOW_POKER_SETTLEMENT_CREDIT"])))
        # Verify settlement audit dimensions include the player, game, round, and action-derived id.
        settlement = [event for event in self.ledger.events if event["transaction_type"] == "PAI_GOW_POKER_SETTLEMENT_CREDIT"][0]
        # Compare core ledger dimensions.
        self.assertEqual(("session-player", engine.GAME_ID, started["round"]["round_id"], "decision-set:settlement"), (settlement["player_id"], settlement["game"], settlement["round_id"], settlement["details"]["pai_gow_poker_action_id"]))

    # Confirm a losing set creates no settlement credit and forfeits only the ante.
    def test_loss_creates_no_settlement_event(self):
        # Deal a deterministic losing round.
        started = self.start("deal-loss", ante=6)
        # Set by the house way once through the public route.
        result = self.call(f"/api/v1/games/pai-gow-poker/rounds/{started['round']['round_id']}/decisions", {"action_id": "decision-loss", "set": "house_way"})
        # Verify the terminal loss returns no tokens.
        self.assertEqual(("loss", 0.0), (result["round"]["outcome"], result["round"]["payout"]))
        # Verify no settlement ledger row was created.
        self.assertEqual(0, len([event for event in self.ledger.events if event["transaction_type"] == "PAI_GOW_POKER_SETTLEMENT_CREDIT"]))
        # Verify the player balance reflects only the ante debit.
        self.assertEqual(194.0, self.ledger.balances["session-player"])

    # Confirm an illegal explicit split is rejected without settling.
    def test_illegal_split_is_rejected(self):
        # Deal a deterministic round whose seven cards make an illegal split available.
        started = self.start("deal-loss", ante=6)
        # Attempt to set the two highest cards low beneath a weaker five-card high hand.
        with self.assertRaises(ValidationError):
            # Exercise the illegal set: a ten-nine low would outrank a seven-high five-card hand.
            self.call(f"/api/v1/games/pai-gow-poker/rounds/{started['round']['round_id']}/decisions", {"action_id": "decision-illegal", "set": [5, 6]})
        # Verify the active round is still awaiting a legal set.
        active = self.repository.documents["session-player"]["active_round"]
        # Verify no settlement occurred.
        self.assertEqual("setting", active["phase"])

    # Confirm conflicting terminal retries fail closed.
    def test_conflicting_decision_retry_fails_closed(self):
        # Deal one deterministic round.
        started = self.start("deal-win", ante=5)
        # Set by the house way once.
        self.call(f"/api/v1/games/pai-gow-poker/rounds/{started['round']['round_id']}/decisions", {"action_id": "decision-conflict", "set": "house_way"})
        # Reject reuse of the same decision identity with a different set choice.
        with self.assertRaises(ConflictError):
            # Exercise conflicting terminal semantics.
            self.call(f"/api/v1/games/pai-gow-poker/rounds/{started['round']['round_id']}/decisions", {"action_id": "decision-conflict", "set": [0, 1]})


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
