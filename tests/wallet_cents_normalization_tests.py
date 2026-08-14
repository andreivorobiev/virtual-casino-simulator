# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Provider-parity tests for explicit wallet cents normalization."""

# Import output capture for deterministic command evidence.
import io
# Import deep-copy support for relational transaction rollback snapshots.
import copy
# Import JSON helpers for source fixtures and audit-row inspection.
import json
# Import temporary directories for isolated JSON provider state.
import tempfile
# Import unittest for the repository's standard test runner.
import unittest
# Import stdout redirection for the operator command contract.
from contextlib import redirect_stdout
# Import Decimal so relational fixtures can retain sub-cent source values.
from decimal import Decimal
# Import paths for isolated provider roots.
from pathlib import Path
# Import patching support for explicit crash-boundary injection.
from unittest import mock

# Import the configured storage module and concrete providers under test.
from casino.core import storage
# Import the explicit operator command entry point.
from scripts import normalize_wallet_balances


# Model the small SQL subset used by the MySQL normalization transaction.
class _MySQLNormalizationCursor:
    # Bind one shared fake relational store.
    def __init__(self, store):
        # Retain mutable players and ledger collections across provider connections.
        self.store = store
        # Start without a pending fetch result.
        self.result = None

    # Execute one recognized provider statement against the fake store.
    def execute(self, statement, params=None):
        # Normalize absent parameters to the empty tuple used by the DB-API.
        params = params or ()
        # Return the complete row-locked wallet projection.
        if statement.startswith("SELECT player_id, balance FROM casino_players ORDER BY"):
            # Copy rows so provider-local mutation cannot bypass UPDATE evidence.
            self.result = [dict(row) for row in self.store["players"]]
            # Stop after preparing the fetch-all result.
            return
        # Resolve one deterministic ledger identity for replay checks.
        if statement.startswith("SELECT ledger_id, ts, player_id") and "WHERE ledger_id = %s" in statement:
            # Return the matching row or no result.
            self.result = self.store["ledger"].get(params[0])
            # Stop after preparing the fetch-one result.
            return
        # Append one normalization audit row.
        if statement.startswith("INSERT INTO casino_ledger"):
            # Decode the bound fields into the same row shape returned by MySQL.
            row = {"ledger_id": params[0], "ts": params[1], "player_id": params[2], "game": params[3], "round_id": params[4], "transaction_type": params[5], "amount": params[6], "balance_before": params[7], "balance_after": params[8], "action_scope": params[9], "action_key": params[10], "action_fingerprint": params[11], "details_json": params[12]}
            # Preserve the append-only row by deterministic ledger identity.
            self.store["ledger"][row["ledger_id"]] = row
            # Clear fetch state for the write statement.
            self.result = None
            # Stop after recording the insert.
            return
        # Update one already locked wallet to exact cents.
        if statement.startswith("UPDATE casino_players SET balance"):
            # Inject one post-audit provider failure for rollback evidence.
            if self.store.get("fail_update"):
                # Stop before the wallet write so the surrounding transaction must undo the audit insert.
                raise RuntimeError("synthetic wallet update failure")
            # Locate the selected durable wallet.
            player = next(row for row in self.store["players"] if row["player_id"] == params[2])
            # Publish the exact Decimal value supplied by the provider.
            player["balance"] = params[0]
            # Clear fetch state for the write statement.
            self.result = None
            # Stop after recording the update.
            return
        # Fail immediately when production SQL expands without updating this proof model.
        raise AssertionError(f"unexpected SQL: {statement}")

    # Return the prepared multi-row result.
    def fetchall(self):
        # Detach the list so test callers cannot mutate cursor state.
        return list(self.result or [])

    # Return the prepared point result.
    def fetchone(self):
        # Return a detached mapping when a row exists.
        return dict(self.result) if isinstance(self.result, dict) else None


# Model transaction and cleanup evidence for one fake MySQL lease.
class _MySQLNormalizationConnection:
    # Bind the shared relational state.
    def __init__(self, store):
        # Retain the fake database collections.
        self.store = store
        # Count explicit transaction starts.
        self.started = 0
        # Count durable commits.
        self.commits = 0
        # Count rollbacks, including read-only scan release.
        self.rollbacks = 0
        # Track final lease cleanup.
        self.closed = False
        # Start without a rollback snapshot before the transaction opens.
        self.snapshot = None

    # Start the provider transaction.
    def start_transaction(self):
        # Record the exact one-transaction boundary.
        self.started += 1
        # Capture the fake relational state so rollback models database atomicity.
        self.snapshot = copy.deepcopy({"players": self.store["players"], "ledger": self.store["ledger"]})

    # Return a cursor over the shared fake store.
    def cursor(self, dictionary=False):
        # Ignore the driver projection flag because this model always returns mappings.
        return _MySQLNormalizationCursor(self.store)

    # Commit the current fake transaction.
    def commit(self):
        # Record successful atomic publication.
        self.commits += 1

    # Roll back the current fake transaction.
    def rollback(self):
        # Record explicit transaction release or failure cleanup.
        self.rollbacks += 1
        # Restore the transaction-start state when a snapshot exists.
        if self.snapshot is not None:
            # Replace player rows with their exact pre-transaction values.
            self.store["players"][:] = copy.deepcopy(self.snapshot["players"])
            # Replace ledger rows with their exact pre-transaction values.
            self.store["ledger"].clear()
            # Restore every original append-only row after clearing later writes.
            self.store["ledger"].update(copy.deepcopy(self.snapshot["ledger"]))

    # Close the fake provider lease.
    def close(self):
        # Record mandatory connection cleanup.
        self.closed = True


# Verify JSON and MySQL providers converge on one cents contract. (TEST-190)
class WalletCentsNormalizationTests(unittest.TestCase):
    # Create one isolated JSON provider before each test.
    def setUp(self):
        # Allocate a temporary directory owned by this test.
        self.temp = tempfile.TemporaryDirectory()
        # Construct the provider without touching repository data.
        self.provider = storage.JsonStorageProvider(Path(self.temp.name))
        # Route the operator script through this exact isolated provider.
        storage.set_provider_for_tests(self.provider)

    # Restore global provider state and remove temporary files.
    def tearDown(self):
        # Clear the injected provider before deleting its root.
        storage.set_provider_for_tests(None)
        # Remove the complete isolated directory.
        self.temp.cleanup()

    # Write one structurally valid wallet document with explicit source balances.
    def _seed_players(self, balances):
        # Ensure the provider directory exists before writing the intentional legacy fixture.
        self.provider.ensure_ready()
        # Build complete compatible player rows around the supplied balances.
        players = [{"player_id": player_id, "display_name": player_id, "type": "human", "balance": balance, "created_at": "2026-08-13T00:00:00Z", "updated_at": "2026-08-13T00:00:00Z", "status": "active"} for player_id, balance in balances]
        # Publish the deliberate pre-normalization bytes without using a guarded writer.
        self.provider.players_path().write_text(json.dumps({"schema_version": "1.0", "players": players}, sort_keys=True), encoding="utf-8")

    # Prove scan is read-only and apply emits one resumable audit row.
    def test_json_residue_is_audited_normalized_and_idempotent(self):
        # Seed one residue wallet and one already exact wallet.
        self._seed_players((("residue", 100.000000001), ("exact", 20.25)))
        # Capture exact source bytes before the read-only scan.
        original = self.provider.players_path().read_bytes()
        # Scan without authorizing a write.
        scanned = self.provider.normalize_wallet_balances(apply=False)
        # Require one finding and byte-identical durable state.
        self.assertEqual((1, 0, False, original), (scanned["residue_count"], scanned["normalized_count"], scanned["clean"], self.provider.players_path().read_bytes()))
        # Apply the explicit provider-owned pass.
        applied = self.provider.normalize_wallet_balances(apply=True)
        # Require one applied normalization and a clean postcondition.
        self.assertEqual((1, 1, True, True), (applied["residue_count"], applied["normalized_count"], applied["clean"], applied["applied"]))
        # Load through the ordinary strict boundary after repair.
        players = self.provider.load_players(lambda: {})["players"]
        # Require both wallets to round-trip through the game-action cents bridge.
        self.assertEqual({"residue": 10000, "exact": 2025}, {row["player_id"]: self.provider._json_wallet_cents(row["balance"]) for row in players})
        # Read the append-only normalization evidence.
        events = [json.loads(line) for line in self.provider.ledger_path().read_text(encoding="utf-8").splitlines()]
        # Require one zero-cent visible audit row with the exact residue retained in details.
        self.assertEqual((1, "WALLET_CENTS_NORMALIZATION", 0.0, "100.000000001", "100.00", "-1E-9"), (len(events), events[0]["transaction_type"], events[0]["amount"], events[0]["details"]["stored_balance"], events[0]["details"]["normalized_balance"], events[0]["details"]["residue"]))
        # Reapply to prove no duplicate event or wallet mutation is invented.
        replay = self.provider.normalize_wallet_balances(apply=True)
        # Require an empty repair set and the original single ledger row.
        self.assertEqual((0, 0, 1), (replay["residue_count"], replay["normalized_count"], len(self.provider.ledger_path().read_text(encoding="utf-8").splitlines())))

    # Prove a stopped JSON pass resumes from its durable audit without duplicating it.
    def test_json_interrupted_apply_resumes_without_duplicate_audit(self):
        # Seed one recoverable residue value.
        self._seed_players((("interrupted", 4.000000001),))
        # Inject failure only at the final atomic players publication boundary.
        with mock.patch.object(self.provider, "_save_players_document", side_effect=OSError("synthetic publication failure")):
            # Require the explicit apply to surface the incomplete publication.
            with self.assertRaisesRegex(OSError, "synthetic publication failure"):
                # Run one interrupted repair after its audit row becomes durable.
                self.provider.normalize_wallet_balances(apply=True)
        # Require the source wallet to remain dirty while exactly one audit row exists.
        self.assertEqual((1, 1), (self.provider.normalize_wallet_balances(apply=False)["residue_count"], len(self.provider.ledger_path().read_text(encoding="utf-8").splitlines())))
        # Resume through the same deterministic operator action.
        resumed = self.provider.normalize_wallet_balances(apply=True)
        # Require successful repair with no second audit row.
        self.assertEqual((1, 0, 1), (resumed["normalized_count"], self.provider.normalize_wallet_balances(apply=False)["residue_count"], len(self.provider.ledger_path().read_text(encoding="utf-8").splitlines())))

    # Prove the command distinguishes check from explicit apply and verifies residue zero.
    def test_operator_command_fails_dirty_check_then_verifies_apply(self):
        # Seed one recoverable residue value.
        self._seed_players((("command", 1.000000001),))
        # Capture the read-only command evidence.
        check_output = io.StringIO()
        # Run the check without provider mutation.
        with redirect_stdout(check_output):
            # Store the conventional dirty status.
            check_status = normalize_wallet_balances.main(["check"])
        # Require a nonzero check and one remaining residue.
        self.assertEqual((1, 1), (check_status, json.loads(check_output.getvalue())["remaining_residue_count"]))
        # Capture the explicit apply evidence.
        apply_output = io.StringIO()
        # Run the one-time operator write path.
        with redirect_stdout(apply_output):
            # Store the verified success status.
            apply_status = normalize_wallet_balances.main(["apply"])
        # Require successful application and an exact zero-residue rescan.
        self.assertEqual((0, 1, 0), (apply_status, json.loads(apply_output.getvalue())["normalized_count"], json.loads(apply_output.getvalue())["remaining_residue_count"]))

    # Prove every ordinary JSON player writer preserves exact integer cents.
    def test_json_write_paths_cannot_reintroduce_residue(self):
        # Seed one exact wallet through the legacy fixture boundary.
        self._seed_players((("updated", 10.00),))
        # Submit a half-cent direct player update.
        self.provider.update_player("updated", lambda row: row.update({"balance": 10.005}))
        # Provision one deterministic wallet with a half-cent source.
        self.provider.ensure_player({"player_id": "ensured", "display_name": "ensured", "type": "human", "balance": 7.015, "created_at": "2026-08-13T00:00:00Z", "updated_at": "2026-08-13T00:00:00Z", "status": "active"})
        # Bootstrap one missing wallet with another half-cent source.
        self.provider.bootstrap_players({"players": [{"player_id": "bootstrapped", "display_name": "bootstrapped", "type": "human", "balance": 8.025, "created_at": "2026-08-13T00:00:00Z", "updated_at": "2026-08-13T00:00:00Z", "status": "active"}]})
        # Load the exact durable wallet values after all three write paths.
        rows = {row["player_id"]: row["balance"] for row in self.provider.load_players(lambda: {})["players"]}
        # Require deterministic half-even cents for every stored wallet.
        self.assertEqual({"updated": 10.0, "ensured": 7.02, "bootstrapped": 8.02}, rows)
        # Require the residue scan to remain clean after ordinary writes.
        self.assertEqual(0, self.provider.normalize_wallet_balances(apply=False)["residue_count"])

    # Prove the relational provider uses one atomic audit-and-wallet transaction.
    def test_mysql_residue_uses_locked_atomic_normalization(self):
        # Build one shared relational store with deliberate high-precision source residue.
        store = {"players": [{"player_id": "mysql-player", "balance": Decimal("12.000000001")}], "ledger": {}, "fail_update": False}
        # Construct a normal lazy provider with a harmless local fixture identity.
        provider = storage.MySQLStorageProvider(storage.MySQLConfig(host="127.0.0.1", port=3306, user="fixture", password="", database="casino_fixture"))
        # Skip network readiness because the deterministic connection model owns all SQL.
        provider.ensure_ready = lambda: None
        # Retain every issued connection for transaction and cleanup assertions.
        connections = []
        # Return one fresh fake lease per provider call.
        provider.connect = lambda: connections.append(_MySQLNormalizationConnection(store)) or connections[-1]
        try:
            # Prove the read-only scan finds the residue and rolls back its locks.
            scanned = provider.normalize_wallet_balances(apply=False)
            # Require one finding, one transaction, one rollback, and closed lease.
            self.assertEqual((1, 1, 1, 0, True), (scanned["residue_count"], connections[0].started, connections[0].rollbacks, connections[0].commits, connections[0].closed))
            # Inject one failure after audit insertion but before wallet publication.
            store["fail_update"] = True
            # Require the provider to surface the failed atomic transaction.
            with self.assertRaisesRegex(RuntimeError, "synthetic wallet update failure"):
                # Run the explicit apply against the failing transaction model.
                provider.normalize_wallet_balances(apply=True)
            # Require rollback to remove the audit and preserve the exact source wallet.
            self.assertEqual((Decimal("12.000000001"), 0, 1, True), (store["players"][0]["balance"], len(store["ledger"]), connections[1].rollbacks, connections[1].closed))
            # Clear the bounded injection before the successful apply.
            store["fail_update"] = False
            # Apply the exact same provider operation.
            applied = provider.normalize_wallet_balances(apply=True)
            # Require one normalized row and one atomic commit.
            self.assertEqual((1, 1, 1, True), (applied["normalized_count"], connections[2].started, connections[2].commits, connections[2].closed))
            # Require exact cents and one append-only relational audit row.
            self.assertEqual((Decimal("12.00"), 1), (store["players"][0]["balance"], len(store["ledger"])))
            # Re-scan to prove the cents bridge has no remaining relational residue.
            self.assertEqual(0, provider.normalize_wallet_balances(apply=False)["residue_count"])
        finally:
            # Close the unused lazy pool without allocating a real connector session.
            provider.close_pool()


# Run the focused suite when invoked directly.
if __name__ == "__main__":
    # Delegate to unittest's standard CLI.
    unittest.main()
