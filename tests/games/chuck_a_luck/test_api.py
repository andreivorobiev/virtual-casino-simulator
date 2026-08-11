# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Focused session-binding and route-shape tests for issue #89."""

# Import the dependency-free standard test runner.
import unittest

# Import the real shared router so session-player precedence is exercised before game dispatch.
from casino.router import Router
# Import the isolated game route registration module.
from casino.games.chuck_a_luck import api


# Provide a service fake that records the identity received after shared resolution.
class FakeService:
    # Initialize state and roll call evidence.
    def __init__(self):
        # Store player ids used for state reads.
        self.state_players = []
        # Store player/body pairs used for atomic rolls.
        self.roll_calls = []

    # Return one minimal raw state payload while recording player scope.
    def state(self, player_id):
        # Record the resolved authenticated player id.
        self.state_players.append(player_id)
        # Return handler data for the HTTP layer's standard envelope.
        return {"game": "chuck_a_luck", "state": {"recent_rounds": []}, "player": {"player_id": player_id}, "bet_catalog": []}

    # Return one minimal raw action payload while recording player scope and body.
    def roll(self, player_id, body):
        # Record the resolved identity and complete retry-safe request.
        self.roll_calls.append((player_id, body))
        # Return handler data for the HTTP layer's standard envelope.
        return {"round": {"round_id": "cal_test", "status": "settled"}, "replayed": False}


# Verify additive registration and hostile identity replacement.
class ChuckALuckApiTests(unittest.TestCase):
    # Register the isolated routes against real dispatch and a fake service.
    def setUp(self):
        # Create one fresh shared router.
        self.router = Router()
        # Create one isolated service fake.
        self.service = FakeService()
        # Register only this game-owned API surface.
        api.register(self.router, service=self.service)
        # Build the normal-user session context that owns player-session.
        self.context = {"bound_player_id": "session-player", "user": {"player_id": "session-player", "role": "user"}}

    # Confirm the shared resolver overrides both body and query spoofing for state.
    def test_state_uses_session_bound_player(self):
        # Dispatch with competing caller-controlled player ids.
        result = self.router.dispatch("GET", "/api/v1/games/chuck-a-luck/state?player_id=query-spoof", {"player_id": "body-spoof"}, context=self.context)
        # Require the game service to receive only the authenticated binding.
        self.assertEqual(["session-player"], self.service.state_players)
        # Require raw route data ready for the standard app envelope.
        self.assertEqual("session-player", result["player"]["player_id"])

    # Confirm the action receives one complete retry-safe body under the session identity.
    def test_roll_uses_session_bound_player_and_complete_body(self):
        # Build a caller body that attempts to spoof another player.
        body = {"player_id": "spoofed-player", "request_id": "api-1", "wagers": {"one": 5}}
        # Dispatch through the real shared session resolver and isolated route.
        result = self.router.dispatch("POST", "/api/v1/games/chuck-a-luck/rolls", body, context=self.context)
        # Read the identity and sanitized payload the shared router actually handed the service.
        bound_player, received_body = self.service.roll_calls[0]
        # Require the router to bind the service call to the session player, not the spoofed compatibility field.
        self.assertEqual("session-player", bound_player)
        # Require the sanitized service payload to carry the bound identity in place of the spoof.
        self.assertEqual("session-player", received_body["player_id"])
        # Require the full retry-safe wager body to survive sanitization intact.
        self.assertEqual(({"one": 5}, "api-1"), (received_body["wagers"], received_body["request_id"]))
        # Require raw settled data rather than a nested game-owned envelope.
        self.assertEqual("settled", result["round"]["status"])


# Run the focused suite directly without central runner edits.
if __name__ == "__main__":
    # Exit through unittest's standard result handling.
    unittest.main()
