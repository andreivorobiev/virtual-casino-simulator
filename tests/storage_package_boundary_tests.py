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
# Import the extracted JSON reset lifecycle owner for exact mixin checks.
from casino.core import storage_reset


# Resolve the repository root from this tracked test module.
ROOT = Path(__file__).resolve().parents[1]
# Point at the concrete-provider monolith retained during the first #728 slice.
STORAGE_SOURCE = ROOT / "casino" / "core" / "storage.py"
# Point at the extracted package-ready provider-neutral base owner.
BASE_SOURCE = ROOT / "casino" / "core" / "storage_base.py"
# Point at the extracted package-ready JSON reset lifecycle owner.
RESET_SOURCE = ROOT / "casino" / "core" / "storage_reset.py"
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
# Bind the lifecycle constants that the historical module must continue to expose.
RESET_CONSTANT_NAMES = (
    "_GAME_ACTION_STORAGE_VERSION",
    "_GAME_ACTION_EPOCH_STORAGE_VERSION",
    "_GAME_ACTION_MAX_EPOCH",
)
# Bind every JSON reset method now single-owned by the lifecycle mixin.
RESET_METHOD_NAMES = (
    "_reset_locked",
    "_reset_backup_prefix",
    "_reset_backup_path",
    "_require_no_reset_recovery_locked",
    "_reset_archive_member_parts",
    "_reset_file_digest",
    "_fsync_reset_directories_locked",
    "_create_reset_backup_locked",
    "_restore_reset_backup_locked",
    "_remove_reset_backup",
    "reset_transaction",
    "reset",
    "state_visibility_transaction",
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

    # Require the second #728 seam to single-own reset and stable-visibility behavior.
    def test_reset_owner_is_bounded_and_single_owned(self):
        # Read both owners as inert UTF-8 source.
        reset_source = RESET_SOURCE.read_text(encoding="utf-8")
        storage_source = STORAGE_SOURCE.read_text(encoding="utf-8")
        # Keep the reset lifecycle comfortably below the permanent module ceiling.
        self.assertLess(len(reset_source.splitlines()), 1200)
        # Parse both modules without constructing a provider or touching storage.
        reset_tree = ast.parse(reset_source)
        storage_tree = ast.parse(storage_source)
        # Locate the sole reset mixin and concrete JSON provider declarations.
        reset_class = next(node for node in reset_tree.body if isinstance(node, ast.ClassDef) and node.name == "JsonResetMixin")
        provider_class = next(node for node in storage_tree.body if isinstance(node, ast.ClassDef) and node.name == "JsonStorageProvider")
        # Require the complete reviewed reset method inventory in its new owner.
        owned_methods = {node.name for node in reset_class.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertEqual(owned_methods, set(RESET_METHOD_NAMES))
        # Reject duplicate reset declarations from the remaining concrete-provider class.
        provider_methods = {node.name for node in provider_class.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertTrue(set(RESET_METHOD_NAMES).isdisjoint(provider_methods))
        # Require the exact mixin to lead the concrete provider MRO.
        self.assertEqual(ast.unparse(provider_class.bases[0]), "JsonResetMixin")
        self.assertIs(storage.JsonStorageProvider.reset_transaction, storage_reset.JsonResetMixin.reset_transaction)
        # Keep ordinary JSON, ledger, document, and game-action implementations outside reset ownership.
        for forbidden in ("_read_json", "_write_json", "transact_ledger", "read_document", "execute_game_action_once", "resolve_game_action"):
            # Name any accidentally broadened lifecycle ownership precisely.
            self.assertNotIn(forbidden, owned_methods)

    # Require exact historical constant exports and accepted cache invalidation ordering.
    def test_reset_owner_preserves_constants_and_cache_invalidation_order(self):
        # Compare every moved constant by identity so storage.py has no duplicate declaration.
        for name in RESET_CONSTANT_NAMES:
            # Require one exact private constant object across both compatibility imports.
            self.assertIs(getattr(storage, name), getattr(storage_reset, name), name)
        # Read and parse the extracted reset owner without executing filesystem behavior.
        reset_source = RESET_SOURCE.read_text(encoding="utf-8")
        reset_tree = ast.parse(reset_source)
        # Locate the reset mixin containing both #412/#432 invalidation boundaries.
        reset_class = next(node for node in reset_tree.body if isinstance(node, ast.ClassDef) and node.name == "JsonResetMixin")
        # Prove destructive clear and rollback restoration each drop ledger before action caches.
        for method_name in ("_reset_locked", "_restore_reset_backup_locked"):
            # Read the exact method source segment from its new single owner.
            method = next(node for node in reset_class.body if isinstance(node, ast.FunctionDef) and node.name == method_name)
            method_source = ast.get_source_segment(reset_source, method)
            # Require exactly one invalidation of each accepted cache per boundary.
            self.assertEqual(method_source.count("self._drop_ledger_cache()"), 1, method_name)
            self.assertEqual(method_source.count("self._drop_actions_cache()"), 1, method_name)
            # Preserve ledger-tail invalidation before action-registry invalidation verbatim.
            self.assertLess(method_source.index("self._drop_ledger_cache()"), method_source.index("self._drop_actions_cache()"), method_name)


# Run the focused seam directly when a developer invokes this file.
if __name__ == "__main__":
    # Return the standard unittest process status.
    unittest.main()
