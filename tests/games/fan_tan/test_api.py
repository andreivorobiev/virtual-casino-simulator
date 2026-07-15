"""Session isolation and exactly-once service tests for GitHub issue #137."""

# Import deep-copy support so fake persistence matches JSON document boundaries.
import copy
# Import the standard dependency-free test runner.
import unittest
# Import the real router to exercise authenticated player replacement.
from casino.router import Router
# Import public conflict errors for route assertions.
from casino.errors import ConflictError
# Import the isolated route adapter and pure engine under test.
from casino.games.fan_tan import api, engine
# Import the isolated service orchestration under test.
from casino.games.fan_tan.service import FanTanService


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
        return next((event for event in reversed(self.events) if event["player_id"] == player_id and event["details"]["fan_tan_action_id"] == action_id), None)

    # Apply or recover one signed movement exactly once.
    def apply_once(self, *, player_id, signed_amount, transaction_type, round_id, action_id, fingerprint, details):
        # Resolve any prior committed action before changing the fake balance.
        existing = self.find(player_id, action_id)
        # Reuse an exact matching event.
        if existing is not None:
            # Reject semantic conflicts like the production gateway.
            if existing["amount"] != signed_amount or existing["transaction_type"] != transaction_type or existing["details"]["request_fingerprint"] != fingerprint:
                # Fail before a second movement.
                raise ConflictError("fake action identity conflict")
            # Return immutable proof and replay evidence.
            return copy.deepcopy(existing), True
        # Calculate the candidate balance after the signed movement.
        self.balances[player_id] = round(self.balances[player_id] + signed_amount, 2)
        # Build the public ledger fields used by service recovery and assertions.
        event = {"ledger_id": f"ledger-{len(self.events) + 1}", "player_id": player_id, "amount": signed_amount, "transaction_type": transaction_type, "game": engine.GAME_ID, "round_id": round_id, "details": {**copy.deepcopy(details), "fan_tan_action_id": action_id, "request_fingerprint": fingerprint}}
        # Append the event once.
        self.events.append(event)
        # Return detached proof and non-replay evidence.
        return copy.deepcopy(event), False


# Verify route binding, retries, and ledger audit dimensions.
class FanTanApiTests(unittest.TestCase):
    # Build isolated state, ledger, service, and router before every test.
    def setUp(self):
        # Create fresh player-scoped state storage.
        self.repository = MemoryRepository()
        # Create fresh fake balances and append-only ledger events.
        self.ledger = RecordingLedger()
        # Build a deterministic service without filesystem or ambient randomness.
        self.service = FanTanService(ledger_gateway=self.ledger, state_loader=self.repository.load, state_saver=self.repository.save, randbelow=lambda span: 3, clock=lambda: "2026-07-14T00:00:00Z")
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
    def test_session_binding_and_idempotent_play(self):
        # Start one round with two competing hostile caller identities.
        first = self.call("/api/v1/games/fan-tan/rounds?player_id=other-player", {"player_id": "other-player", "action_id": "fan-retry-1", "wagers": {"4": 5}})
        # Replay the exact action through the same hostile inputs.
        second = self.call("/api/v1/games/fan-tan/rounds?player_id=other-player", {"player_id": "other-player", "action_id": "fan-retry-1", "wagers": {"4": 5}})
        # Verify round ownership follows only the authenticated session.
        self.assertEqual("session-player", first["round"]["player_id"])
        # Verify another player's balance remains untouched.
        self.assertEqual(100.0, self.ledger.balances["other-player"])
        # Verify the same stable round is returned on replay.
        self.assertEqual(first["round"]["round_id"], second["round"]["round_id"])
        # Verify exactly one wager debit and one settlement credit exist.
        self.assertEqual((1, 1), (len([event for event in self.ledger.events if event["transaction_type"] == "FAN_TAN_WAGER_DEBIT"]), len([event for event in self.ledger.events if event["transaction_type"] == "FAN_TAN_SETTLEMENT_CREDIT"])))
        # Verify the winning round produced the documented net balance change.
        self.assertEqual(115.0, self.ledger.balances["session-player"])

    # Confirm conflicting action retries fail without duplicate ledger movements.
    def test_conflicting_retry_rejected(self):
        # Commit one valid wager action.
        self.call("/api/v1/games/fan-tan/rounds", {"action_id": "fan-conflict", "wagers": {"1": 3}})
        # Reject reuse of the same identity with changed wagers.
        with self.assertRaises(ConflictError):
            # Exercise the conflicting semantic fingerprint.
            self.call("/api/v1/games/fan-tan/rounds", {"action_id": "fan-conflict", "wagers": {"1": 4}})
        # Verify the conflicting retry created no second debit.
        self.assertEqual(1, len([event for event in self.ledger.events if event["transaction_type"] == "FAN_TAN_WAGER_DEBIT"]))

    # Confirm state is player-scoped and exposes transparent rules metadata.
    def test_state_is_session_scoped_with_rules(self):
        # Create one session-owned settled round.
        self.call("/api/v1/games/fan-tan/rounds", {"action_id": "fan-state", "wagers": {"4": 2}})
        # Read state through a different authenticated session while spoofing the first player.
        other = self.call("/api/v1/games/fan-tan/state?player_id=session-player", method="GET", context={"bound_player_id": "other-player", "user": {"player_id": "other-player"}})
        # Verify the other session sees no first-player history.
        self.assertEqual([], other["state"]["recent_rounds"])
        # Verify the backend owns the paytable and modulo-four profile.
        self.assertEqual(("counted-pile-modulo-four", 4), (other["rules"]["profile"], len(other["outcomes"])))


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
