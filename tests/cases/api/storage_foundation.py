# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Own storage and MySQL API registrations for the #727 thin-runner series."""

# Import the active interpreter stream for focused unittest reporting.
import sys
# Import standard unittest loading and focused class/module execution.
import unittest

# Import the enrollment-policy suite owned by this registration area.
from tests import enrollment_policy_tests
# Import the checksum-bound MySQL migration-policy suite.
from tests import mysql_migration_tests
# Import the bounded MySQL connection-pool suite.
from tests import mysql_pool_tests
# Import PostgreSQL configuration and lazy-selector coverage without importing psycopg. (TEST-252)
from tests import postgres_registration_tests
# Import the listener-free bounded PostgreSQL pool suite without importing psycopg. (TEST-253)
from tests import postgres_pool_tests
# Import the authenticated recovery-policy suite.
from tests import recovery_tests
# Import provider-neutral player-state atomicity coverage.
from tests import state_store_atomic_tests
# Import first-class session lifecycle and concurrency parity coverage.
from tests import session_storage_tests
# Import JSON and modeled-MySQL provider parity helpers.
from tests import storage_tests
# Import the first #728 package-boundary ownership suite.
from tests import storage_package_boundary_tests
# Import the final #728 named cross-provider settlement-parity suite.
from tests import storage_provider_parity_tests
# Import cents-only wallet normalization coverage.
from tests import wallet_cents_normalization_tests
# Import fail-closed wallet-corruption coverage.
from tests import wallet_corruption_tests
# Import descriptor and runtime game-rule governance coverage.
from tests.games import test_game_rule_schema


# Register the complete storage/MySQL area at its historical CLI boundary.
def run_cases(run_case, include_live=False, include_migration_live=False, request_latency_callback=None, gunicorn_json_load_callback=None, gunicorn_load_callback=None):
    """Run the exact default and explicitly selected live storage cases."""
    # Define one focused runner for the extracted provider-neutral package boundary.
    def run_storage_package_boundary_tests():
        # Load only the STORAGE-016 and TEST-243 ownership/compatibility test class.
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(storage_package_boundary_tests.StoragePackageBoundaryTests)
        # Execute the listener-free suite with concise standard output.
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Fail the existing storage parity case when package ownership or imports drift.
        if not result.wasSuccessful():
            # Preserve one fixed diagnostic without opening a provider or listener.
            raise AssertionError("storage package boundary suite failed")

    # Run package ownership proof before the existing JSON provider scenario.
    def run_storage_base_and_json_parity():
        # Prove import compatibility and bounded ownership before provider behavior.
        run_storage_package_boundary_tests()
        # Preserve the accepted JSON players, ledger, history, and settings scenario unchanged.
        storage_tests.run_json_provider_parity()
    # Define the final package gate that executes one settlement on both providers.
    def run_storage_provider_settlement_parity_tests():
        # Load only the connector-free named JSON/MySQL settlement-parity class.
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(storage_provider_parity_tests.StorageProviderSettlementParityTests)
        # Execute the focused suite with concise standard output.
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Fail the named central case when provider settlement semantics diverge.
        if not result.wasSuccessful():
            # Preserve one fixed provider-neutral diagnostic.
            raise AssertionError("storage provider settlement parity suite failed")
    # Define one focused unittest runner for corrupt-wallet fail-closed behavior.
    def run_wallet_corruption_tests():
        # Load only the STORAGE-014 wallet-corruption test class.
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(wallet_corruption_tests.WalletCorruptionTests)
        # Execute the focused suite with concise standard output.
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Fail the named central case when any corruption boundary assertion fails.
        if not result.wasSuccessful():
            raise AssertionError("wallet corruption suite failed")

    # Define one focused unittest runner for cents-only wallet persistence.
    def run_wallet_cents_normalization_tests():
        # Load only the STORAGE-015 wallet-cents test class.
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(wallet_cents_normalization_tests.WalletCentsNormalizationTests)
        # Execute the focused suite with concise standard output.
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Fail the mapped case whenever any normalization assertion fails.
        if not result.wasSuccessful():
            raise AssertionError("wallet cents normalization suite failed")

    # Define one listener-free runner for the STORAGE-011 JSON game-action boundary.
    def run_json_game_action_provider_tests():
        # Import the provider-specific suite only when the storage profile executes.
        from tests import json_game_action_provider_tests
        # Load the complete recovery, reset, contention, and hostile-input test case.
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(json_game_action_provider_tests.JsonGameActionProviderTests)
        # Execute the focused suite with concise standard output.
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Fail the mapped case whenever any provider-boundary assertion fails.
        if not result.wasSuccessful():
            raise AssertionError("JSON game-action provider suite failed")

    # Define one listener-free runner for schema-four MySQL lifecycle transactions.
    def run_mysql_game_action_provider_tests():
        # Import the deterministic transactional model only for its named case.
        from tests import mysql_game_action_provider_tests
        # Load the complete executor, resolver, rollback, and schema-gate test class.
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(mysql_game_action_provider_tests.MySQLGameActionProviderTests)
        # Execute the focused suite with concise standard output.
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Fail the mapped case whenever any MySQL lifecycle assertion fails.
        if not result.wasSuccessful():
            raise AssertionError("MySQL game-action provider suite failed")

    # Define one focused unittest runner for provider-neutral player-game-state atomicity.
    def run_player_state_atomic_tests():
        # Load only the CORE-030 player-state atomicity test class.
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(state_store_atomic_tests.PlayerGameStateAtomicTests)
        # Execute the focused listener-free suite with concise standard output.
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Fail the named central case when any concurrency or rollback assertion failed.
        if not result.wasSuccessful():
            raise AssertionError("player game-state atomicity suite failed")

    # Define one focused unittest runner for bounded MySQL pool lifecycle behavior.
    def run_mysql_pool_tests():
        # Load only the STORAGE-010 and TEST-141 pool test class.
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(mysql_pool_tests.MySQLPoolTests)
        # Execute the focused suite with concise standard output.
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Fail the named central case when any lifecycle or concurrency assertion failed.
        if not result.wasSuccessful():
            raise AssertionError("MySQL connection pool lifecycle suite failed")

    # Define one listener-free runner for PostgreSQL configuration and lazy registration.
    def run_postgres_registration_tests():
        # Load only the STORAGE-020 and TEST-252 registration test class.
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(postgres_registration_tests.PostgresRegistrationTests)
        # Execute without a connector, listener, provider implementation, or external target.
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Fail the named central case when configuration or import isolation drifts.
        if not result.wasSuccessful():
            # Preserve one fixed provider-neutral diagnostic.
            raise AssertionError("PostgreSQL registration suite failed")

    # Define one listener-free runner for bounded PostgreSQL pool lifecycle behavior.
    def run_postgres_pool_tests():
        # Load only the STORAGE-021 and TEST-253 pool test class.
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(postgres_pool_tests.PostgresPoolTests)
        # Execute without a connector, listener, provider implementation, or external target.
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Fail the named central case when lifecycle or concurrency evidence drifts.
        if not result.wasSuccessful():
            # Preserve one fixed provider-neutral diagnostic.
            raise AssertionError("PostgreSQL connection pool lifecycle suite failed")

    # Define one focused unittest runner for authenticated recovery and clean-target policy.
    def run_recovery_policy_tests():
        # Load only the #205 synthetic recovery test case.
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(recovery_tests.RecoveryEvidenceTests)
        # Execute with concise standard output.
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Fail the named central case when any focused assertion failed.
        if not result.wasSuccessful():
            raise AssertionError("recovery policy suite failed")

    # Define one focused unittest runner for checksum, proof, failure, and SELECT-only policy.
    def run_mysql_migration_policy_tests():
        # Load only the #204 migration test case.
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(mysql_migration_tests.MySQLMigrationTests)
        # Execute with concise standard output.
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Fail the named central case when any focused assertion failed.
        if not result.wasSuccessful():
            raise AssertionError("MySQL migration policy suite failed")

    # Define one focused unittest runner for first-class session provider parity.
    def run_session_storage_tests():
        # Load the complete keyed JSON and modeled-MySQL lifecycle suite.
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(session_storage_tests.SessionStorageProviderTests)
        # Execute the concurrency, cap, rotation, expiry, and importer cases.
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Fail the named central case when any session-storage assertion failed.
        if not result.wasSuccessful():
            # Preserve one fixed listener-free diagnostic.
            raise AssertionError("first-class session storage suite failed")

    # Map the listener-free policy suite to the permanent migration requirements.
    run_case("MYSQL-MIGRATION-001", ["MYSQL-005", "MYSQL-007", "MYSQL-008", "MYSQL-009", "STORAGE-007", "TEST-048", "TEST-174"], run_mysql_migration_policy_tests)
    # Prove keyed session rows, deterministic caps, rotation, expiry, and concurrent login/logout parity.
    run_case("STORAGE-SESSIONS-001", ["SESSION-014", "STORAGE-019", "MYSQL-010", "TEST-250"], run_session_storage_tests)
    # Map the listener-free recovery suite to the permanent recovery requirements.
    run_case("RECOVERY-POLICY-001", ["MYSQL-006", "MYSQL-008", "MYSQL-009", "TOOL-004", "TEST-049", "TEST-174"], run_recovery_policy_tests)
    # Prove deterministic configuration and an explicit lazy selector with JSON/MySQL import isolation.
    run_case("POSTGRES-CONFIG-001", ["STORAGE-001", "STORAGE-003", "STORAGE-004", "STORAGE-020", "TEST-252"], run_postgres_registration_tests)
    # Prove bounded checkout, cleanup, fork isolation, shutdown, and secret-free pool evidence.
    run_case("POSTGRES-POOL-001", ["STORAGE-010", "STORAGE-021", "TEST-253"], run_postgres_pool_tests)
    # Execute the JSON fallback parity test for provider-backed players, ledger, history, and settings.
    run_case("STORAGE-JSON-001", ["CORE-017", "LEDGER-001", "LEDGER-007", "AUDIO-010", "STORAGE-016", "TEST-030", "TEST-243"], run_storage_base_and_json_parity)
    # Execute one identical paid settlement, replay, resolve, and conflict schedule on JSON and MySQL.
    run_case("STORAGE-PROVIDER-SETTLEMENT-PARITY-001", ["CORE-031", "STORAGE-013", "STORAGE-016", "TEST-243"], run_storage_provider_settlement_parity_tests)
    # Prove corrupt wallet state cannot seed defaults or reach a settlement on either provider.
    run_case("STORAGE-WALLET-CORRUPTION-001", ["STORAGE-014", "TEST-177"], run_wallet_corruption_tests)
    # Prove explicit residue repair, audit evidence, and cents-only writes on both providers.
    run_case("STORAGE-WALLET-CENTS-001", ["STORAGE-015", "LEDGER-036", "TOOL-019", "TEST-190"], run_wallet_cents_normalization_tests)
    # Execute storage-enforced replay, conflict, restart, and cross-process JSON action tests.
    run_case("STORAGE-JSON-IDEMPOTENCY-001", ["LEDGER-026", "LEDGER-033", "LEDGER-034", "STORAGE-005", "STORAGE-006", "TEST-043", "TEST-164", "TEST-169"], storage_tests.run_json_action_idempotency)
    # Execute provider-owned journal recovery, contention, reset, and fail-closed proof.
    run_case("STORAGE-GAME-ACTION-ONCE-001", ["STORAGE-011"], run_json_game_action_provider_tests)
    # Prove immutable JSON claims, pending resolution, restart tombstones, and late-executor refusal.
    run_case("STORAGE-GAME-ACTION-LIFECYCLE-001", ["CORE-031", "STORAGE-013", "TEST-174"], run_json_game_action_provider_tests)
    # Prove schema-four MySQL claim, transaction, resolver, replay, and rollback parity.
    run_case("MYSQL-GAME-ACTION-LIFECYCLE-001", ["MYSQL-009", "STORAGE-013", "TEST-174"], run_mysql_game_action_provider_tests)
    # Prove player-scoped concurrency plus thin-facade parity, containment, rollback, and delegation.
    run_case("STORAGE-PLAYER-STATE-ATOMIC-001", ["CORE-030", "STORAGE-001", "STORAGE-002", "STORAGE-018", "TEST-247"], run_player_state_atomic_tests)
    # Execute funded practice-opponent debit, refund, payout, restart, owner, and process evidence.
    run_case("STORAGE-PRACTICE-OPPONENT-001", ["BOT-009", "BOT-010", "BOT-011", "ADMIN-023", "LEDGER-026", "STORAGE-005", "STORAGE-006"], storage_tests.run_practice_opponent_accounting)

    # Define one focused unittest runner for durable enrollment policy.
    def run_enrollment_policy_tests():
        # Load the focused listener-free policy suite.
        suite = unittest.defaultTestLoader.loadTestsFromModule(enrollment_policy_tests)
        # Execute with concise standard output.
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Fail the named central case when any focused assertion failed.
        if not result.wasSuccessful():
            raise AssertionError("enrollment policy suite failed")

    # Map the permanent requirement to its existing focused central case.
    run_case("API-ENROLLMENT-POLICY-001", ["AUTH-013", "AUTH-014", "AUTH-015", "OAUTH-011", "TEST-158"], run_enrollment_policy_tests)
    # Prove player creation preserves committed ledger history and never reverts a balance.
    run_case("STORAGE-LEDGER-GUARD-001", ["STORAGE-008", "STORAGE-012", "LEDGER-001", "CORE-017", "TEST-162"], storage_tests.run_player_creation_preserves_ledger)

    # Run the descriptor, router, state-repair, and catalog suite through the permanent API gate.
    def run_game_rule_schema_tests():
        # Load only the listener-free descriptor-governance test class.
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(test_game_rule_schema.GameRuleSchemaTests)
        # Execute the focused suite with concise central-runner output.
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)
        # Fail the named central case when any descriptor or runtime-boundary assertion fails.
        if not result.wasSuccessful():
            raise AssertionError("game rule schema suite failed")

    # Bind central request coercion, read repair, generated contracts, and catalog governance permanently.
    run_case("API-GAME-RULES-001", ["SEC-002", "SEC-004", "SEC-014", "TEST-163"], run_game_rule_schema_tests)
    # Prove client-supplied table rules and token credits stay inside their declared domains.
    run_case("STORAGE-TABLE-RULES-001", ["LEDGER-029", "TOKEN-006"], storage_tests.run_table_rule_authority)
    # Execute the MySQL schema and atomic ledger-provider path test without requiring a live service.
    run_case("STORAGE-MYSQL-001", ["CORE-017", "LEDGER-001", "LEDGER-007", "LEDGER-009", "LEDGER-033", "TEST-164"], storage_tests.run_mysql_schema_provider_path)
    # Execute bounded capacity, cleanup, fork, observability, and pool evidence without a service.
    run_case("MYSQL-POOL-001", ["STORAGE-010", "MYSQL-011", "TEST-141", "TEST-220"], run_mysql_pool_tests)
    # Exercise ordinary JSON concurrency through the exact production Gunicorn stack when explicitly hosted.
    if gunicorn_json_load_callback is not None:
        # Keep the provider-neutral profile inside the central inventory and aggregate result ledger.
        gunicorn_json_load_callback()
    # Execute the real-service persistence and concurrent-ledger gate only when explicitly requested.
    if include_live:
        # Map the live integration case to the durable storage and MySQL requirements.
        run_case("STORAGE-MYSQL-LIVE-001", ["STORAGE-001", "STORAGE-002", "STORAGE-003", "STORAGE-004", "STORAGE-005", "STORAGE-006", "STORAGE-010", "MYSQL-001", "MYSQL-002", "MYSQL-003", "MYSQL-004", "OTT-001", "OTT-002", "MAIL-002", "MAIL-004", "INVITE-003", "TEST-038", "TEST-043", "TEST-089", "TEST-090", "TEST-091", "TEST-141", "TEST-171", "TEST-220"], storage_tests.run_mysql_live_provider_path)
    # Execute the disposable MySQL 8.4 gate only when explicitly requested.
    if include_migration_live:
        # Import the service-dependent matrix only after the disposable selector is explicit.
        from tests.mysql_migration_live import run_mysql_migration_live_matrix
        # Map clean bootstrap, upgrade, refusal, restart, grants, and lock evidence.
        run_case("MYSQL-MIGRATION-LIVE-001", ["MYSQL-005", "MYSQL-007", "MYSQL-008", "MYSQL-009", "STORAGE-007", "STORAGE-010", "STORAGE-018", "GAMECORE-009", "OTT-001", "OTT-002", "MAIL-002", "MAIL-004", "TEST-048", "TEST-089", "TEST-090", "TEST-141", "TEST-174", "TEST-220", "TEST-246", "TEST-247", "TEST-251"], lambda: run_mysql_migration_live_matrix(request_latency_callback, gunicorn_load_callback))
