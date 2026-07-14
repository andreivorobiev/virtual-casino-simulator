"""Focused router-shape tests for the isolated Big Six Wheel API."""

# Import the dependency-free standard test runner.
import unittest
# Import mock patching so route tests never touch the real ledger or filesystem.
from unittest.mock import patch
# Import the game-owned API registration module.
from casino.games.big_six_wheel import api


# Capture route decorators without starting a listener or editing the shared router.
class FakeRouter:
    # Initialize route storage keyed by method and path.
    def __init__(self):
        # Store registered handlers for direct invocation.
        self.routes = {}

    # Build one decorator for GET registration.
    def get(self, path):
        # Capture the decorated handler under its method and path.
        return lambda handler: self.routes.setdefault(("GET", path), handler) or handler

    # Build one decorator for POST registration.
    def post(self, path):
        # Capture the decorated handler under its method and path.
        return lambda handler: self.routes.setdefault(("POST", path), handler) or handler


# Provide a service fake that records the resolved session player.
class FakeService:
    # Initialize call evidence.
    def __init__(self):
        # Store every state player id.
        self.state_players = []
        # Store every spin call tuple.
        self.spin_calls = []

    # Return minimal state while recording player scope.
    def state(self, player_id):
        # Record the resolved player id.
        self.state_players.append(player_id)
        # Return a stable game-owned payload.
        return {"game": "big_six_wheel", "outcomes": [], "recent_rounds": []}

    # Return minimal settlement while recording body and player scope.
    def spin(self, player_id, body):
        # Record the resolved player id and original action body.
        self.spin_calls.append((player_id, body))
        # Return a stable settled response shape.
        return {"round": {"round_id": "bsw_test", "status": "settled"}, "replayed": False}


# Verify isolated registration and #81-compatible player precedence.
class BigSixWheelApiTests(unittest.TestCase):
    # Register routes against fresh fakes before every test.
    def setUp(self):
        # Create one isolated router.
        self.router = FakeRouter()
        # Create one isolated service.
        self.service = FakeService()
        # Replace the module singleton only for registration-handler tests.
        self.service_patch = patch.object(api, "SERVICE", self.service)
        # Activate the patch before route invocation.
        self.service_patch.start()
        # Register only game-owned routes.
        api.register(self.router)

    # Restore the module singleton after every test.
    def tearDown(self):
        # Stop the scoped patch cleanly.
        self.service_patch.stop()

    # Confirm the shared router's authenticated context takes precedence over caller values.
    def test_state_uses_authenticated_context_player(self):
        # Invoke the state handler with competing context, body, and query ids.
        result = self.router.routes[("GET", "/api/v1/games/big-six-wheel/state")]({"player_id": "body-player"}, {"player_id": "query-player"}, {"resolved_player_id": "session-player"})
        # Verify the game receives only the upstream-bound player identity.
        self.assertEqual(["session-player"], self.service.state_players)
        # Verify the raw data is ready for the shared standard envelope.
        self.assertEqual("big_six_wheel", result["game"])

    # Confirm the spin endpoint passes one complete atomic action to the service.
    def test_spin_passes_session_player_and_action_body(self):
        # Build the body shape from the additive OpenAPI contract.
        body = {"player_id": "session-player", "client_request_id": "api-1", "wagers": {"one": 5}}
        # Invoke the isolated action handler directly.
        result = self.router.routes[("POST", "/api/v1/games/big-six-wheel/spins")](body, {}, {"bound_player_id": "session-player"})
        # Verify the service receives the session-bound identity and complete request.
        self.assertEqual(("session-player", body), self.service.spin_calls[0])
        # Verify the response exposes settlement without building its own envelope.
        self.assertEqual("settled", result["round"]["status"])


# Run this focused API suite directly without central runner registration.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
