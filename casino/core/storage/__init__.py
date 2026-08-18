# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Import annotations so facade type hints remain compatible with historical callers.
from __future__ import annotations
# Import process-exit hooks so cached MySQL pools release idle connections on shutdown.
import atexit
# Preserve the historical deep-copy module attribute during incremental package cutover.
import copy
# Import required dependency so historical decimal constants retain their exact values.
from decimal import Decimal
# Preserve the historical JSON module attribute during incremental package cutover.
import json
# Import environment access so runtime configuration can select the provider.
import os
# Preserve the historical filesystem module attribute during incremental package cutover.
import shutil
# Import thread primitives so provider construction remains process-thread safe.
import threading
# Preserve the historical time module attribute during incremental package cutover.
import time
# Preserve the historical path type during incremental package cutover.
from pathlib import Path
# Import provider-factory typing used by the bootstrap facade.
from typing import Any, Callable

# Import and re-export runtime paths and schema constants shared by all storage providers.
from casino.config import DATA_DIR, DEFAULT_STORAGE_PROVIDER, GAME_DATA_DIR, LOG_DIR, SCHEMA_VERSION
# Preserve the historical timestamp-helper import during incremental package cutover.
from casino.core.clock import utc_now
# Import and re-export the immutable route-free game-action contract.
from casino.core.game_action import GameActionExecutor, GameActionMovement, GameActionPlan, GameActionReceipt, GameActionResolution, GameActionResources, GameActionSnapshot, apply_plan_to_snapshot, validate_execution_request, validate_resolution_request
# Preserve the historical pool-configuration import used by storage fixtures and live validation.
from casino.core.mysql_pool import MySQLPoolConfig
# Import and re-export the provider-neutral storage contract and shared helpers.
from casino.core.storage.base import HISTORY_FIELDS, MySQLConfig, StorageProvider, _action_details, _action_fingerprint, _action_scope, _decode_json, _history_from_row, _ledger_event, _ledger_from_row, _money, _money_decimal, _normalizable_players_document, _normalize_action_key, _quantized_money, _quantized_money_decimal, _validate_action_replay, _validate_wallet_normalization_replay, _validated_players_document, _validated_strict_document, _wallet_normalization_event
# Import and re-export the JSON reset lifecycle and shared private epoch constants.
from casino.core.storage.reset import JsonResetMixin, _GAME_ACTION_EPOCH_STORAGE_VERSION, _GAME_ACTION_MAX_EPOCH, _GAME_ACTION_STORAGE_VERSION
# Import and re-export the JSON game-action lifecycle and private recovery-stage set.
from casino.core.storage.game_actions_json import JsonGameActionMixin, _GAME_ACTION_STAGES
# Import and re-export the JSON filesystem, locking, cache, and planner infrastructure aliases.
from casino.core.storage.json_infrastructure import JsonInfrastructureMixin, _JSON_GATE_LOCAL, _JSON_GATE_LOCKS, _JSON_GATE_REGISTRY_LOCK, _json_gate_lock
# Import and re-export the complete ordinary JSON provider from its bounded owner.
from casino.core.storage.json_provider import JsonStorageProvider, _LEDGER_ACTION_COMPACT_BYTES
# Import and re-export the complete MySQL provider from its bounded owner.
from casino.core.storage.mysql_provider import MySQLStorageProvider, _BorrowedMySQLConnection
# Import required dependency so the facade surfaces existing API errors.
from casino.errors import ConflictError, InsufficientFundsError, NotFoundError, ValidationError

# Set _PROVIDER_LOCK to guard lazy provider construction.
_PROVIDER_LOCK = threading.RLock()
# Set _PROVIDER to cache the selected provider for one process.
_PROVIDER: StorageProvider | None = None
# Set _TEST_PROVIDER to allow storage tests to inject an isolated provider.
_TEST_PROVIDER: StorageProvider | None = None
# Preserve the canonical fake-money quantum historical module attribute. (LEDGER-036)
_MONEY_QUANTUM = Decimal("0.01")
# Preserve the signed-cent range historical module attribute.
_MAX_MONEY = Decimal("90000000000000000")


# Return the configured provider name with JSON as the local default.
def storage_provider_name() -> str:
    # Read the provider setting from the environment.
    return os.getenv("CASINO_STORAGE_PROVIDER", DEFAULT_STORAGE_PROVIDER).strip().lower() or DEFAULT_STORAGE_PROVIDER


# Build a provider instance for the current configuration.
def _build_provider() -> StorageProvider:
    # Read the selected provider name.
    name = storage_provider_name()
    # Return the JSON provider for the default local mode.
    if name == "json":
        # Build the local JSON fallback provider.
        return JsonStorageProvider()
    # Return the MySQL provider when explicitly configured.
    if name == "mysql":
        # Build the configured MySQL provider.
        return MySQLStorageProvider()
    # Reject unknown provider names with a clear validation error.
    raise ValidationError(f"Unsupported storage provider: {name}")


# Return the process-wide storage provider.
def get_storage_provider() -> StorageProvider:
    # Allow tests to inject an isolated provider without environment churn.
    if _TEST_PROVIDER is not None:
        # Return the injected test provider.
        return _TEST_PROVIDER
    # Use a lock so parallel requests share one lazily constructed provider.
    with _PROVIDER_LOCK:
        # Declare the module-level provider cache for assignment.
        global _PROVIDER
        # Build the provider the first time it is requested.
        if _PROVIDER is None:
            # Store the selected provider instance.
            _PROVIDER = _build_provider()
        # Return the cached provider.
        return _PROVIDER


# Inject a provider for storage tests.
def set_provider_for_tests(provider: StorageProvider | None) -> None:
    # Declare provider caches for assignment.
    global _TEST_PROVIDER, _PROVIDER
    # Preserve test and runtime provider instances before replacing the caches.
    previous_test_provider = _TEST_PROVIDER
    # Preserve the regular provider because test injection always invalidates that cache.
    previous_runtime_provider = _PROVIDER
    # Store the explicit test provider.
    _TEST_PROVIDER = provider
    # Clear the regular cache so later tests rebuild from environment.
    _PROVIDER = None
    # Close the regular cache, plus a test provider only when test injection is being cleared.
    providers_to_close = (previous_runtime_provider, previous_test_provider if provider is None else None)
    # Release eligible replaced MySQL pools without affecting the newly injected provider.
    for previous_provider in providers_to_close:
        # Skip empty caches, duplicate references, and the provider now being installed.
        if previous_provider is None or previous_provider is provider:
            # Continue to the next cached provider.
            continue
        # Resolve the optional lifecycle hook without imposing it on JSON providers.
        close_pool = getattr(previous_provider, "close_pool", None)
        # Close idle physical sessions when the replaced provider owns a pool.
        if callable(close_pool):
            # Execute the provider-owned shutdown hook.
            close_pool()


# Close process-wide cached MySQL pools during interpreter shutdown.
def _close_cached_provider_pools() -> None:
    # Deduplicate current test and runtime provider references by object identity.
    cached_providers = {id(provider): provider for provider in (_TEST_PROVIDER, _PROVIDER) if provider is not None}
    # Visit each distinct cached provider once.
    for provider in cached_providers.values():
        # Resolve the optional pool lifecycle hook without affecting JSON providers.
        close_pool = getattr(provider, "close_pool", None)
        # Close idle physical sessions when this cached provider owns a pool.
        if callable(close_pool):
            # Execute the provider-owned shutdown hook.
            close_pool()


# Register one module-level shutdown hook without retaining every test-created provider.
atexit.register(_close_cached_provider_pools)


# Seed players idempotently through the configured provider.
def bootstrap_players(default_factory: Callable[[], dict]) -> None:
    # Get the active storage provider.
    provider = get_storage_provider()
    # Ensure backing storage exists before checking player bootstrap state.
    provider.ensure_ready()
    # Delegate the complete row set so each provider owns one race-free bootstrap boundary. (issue #431)
    provider.bootstrap_players(default_factory())
