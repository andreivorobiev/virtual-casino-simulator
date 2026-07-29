"""Session isolation and exactly-once service tests for GitHub issue #140."""

# Import deep-copy support so fake persistence matches JSON document boundaries.
import copy
# Import the standard dependency-free test runner.
import unittest

# Import the real router to exercise authenticated player replacement.
from casino.router import Router
# Import public conflict and validation errors for route assertions.
from casino.errors import ConflictError, ValidationError
# Import the isolated route adapter and pure engine under test.
from casino.games.andar_bahar import api, engine
# Import the isolated service orchestration under test.
from casino.games.andar_bahar.service import AndarBaharService


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
        return next((event for event in reversed(self.events) if event["player_id"] == player_id and event["game"] == engine.GAME_ID and event["details"]["andar_bahar_action_id"] == action_id), None)

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
        # Calculate the candidate balance after the signed movement.
        new_balance = round(self.balances[player_id] + signed_amount, 2)
        # Reject overdrafts like the shared ledger provider.
        if new_balance < 0:
            # Keep the fake state unchanged on rejected debit.
            raise ValidationError("Insufficient fake balance")
        # Commit the fake balance only through this ledger adapter.
        self.balances[player_id] = new_balance
        # Build the public ledger fields used by service recovery and assertions.
        event = {"ledger_id": f"ledger-{len(self.events) + 1}", "player_id": player_id, "amount": signed_amount, "transaction_type": transaction_type, "game": engine.GAME_ID, "round_id": round_id, "details": {**copy.deepcopy(details), "andar_bahar_action_id": action_id, "request_fingerprint": fingerprint}}
        # Append the event once.
        self.events.append(event)
        # Return detached proof and non-replay evidence.
        return copy.deepcopy(event), False


# Verify route binding, retries, crash markers, and ledger audit dimensions.
class AndarBaharApiTests(unittest.TestCase):
    # Build isolated state, ledger, service, and router before every test.
    def setUp(self):
        # Create fresh player-scoped state storage.
        self.repository = MemoryRepository()
        # Create fresh fake balances and append-only ledger events.
        self.ledger = RecordingLedger()
        # Define deterministic fixtures keyed by action id.
        self.fixtures = {"play-win": {"match_card": "7H", "dealt_cards": [{"side": "andar", "card": "2C", "matched": False}, {"side": "bahar", "card": "QS", "matched": False}, {"side": "andar", "card": "7D", "matched": True}]}, "play-loss": {"match_card": "9C", "dealt_cards": [{"side": "andar", "card": "4C", "matched": False}, {"side": "bahar", "card": "9S", "matched": True}]}, "play-bahar-win": {"match_card": "9C", "dealt_cards": [{"side": "andar", "card": "4C", "matched": False}, {"side": "bahar", "card": "9S", "matched": True}]}}
        # Build a deterministic service without filesystem or ambient randomness.
        self.service = AndarBaharService(ledger_gateway=self.ledger, state_loader=self.repository.load, state_saver=self.repository.save, get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:00Z", fixture_factory=lambda action_id: self.fixtures.get(action_id))
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
    def test_session_binding_and_idempotent_win(self):
        # Start one play with two competing hostile caller identities.
        first = self.call("/api/v1/games/andar-bahar/rounds?player_id=other-player", {"player_id": "other-player", "action_id": "play-win", "wager": 7, "side": "andar"})
        # Replay the exact action through the same hostile inputs.
        second = self.call("/api/v1/games/andar-bahar/rounds?player_id=other-player", {"player_id": "other-player", "action_id": "play-win", "wager": 7, "side": "andar"})
        # Verify round ownership follows only the authenticated session.
        self.assertEqual("session-player", first["round"]["player_id"])
        # Verify another player's balance remains untouched.
        self.assertEqual(100.0, self.ledger.balances["other-player"])
        # Verify the same stable round is returned on replay.
        self.assertEqual(first["round"]["round_id"], second["round"]["round_id"])
        # Verify one wager debit and one payout credit exist after replay.
        self.assertEqual(1, len([event for event in self.ledger.events if event["transaction_type"] == "ANDAR_BAHAR_WAGER_DEBIT"]))
        # Verify the winning payout returns stake plus even-money winnings.
        self.assertEqual(1, len([event for event in self.ledger.events if event["transaction_type"] == "ANDAR_BAHAR_PAYOUT_CREDIT"]))
        # Verify the final fake balance reflects one debit and the 1.90x Andar return.
        self.assertEqual(106.3, self.ledger.balances["session-player"])
        # Verify old clients retain the required integer scalar while new clients receive both prices.
        self.assertEqual((2, int, {"andar": 1.9, "bahar": 2.0}), (first["rules"]["return_multiplier"], type(first["rules"]["return_multiplier"]), first["rules"]["return_multipliers"]))
        # Request the other player's isolated state while spoofing the first player in the query.
        other_state = self.call("/api/v1/games/andar-bahar/state?player_id=session-player", method="GET", context={"bound_player_id": "other-player", "user": {"player_id": "other-player"}})
        # Verify the other session cannot read the first player's history.
        self.assertEqual([], other_state["state"]["recent_rounds"])

    # Confirm conflicting retries and insufficient funds fail without extra movement.
    def test_play_conflict_and_rejected_debit_cleanup(self):
        # Commit one valid wager action.
        self.call("/api/v1/games/andar-bahar/rounds", {"action_id": "play-win", "wager": 3, "side": "andar"})
        # Reject reuse of the same identity with a changed side.
        with self.assertRaises(ConflictError):
            # Exercise the conflicting semantic fingerprint.
            self.call("/api/v1/games/andar-bahar/rounds", {"action_id": "play-win", "wager": 3, "side": "bahar"})
        # Build a separate empty-balance service for rollback behavior.
        empty_ledger = RecordingLedger({"session-player": 0.0})
        # Build fresh storage for the rejected action.
        empty_repository = MemoryRepository()
        # Create the isolated empty-balance service.
        empty_service = AndarBaharService(ledger_gateway=empty_ledger, state_loader=empty_repository.load, state_saver=empty_repository.save, get_player=lambda player_id: {"player_id": player_id, "balance": empty_ledger.balances[player_id]}, clock=lambda: "2026-07-14T00:00:00Z", fixture_factory=lambda action_id: self.fixtures["play-win"])
        # Reject the debit without committing a ledger row.
        with self.assertRaises(ValidationError):
            # Attempt one unaffordable round.
            empty_service.play("session-player", {"action_id": "play-no-funds", "wager": 1, "side": "andar"})
        # Verify no history row is stranded after a non-committed debit.
        self.assertEqual([], empty_repository.documents["session-player"]["recent_rounds"])
        # Verify no ledger event exists for the rejected action.
        self.assertEqual([], empty_ledger.events)

    # Confirm losing side records no zero-value settlement event.
    def test_loss_creates_no_settlement_event(self):
        # Play one losing Andar prediction where Bahar matches first.
        result = self.call("/api/v1/games/andar-bahar/rounds", {"action_id": "play-loss", "wager": 4, "side": "andar"})
        # Verify the documented losing result and zero returned tokens.
        self.assertEqual(("bahar", "loss", 0.0, "complete"), (result["round"]["winning_side"], result["round"]["outcome"], result["round"]["payout"], result["round"]["settlement_status"]))
        # Verify the game never asks the shared ledger to append a zero credit.
        self.assertEqual([], [event for event in self.ledger.events if event["transaction_type"] == "ANDAR_BAHAR_PAYOUT_CREDIT"])
        # Verify only the wager debit changed the fake balance.
        self.assertEqual(96.0, self.ledger.balances["session-player"])

    # Confirm Bahar keeps even-money settlement through the public route and ledger.
    def test_bahar_win_retains_even_money_return(self):
        # Play one winning Bahar prediction through the real route adapter.
        result = self.call("/api/v1/games/andar-bahar/rounds", {"action_id": "play-bahar-win", "wager": 7, "side": "bahar"})
        # Verify the exact winning side, 2.00x payout, and net result.
        self.assertEqual(("bahar", 14.0, 7.0), (result["round"]["winning_side"], result["round"]["payout"], result["round"]["net"]))
        # Verify exactly one payout credit used the side-priced amount.
        payout_events = [event for event in self.ledger.events if event["transaction_type"] == "ANDAR_BAHAR_PAYOUT_CREDIT"]
        # Require the returned-token ledger movement and resulting wallet value.
        self.assertEqual(([14.0], 107.0), ([event["amount"] for event in payout_events], self.ledger.balances["session-player"]))


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
