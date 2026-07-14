"""Replay, ledger, and session-bound Casino War controller tests."""

# Import deep-copy support to simulate persistence boundaries.
import copy
# Import unittest for dependency-free focused tests.
import unittest

# Import the router so routes can be exercised without global registration.
from casino.router import Router
# Import the isolated API and pure state factory.
from casino.games.casino_war import api, engine


# Simulate player-scoped persistence without touching repository data files.
class MemoryRepository:
    # Seed one player's document with deterministic state.
    def __init__(self, player_id: str, state: dict):
        # Store a detached copy to model serialization.
        self.documents = {player_id: copy.deepcopy(state)}

    # Load one detached player document.
    def load(self, player_id: str) -> dict:
        # Return a fresh default only for unexpected test players.
        return copy.deepcopy(self.documents.get(player_id, engine.default_state()))

    # Save one detached player document.
    def save(self, player_id: str, state: dict) -> None:
        # Persist a copy so later mutations require another explicit save.
        self.documents[player_id] = copy.deepcopy(state)


# Record append-only events and expose game action lookup for crash recovery.
class RecordingLedger:
    # Start with no committed events.
    def __init__(self):
        # Retain committed events in append order.
        self.events = []

    # Find one prior action exactly as the production adapter does.
    def find_action(self, player_id: str, action_id: str):
        # Search newest-first for the player's matching details key.
        return next((event for event in reversed(self.events) if event["player_id"] == player_id and event["details"]["casino_war_action_id"] == action_id), None)

    # Record one debit or credit as a ledger-shaped event.
    def transact(self, intent: dict) -> dict:
        # Build a stable event identifier from append order.
        event = {
            "ledger_id": f"ledger-{len(self.events) + 1}",  # Identify the event.
            "player_id": intent["player_id"],  # Preserve player ownership.
            "game": intent["game"],  # Preserve game ownership.
            "round_id": intent["round_id"],  # Preserve round ownership.
            "transaction_type": intent["transaction_type"],  # Preserve movement type.
            "amount": -intent["amount"] if intent["direction"] == "debit" else intent["amount"],  # Record signed amount.
            "details": copy.deepcopy(intent["details"]),  # Preserve the idempotency detail.
        }
        # Append once to simulate the shared append-only ledger.
        self.events.append(event)
        # Return the committed event to the controller.
        return copy.deepcopy(event)


# Verify exactly-once replay and session resolver compatibility.
class CasinoWarApiTests(unittest.TestCase):
    # Build deterministic state where the player wins immediately.
    def winning_state(self) -> dict:
        # Start from the production state shape.
        state = engine.default_state()
        # Arrange player ace, dealer deuce, and sufficient remaining cards.
        state["shoe"] = list(reversed(["AH", "2S", "3C", "4C", "5C", "6C", "7C"]))
        # Identify the fixture shoe.
        state["shoe_id"] = "fixture-win"
        # Return the prepared state.
        return state

    # Build deterministic state where the initial cards tie.
    def tied_state(self) -> dict:
        # Start from the production state shape.
        state = engine.default_state()
        # Arrange initial sevens, burns, and a player-winning war comparison.
        state["shoe"] = list(reversed(["7H", "7S", "2D", "3D", "4D", "KH", "9S"]))
        # Identify the fixture shoe.
        state["shoe_id"] = "fixture-tie"
        # Return the prepared state.
        return state

    # Create one controller with recording ports.
    def controller(self, repository, recording_ledger):
        # Return a controller whose player payload is deterministic.
        return api.CasinoWarController(repository, recording_ledger, lambda player_id: {"player_id": player_id, "balance": 1000.0})

    # Confirm retrying the same command never repeats debit or settlement credit.
    def test_start_round_replay_is_exactly_once(self):
        # Seed one player with a winning deterministic round.
        repository = MemoryRepository("bound-player", self.winning_state())
        # Record all wallet movements.
        recording_ledger = RecordingLedger()
        # Build the isolated controller.
        controller = self.controller(repository, recording_ledger)
        # Execute the original command.
        first = controller.start_round("bound-player", 25, "action-start-101")
        # Replay the exact client command.
        second = controller.start_round("bound-player", 25, "action-start-101")
        # Assert one ante debit and one settlement credit total.
        self.assertEqual([event["amount"] for event in recording_ledger.events], [-25.0, 50.0])
        # Assert both responses identify the same logical round.
        self.assertEqual(first["round"]["round_id"], second["round"]["round_id"])

    # Confirm a crash after ledger commit but before marker save is recovered by scan.
    def test_reload_recovers_committed_events_without_duplicates(self):
        # Seed and execute one immediate win.
        repository = MemoryRepository("bound-player", self.winning_state())
        # Record the committed events.
        recording_ledger = RecordingLedger()
        # Build the isolated controller.
        controller = self.controller(repository, recording_ledger)
        # Commit the ante and settlement once.
        controller.start_round("bound-player", 25, "action-start-102")
        # Simulate state-marker loss after both append-only events committed.
        repository.documents["bound-player"]["ledger_actions"] = {}
        # Trigger reload recovery through the state endpoint behavior.
        payload = controller.state("bound-player")
        # Assert recovery reused the two existing events.
        self.assertEqual(len(recording_ledger.events), 2)
        # Assert state markers were reconstructed and settlement remains complete.
        self.assertEqual(payload["state"]["rounds"][0]["settlement"]["committed_actions"], 2)

    # Confirm war replay creates only ante, matching wager, and one settlement.
    def test_war_replay_is_exactly_once(self):
        # Seed a deterministic initial tie.
        repository = MemoryRepository("bound-player", self.tied_state())
        # Record wallet movements.
        recording_ledger = RecordingLedger()
        # Build the isolated controller.
        controller = self.controller(repository, recording_ledger)
        # Deal the initial tie and ante debit.
        started = controller.start_round("bound-player", 40, "action-start-103")
        # Resolve through war once.
        first = controller.decide("bound-player", started["round"]["round_id"], "war", "action-war-101")
        # Replay the same decision command.
        second = controller.decide("bound-player", started["round"]["round_id"], "war", "action-war-101")
        # Assert one ante debit, one war debit, and one total settlement credit.
        self.assertEqual([event["amount"] for event in recording_ledger.events], [-40.0, -40.0, 120.0])
        # Assert the replay returns the same terminal outcome.
        self.assertEqual((first["round"]["outcome"], second["round"]["outcome"]), ("war_win", "war_win"))

    # Confirm the route adapter gives session binding precedence over hostile body ids.
    def test_router_context_binding_overrides_body_player(self):
        # Seed only the authenticated player's state.
        repository = MemoryRepository("bound-player", self.winning_state())
        # Record wallet ownership.
        recording_ledger = RecordingLedger()
        # Build and register the isolated controller on a local router.
        router = Router()
        # Register without touching the global application registry.
        api.register(router, self.controller(repository, recording_ledger))
        # Dispatch with a conflicting body player and a session-bound context.
        payload = router.dispatch("POST", "/api/v1/games/casino-war/rounds", {"player_id": "other-player", "wager": 10, "action_id": "action-start-104"}, {"bound_player_id": "bound-player"})
        # Assert the response and every ledger event belong to the session player.
        self.assertEqual(payload["player"]["player_id"], "bound-player")
        # Assert hostile body input never reached wallet ownership.
        self.assertTrue(all(event["player_id"] == "bound-player" for event in recording_ledger.events))


# Run this focused module directly when invoked as a script.
if __name__ == "__main__":
    # Execute unittest discovery for this file.
    unittest.main()
