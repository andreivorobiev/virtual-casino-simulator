"""Session binding and ledger retry tests for Acey-Deucey."""

# Import deep-copy support so fake persistence models JSON documents.
import copy
# Import the standard dependency-free test runner.
import unittest

# Import the shared router to exercise route binding.
from casino.router import Router
# Import public conflict and lookup errors for assertions.
from casino.errors import ConflictError, NotFoundError
# Import the isolated route adapter and engine under test.
from casino.games.acey_deucey import api, engine
# Import the isolated service orchestration under test.
from casino.games.acey_deucey.service import AceyDeuceyService, request_fingerprint


# Simulate player-scoped state documents without touching repository data files.
class MemoryRepository:
    # Start with no persisted documents.
    def __init__(self):
        # Store detached state documents by player id.
        self.documents = {}

    # Load one detached state document or a fresh default.
    def load(self, player_id):
        # Copy state so service mutations require explicit saves.
        return copy.deepcopy(self.documents.get(player_id, engine.default_state()))

    # Save one detached player document.
    def save(self, player_id, state):
        # Persist a deep copy to model the provider boundary.
        self.documents[player_id] = copy.deepcopy(state)


# Record signed ledger events and enforce action-id replay behavior in memory.
class RecordingLedger:
    # Seed deterministic balances for two isolated players.
    def __init__(self):
        # Store fake balances only inside this ledger adapter.
        self.balances = {"session-player": 100.0, "other-player": 100.0}
        # Retain append-only committed events.
        self.events = []

    # Find one committed Acey-Deucey ledger action.
    def find(self, player_id, ledger_action_id):
        # Search newest-first using the production details key.
        return next((event for event in reversed(self.events) if event["player_id"] == player_id and event["game"] == engine.GAME_ID and event["details"]["acey_deucey_action_id"] == ledger_action_id), None)

    # Apply or recover one signed movement exactly once.
    def apply_once(self, *, player_id, signed_amount, transaction_type, round_id, ledger_action_id, fingerprint, details):
        # Resolve any prior committed action before changing balance.
        existing = self.find(player_id, ledger_action_id)
        # Reuse exact matching events.
        if existing is not None:
            # Reject semantic conflicts like production.
            if existing["amount"] != signed_amount or existing["transaction_type"] != transaction_type or existing["round_id"] != round_id or existing["details"]["request_fingerprint"] != fingerprint:
                # Fail before a second movement.
                raise ConflictError("fake action identity conflict")
            # Return detached proof and replay evidence.
            return copy.deepcopy(existing), True
        # Calculate the candidate balance.
        new_balance = round(self.balances[player_id] + signed_amount, 2)
        # Reject fake overdrafts.
        if new_balance < 0:
            # Raise the same broad error class the service propagates.
            raise ConflictError("insufficient fake balance")
        # Commit the fake balance.
        self.balances[player_id] = new_balance
        # Build public ledger fields used by assertions.
        event = {"ledger_id": f"ledger-{len(self.events) + 1}", "player_id": player_id, "amount": signed_amount, "transaction_type": transaction_type, "game": engine.GAME_ID, "round_id": round_id, "details": {**copy.deepcopy(details), "acey_deucey_action_id": ledger_action_id, "request_fingerprint": fingerprint}}
        # Append the event once.
        self.events.append(event)
        # Return detached proof and non-replay evidence.
        return copy.deepcopy(event), False


# Verify route binding, retries, pass behavior, and ledger audit dimensions.
class AceyDeuceyApiTests(unittest.TestCase):
    # Build isolated state, ledger, service, and router before each test.
    def setUp(self):
        # Create fresh player-scoped state storage.
        self.repository = MemoryRepository()
        # Create fresh fake balances and append-only ledger events.
        self.ledger = RecordingLedger()
        # Build a deterministic service without filesystem or ambient randomness.
        self.service = AceyDeuceyService(ledger_gateway=self.ledger, state_loader=self.repository.load, state_saver=self.repository.save, get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:00Z", seed_factory=lambda action_id: f"api:{action_id}")
        # Register only game-owned routes on the shared router.
        self.router = Router()
        # Inject the focused service without global registration.
        api.register(self.router, service=self.service)
        # Store authenticated context that must override caller ids.
        self.context = {"bound_player_id": "session-player", "user": {"player_id": "session-player"}}

    # Dispatch one game action through the router.
    def call(self, path, body=None, method="POST", context=None):
        # Delegate with copied context so requests remain isolated.
        return self.router.dispatch(method, path, body or {}, context=dict(context or self.context))

    # Prepare one active deterministic fixture round.
    def prepared_round(self, left_card, right_card, third_card, action_id="deal-fixture"):
        # Build the same deal fingerprint shape as production.
        fingerprint = request_fingerprint({"stage": "deal"})
        # Derive a stable round id.
        round_id = engine.round_id_for("session-player", action_id)
        # Create prepared state with a private result card.
        round_state = engine.create_round("session-player", action_id, left_card=left_card, right_card=right_card, third_card=third_card, round_id=round_id, created_at="2026-07-14T00:00:00Z", request_fingerprint=fingerprint)
        # Persist the active player document.
        self.repository.save("session-player", {"active_round": round_state, "recent_rounds": [], "action_receipts": {action_id: {"stage": "deal", "round_id": round_id, "request_fingerprint": fingerprint}}})
        # Return the stable route id.
        return round_id

    # Confirm hostile body and query player ids cannot override the session.
    def test_session_binding_and_idempotent_free_deal(self):
        # Deal boundaries with competing hostile player ids.
        first = self.call("/api/v1/games/acey-deucey/rounds?player_id=other-player", {"player_id": "other-player", "action_id": "deal-retry-1"})
        # Replay the exact free deal.
        second = self.call("/api/v1/games/acey-deucey/rounds?player_id=other-player", {"player_id": "other-player", "action_id": "deal-retry-1"})
        # Verify round ownership follows the authenticated session.
        self.assertEqual("session-player", first["round"]["player_id"])
        # Verify no ledger movement happens during the free boundary deal.
        self.assertEqual([], self.ledger.events)
        # Verify the same round is returned on replay.
        self.assertEqual(first["round"]["round_id"], second["round"]["round_id"])
        # Verify the hidden third card is not public before play.
        self.assertNotIn("_third_card", first["round"])
        # Read through another authenticated session.
        other_context = {"bound_player_id": "other-player", "user": {"player_id": "other-player"}}
        # Verify the other session cannot see the first player's active deal.
        other_state = self.call("/api/v1/games/acey-deucey/state?player_id=session-player", method="GET", context=other_context)
        # Confirm session isolation.
        self.assertIsNone(other_state["state"]["active_round"])
        # Reject cross-session play against the first player's round.
        with self.assertRaises(NotFoundError):
            # Exercise private round lookup through the real router.
            self.call(f"/api/v1/games/acey-deucey/rounds/{first['round']['round_id']}/play", {"action_id": "play-cross", "wager": 1}, context=other_context)

    # Confirm inside wins debit and credit exactly once under stable ledger ids.
    def test_inside_play_replay_is_exactly_once(self):
        # Prepare a guaranteed inside result.
        round_id = self.prepared_round("2H", "AS", "7C")
        # Play the round once.
        first = self.call(f"/api/v1/games/acey-deucey/rounds/{round_id}/play", {"action_id": "play-win", "wager": 5})
        # Replay the same play action.
        second = self.call(f"/api/v1/games/acey-deucey/rounds/{round_id}/play", {"action_id": "play-win", "wager": 5})
        # Verify the inside return table.
        self.assertEqual(("inside", 10.0, 5.0), (first["round"]["outcome"], first["round"]["payout"], first["round"]["net"]))
        # Verify replay reports the terminal result.
        self.assertTrue(second["replayed"])
        # Select wager debits and payout credits.
        debits = [event for event in self.ledger.events if event["transaction_type"] == "ACEY_DEUCEY_WAGER_DEBIT"]
        # Select payout credits.
        credits = [event for event in self.ledger.events if event["transaction_type"] == "ACEY_DEUCEY_PAYOUT_CREDIT"]
        # Verify exactly one debit and one payout.
        self.assertEqual((1, -5.0, 1, 10.0), (len(debits), debits[0]["amount"], len(credits), credits[0]["amount"]))
        # Verify stable ledger action suffixes.
        self.assertEqual(("ad:play-win:wager", "ad:play-win:payout"), (debits[0]["details"]["acey_deucey_action_id"], credits[0]["details"]["acey_deucey_action_id"]))

    # Confirm outside and boundary ties create no zero-value credit.
    def test_losing_edge_cases_have_no_credit(self):
        # Prepare a boundary-tie loss.
        tie_round_id = self.prepared_round("2H", "AS", "2C", action_id="deal-tie")
        # Play the boundary-tie result.
        tie = self.call(f"/api/v1/games/acey-deucey/rounds/{tie_round_id}/play", {"action_id": "play-tie", "wager": 3})
        # Prepare a second outside loss after the first terminal round.
        outside_round_id = self.prepared_round("8H", "10S", "QC", action_id="deal-outside")
        # Play the outside result.
        outside = self.call(f"/api/v1/games/acey-deucey/rounds/{outside_round_id}/play", {"action_id": "play-outside", "wager": 4})
        # Verify both losing outcome keys.
        self.assertEqual(("boundary_tie", "outside"), (tie["round"]["outcome"], outside["round"]["outcome"]))
        # Verify only wager debits exist.
        self.assertEqual([], [event for event in self.ledger.events if event["transaction_type"] == "ACEY_DEUCEY_PAYOUT_CREDIT"])

    # Confirm pass closes the round without wallet movement or result reveal.
    def test_pass_has_no_ledger_movement_and_no_reveal(self):
        # Prepare an active deal with a hidden third card.
        round_id = self.prepared_round("3H", "JS", "7C", action_id="deal-pass")
        # Pass the round.
        result = self.call(f"/api/v1/games/acey-deucey/rounds/{round_id}/pass", {"action_id": "pass-1"})
        # Verify pass terminal state.
        self.assertEqual(("passed", "passed"), (result["round"]["phase"], result["round"]["outcome"]))
        # Verify the third card remains unrevealed.
        self.assertNotIn("third_card", result["round"])
        # Verify no ledger events were created.
        self.assertEqual([], self.ledger.events)


# Run this focused suite when invoked directly.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()

