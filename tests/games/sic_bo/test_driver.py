"""Focused catalog-driver contract test for issue #88."""

# Import the dependency-free standard unit-test runner.
import unittest

# Import the game-owned long-suite entrypoint proposed to #77.
from tests.game_drivers.sic_bo import play
# Import the isolated listener harness for protected-port safety checks.
from tests.games.sic_bo import browser_server


# Simulate only the public client contract consumed by long-suite drivers.
class FakeLongSuiteClient:
    # Initialize one ordered call log for exact request assertions.
    def __init__(self):
        # Retain path, method, and body for every driver action.
        self.calls = []
        # Count action calls so the second response is reported as a replay.
        self.round_calls = 0

    # Return stable public endpoint responses without registering shared catalog files.
    def call(self, path, method="GET", body=None):
        # Record a detached request body for mutation-safe comparisons.
        self.calls.append((path, method, dict(body) if body is not None else None))
        # Return exactly fifty metadata rows for the state precondition.
        if path.endswith("/state"):
            # Provide only the field the long driver is responsible for checking.
            return {"bets": [{"id": f"position-{index}"} for index in range(50)]}
        # Advance the retry counter for one public round action.
        self.round_calls += 1
        # Return one stable authoritative result and explicit replay evidence.
        return {"round": {"round_id": "sb_driver", "dice": [1, 2, 3]}, "replayed": self.round_calls > 1}


# Verify the driver uses session-bound public actions and one exact retry payload.
class SicBoDriverTests(unittest.TestCase):
    # Confirm the issue-owned harness cannot bind either user live-session port.
    def test_browser_harness_rejects_protected_ports(self):
        # Exercise both ports named by the current readiness wake.
        for protected_port in (8765, 8877):
            # Preserve the failing port in any focused-test diagnostic.
            with self.subTest(port=protected_port):
                # Require rejection before application imports, storage, or listener creation.
                with self.assertRaisesRegex(ValueError, "protected live-session ports 8765 or 8877"):
                    # Supply inert required control paths that must never be touched.
                    browser_server.main(["--port", str(protected_port), "--ready-file", "unused-ready.json", "--stop-file", "unused-stop.flag"])

    # Confirm catalog execution can call the driver without player-id compatibility input.
    def test_driver_uses_canonical_positions_and_exact_retry(self):
        # Create one isolated public-client recorder.
        client = FakeLongSuiteClient()
        # Run the production driver at one deterministic suite index.
        play(client, 7)
        # Verify one state read precedes exactly two round calls.
        self.assertEqual(["GET", "POST", "POST"], [method for _, method, _ in client.calls])
        # Verify both action calls target the additive v1 rounds endpoint.
        self.assertEqual(["/api/v1/games/sic-bo/rounds"] * 2, [path for path, _, _ in client.calls[1:]])
        # Verify the retry sends the exact same semantic request snapshot.
        self.assertEqual(client.calls[1][2], client.calls[2][2])
        # Verify canonical colon-delimited bet ids and no caller-controlled player id.
        self.assertEqual({"action_id": "long-sic-bo-7", "wagers": {"small": 1, "total:10": 1}}, client.calls[1][2])


# Run the focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
