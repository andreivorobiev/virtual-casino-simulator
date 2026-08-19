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
# Import the provider-neutral package owner for exact identity checks.
from casino.core.storage import base as storage_base
# Import the JSON reset package owner for exact mixin checks.
from casino.core.storage import reset as storage_reset
# Import the JSON game-action package owner for exact mixin checks.
from casino.core.storage import game_actions_json as storage_game_actions_json
# Import the JSON filesystem and concurrency package owner for exact ownership checks.
from casino.core.storage import json_infrastructure as storage_json_infrastructure
# Import the complete ordinary JSON package owner for exact compatibility checks.
from casino.core.storage import json_provider as storage_json_provider
# Import the provider-neutral lifecycle codec package owner for exact identity checks.
from casino.core.storage import game_action_codecs as storage_game_action_codecs
# Import the MySQL game-action package owner for exact mixin checks.
from casino.core.storage import game_actions_mysql as storage_game_actions_mysql
# Import the complete MySQL package owner for exact compatibility checks.
from casino.core.storage import mysql_provider as storage_mysql_provider


# Resolve the repository root from this tracked test module.
ROOT = Path(__file__).resolve().parents[1]
# Point at the final provider-selection and compatibility package facade.
STORAGE_SOURCE = ROOT / "casino" / "core" / "storage" / "__init__.py"
# Point at the final provider-neutral base owner.
BASE_SOURCE = ROOT / "casino" / "core" / "storage" / "base.py"
# Point at the final JSON reset lifecycle owner.
RESET_SOURCE = ROOT / "casino" / "core" / "storage" / "reset.py"
# Point at the final JSON game-action lifecycle owner.
JSON_ACTION_SOURCE = ROOT / "casino" / "core" / "storage" / "game_actions_json.py"
# Point at the final JSON filesystem and concurrency substrate.
JSON_INFRASTRUCTURE_SOURCE = ROOT / "casino" / "core" / "storage" / "json_infrastructure.py"
# Point at the final complete ordinary JSON provider owner.
JSON_PROVIDER_SOURCE = ROOT / "casino" / "core" / "storage" / "json_provider.py"
# Point at the final MySQL game-action lifecycle owner.
MYSQL_ACTION_SOURCE = ROOT / "casino" / "core" / "storage" / "game_actions_mysql.py"
# Point at the final provider-neutral durable game-action codec owner.
CODEC_SOURCE = ROOT / "casino" / "core" / "storage" / "game_action_codecs.py"
# Point at the final complete MySQL provider owner.
MYSQL_PROVIDER_SOURCE = ROOT / "casino" / "core" / "storage" / "mysql_provider.py"
# Bind every transitional root module that final package cutover must retire.
TRANSITIONAL_SOURCES = tuple((ROOT / "casino" / "core" / name) for name in ("storage.py", "storage_base.py", "storage_reset.py", "storage_game_actions_json.py", "storage_game_actions_mysql.py", "storage_game_action_codecs.py", "storage_json_infrastructure.py", "storage_json_provider.py", "storage_mysql_provider.py"))
# Bind every moved compatibility name that the historical module must re-export.
MOVED_NAMES = (
    "ECONOMICS_EXCLUDED_TRANSACTION_FRAGMENTS",
    "MySQLConfig",
    "StorageProvider",
    "_action_details",
    "_action_fingerprint",
    "_action_scope",
    "_decode_json",
    "_history_from_row",
    "_is_player_economics_event",
    "_ledger_event",
    "_ledger_from_row",
    "_money",
    "_money_decimal",
    "_normalizable_players_document",
    "_normalize_action_key",
    "_player_economics_amount",
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
# Bind every JSON game-action method now single-owned by the lifecycle mixin.
JSON_ACTION_METHOD_NAMES = (
    "_serialize_game_action_resources",
    "_deserialize_game_action_resources",
    "_serialize_game_action_snapshot",
    "_deserialize_game_action_snapshot",
    "_serialize_game_action_plan",
    "_deserialize_game_action_plan",
    "_serialize_game_action_receipt",
    "_deserialize_game_action_receipt",
    "_empty_game_action_epoch",
    "_read_game_action_epoch",
    "_write_game_action_epoch",
    "_ready_game_action_epoch",
    "_empty_game_action_receipts",
    "_read_game_action_receipts",
    "_empty_game_action_claims",
    "_read_game_action_claims",
    "_commit_game_action_claim",
    "_empty_game_action_states",
    "_read_game_action_states",
    "_json_wallet_cents",
    "_json_wallet_value",
    "_read_game_action_players",
    "_capture_game_action_snapshot",
    "_game_action_journal_record",
    "_read_game_action_journal",
    "_write_game_action_journal_stage",
    "_apply_game_action_wallets",
    "_apply_game_action_states",
    "_commit_game_action_receipt",
    "_game_action_ledger_events",
    "_apply_game_action_ledger",
    "_recover_game_action_journal_locked",
    "_recover_all_json_actions_locked",
    "execute_game_action_once",
    "resolve_game_action",
)
# Bind every MySQL game-action method now single-owned by its lifecycle mixin.
MYSQL_ACTION_METHOD_NAMES = (
    "_runtime_schema_state",
    "_require_game_action_schema",
    "_mysql_game_action_epoch",
    "_mysql_game_action_cents",
    "_decode_mysql_game_action_json",
    "_mysql_game_action_receipt",
    "_select_mysql_game_action_receipt",
    "_claim_mysql_game_action",
    "_capture_mysql_game_action_snapshot",
    "_insert_mysql_game_action_ledger",
    "execute_game_action_once",
    "resolve_game_action",
)
# Bind every provider-neutral durable codec now shared by both lifecycle implementations.
CODEC_METHOD_NAMES = (
    "_plain_canonical",
    "_unique_json_object",
    "_game_action_scope_key",
    "_serialize_game_action_identity",
    "_deserialize_game_action_identity",
)
# Bind every ordinary method now single-owned by the complete MySQL provider module.
MYSQL_PROVIDER_METHOD_NAMES = (
    "__init__",
    "_connector",
    "_open_physical_connection",
    "connect",
    "pool_snapshot",
    "close_pool",
    "_planner_key",
    "_planner_is_active",
    "_reset_is_active",
    "_reject_planner_mutation",
    "_planner_boundary",
    "ensure_ready",
    "_mysql_reset_lock_name",
    "_clear_mysql_mutable_state",
    "reset_transaction",
    "reset",
    "_player_from_row",
    "load_players",
    "get_player",
    "normalize_wallet_balances",
    "insert_player",
    "bootstrap_players",
    "update_player",
    "ensure_player",
    "transact_ledger",
    "transact_ledger_once",
    "find_ledger_action",
    "read_ledger_recent",
    "ledger_economics",
    "append_history",
    "recent_history",
    "read_document",
    "document_exists",
    "read_document_strict",
    "write_document",
    "update_document",
)
# Bind every ordinary method now single-owned by the complete JSON provider module.
JSON_PROVIDER_METHOD_NAMES = (
    "_load_players_document",
    "_save_players_document",
    "load_players",
    "get_player",
    "normalize_wallet_balances",
    "insert_player",
    "bootstrap_players",
    "update_player",
    "ensure_player",
    "_empty_action_registry",
    "_action_identity",
    "_decode_ledger_line",
    "_ledger_rows",
    "_project_committed_action",
    "_optional_file_stat",
    "_normalize_actions_registry",
    "_apply_action_journal_record",
    "_apply_action_journal_bytes",
    "_read_actions_registry",
    "_append_action_journal_record",
    "_compact_action_journal",
    "_maybe_compact_action_journal",
    "_recover_committed_actions",
    "_transact_ledger_locked",
    "transact_ledger",
    "transact_ledger_once",
    "find_ledger_action",
    "read_ledger_recent",
    "_decode_history_region",
    "_history_rows",
    "append_history",
    "recent_history",
    "read_document",
    "document_exists",
    "read_document_strict",
    "write_document",
    "update_document",
)
# Bind every JSON filesystem, locking, cache, and planner method moved as one reviewed seam.
JSON_INFRASTRUCTURE_METHOD_NAMES = (
    "__init__",
    "players_path",
    "ledger_path",
    "ledger_actions_path",
    "ledger_action_journal_path",
    "ledger_lock_path",
    "json_gate_path",
    "game_action_journal_path",
    "game_action_receipts_path",
    "game_action_claims_path",
    "game_action_epoch_path",
    "game_action_states_path",
    "document_lock_path",
    "history_path",
    "document_path",
    "document_reference",
    "_ensure_ready_direct",
    "ensure_ready",
    "_drop_ledger_cache",
    "_drop_history_cache",
    "_drop_actions_cache",
    "_read_json",
    "_preserve_corrupt_players",
    "_read_players_document",
    "_read_normalizable_players_document",
    "_write_json",
    "_json_root_key",
    "_canonical_path_is_within",
    "_json_control_root",
    "_exclusive_process_file_lock",
    "_try_exclusive_process_file_lock",
    "_json_global_gate",
    "_try_json_global_gate",
    "_ledger_process_lock",
    "_document_process_lock",
    "_planner_is_active",
    "_reject_planner_mutation",
    "_planner_boundary",
    "_game_action_checkpoint",
    "_reset_recovery_checkpoint",
    "_read_game_action_json",
    "_cleanup_game_action_temps_locked",
    "_fsync_game_action_parent",
    "_write_game_action_json",
    "_remove_game_action_journal",
    "_append_jsonl",
)
# Bind the exact #412/#432 cache field construction order moved with the JSON substrate.
JSON_CACHE_FIELD_NAMES = (
    "_ledger_cache_offset",
    "_ledger_cache_mtime_ns",
    "_ledger_cache_rows",
    "_ledger_cache_by_player",
    "_ledger_cache_by_id",
    "_ledger_cache_tail_rows",
    "_actions_cache_registry",
    "_actions_cache_snapshot_stat",
    "_actions_cache_journal_offset",
    "_actions_cache_journal_stat",
    "_actions_cache_compaction_floor",
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

    # Require the completed cutover to expose only the final package topology.
    def test_final_package_retires_every_transitional_root_module(self):
        # Require the historical import path to resolve to the package facade.
        self.assertEqual(Path(storage.__file__).resolve(), STORAGE_SOURCE.resolve())
        # Reject every temporary storage_*.py extraction owner after package assembly.
        self.assertTrue(all(not path.exists() for path in TRANSITIONAL_SOURCES))
        # Require every final owner to remain a regular bounded Python source file.
        for source in (STORAGE_SOURCE, BASE_SOURCE, RESET_SOURCE, JSON_ACTION_SOURCE, MYSQL_ACTION_SOURCE, CODEC_SOURCE, JSON_INFRASTRUCTURE_SOURCE, JSON_PROVIDER_SOURCE, MYSQL_PROVIDER_SOURCE):
            # Bind each final package member to the permanent 1,200-line ceiling.
            self.assertTrue(source.is_file() and len(source.read_text(encoding="utf-8").splitlines()) < 1200, source)

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
            "document_reference": ("self", "path", "data_root"),
            "document_exists": ("self", "key"),
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

    # Reject duplicate base or provider declarations left in the compatibility facade.
    def test_concrete_provider_source_imports_base_without_duplicate_owners(self):
        # Parse the compatibility facade as inert source.
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
        self.assertEqual(source.count("from casino.core.storage.base import "), 1)
        # Reject both complete concrete providers and the borrowed-session owner from the facade.
        self.assertTrue({"JsonStorageProvider", "MySQLStorageProvider", "_BorrowedMySQLConnection"}.isdisjoint(declared))
        # Require one explicit JSON-provider import owner during package cutover.
        self.assertEqual(source.count("from casino.core.storage.json_provider import "), 1)

    # Require the second #728 seam to single-own reset and stable-visibility behavior.
    def test_reset_owner_is_bounded_and_single_owned(self):
        # Read both owners as inert UTF-8 source.
        reset_source = RESET_SOURCE.read_text(encoding="utf-8")
        provider_source = JSON_PROVIDER_SOURCE.read_text(encoding="utf-8")
        # Keep the reset lifecycle comfortably below the permanent module ceiling.
        self.assertLess(len(reset_source.splitlines()), 1200)
        # Parse both modules without constructing a provider or touching storage.
        reset_tree = ast.parse(reset_source)
        provider_tree = ast.parse(provider_source)
        # Locate the sole reset mixin and concrete JSON provider declarations.
        reset_class = next(node for node in reset_tree.body if isinstance(node, ast.ClassDef) and node.name == "JsonResetMixin")
        provider_class = next(node for node in provider_tree.body if isinstance(node, ast.ClassDef) and node.name == "JsonStorageProvider")
        # Require the complete reviewed reset method inventory in its new owner.
        owned_methods = {node.name for node in reset_class.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertEqual(owned_methods, set(RESET_METHOD_NAMES))
        # Reject duplicate reset declarations from the remaining concrete-provider class.
        provider_methods = {node.name for node in provider_class.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertTrue(set(RESET_METHOD_NAMES).isdisjoint(provider_methods))
        # Require reset ownership to remain before the provider contracts after later mixins.
        self.assertEqual([ast.unparse(base) for base in provider_class.bases], ["JsonInfrastructureMixin", "JsonGameActionMixin", "JsonResetMixin", "StorageProvider", "GameActionExecutor"])
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

    # Require the third #728 seam to single-own the JSON game-action lifecycle.
    def test_json_game_action_owner_is_bounded_and_single_owned(self):
        # Read both owners as inert UTF-8 source.
        action_source = JSON_ACTION_SOURCE.read_text(encoding="utf-8")
        provider_source = JSON_PROVIDER_SOURCE.read_text(encoding="utf-8")
        # Keep the complete extracted lifecycle below the permanent module ceiling.
        self.assertLess(len(action_source.splitlines()), 1200)
        # Parse both modules without constructing a provider or touching storage.
        action_tree = ast.parse(action_source)
        provider_tree = ast.parse(provider_source)
        # Locate the sole action mixin and concrete JSON provider declarations.
        action_class = next(node for node in action_tree.body if isinstance(node, ast.ClassDef) and node.name == "JsonGameActionMixin")
        provider_class = next(node for node in provider_tree.body if isinstance(node, ast.ClassDef) and node.name == "JsonStorageProvider")
        # Require the complete reviewed game-action method inventory in its new owner.
        owned_methods = {node.name for node in action_class.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertEqual(owned_methods, set(JSON_ACTION_METHOD_NAMES))
        # Reject duplicate lifecycle declarations from the remaining concrete provider.
        provider_methods = {node.name for node in provider_class.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertTrue(set(JSON_ACTION_METHOD_NAMES).isdisjoint(provider_methods))
        # Require every inherited implementation to be the exact mixin object.
        for method_name in JSON_ACTION_METHOD_NAMES:
            # Compare descriptor identity without constructing a provider.
            self.assertIs(getattr(storage.JsonStorageProvider, method_name), getattr(storage_game_actions_json.JsonGameActionMixin, method_name), method_name)
        # Keep ordinary JSON, reset, ledger, document, and MySQL implementations outside action ownership.
        for forbidden in ("_read_json", "reset_transaction", "transact_ledger", "read_document", "_mysql_game_action_epoch"):
            # Name any accidentally broadened lifecycle ownership precisely.
            self.assertNotIn(forbidden, owned_methods)

    # Require the private recovery-stage set to remain one exact compatibility object.
    def test_json_game_action_owner_preserves_stage_constant_identity(self):
        # Preserve the historical private import without duplicating its mutable set.
        self.assertIs(storage._GAME_ACTION_STAGES, storage_game_actions_json._GAME_ACTION_STAGES)

    # Require provider-neutral lifecycle codecs to stay bounded and exact across both providers.
    def test_game_action_codec_owner_is_bounded_and_single_owned(self):
        # Read the codec owner and historical provider facade as inert UTF-8 source.
        codec_source = CODEC_SOURCE.read_text(encoding="utf-8")
        provider_source = JSON_PROVIDER_SOURCE.read_text(encoding="utf-8")
        # Keep the shared codec seam compact rather than growing another provider monolith.
        self.assertLess(len(codec_source.splitlines()), 200)
        # Parse source ownership without constructing a provider.
        codec_tree = ast.parse(codec_source)
        provider_tree = ast.parse(provider_source)
        # Locate the sole codec mixin and remaining JSON provider.
        codec_class = next(node for node in codec_tree.body if isinstance(node, ast.ClassDef) and node.name == "GameActionCodecMixin")
        json_provider = next(node for node in provider_tree.body if isinstance(node, ast.ClassDef) and node.name == "JsonStorageProvider")
        # Require the exact reviewed codec inventory and no duplicates in the facade.
        owned_methods = {node.name for node in codec_class.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertEqual(owned_methods, set(CODEC_METHOD_NAMES))
        provider_methods = {node.name for node in json_provider.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertTrue(set(CODEC_METHOD_NAMES).isdisjoint(provider_methods))
        # Require JSON lifecycle inheritance and the complete MySQL provider aliases to share exact descriptors.
        for method_name in CODEC_METHOD_NAMES:
            # Compare all three access paths without touching durable storage.
            owned_method = getattr(storage_game_action_codecs.GameActionCodecMixin, method_name)
            self.assertIs(getattr(storage.JsonStorageProvider, method_name), owned_method, method_name)
            self.assertIs(getattr(storage.MySQLStorageProvider, method_name), owned_method, method_name)

    # Require the fourth #728 seam to single-own the MySQL game-action lifecycle.
    def test_mysql_game_action_owner_is_bounded_and_single_owned(self):
        # Read both owners as inert UTF-8 source.
        action_source = MYSQL_ACTION_SOURCE.read_text(encoding="utf-8")
        provider_source = MYSQL_PROVIDER_SOURCE.read_text(encoding="utf-8")
        # Keep the complete extracted lifecycle below the permanent module ceiling.
        self.assertLess(len(action_source.splitlines()), 1200)
        # Parse both modules without constructing a provider or opening MySQL.
        action_tree = ast.parse(action_source)
        provider_tree = ast.parse(provider_source)
        # Locate the sole action mixin and concrete MySQL provider declarations.
        action_class = next(node for node in action_tree.body if isinstance(node, ast.ClassDef) and node.name == "MySQLGameActionMixin")
        provider_class = next(node for node in provider_tree.body if isinstance(node, ast.ClassDef) and node.name == "MySQLStorageProvider")
        # Require the complete reviewed game-action method inventory in its new owner.
        owned_methods = {node.name for node in action_class.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertEqual(owned_methods, set(MYSQL_ACTION_METHOD_NAMES))
        # Reject duplicate lifecycle declarations from the remaining concrete provider.
        provider_methods = {node.name for node in provider_class.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertTrue(set(MYSQL_ACTION_METHOD_NAMES).isdisjoint(provider_methods))
        # Require lifecycle ownership to precede the provider contracts in the exact MRO.
        self.assertEqual([ast.unparse(base) for base in provider_class.bases], ["MySQLGameActionMixin", "StorageProvider", "GameActionExecutor"])
        # Require every inherited implementation to be the exact mixin object.
        for method_name in MYSQL_ACTION_METHOD_NAMES:
            # Compare descriptor identity without constructing a provider or checking out a connection.
            self.assertIs(getattr(storage.MySQLStorageProvider, method_name), getattr(storage_game_actions_mysql.MySQLGameActionMixin, method_name), method_name)
        # Keep pool, reset, ordinary ledger/document, and JSON implementations outside action ownership.
        for forbidden in ("connect", "reset_transaction", "transact_ledger", "read_document", "_read_game_action_journal"):
            # Name any accidentally broadened lifecycle ownership precisely.
            self.assertNotIn(forbidden, owned_methods)

    # Require the fifth #728 seam to single-own the complete ordinary MySQL provider.
    def test_complete_mysql_provider_is_bounded_single_owned_and_reexported(self):
        # Read the extracted provider and historical facade as inert UTF-8 source.
        provider_source = MYSQL_PROVIDER_SOURCE.read_text(encoding="utf-8")
        storage_source = STORAGE_SOURCE.read_text(encoding="utf-8")
        # Keep the complete provider below the parent issue's permanent module ceiling.
        self.assertLess(len(provider_source.splitlines()), 1200)
        # Parse both modules without constructing a pool or importing a connector.
        provider_tree = ast.parse(provider_source)
        storage_tree = ast.parse(storage_source)
        # Require exactly the borrowed-session facade and complete provider as class owners.
        provider_classes = {node.name for node in provider_tree.body if isinstance(node, ast.ClassDef)}
        self.assertEqual(provider_classes, {"_BorrowedMySQLConnection", "MySQLStorageProvider"})
        # Reject duplicate provider classes and MySQL thread/reset globals from the facade.
        storage_classes = {node.name for node in storage_tree.body if isinstance(node, ast.ClassDef)}
        self.assertTrue(provider_classes.isdisjoint(storage_classes))
        for forbidden in ("_MYSQL_PLANNER_LOCAL", "_MYSQL_RESET_REGISTRY_LOCK", "_MYSQL_RESET_TARGETS"):
            # Require process-local MySQL lifecycle state to move with its sole provider owner.
            self.assertNotIn(forbidden, storage_source)
            self.assertIn(forbidden, provider_source)
        # Require the exact reviewed ordinary provider method inventory.
        provider_class = next(node for node in provider_tree.body if isinstance(node, ast.ClassDef) and node.name == "MySQLStorageProvider")
        owned_methods = {node.name for node in provider_class.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertEqual(owned_methods, set(MYSQL_PROVIDER_METHOD_NAMES))
        # Preserve the accepted lifecycle-first provider contract MRO.
        self.assertEqual([ast.unparse(base) for base in provider_class.bases], ["MySQLGameActionMixin", "StorageProvider", "GameActionExecutor"])
        # Require historical imports to remain exact class objects rather than wrappers.
        self.assertIs(storage.MySQLStorageProvider, storage_mysql_provider.MySQLStorageProvider)
        self.assertIs(storage._BorrowedMySQLConnection, storage_mysql_provider._BorrowedMySQLConnection)
        # Require every ordinary method descriptor to remain owned by the extracted class.
        for method_name in MYSQL_PROVIDER_METHOD_NAMES:
            # Compare the public compatibility descriptor to the sole extracted owner.
            self.assertIs(getattr(storage.MySQLStorageProvider, method_name), getattr(storage_mysql_provider.MySQLStorageProvider, method_name), method_name)
        # Keep JSON cache, filesystem gate, and private journal responsibilities outside this owner.
        for forbidden in ("_drop_ledger_cache", "_read_actions_registry", "_json_global_gate", "_read_game_action_journal"):
            # Name any accidentally broadened provider ownership precisely.
            self.assertNotIn(forbidden, provider_source)

    # Require the sixth #728 seam to single-own JSON filesystem and concurrency infrastructure.
    def test_json_infrastructure_is_bounded_single_owned_and_reexported(self):
        # Read the extracted infrastructure and historical facade as inert UTF-8 source.
        infrastructure_source = JSON_INFRASTRUCTURE_SOURCE.read_text(encoding="utf-8")
        storage_source = STORAGE_SOURCE.read_text(encoding="utf-8")
        provider_source = JSON_PROVIDER_SOURCE.read_text(encoding="utf-8")
        # Keep both sides of this split below the permanent parent-issue ceiling.
        self.assertLess(len(infrastructure_source.splitlines()), 1200)
        self.assertLess(len(storage_source.splitlines()), 1200)
        self.assertLess(len(provider_source.splitlines()), 1200)
        # Parse both modules without opening any filesystem path or provider gate.
        infrastructure_tree = ast.parse(infrastructure_source)
        provider_tree = ast.parse(provider_source)
        # Locate the sole substrate owner and the concrete compatibility provider.
        infrastructure_class = next(node for node in infrastructure_tree.body if isinstance(node, ast.ClassDef) and node.name == "JsonInfrastructureMixin")
        provider_class = next(node for node in provider_tree.body if isinstance(node, ast.ClassDef) and node.name == "JsonStorageProvider")
        # Require the exact reviewed substrate inventory and no duplicate concrete declarations.
        owned_methods = {node.name for node in infrastructure_class.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertEqual(owned_methods, set(JSON_INFRASTRUCTURE_METHOD_NAMES))
        provider_methods = {node.name for node in provider_class.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertTrue(set(JSON_INFRASTRUCTURE_METHOD_NAMES).isdisjoint(provider_methods))
        # Preserve substrate-first method resolution before action, reset, and public contracts.
        self.assertEqual([ast.unparse(base) for base in provider_class.bases], ["JsonInfrastructureMixin", "JsonGameActionMixin", "JsonResetMixin", "StorageProvider", "GameActionExecutor"])
        # Require every historical provider descriptor to resolve to the exact extracted object.
        for method_name in JSON_INFRASTRUCTURE_METHOD_NAMES:
            # Compare descriptor identity without constructing a provider or touching storage.
            self.assertIs(getattr(storage.JsonStorageProvider, method_name), getattr(storage_json_infrastructure.JsonInfrastructureMixin, method_name), method_name)

    # Require the seventh #728 seam to single-own the complete ordinary JSON provider.
    def test_json_provider_is_bounded_single_owned_and_reexported(self):
        # Read the extracted owner and facade as inert UTF-8 source.
        provider_source = JSON_PROVIDER_SOURCE.read_text(encoding="utf-8")
        storage_source = STORAGE_SOURCE.read_text(encoding="utf-8")
        # Keep the provider and facade below the permanent parent-issue ceiling.
        self.assertLess(len(provider_source.splitlines()), 1200)
        self.assertLess(len(storage_source.splitlines()), 1200)
        # Parse both modules without constructing a provider or touching storage.
        provider_tree = ast.parse(provider_source)
        storage_tree = ast.parse(storage_source)
        # Require one concrete JSON provider declaration in the extracted owner only.
        provider_classes = [node for node in provider_tree.body if isinstance(node, ast.ClassDef) and node.name == "JsonStorageProvider"]
        facade_classes = [node for node in storage_tree.body if isinstance(node, ast.ClassDef) and node.name == "JsonStorageProvider"]
        self.assertEqual(len(provider_classes), 1)
        self.assertEqual(facade_classes, [])
        # Require the exact reviewed ordinary-method inventory in the sole owner.
        provider_class = provider_classes[0]
        owned_methods = {node.name for node in provider_class.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.assertEqual(owned_methods, set(JSON_PROVIDER_METHOD_NAMES))
        # Preserve the accepted substrate, action, reset, and contract MRO exactly.
        self.assertEqual([ast.unparse(base) for base in provider_class.bases], ["JsonInfrastructureMixin", "JsonGameActionMixin", "JsonResetMixin", "StorageProvider", "GameActionExecutor"])
        # Require historical callers to receive the exact extracted class object.
        self.assertIs(storage.JsonStorageProvider, storage_json_provider.JsonStorageProvider)
        # Require every ordinary descriptor to resolve to the sole extracted owner.
        for method_name in JSON_PROVIDER_METHOD_NAMES:
            # Compare descriptors without opening any file or provider gate.
            self.assertIs(getattr(storage.JsonStorageProvider, method_name), getattr(storage_json_provider.JsonStorageProvider, method_name), method_name)
        # Keep provider selection, injection, cleanup, and bootstrap in the compatibility facade.
        facade_functions = {node.name for node in storage_tree.body if isinstance(node, ast.FunctionDef)}
        self.assertEqual(facade_functions, {"storage_provider_name", "_build_provider", "get_storage_provider", "set_provider_for_tests", "_close_cached_provider_pools", "bootstrap_players"})
        # Reject duplicate facade/cache ownership in the extracted provider.
        provider_functions = {node.name for node in provider_tree.body if isinstance(node, ast.FunctionDef)}
        self.assertTrue(facade_functions.isdisjoint(provider_functions))

    # Require process-shared JSON gate state and #412/#432 cache invalidation to move exactly once.
    def test_json_infrastructure_preserves_gate_and_cache_ownership(self):
        # Read and parse both modules without executing lock construction.
        infrastructure_source = JSON_INFRASTRUCTURE_SOURCE.read_text(encoding="utf-8")
        storage_source = STORAGE_SOURCE.read_text(encoding="utf-8")
        infrastructure_tree = ast.parse(infrastructure_source)
        storage_tree = ast.parse(storage_source)
        # Collect top-level assignment names to distinguish ownership from compatibility imports.
        def assigned_names(tree):
            # Flatten simple reviewed top-level assignments into one ownership set.
            return {target.id for node in tree.body if isinstance(node, (ast.Assign, ast.AnnAssign)) for target in ((node.targets if isinstance(node, ast.Assign) else [node.target])) if isinstance(target, ast.Name)}
        # Require the three mutable gate objects only in the extracted owner.
        for name in ("_JSON_GATE_REGISTRY_LOCK", "_JSON_GATE_LOCKS", "_JSON_GATE_LOCAL"):
            # Bind one exact object through the compatibility import and reject a duplicate assignment.
            self.assertIn(name, assigned_names(infrastructure_tree), name)
            self.assertNotIn(name, assigned_names(storage_tree), name)
            self.assertIs(getattr(storage, name), getattr(storage_json_infrastructure, name), name)
        # Require the shared root-lock function to remain one exact implementation object.
        self.assertIs(storage._json_gate_lock, storage_json_infrastructure._json_gate_lock)
        # Locate the exact construction and invalidation methods in the extracted class.
        infrastructure_class = next(node for node in infrastructure_tree.body if isinstance(node, ast.ClassDef) and node.name == "JsonInfrastructureMixin")
        methods = {node.name: node for node in infrastructure_class.body if isinstance(node, ast.FunctionDef)}
        # Preserve the reviewed construction order of every ledger and action cache field.
        initialized = tuple((node.target if isinstance(node, ast.AnnAssign) else node.targets[0]).attr for node in methods["__init__"].body if isinstance(node, (ast.Assign, ast.AnnAssign)) and (isinstance(node, ast.AnnAssign) or len(node.targets) == 1) and isinstance(node.target if isinstance(node, ast.AnnAssign) else node.targets[0], ast.Attribute) and (node.target if isinstance(node, ast.AnnAssign) else node.targets[0]).attr in JSON_CACHE_FIELD_NAMES)
        self.assertEqual(initialized, JSON_CACHE_FIELD_NAMES)
        # Preserve exact invalidation field order for ledger and committed-action caches.
        for method_name, expected in (("_drop_ledger_cache", JSON_CACHE_FIELD_NAMES[:6]), ("_drop_actions_cache", JSON_CACHE_FIELD_NAMES[6:])):
            # Read assignments in source order rather than relying on mutable runtime state.
            invalidated = tuple(node.targets[0].attr for node in methods[method_name].body if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Attribute))
            self.assertEqual(invalidated, expected, method_name)

    # Require shared history fields to move once while preserving historical identity.
    def test_history_fields_are_single_owned_by_base_and_reexported(self):
        # Read both sources without executing provider construction.
        base_source = BASE_SOURCE.read_text(encoding="utf-8")
        storage_source = STORAGE_SOURCE.read_text(encoding="utf-8")
        # Require one declaration in the provider-neutral owner and no facade duplicate.
        self.assertEqual(base_source.count("HISTORY_FIELDS = ["), 1)
        self.assertEqual(storage_source.count("HISTORY_FIELDS = ["), 0)
        # Preserve one exact mutable compatibility object across import paths.
        self.assertIs(storage.HISTORY_FIELDS, storage_base.HISTORY_FIELDS)


# Run the focused seam directly when a developer invokes this file.
if __name__ == "__main__":
    # Return the standard unittest process status.
    unittest.main()
