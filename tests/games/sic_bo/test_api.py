"""Focused SESSION-005 Sic Bo route-binding tests for issue #88."""

# Import the dependency-free standard unit-test runner.
import unittest

# Import the real shared router so authenticated player replacement is exercised.
from casino.router import Router
# Import only the isolated game API registration module.
from casino.games.sic_bo import api


# Record route calls without touching filesystem state or the shared ledger.
class FakeService:
    # Initialize captured state and play calls.
    def __init__(self):
        # Store player IDs used for state reads.
        self.state_players = []
        # Store player and request pairs used for round actions.
        self.play_calls = []

    # Return minimal state while recording authenticated ownership.
    def payload(self, player_id):
        # Record the resolved player identity.
        self.state_players.append(player_id)
        # Return one valid raw data mapping for the shared envelope layer.
        return {"game": "sic_bo", "state": {"active_round": None, "recent_rounds": []}, "bets": [], "player": {"player_id": player_id}}

    # Return minimal settlement while recording authenticated ownership and body.
    def play(self, player_id, body):
        # Record the resolved player and complete action body.
        self.play_calls.append((player_id, dict(body)))
        # Return one stable settled result shape.
        return {"round": {"round_id": "sb_test", "player_id": player_id, "phase": "settled"}, "replayed": False}


# Verify direct reachability and hostile caller-ID replacement.
class SicBoApiTests(unittest.TestCase):
    # Register isolated routes against the real shared resolver before each test.
    def setUp(self):
        # Create a fresh router without shared application registration.
        self.router = Router()
        # Create a fresh service recorder.
        self.service = FakeService()
        # Register only the Sic Bo game routes.
        api.register(self.router, service=self.service)
        # Store one authenticated session context for route dispatch.
        self.context = {"bound_player_id": "session-player", "user": {"player_id": "session-player"}}

    # Confirm body and query player IDs cannot override the authenticated session.
    def test_state_and_round_use_bound_session_player(self):
        # Read state with a malicious compatibility query identity.
        state = self.router.dispatch("GET", "/api/v1/games/sic-bo/state?player_id=attacker", {}, context=dict(self.context))
        # Execute a round with a malicious body identity.
        result = self.router.dispatch("POST", "/api/v1/games/sic-bo/rounds", {"player_id": "attacker", "action_id": "api-1", "wagers": {"small": 1}}, context=dict(self.context))
        # Verify both routes used only the authenticated session player.
        self.assertEqual(["session-player"], self.service.state_players)
        # Verify the action service received the bound player.
        self.assertEqual("session-player", self.service.play_calls[0][0])
        # Verify the shared router replaced the malicious body field before dispatch.
        self.assertEqual("session-player", self.service.play_calls[0][1]["player_id"])
        # Verify handlers return raw data for the HTTP layer's standard envelope.
        self.assertEqual(("sic_bo", "settled"), (state["game"], result["round"]["phase"]))

    # Confirm a context-resolved identity wins even under direct handler semantics.
    def test_request_player_prefers_resolved_context(self):
        # Resolve competing body, query, and authenticated context identities.
        player_id = api.request_player_id({"player_id": "body-player"}, {"player_id": "query-player"}, {"resolved_player_id": "resolved-player"})
        # Verify authenticated context has absolute precedence.
        self.assertEqual("resolved-player", player_id)


# Run the focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
