"""Session isolation and exactly-once tests for issue #135."""

# Import deep-copy support so fake persistence models JSON boundaries.
import copy
# Import the standard dependency-free test runner.
import unittest

# Import the real router to exercise route patterns.
from casino.router import Router
# Import public conflict and validation errors for route assertions.
from casino.errors import ConflictError, ValidationError
# Import the isolated API and engine modules.
from casino.games.over_under_7 import api, engine
# Import the isolated service under test.
from casino.games.over_under_7.service import OverUnder7Service


# Simulate player-scoped state documents without touching data files.
class MemoryRepository:
    # Start with no persisted documents.
    def __init__(self):
        # Store detached documents by player id.
        self.documents = {}

    # Load one detached state document or a fresh default.
    def load(self, player_id):
        # Return a deep copy so mutation requires save.
        return copy.deepcopy(self.documents.get(player_id, engine.default_state()))

    # Save one detached player document.
    def save(self, player_id, state):
        # Persist a deep copy to model JSON storage.
        self.documents[player_id] = copy.deepcopy(state)


# Record signed ledger events and enforce action-key replay in memory.
class RecordingLedger:
    # Seed deterministic balances for isolated players.
    def __init__(self, balances=None):
        # Store fake balances only inside this test adapter.
        self.balances = balances or {"session-player": 100.0, "other-player": 100.0}
        # Retain append-only event rows.
        self.events = []

    # Find one committed action key for a player.
    def find(self, player_id, action_key):
        # Search newest first using the game-owned details key.
        return next((event for event in reversed(self.events) if event["player_id"] == player_id and event["details"]["over_under_7_action_key"] == action_key), None)

    # Apply or recover one signed movement exactly once.
    def apply_once(self, *, player_id, signed_amount, transaction_type, round_id, action_key, fingerprint, details):
        # Resolve any prior committed action.
        existing = self.find(player_id, action_key)
        # Reuse exact matching events.
        if existing is not None:
            # Reject semantic conflicts.
            if existing["amount"] != signed_amount or existing["transaction_type"] != transaction_type or existing["round_id"] != round_id or existing["details"]["request_fingerprint"] != fingerprint:
                # Fail before a second movement.
                raise ConflictError("fake action conflict")
            # Return detached proof and replay evidence.
            return copy.deepcopy(existing), True
        # Calculate the candidate balance.
        new_balance = round(self.balances[player_id] + signed_amount, 2)
        # Reject overdrafts like the shared ledger provider.
        if new_balance < 0:
            # Keep state unchanged on rejected debit.
            raise ValidationError("Insufficient fake balance")
        # Commit the fake balance.
        self.balances[player_id] = new_balance
        # Build the public ledger row used by service recovery.
        event = {"ledger_id": f"ledger-{len(self.events) + 1}", "player_id": player_id, "amount": signed_amount, "transaction_type": transaction_type, "game": engine.GAME_ID, "round_id": round_id, "ts": "2026-07-14T00:00:00Z", "details": {**copy.deepcopy(details), "over_under_7_action_key": action_key, "request_fingerprint": fingerprint}}
        # Append the event once.
        self.events.append(event)
        # Return detached proof and non-replay evidence.
        return copy.deepcopy(event), False


# Verify route binding, retries, reload recovery, and ledger audit dimensions.
class OverUnder7ApiTests(unittest.TestCase):
    # Build isolated state, ledger, service, and router before every test.
    def setUp(self):
        # Create fresh player-scoped storage.
        self.repository = MemoryRepository()
        # Create fresh fake balances and ledger events.
        self.ledger = RecordingLedger()
        # Build deterministic dice values for exact-seven then under results.
        self.dice_values = iter([2, 3, 0, 4])
        # Build the isolated service without filesystem or ambient randomness.
        self.service = OverUnder7Service(ledger_gateway=self.ledger, state_loader=self.repository.load, state_saver=self.repository.save, get_player=lambda player_id: {"player_id": player_id, "balance": self.ledger.balances[player_id]}, randbelow=lambda sides: next(self.dice_values), clock=lambda: "2026-07-14T00:00:00Z")
        # Register only game-owned routes on the real router.
        self.router = Router()
        # Inject the focused service.
        api.register(self.router, service=self.service)
        # Store the authenticated context that must override caller ids.
        self.context = {"bound_player_id": "session-player", "user": {"player_id": "session-player"}}

    # Dispatch through the shared router.
    def call(self, path, body=None, method="POST", context=None):
        # Delegate with a copied context so requests remain isolated.
        return self.router.dispatch(method, path, body or {}, context=dict(context or self.context))

    # Confirm hostile player ids cannot override the authenticated session.
    def test_session_binding_and_exact_replay(self):
        # Play once with hostile caller-supplied ids.
        first = self.call("/api/v1/games/over-under-7/plays?player_id=other-player", {"player_id": "other-player", "action_id": "play-1", "wagers": {"seven": 5}})
        # Replay the exact action.
        second = self.call("/api/v1/games/over-under-7/plays?player_id=other-player", {"player_id": "other-player", "action_id": "play-1", "wagers": {"seven": 5}})
        # Verify ownership follows the session only.
        self.assertEqual("session-player", first["round"]["player_id"])
        # Verify another player's balance is untouched.
        self.assertEqual(100.0, self.ledger.balances["other-player"])
        # Verify the same round is returned on retry.
        self.assertEqual(first["round"]["round_id"], second["round"]["round_id"])
        # Verify exactly one debit and one settlement credit exist.
        self.assertEqual((1, 1), (len([event for event in self.ledger.events if event["transaction_type"] == "OVER_UNDER_7_WAGER_DEBIT"]), len([event for event in self.ledger.events if event["transaction_type"] == "OVER_UNDER_7_SETTLEMENT_CREDIT"])))
        # Verify exact-seven return used stake plus 4:1 net.
        self.assertEqual((25.0, 120.0), (first["round"]["total_return"], self.ledger.balances["session-player"]))

    # Confirm changed retries fail closed.
    def test_conflicting_retry_rejected(self):
        # Commit one valid play.
        self.call("/api/v1/games/over-under-7/plays", {"action_id": "play-conflict", "wagers": {"under": 3}})
        # Reject reuse with changed wagers.
        with self.assertRaises(ConflictError):
            # Exercise semantic action-id conflict.
            self.call("/api/v1/games/over-under-7/plays", {"action_id": "play-conflict", "wagers": {"under": 4}})
        # Verify no extra debit was created.
        self.assertEqual(1, len([event for event in self.ledger.events if event["transaction_type"] == "OVER_UNDER_7_WAGER_DEBIT"]))

    # Confirm committed debit details recover a round after lost state.
    def test_reload_recovery_from_committed_debit(self):
        # Create a service that fails its state save after ledger movements.
        class FailingRepository(MemoryRepository):
            # Fail all saves to simulate a post-ledger crash.
            def save(self, player_id, state):
                # Raise after ledger events commit.
                raise RuntimeError("simulated save crash")
        # Create isolated failing storage.
        failing_repository = FailingRepository()
        # Create a deterministic ledger.
        ledger = RecordingLedger()
        # Build an explicit two-die sequence that totals seven.
        dice_values = iter([2, 3])
        # Build a service with controlled exact-seven dice.
        service = OverUnder7Service(ledger_gateway=ledger, state_loader=failing_repository.load, state_saver=failing_repository.save, get_player=lambda player_id: {"player_id": player_id, "balance": ledger.balances[player_id]}, randbelow=lambda sides: next(dice_values), clock=lambda: "2026-07-14T00:00:00Z")
        # Allow the save failure to happen after ledger commit.
        with self.assertRaises(RuntimeError):
            # Execute the play once.
            service.play("session-player", {"action_id": "recover-play", "wagers": {"seven": 5}})
        # Create normal restarted storage for recovered state.
        restarted_repository = MemoryRepository()
        # Build a restarted service with normal storage but the same ledger.
        restarted = OverUnder7Service(ledger_gateway=ledger, state_loader=restarted_repository.load, state_saver=restarted_repository.save, get_player=lambda player_id: {"player_id": player_id, "balance": ledger.balances[player_id]}, randbelow=lambda sides: 0, clock=lambda: "2026-07-14T00:00:01Z")
        # Replay the same action and recover from debit/credit ledger proof.
        recovered = restarted.play("session-player", {"action_id": "recover-play", "wagers": {"seven": 5}})
        # Verify recovery did not append duplicate movements.
        self.assertEqual((True, 2), (recovered["replayed"], len(ledger.events)))
        # Verify dice came from durable ledger details rather than new randomness.
        self.assertEqual([3, 4], recovered["round"]["dice"])


# Run this focused suite when invoked directly.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
