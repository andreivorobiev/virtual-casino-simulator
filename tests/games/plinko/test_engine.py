"""Deterministic rule tests for integrated Plinko issue #136."""

# Import the dependency-free standard test runner.
import unittest

# Import public errors for invalid transition assertions.
from casino.errors import ConflictError, ValidationError
# Import only the isolated game engine under test.
from casino.games.plinko import engine


# Verify Plinko path, bucket, payout, and retry semantics.
class PlinkoEngineTests(unittest.TestCase):
    # Confirm seeded paths are deterministic and profile-sized.
    def test_committed_path_is_deterministic_and_sized(self):
        # Generate one seeded path from the pure rules helper.
        first = engine.committed_path(seed="issue-136")
        # Repeat the same seeded path for deterministic tests.
        second = engine.committed_path(seed="issue-136")
        # Verify stable output for identical seeds.
        self.assertEqual(first, second)
        # Verify one peg decision exists for every configured row.
        self.assertEqual(engine.ROWS, len(first))
        # Verify every decision is one documented left/right value.
        self.assertTrue(all(step in ("L", "R") for step in first))

    # Confirm bucket index derives only from right-bounce count.
    def test_bucket_and_multiplier_follow_committed_path(self):
        # Build a path with three right bounces.
        path = ["L", "R", "L", "R", "R", "L", "L", "L"]
        # Verify the terminal bucket equals right-bounce count.
        self.assertEqual(3, engine.bucket_for_path(path))
        # Verify the transparent multiplier table is addressed by bucket.
        self.assertEqual(1.5, engine.multiplier_for_bucket(3))

    # Confirm a created drop stores settlement facts without wallet mutation.
    def test_create_drop_calculates_transparent_payout(self):
        # Build a deterministic path that reaches bucket five.
        path = ["R", "R", "R", "R", "R", "L", "L", "L"]
        # Create the pure drop result with stable audit fields.
        drop = engine.create_drop("session-player", 10, "drop-1", path=path, drop_id="plinko_0123456789abcdef01234567", created_at="2026-07-14T00:00:00Z", request_fingerprint="fingerprint")
        # Verify payout follows wager times multiplier.
        self.assertEqual((5, 5.0, 50.0, 40.0), (drop["bucket"], drop["multiplier"], drop["payout"], drop["net"]))
        # Verify the committed path is public replay data.
        self.assertEqual(path, drop["path"])

    # Confirm malformed wagers and impossible paths fail closed.
    def test_invalid_boundaries_fail_closed(self):
        # Reject boolean wagers despite Python's numeric subtype behavior.
        with self.assertRaises(ValidationError):
            # Exercise the malformed wager boundary.
            engine.normalize_wager(True)
        # Reject non-finite ledger amounts.
        with self.assertRaises(ValidationError):
            # Exercise the infinity boundary.
            engine.normalize_wager(float("inf"))
        # Reject paths that are shorter than the fixed profile.
        with self.assertRaises(ValidationError):
            # Exercise malformed path validation.
            engine.bucket_for_path(["L"])
        # Reject unsupported path decisions.
        with self.assertRaises(ValidationError):
            # Exercise invalid path values.
            engine.bucket_for_path(["L"] * 7 + ["X"])

    # Confirm replay guard rejects a changed semantic request.
    def test_replay_guard_rejects_changed_fingerprint(self):
        # Build one retained drop with an original request fingerprint.
        drop = {"request_fingerprint": "original"}
        # Reject a later action body that reuses the same action id differently.
        with self.assertRaises(ConflictError):
            # Exercise the conflict guard.
            engine.assert_replay(drop, "changed")


# Run this focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
