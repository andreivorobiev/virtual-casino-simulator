"""Focused session-bound router tests for the additive Scratch Cards v1 API."""

# Import the dependency-free standard test runner.
import unittest
# Import scoped patching for the module-owned service singleton.
from unittest.mock import patch

# Import the real shared router so SESSION-005 precedence is exercised directly.
from casino.router import Router
# Import the game-owned registration module under test.
from casino.games.scratch_cards import api


# Capture service calls without touching filesystem state or the real ledger.
class FakeService:
    # Initialize call evidence for every public action.
    def __init__(self):
        # Store authenticated state-read players.
        self.state_players = []
        # Store start-card calls with their resolved players and bodies.
        self.start_calls = []
        # Store scratch calls with player, card, and request content.
        self.scratch_calls = []

    # Return minimal masked state while recording player scope.
    def state(self, player_id):
        # Record the only player identity received by the game.
        self.state_players.append(player_id)
        # Return stable raw data for the shared envelope layer.
        return {"game": "scratch_cards", "current_card": None, "recent_cards": []}

    # Return a minimal funded card response while recording call content.
    def start_card(self, player_id, body):
        # Record identity and request body after shared resolver mutation.
        self.start_calls.append((player_id, dict(body)))
        # Return stable game-owned action data.
        return {"card": {"card_id": "scr_api", "status": "ready"}, "replayed": False}

    # Return a minimal reveal response while recording path identity.
    def scratch(self, player_id, card_id, body):
        # Record the full public action tuple.
        self.scratch_calls.append((player_id, card_id, dict(body)))
        # Return stable terminal game-owned data.
        return {"card": {"card_id": card_id, "status": "settled"}, "replayed": False}


# Verify CORE-009, CORE-011, CORE-012, and SESSION-005 route behavior.
class ScratchCardsApiTests(unittest.TestCase):
    # Register fresh game-owned routes and service fakes before every test.
    def setUp(self):
        # Create the actual shared router used by focused dispatch tests.
        self.router = Router()
        # Create one call-recording service fake.
        self.service = FakeService()
        # Replace the module singleton only for this test instance.
        self.service_patch = patch.object(api, "SERVICE", self.service)
        # Activate the patch before route registration and invocation.
        self.service_patch.start()
        # Register only the isolated Scratch Cards routes.
        api.register(self.router)

    # Restore the real service singleton after every test.
    def tearDown(self):
        # Stop the scoped patch cleanly.
        self.service_patch.stop()

    # Prove hostile body and query IDs cannot override an authenticated binding.
    def test_state_uses_bound_session_player(self):
        # Dispatch with competing caller identities and one authoritative session binding.
        result = self.router.dispatch("GET", "/api/v1/games/scratch-cards/state?player_id=query-attacker", {"player_id": "body-attacker"}, context={"bound_player_id": "session-player"})
        # Verify only the bound session player reached the game service.
        self.assertEqual(["session-player"], self.service.state_players)
        # Verify raw data remains ready for the shared standard success envelope.
        self.assertEqual("scratch_cards", result["game"])

    # Prove the purchase route preserves action content but replaces caller identity.
    def test_start_card_uses_resolved_player_and_action_body(self):
        # Build a hostile compatibility field beside valid purchase content.
        body = {"player_id": "attacker", "client_request_id": "api-start", "wager": 2}
        # Dispatch through the shared game resolver with one authenticated binding.
        result = self.router.dispatch("POST", "/api/v1/games/scratch-cards/cards", body, context={"bound_player_id": "session-player"})
        # Verify the service received the authoritative player only.
        self.assertEqual("session-player", self.service.start_calls[0][0])
        # Verify the router replaced the hostile compatibility field in the action body.
        self.assertEqual("session-player", self.service.start_calls[0][1]["player_id"])
        # Verify the game-owned card response was returned unchanged for envelope wrapping.
        self.assertEqual("ready", result["card"]["status"])

    # Prove the card-scoped scratch route preserves path and action identity.
    def test_scratch_route_passes_card_and_session_identity(self):
        # Build one complete partial-reveal action.
        body = {"player_id": "attacker", "action_id": "api-scratch", "positions": [0, 4]}
        # Dispatch through the real card-id route matcher.
        result = self.router.dispatch("POST", "/api/v1/games/scratch-cards/cards/scr_api/scratches", body, context={"bound_player_id": "session-player"})
        # Verify service scope, path identity, and resolver-mutated body together.
        self.assertEqual(("session-player", "scr_api", "session-player"), (self.service.scratch_calls[0][0], self.service.scratch_calls[0][1], self.service.scratch_calls[0][2]["player_id"]))
        # Verify raw terminal data is returned for the shared standard envelope.
        self.assertEqual("settled", result["card"]["status"])


# Run this focused suite directly without central runner registration.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
