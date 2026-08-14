#!/usr/bin/env python3
# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Import isolated-directory support so teardown evidence never touches repository data.
import tempfile
# Import unittest for focused replay and reconstruction assertions.
import unittest
# Import portable paths for isolated auth, analytics, and autoplay documents.
from pathlib import Path
# Import patching so a failed ledger boundary can prove no direct balance overwrite remains.
from unittest.mock import patch

# Import Admin economics to prove lifecycle cleanup cannot affect payout reporting.
from casino import admin
# Import the exact lifecycle and money services used by production teardown.
from casino.core import auth, autoplay, guest_analytics, ledger, players, storage


# Prove Guest Trial wallet destruction is an exactly-once ledger movement. (LEDGER-035, TEST-188)
class GuestTeardownLedgerTests(unittest.TestCase):
    # Build one complete isolated guest lifecycle boundary for each test.
    def setUp(self):
        # Own a temporary root deleted after the test.
        self.temporary = tempfile.TemporaryDirectory()
        # Resolve the isolated data root once for every module path override.
        self.root = Path(self.temporary.name) / "data"
        # Inject the real JSON provider so wallet and ledger writes share production semantics.
        self.provider = storage.JsonStorageProvider(self.root)
        # Route public player and ledger services into the isolated provider.
        storage.set_provider_for_tests(self.provider)
        # Preserve module-owned document paths before redirecting them.
        self.original_paths = (auth.USERS_PATH, auth.SESSIONS_PATH, auth.GUEST_CREATION_LOG_PATH, autoplay.AUTOPLAY_PATH, guest_analytics.TRIALS_PATH)
        # Redirect the identity document into the isolated root.
        auth.USERS_PATH = self.root / "auth" / "users.json"
        # Redirect the session document into the isolated root.
        auth.SESSIONS_PATH = self.root / "auth" / "sessions.json"
        # Redirect the admission log into the isolated root.
        auth.GUEST_CREATION_LOG_PATH = self.root / "auth" / "guest_creation_log.json"
        # Redirect autoplay state into the isolated root.
        autoplay.AUTOPLAY_PATH = self.root / "autoplay.json"
        # Redirect de-identified lifecycle telemetry into the isolated root.
        guest_analytics.TRIALS_PATH = self.root / "analytics" / "guest_trials.json"

    # Restore every process-global test seam and delete isolated bytes.
    def tearDown(self):
        # Restore the original auth and lifecycle document paths.
        auth.USERS_PATH, auth.SESSIONS_PATH, auth.GUEST_CREATION_LOG_PATH, autoplay.AUTOPLAY_PATH, guest_analytics.TRIALS_PATH = self.original_paths
        # Clear provider injection before deleting the data root.
        storage.set_provider_for_tests(None)
        # Delete the complete isolated fixture tree.
        self.temporary.cleanup()

    # Create one server-shaped guest without involving unrelated admission limits.
    def _guest(self):
        # Create the disposable wallet through the public player service.
        player = players.create_player("Guest trial", "guest", auth.GUEST_STARTING_BALANCE)
        # Create the opaque de-identified trial identity used by the action key.
        analytics_id = guest_analytics.record_started("en-US", "desktop", auth.GUEST_STARTING_BALANCE)
        # Build only the server-owned fields consumed by teardown.
        user = {"user_id": "guest_unit", "player_id": player["player_id"], "guest": True, "role": "guest", "roles": ["guest"], "status": "active", "identity_provider": "guest", "guest_analytics_id": analytics_id}
        # Persist the identity so terminal status can be proved after teardown.
        auth.save_users({"schema_version": 1, "users": [user], "reservations": []})
        # Persist one resumable session so revocation is measured rather than assumed.
        auth.save_sessions({"schema_version": 1, "sessions": [{"session_id": "session_unit", "user_id": user["user_id"]}]})
        # Return the server-shaped principal to the focused test.
        return user

    # Prove one terminal debit, safe replay, exact reconstruction, and economics isolation.
    def test_terminal_wallet_debit_is_exactly_once_and_reconstructs_zero(self):
        # Create one isolated guest with the reviewed starting grant.
        user = self._guest()
        # Capture the game-economics projection before lifecycle money moves.
        economics_before = admin.game_economics()
        # End the trial through the canonical production service.
        auth.end_guest_trial(user, "ended")
        # Repeat the same lifecycle call to prove idempotent replay.
        auth.end_guest_trial(user, "ended")
        # Read the terminal movement from the provider-backed ledger.
        terminal_events = [event for event in ledger.read_recent(user["player_id"], 100) if event.get("transaction_type") == "GUEST_TRIAL_END"]
        # Require exactly one debit with the complete pre/post wallet proof.
        self.assertEqual(len(terminal_events), 1)
        # Bind the exact debit magnitude and terminal wallet.
        self.assertEqual((terminal_events[0]["amount"], terminal_events[0]["balance_before"], terminal_events[0]["balance_after"]), (-auth.GUEST_STARTING_BALANCE, auth.GUEST_STARTING_BALANCE, 0.0))
        # Require the action identity to derive from the immutable trial id.
        self.assertEqual(terminal_events[0]["details"]["ledger_action_key"], f"guest-trial-end:{user['guest_analytics_id']}")
        # Reconstruct the final wallet from the reviewed grant plus every durable movement.
        reconstructed = round(auth.GUEST_STARTING_BALANCE + sum(float(event["amount"]) for event in ledger.read_recent(user["player_id"], 100)), 2)
        # Require the ledger graph and authoritative wallet to converge at zero.
        self.assertEqual((reconstructed, players.get_player(user["player_id"])["balance"]), (0.0, 0.0))
        # Require terminal identity, session, and wallet presentation state.
        self.assertEqual((auth.find_user_by_id(user["user_id"])["status"], auth.load_sessions()["sessions"], players.get_player(user["player_id"])["status"]), ("ended", [], "ended"))
        # Prove infrastructure-only teardown cannot alter Admin payout economics.
        self.assertEqual(admin.game_economics(), economics_before)
        # Prove the explicit teardown type stays excluded even if malformed historical data adds a game.
        self.assertFalse(admin._is_player_facing({"game": "roulette", "transaction_type": "GUEST_TRIAL_END"}))

    # Prove a failed terminal ledger operation leaves the wallet intact for operator recovery.
    def test_terminal_ledger_failure_never_forces_balance_to_zero(self):
        # Create one isolated funded guest whose terminal debit will be interrupted.
        user = self._guest()
        # Replace only the ledger boundary with a deterministic storage failure.
        with patch.object(auth.ledger, "debit_once", side_effect=RuntimeError("ledger unavailable")):
            # Require the canonical teardown to preserve the provider failure.
            with self.assertRaisesRegex(RuntimeError, "ledger unavailable"):
                # Attempt terminal lifecycle processing once.
                auth.end_guest_trial(user, "revoked")
        # Require the authoritative wallet to retain every token instead of being overwritten.
        self.assertEqual(players.get_player(user["player_id"])["balance"], auth.GUEST_STARTING_BALANCE)
        # Require no invented lifecycle ledger row.
        self.assertEqual(ledger.read_recent(user["player_id"], 100), [])


# Run the focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
