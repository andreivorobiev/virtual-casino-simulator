"""Focused Crown and Anchor API/service tests for issue #133."""

# Import unittest so the focused module can run without central discovery edits.
import unittest
# Import public conflict errors for idempotency assertions.
from casino.errors import ConflictError
# Import the isolated API adapter and service under test.
from casino.games.crown_and_anchor import api
# Import the service class so tests can inject deterministic seams.
from casino.games.crown_and_anchor.service import CrownAndAnchorService


# Capture game routes registered by the isolated adapter.
class FakeRouter:
    # Initialize empty route maps for GET and POST handlers.
    def __init__(self):
        # Store GET handlers by route pattern.
        self.gets = {}
        # Store POST handlers by route pattern.
        self.posts = {}

    # Register one GET handler using the production decorator contract.
    def get(self, path):
        # Return a decorator that records the handler.
        def decorator(handler):
            # Store the handler for focused assertions.
            self.gets[path] = handler
            # Return the handler unchanged.
            return handler
        # Return the decorator to the caller.
        return decorator

    # Register one POST handler using the production decorator contract.
    def post(self, path):
        # Return a decorator that records the handler.
        def decorator(handler):
            # Store the handler for focused assertions.
            self.posts[path] = handler
            # Return the handler unchanged.
            return handler
        # Return the decorator to the caller.
        return decorator


# Provide an in-memory exactly-once ledger gateway for service tests.
class FakeLedgerGateway:
    # Initialize an empty committed-event map.
    def __init__(self):
        # Store events by deterministic action key.
        self.events = {}

    # Apply one signed movement only once.
    def apply_once(self, *, player_id, amount, transaction_type, round_id, action_key, details):
        # Branch when a retry has already committed this action.
        if action_key in self.events:
            # Return the original event and replay evidence.
            return self.events[action_key], True
        # Build a minimal append-only event shape.
        event = {"player_id": player_id, "amount": round(float(amount), 2), "transaction_type": transaction_type, "game": "crown_and_anchor", "round_id": round_id, "details": {**details, "idempotency_key": action_key}, "ts": "2026-07-14T00:00:00Z"}
        # Persist the committed event under its deterministic key.
        self.events[action_key] = event
        # Return the new event and non-replay evidence.
        return event, False


# Cover session-bound routing and exactly-once service behavior.
class CrownAndAnchorApiTests(unittest.TestCase):
    # Build a deterministic service for each test.
    def make_service(self, faces=None):
        # Store player states in a local dictionary.
        states = {}
        # Copy the requested deterministic dice faces.
        pending_faces = list(faces or [1, 2, 3])
        # Load or initialize player-owned state.
        loader = lambda player_id: states.setdefault(player_id, {"game": "crown_and_anchor", "recent_rounds": []})
        # Save state in place for the focused test.
        saver = lambda player_id, state: states.__setitem__(player_id, state)
        # Pop one deterministic face per dice roll.
        roller = lambda: pending_faces.pop(0)
        # Return a service with fake ports and exposed state.
        return CrownAndAnchorService(ledger_gateway=FakeLedgerGateway(), state_loader=loader, state_saver=saver, roll_die=roller, clock=lambda: "2026-07-14T00:00:00Z")

    # Verify body and query player_id cannot override authenticated context.
    def test_request_player_id_prefers_session_context(self):
        # Resolve a trusted context identity despite hostile caller ids.
        player_id = api.request_player_id({"player_id": "attacker"}, {"player_id": "query"}, {"bound_player_id": "session-player"})
        # Assert the session-bound player wins.
        self.assertEqual(player_id, "session-player")

    # Verify the registered handler uses trusted identity and settles one round.
    def test_registered_round_uses_session_identity(self):
        # Create a fake router for isolated registration.
        router = FakeRouter()
        # Create a deterministic service with three crown hits.
        service = self.make_service([1, 1, 1])
        # Register the game-owned routes with the fake service.
        api.register(router, service=service)
        # Execute one round with a hostile body player id.
        payload = router.posts[r"/api/v1/games/crown-and-anchor/rounds"]({"player_id": "attacker", "client_request_id": "round-0001", "wagers": {"crown": 5}}, {}, context={"resolved_player_id": "trusted"})
        # Assert the public round is bound to the trusted session identity.
        self.assertEqual(payload["round"]["player_id"], "trusted")
        # Assert the three-hit payout returns stake plus three-to-one net.
        self.assertEqual(payload["round"]["total_return"], 20.0)

    # Verify exact retries reuse the original ledger movements and dice.
    def test_exact_retry_is_replayed_once(self):
        # Create a deterministic service with one prepared roll.
        service = self.make_service([1, 2, 3])
        # Execute one new command.
        first = service.play("player-a", {"client_request_id": "round-0002", "wagers": {"anchor": 2}})
        # Replay the exact same command after state persisted.
        second = service.play("player-a", {"client_request_id": "round-0002", "wagers": {"anchor": 2}})
        # Assert the retry reports replay status.
        self.assertTrue(second["replayed"])
        # Assert the dice result stays identical.
        self.assertEqual(second["round"]["faces"], first["round"]["faces"])

    # Verify conflicting reuse of one request id fails before new dice or ledger actions.
    def test_conflicting_retry_rejected(self):
        # Create a deterministic service with one prepared roll.
        service = self.make_service([1, 2, 3])
        # Execute one new command.
        service.play("player-a", {"client_request_id": "round-0003", "wagers": {"anchor": 2}})
        # Assert different wagers under the same request id fail closed.
        with self.assertRaises(ConflictError):
            # Reuse the public identity with conflicting coverage.
            service.play("player-a", {"client_request_id": "round-0003", "wagers": {"crown": 2}})


# Run this focused module directly when invoked as a script.
if __name__ == "__main__":
    # Execute unittest's standard command-line runner.
    unittest.main()
