# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Storage package-boundary ownership and compatibility tests for #728."""

# Import abstract syntax parsing so ownership checks never execute source text.
import ast
# Import signature inspection so the provider contract cannot drift during extraction.
import inspect
# Import concrete repository paths for bounded source and line-count checks.
from pathlib import Path
# Import standard unittest assertions for the focused package seam.
import unittest

# Import the historical public storage module whose callers must remain unchanged.
from casino.core import storage
# Import the extracted provider-neutral owner for exact identity checks.
from casino.core import storage_base


# Resolve the repository root from this tracked test module.
ROOT = Path(__file__).resolve().parents[1]
# Point at the concrete-provider monolith retained during the first #728 slice.
STORAGE_SOURCE = ROOT / "casino" / "core" / "storage.py"
# Point at the extracted package-ready provider-neutral base owner.
BASE_SOURCE = ROOT / "casino" / "core" / "storage_base.py"
# Bind every moved compatibility name that the historical module must re-export.
MOVED_NAMES = (
    "MySQLConfig",
    "StorageProvider",
    "_action_details",
    "_action_fingerprint",
    "_action_scope",
    "_decode_json",
    "_history_from_row",
    "_ledger_event",
    "_ledger_from_row",
    "_money",
    "_money_decimal",
    "_normalizable_players_document",
    "_normalize_action_key",
    "_quantized_money",
    "_quantized_money_decimal",
    "_validate_action_replay",
    "_validate_wallet_normalization_replay",
    "_validated_players_document",
    "_validated_strict_document",
    "_wallet_normalization_event",
)


# Prove the first #728 seam moves ownership without changing the public storage module.
class StoragePackageBoundaryTests(unittest.TestCase):
    """Bind provider-neutral ownership, size, signatures, and compatibility exports."""

    # Require the package-ready base owner to stay below the parent issue ceiling.
    def test_base_owner_is_bounded_and_provider_neutral(self):
        # Read the extracted owner as inert UTF-8 source.
        source = BASE_SOURCE.read_text(encoding="utf-8")
        # Keep this extracted module below the permanent 1,200-line ceiling.
        self.assertLess(len(source.splitlines()), 1200)
        # Parse ownership without importing any concrete provider or opening storage.
        tree = ast.parse(source)
        # Collect top-level concrete classes and functions declared by the base owner.
        declared = {node.name for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))}
        # Require both reviewed public contract objects in their new owner.
        self.assertTrue({"MySQLConfig", "StorageProvider"}.issubset(declared))
        # Reject concrete provider ownership from the provider-neutral base.
        self.assertTrue({"JsonStorageProvider", "MySQLStorageProvider", "_BorrowedMySQLConnection"}.isdisjoint(declared))
        # Reject cache, reset-recovery, and game-action implementation seams from this first slice.
        for forbidden in ("_drop_ledger_cache", "_read_actions_registry", "_create_reset_backup_locked", "execute_game_action_once", "resolve_game_action", "_mysql_game_action_epoch"):
            # Name any accidentally moved concrete responsibility precisely.
            self.assertNotIn(forbidden, source)

    # Require the historical module to expose the exact extracted objects, not wrappers or copies.
    def test_historical_module_reexports_exact_base_objects(self):
        # Compare every moved name by object identity so signatures and function globals stay single-owned.
        for name in MOVED_NAMES:
            # Read the historical compatibility object.
            public_object = getattr(storage, name)
            # Read the extracted owner object.
            owned_object = getattr(storage_base, name)
            # Require one exact object to serve both import paths.
            self.assertIs(public_object, owned_object, name)

    # Require the provider contract and MySQL configuration signatures to remain source-compatible.
    def test_public_contract_signatures_remain_compatible(self):
        # Bind the established MySQL constructor field order used by tests and operators.
        self.assertEqual(tuple(inspect.signature(storage.MySQLConfig).parameters), ("host", "port", "user", "password", "database"))
        # Bind every provider method name and parameter order before concrete-provider extraction.
        expected = {
            "ensure_ready": ("self",),
            "reset": ("self",),
            "reset_transaction": ("self",),
            "state_visibility_transaction": ("self",),
            "load_players": ("self", "default_factory"),
            "normalize_wallet_balances": ("self", "apply"),
            "insert_player": ("self", "player"),
            "bootstrap_players": ("self", "state"),
            "update_player": ("self", "player_id", "updater"),
            "ensure_player": ("self", "player"),
            "transact_ledger": ("self", "player_id", "amount", "transaction_type", "game", "round_id", "details"),
            "transact_ledger_once": ("self", "player_id", "amount", "transaction_type", "action_key", "game", "round_id", "details"),
            "find_ledger_action": ("self", "player_id", "game", "action_key"),
            "read_ledger_recent": ("self", "player_id", "limit"),
            "append_history": ("self", "event"),
            "recent_history": ("self", "limit", "game"),
            "read_document": ("self", "key", "default"),
            "read_document_strict": ("self", "key", "default", "validator"),
            "write_document": ("self", "key", "data"),
            "update_document": ("self", "key", "mutator", "default", "validator"),
        }
        # Compare every established method without instantiating a provider.
        for method_name, parameter_names in expected.items():
            # Read the exact re-exported provider method.
            method = getattr(storage.StorageProvider, method_name)
            # Require the public parameter order to remain unchanged.
            self.assertEqual(tuple(inspect.signature(method).parameters), parameter_names, method_name)

    # Reject duplicate base declarations left in the concrete-provider source.
    def test_concrete_provider_source_imports_base_without_duplicate_owners(self):
        # Parse the remaining monolith as inert source.
        source = STORAGE_SOURCE.read_text(encoding="utf-8")
        # Parse top-level ownership without importing providers a second time.
        tree = ast.parse(source)
        # Collect only declarations still owned by the concrete-provider source.
        declared = {node.name for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))}
        # Reject duplicate public contract classes after the move.
        self.assertTrue({"MySQLConfig", "StorageProvider"}.isdisjoint(declared))
        # Reject duplicate helper function implementations after the move.
        self.assertTrue(set(MOVED_NAMES[2:]).isdisjoint(declared))
        # Require one explicit provider-neutral import owner.
        self.assertEqual(source.count("from casino.core.storage_base import "), 1)
        # Keep both concrete providers in the old source during this bounded first slice.
        self.assertTrue({"JsonStorageProvider", "MySQLStorageProvider"}.issubset(declared))


# Run the focused seam directly when a developer invokes this file.
if __name__ == "__main__":
    # Return the standard unittest process status.
    unittest.main()
