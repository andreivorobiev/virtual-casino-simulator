#!/usr/bin/env python3
# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Import isolated-directory support so teardown evidence never touches repository data.
import tempfile
# Import deterministic thread coordination for conversion-versus-teardown ownership races.
import threading
# Import unittest for focused replay and reconstruction assertions.
import unittest
# Import portable paths for isolated auth, analytics, and autoplay documents.
from pathlib import Path
# Import patching so a failed ledger boundary can prove no direct balance overwrite remains.
from unittest.mock import patch

# Import Admin economics to prove lifecycle cleanup cannot affect payout reporting.
from casino import admin
# Import the exact lifecycle and money services used by production teardown.
# Import the canonical conversion service so both lifecycle contenders use production code.
from casino.core import auth, autoplay, guest_analytics, guest_conversion, ledger, players, storage
# Import bounded application conflicts used by the losing ownership contender.
from casino.errors import ConflictError, ValidationError


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

    # Build one valid conversion payload with a stable operation identity for race tests.
    def _conversion_payload(self, suffix: str) -> dict:
        # Return policy-compliant content that adopts the existing guest wallet.
        return {"email": f"teardown-{suffix}@example.test", "password": "TeardownRacePassw0rd!23", "display_name": "Teardown Race Player", "terms_version": "v1", "accepted": True, "idempotency_key": f"guest-teardown-conversion-{suffix}-0001"}

    # Read the isolated provider's complete bounded history projection for byte-stable comparisons.
    def _history(self) -> list[dict]:
        # Return detached provider history so later mutations cannot alter the captured baseline.
        return [dict(row) for row in self.provider.recent_history(limit=100)]

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
        # Require the canonical identity to retain a recoverable claim instead of publishing false completion.
        self.assertEqual((auth.find_user_by_id(user["user_id"])["status"], auth.find_user_by_id(user["user_id"])["guest_teardown_reason"]), ("ending", "revoked"))
        # Resume the interrupted claim through the same expiry sweep used after process restart.
        self.assertEqual(auth.expire_overdue_guests(), 1)
        # Require the resumed teardown to converge on one terminal wallet movement.
        terminal_events = [event for event in ledger.read_recent(user["player_id"], 100) if event.get("transaction_type") == "GUEST_TRIAL_END"]
        # Bind exact retry, wallet, identity, and player terminal state.
        self.assertEqual((len(terminal_events), players.get_player(user["player_id"])["balance"], players.get_player(user["player_id"])["status"], auth.find_user_by_id(user["user_id"])["status"]), (1, 0.0, "ended", "ended"))
        # Require the first durable reason to survive failure and recovery.
        trial = next(row for row in guest_analytics.read_json(guest_analytics.TRIALS_PATH, guest_analytics.default_trials)["trials"] if row["analytics_id"] == user["guest_analytics_id"])
        # Prove recovery did not relabel the operator-requested terminal reason.
        self.assertEqual(trial["end_reason"], "revoked")

    # Prove a conversion that wins the identity lock makes an overlapping stale teardown a complete no-op.
    def test_conversion_winner_blocks_stale_teardown_without_wallet_or_session_mutation(self):
        # Create one active guest and one distinguishable legitimate money movement.
        user = self._guest()
        # Move fake money through the ledger so balance, history, and ledger preservation are measurable.
        ledger.debit(user["player_id"], 125, "GUEST_PLAY", game="roulette", round_id="teardown-convert-round")
        # Pause teardown immediately before its canonical identity transaction.
        claim_entered = threading.Event()
        # Release teardown only after conversion publishes the durable account owner.
        release_claim = threading.Event()
        # Retain the production strict mutation helper behind the synchronization seam.
        strict_update = auth.update_json_strict
        # Capture unexpected teardown failures for the parent assertion.
        teardown_errors = []

        # Hold only the new guest-claim callback before it acquires the provider document lock.
        def held_strict_update(path, mutator, default, invalid_message):
            # Synchronize only the canonical teardown claim on the shared users document.
            if path == auth.USERS_PATH and getattr(mutator, "__name__", "") == "claim":
                # Signal that the stale request is genuinely overlapping conversion.
                claim_entered.set()
                # Wait a bounded interval for conversion to win ownership.
                if not release_claim.wait(5):
                    # Surface deterministic coordination failure without touching production state.
                    raise AssertionError("conversion did not release stale teardown")
            # Delegate every real mutation to the production implementation.
            return strict_update(path, mutator, default, invalid_message)

        # Invoke the stale teardown in one independent request thread.
        def stale_teardown():
            # Preserve any unexpected exception for exact parent-thread reporting.
            try:
                # Submit the pre-conversion user dictionary while conversion is about to win.
                auth.end_guest_trial(dict(user), "expired")
            # Retain failures without swallowing them as thread warnings.
            except BaseException as exc:
                # Append only the in-memory exception object.
                teardown_errors.append(exc)

        # Replace only auth's strict update alias during the deterministic rendezvous.
        with patch.object(auth, "update_json_strict", side_effect=held_strict_update):
            # Start the stale teardown before conversion.
            teardown_thread = threading.Thread(target=stale_teardown)
            # Begin the overlapping request.
            teardown_thread.start()
            # Require the stale request to reach the exact pre-claim boundary.
            self.assertTrue(claim_entered.wait(5))
            # Convert through the canonical self-service path while teardown remains paused.
            result = guest_conversion.convert(user, **self._conversion_payload("winner"))
            # Release the stale caller after the account and terminal conversion marker are durable.
            release_claim.set()
            # Join the bounded stale request.
            teardown_thread.join(5)
        # Require the stale request to stop cleanly and without hidden failure.
        self.assertFalse(teardown_thread.is_alive())
        # Require no exception because converted teardown is a stable no-op.
        self.assertEqual(teardown_errors, [])
        # Resolve the canonical account before creating a retained account session.
        account = auth.find_user_by_email(result["email"])
        # Create one post-conversion account session that stale guest teardown must not revoke.
        auth.create_session(account, "stale-teardown-race")
        # Capture exact adopted-wallet state after completed conversion.
        player_before = dict(players.get_player(user["player_id"]))
        # Capture exact ledger and history state after completed conversion.
        ledger_before = ledger.read_recent(user["player_id"], 100)
        # Capture exact session state after the durable account session exists.
        sessions_before = auth.load_sessions()
        # Capture exact provider history after completed conversion.
        history_before = self._history()
        # Replay the stale pre-conversion dictionary twice after conversion.
        auth.end_guest_trial(dict(user), "ended")
        # Repeat with a different bounded reason to prove no terminal relabeling or hidden side effect.
        auth.end_guest_trial(dict(user), "expired")
        # Require wallet, ledger, history, and sessions to remain byte-stable across both stale calls.
        self.assertEqual((players.get_player(user["player_id"]), ledger.read_recent(user["player_id"], 100), self._history(), auth.load_sessions()), (player_before, ledger_before, history_before, sessions_before))
        # Require one exact converted account owner and no terminal teardown movement.
        owners = [stored for stored in auth.load_users()["users"] if stored.get("player_id") == user["player_id"] and not auth.is_guest(stored)]
        # Bind account ownership, preserved balance, and the absence of a stale teardown debit.
        self.assertEqual((len(owners), owners[0]["user_id"], result["balance"], [event for event in ledger_before if event.get("transaction_type") == "GUEST_TRIAL_END"]), (1, account["user_id"], player_before["balance"], []))
        # Require the guest marker and analytics to avoid an ordinary ended or expired classification.
        terminal_guest = auth.find_user_by_id(user["user_id"])
        # Read the de-identified trial row without publishing its opaque identity.
        trial = next(row for row in guest_analytics.read_json(guest_analytics.TRIALS_PATH, guest_analytics.default_trials)["trials"] if row["analytics_id"] == user["guest_analytics_id"])
        # Prove the stale caller did not overwrite converted identity or close ordinary teardown analytics.
        self.assertEqual(terminal_guest["status"], "converted")
        # Keep the self-service row open rather than misclassifying it as ended or expired.
        self.assertNotIn(trial.get("end_reason"), {"ended", "expired"})

    # Prove a teardown claim that wins the identity lock prevents a parallel conversion from adopting the wallet.
    def test_teardown_winner_blocks_parallel_conversion_and_remains_exactly_once(self):
        # Create one active funded guest shared by both lifecycle contenders.
        user = self._guest()
        # Pause conversion immediately before its account append transaction.
        append_entered = threading.Event()
        # Release conversion only after teardown reaches complete terminal state.
        release_append = threading.Event()
        # Retain the production identity update helper behind the synchronization seam.
        normal_update = auth.update_json
        # Capture the losing conversion outcome without thread-level warnings.
        conversion_errors = []

        # Hold only account creation's append callback before the provider transaction.
        def held_update(path, mutator, default):
            # Synchronize only the account adoption attempt on the shared users document.
            if path == auth.USERS_PATH and getattr(mutator, "__name__", "") == "append_user":
                # Signal that conversion passed every validation and reached ownership publication.
                append_entered.set()
                # Wait a bounded interval for teardown to win the identity lock.
                if not release_append.wait(5):
                    # Surface deterministic coordination failure without weakening production code.
                    raise AssertionError("teardown did not release conversion")
            # Delegate every mutation to the production helper.
            return normal_update(path, mutator, default)

        # Attempt canonical conversion in an independent request thread.
        def parallel_conversion():
            # Preserve only the bounded losing exception for parent-thread proof.
            try:
                # Submit one valid conversion that will pause before account append.
                guest_conversion.convert(user, **self._conversion_payload("loser"))
            # Retain the expected bounded application rejection.
            except (ConflictError, ValidationError) as exc:
                # Append the exact exception object for type and count assertions.
                conversion_errors.append(exc)

        # Replace only auth's normal update alias during the account-append rendezvous.
        with patch.object(auth, "update_json", side_effect=held_update):
            # Start conversion before terminal teardown.
            conversion_thread = threading.Thread(target=parallel_conversion)
            # Begin the overlapping account adoption request.
            conversion_thread.start()
            # Require conversion to reach the exact pre-append boundary.
            self.assertTrue(append_entered.wait(5))
            # Let teardown claim, debit, revoke, and finalize the guest first.
            auth.end_guest_trial(dict(user), "revoked")
            # Release account append only after terminal teardown is durable.
            release_append.set()
            # Join the bounded losing request.
            conversion_thread.join(5)
        # Require conversion to terminate and report one bounded ownership rejection.
        self.assertFalse(conversion_thread.is_alive())
        # Require exactly one expected conflict or inactive-guest validation outcome.
        self.assertEqual(len(conversion_errors), 1)
        # Require no durable account to share the ended guest player.
        owners = [stored for stored in auth.load_users()["users"] if stored.get("player_id") == user["player_id"] and not auth.is_guest(stored)]
        # Bind one terminal identity and no account owner.
        self.assertEqual((auth.find_user_by_id(user["user_id"])["status"], owners), ("ended", []))
        # Require one exact teardown debit across an explicit terminal replay.
        auth.end_guest_trial(dict(user), "ended")
        # Select only the terminal movement from authoritative ledger history.
        terminal_events = [event for event in ledger.read_recent(user["player_id"], 100) if event.get("transaction_type") == "GUEST_TRIAL_END"]
        # Bind exactly-once wallet, player, identity, and session terminal state.
        self.assertEqual((len(terminal_events), players.get_player(user["player_id"])["balance"], players.get_player(user["player_id"])["status"], auth.load_sessions()["sessions"]), (1, 0.0, "ended", []))


# Run the focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
