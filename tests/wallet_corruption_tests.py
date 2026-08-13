#!/usr/bin/env python3
# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Import SHA-256 for non-sensitive hostile-fixture labels.
import hashlib
# Import JSON encoding for structurally corrupt wallet fixtures.
import json
# Import isolated-directory support so tests never touch user wallet data.
import tempfile
# Import unittest for focused provider-neutral recovery evidence.
import unittest
# Import portable paths for exact forensic artifact inspection.
from pathlib import Path

# Import the schema version used by compatible wallet documents.
from casino.config import SCHEMA_VERSION
# Import public player and storage seams for end-to-end fallback rejection.
from casino.core import players, storage
# Import the fixed conflict envelope expected from corrupt money state.
from casino.errors import ConflictError


# Prove wallet corruption never seeds defaults or permits a settlement. (STORAGE-014, TEST-177)
class WalletCorruptionTests(unittest.TestCase):
    # Allocate one isolated valid wallet document for each corruption schedule.
    def setUp(self):
        # Own a temporary root that is deleted after the individual test.
        self.temporary = tempfile.TemporaryDirectory()
        # Build the production JSON provider over the isolated root.
        self.provider = storage.JsonStorageProvider(Path(self.temporary.name) / "data")
        # Define one exact durable wallet without unrelated default accounts.
        self.valid_state = {
            # Preserve the current public storage schema marker.
            "schema_version": SCHEMA_VERSION,
            # Store one synthetic player used by read and settlement proof.
            "players": [{"player_id": "human", "display_name": "You", "type": "human", "balance": 5000.0, "created_at": "created", "updated_at": "updated", "status": "active"}],
        }
        # Publish the valid starting wallet through the production atomic writer.
        self.provider._save_players_document(self.valid_state)
        # Prime recovery state before corruption so later inventory comparisons are exact.
        self.assertEqual(self.provider.load_players(lambda: self.valid_state)["players"][0]["balance"], 5000.0)
        # Capture the exact verified source bytes used for operator recovery.
        self.valid_bytes = self.provider.players_path().read_bytes()

    # Release provider injection and the isolated root after every outcome.
    def tearDown(self):
        # Clear any public-service provider override left by a failing assertion.
        storage.set_provider_for_tests(None)
        # Delete the isolated temporary tree.
        self.temporary.cleanup()

    # Prove only a genuinely absent wallet document can use reviewed bootstrap defaults.
    def test_absent_wallet_uses_default_once_without_forensic_artifact(self):
        # Remove the valid document to model an unused first-run data root.
        self.provider.players_path().unlink()
        # Track exact lazy default evaluation.
        default_calls = []
        # Define one reviewed first-run wallet factory.
        def reviewed_default():
            # Record the only permitted fallback evaluation.
            default_calls.append("called")
            # Return an isolated copy of the valid wallet fixture.
            return json.loads(json.dumps(self.valid_state))
        # Read the genuinely absent wallet through the production provider.
        state = self.provider.load_players(reviewed_default)
        # Require exactly one evaluation and the reviewed balance.
        self.assertEqual((default_calls, state["players"][0]["balance"]), (["called"], 5000.0))
        # Require an absent file not to create false corruption evidence.
        self.assertEqual(list(self.provider.players_path().parent.glob("players.json.corrupt-*")), [])

    # Enumerate every syntax, shape, identity, and money corruption class.
    def test_corrupt_wallet_variants_fail_closed_with_exact_forensic_copy(self):
        # Define hostile bytes that must never select a default wallet document.
        hostile_payloads = (
            # Refuse truncated JSON.
            b'{"schema_version":1,"players":[',
            # Refuse invalid UTF-8.
            b"\xff\xfe\xfa",
            # Refuse duplicate keys instead of accepting the final value.
            b'{"players":[],"players":[]}',
            # Refuse a non-object document.
            b"[]",
            # Refuse a non-list player collection.
            b'{"players":{}}',
            # Refuse duplicate durable wallet identities.
            json.dumps({"players": [{"player_id": "human", "balance": 1}, {"player_id": "human", "balance": 2}]}).encode("utf-8"),
            # Refuse a string balance that legacy float coercion would have accepted.
            json.dumps({"players": [{"player_id": "human", "balance": "5000"}]}).encode("utf-8"),
            # Refuse non-finite JSON constants.
            b'{"players":[{"player_id":"human","balance":NaN}]}',
            # Refuse hidden sub-cent money.
            json.dumps({"players": [{"player_id": "human", "balance": 1.001}]}).encode("utf-8"),
            # Refuse an impossible negative durable wallet.
            json.dumps({"players": [{"player_id": "human", "balance": -1}]}).encode("utf-8"),
        )
        # Exercise each corruption class against a clean verified wallet baseline.
        for hostile in hostile_payloads:
            # Label failures without reflecting hostile bytes in production diagnostics.
            with self.subTest(payload_digest=hashlib.sha256(hostile).hexdigest()):
                # Restore the exact verified wallet before this hostile schedule.
                self.provider.players_path().write_bytes(self.valid_bytes)
                # Remove only prior test-created forensic artifacts.
                for artifact in self.provider.players_path().parent.glob("players.json.corrupt-*"):
                    # Delete the isolated artifact before measuring this schedule.
                    artifact.unlink()
                # Replace the authoritative wallet with the exact corrupt bytes.
                self.provider.players_path().write_bytes(hostile)
                # Track whether a forbidden bootstrap default is evaluated.
                default_calls = []
                # Define a default factory that would recreate funded wallets if reached.
                def forbidden_default():
                    # Record any unsafe corruption fallback.
                    default_calls.append("called")
                    # Return the original valid wallet solely to expose fallback use.
                    return self.valid_state
                # Require the provider read to use one fixed recovery boundary.
                with self.assertRaisesRegex(ConflictError, "^Wallet storage requires operator recovery$"):
                    # Attempt to load corrupt money state.
                    self.provider.load_players(forbidden_default)
                # Require no funded default creation.
                self.assertEqual(default_calls, [])
                # Require the authoritative corrupt bytes to remain untouched.
                self.assertEqual(self.provider.players_path().read_bytes(), hostile)
                # Locate the sole content-addressed forensic backup.
                backups = list(self.provider.players_path().parent.glob("players.json.corrupt-*"))
                # Require exactly one exact copy rather than repeated timestamped artifacts.
                self.assertEqual(len(backups), 1)
                # Require byte-identical forensic evidence.
                self.assertEqual(backups[0].read_bytes(), hostile)
                # Repeat the same read to prove the content-addressed backup is idempotent.
                with self.assertRaisesRegex(ConflictError, "^Wallet storage requires operator recovery$"):
                    # Attempt the identical corrupt read again.
                    self.provider.load_players(forbidden_default)
                # Require the repeat to keep one backup and zero default calls.
                self.assertEqual((len(list(self.provider.players_path().parent.glob("players.json.corrupt-*"))), default_calls), (1, []))

    # Prove public reads and both ledger paths stay locked until an operator restores verified bytes.
    def test_corruption_blocks_public_wallet_and_settlement_then_allows_verified_recovery(self):
        # Replace the valid wallet with one truncated payload.
        corrupt = b'{"schema_version":1,"players":[{"player_id":"human"'
        # Persist the corruption outside the provider to model disk damage.
        self.provider.players_path().write_bytes(corrupt)
        # Capture every non-forensic file before attempting reads or writes.
        before = {path.relative_to(self.provider.players_path().parent).as_posix(): path.read_bytes() for path in self.provider.players_path().parent.rglob("*") if path.is_file()}
        # Route public player calls through the isolated provider.
        storage.set_provider_for_tests(self.provider)
        # Require the public read to propagate the provider-owned recovery error.
        with self.assertRaisesRegex(ConflictError, "^Wallet storage requires operator recovery$"):
            # Attempt the ordinary player listing used by wallet surfaces.
            players.list_players()
        # Require an ordinary settlement to stop before balance or ledger mutation.
        with self.assertRaisesRegex(ConflictError, "^Wallet storage requires operator recovery$"):
            # Attempt a debit through the legacy ledger boundary.
            self.provider.transact_ledger("human", -5, "TEST_CORRUPT_DEBIT", "storage", "corrupt-round")
        # Require an idempotent settlement to stop before action-journal commitment.
        with self.assertRaisesRegex(ConflictError, "^Wallet storage requires operator recovery$"):
            # Attempt a keyed debit through the exactly-once boundary.
            self.provider.transact_ledger_once("human", -5, "TEST_CORRUPT_DEBIT", "corrupt-key", "storage", "corrupt-round")
        # Require bootstrap to refuse instead of recreating the missing wallet set.
        with self.assertRaisesRegex(ConflictError, "^Wallet storage requires operator recovery$"):
            # Attempt the normal startup player bootstrap.
            self.provider.bootstrap_players(players.default_players())
        # Require a row-scoped update to stop before invoking its caller mutation.
        update_calls = []
        # Require the player updater to remain unreachable on corrupt money state.
        with self.assertRaisesRegex(ConflictError, "^Wallet storage requires operator recovery$"):
            # Attempt a mutation whose callback records unsafe reachability.
            self.provider.update_player("human", lambda row: update_calls.append(row))
        # Require corruption to prevent caller code from observing the stored row.
        self.assertEqual(update_calls, [])
        # Require every original non-forensic file to remain byte-identical.
        after = {path.relative_to(self.provider.players_path().parent).as_posix(): path.read_bytes() for path in self.provider.players_path().parent.rglob("*") if path.is_file() and ".corrupt-" not in path.name}
        # Compare authoritative and provider-private bytes without the intentional backup.
        self.assertEqual(after, before)
        # Restore only the exact previously verified wallet bytes as the documented operator action.
        self.provider.players_path().write_bytes(self.valid_bytes)
        # Require the restored balance to be visible without default replacement.
        self.assertEqual(players.get_player("human")["balance"], 5000.0)
        # Apply one explicit post-recovery debit.
        event = self.provider.transact_ledger("human", -5, "TEST_RECOVERED_DEBIT", "storage", "recovered-round")
        # Require exactly the original balance minus the requested debit.
        self.assertEqual((event["balance_before"], event["balance_after"]), (5000.0, 4995.0))

    # Prove MySQL row decoding reports the same provider-neutral corruption boundary.
    def test_mysql_corrupt_money_row_uses_same_recovery_error_and_closes_connection(self):
        # Define the dictionary cursor used by the production load path.
        class CorruptCursor:
            # Accept the stable player-select statement without external I/O.
            def execute(self, statement):
                # Require the bounded wallet query rather than an unrelated path.
                self.statement = statement

            # Return one impossible connector row with an invalid string balance.
            def fetchall(self):
                # Model storage corruption below the public provider boundary.
                return [{"player_id": "human", "display_name": "You", "player_type": "human", "balance": "not-money", "created_at": "created", "updated_at": "updated", "status": "active"}]

        # Define one connection that records mandatory cleanup.
        class CorruptConnection:
            # Initialize the connection cleanup marker.
            def __init__(self):
                # Record that close has not happened yet.
                self.closed = False

            # Return the deterministic dictionary cursor.
            def cursor(self, dictionary=False):
                # Require the production mapping mode.
                self.dictionary = dictionary
                # Return one isolated cursor instance.
                return CorruptCursor()

            # Record provider cleanup after the refused read.
            def close(self):
                # Mark the fake lease released.
                self.closed = True

        # Construct the real lazy provider without opening a connector.
        provider = storage.MySQLStorageProvider()
        # Bypass schema readiness because migration policy is proven separately.
        provider.ensure_ready = lambda: None
        # Supply one deterministic corrupt-row connection.
        connection = CorruptConnection()
        # Route only this call into the fake connection.
        provider.connect = lambda: connection
        # Require the same value-free boundary as JSON storage.
        with self.assertRaisesRegex(ConflictError, "^Wallet storage requires operator recovery$"):
            # Attempt the production MySQL player mapping path.
            provider.load_players(players.default_players)
        # Require the provider to release the operation-scoped connection.
        self.assertTrue(connection.closed)


# Run the focused suite when invoked directly by a worker.
if __name__ == "__main__":
    # Exit through unittest's normal result handling.
    unittest.main()
