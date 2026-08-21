# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Import thread-pool helpers for bounded 1/2/4/8 concurrency evidence.
from concurrent.futures import ThreadPoolExecutor
# Import JSON so secret-free metric snapshots can be inspected exactly.
import json
# Import operating-system helpers for environment and PID-boundary tests.
import os
# Import threading primitives for deterministic waiter and fake-connector coordination.
import threading
# Import monotonic timing and short synthetic operation delays.
import time
# Import the standard unittest framework and environment patch helper.
import unittest
from unittest.mock import patch
# Import a generic result type for thread-worker diagnostics.
from typing import Any

# Import the production pool and fixed error classes under test.
from casino.core.mysql_pool import MySQLConnectionPool, MySQLPoolClosedError, MySQLPoolConfig, MySQLPoolConnectionError, MySQLPoolExhaustedError
# Import the storage provider integration and explicit connection configuration.
from casino.core.storage import MySQLConfig, MySQLStorageProvider


# Define a deterministic connector-owned cursor for lifecycle tests.
class FakeCursor:
    # Initialize one fake cursor with optional cleanup failure.
    def __init__(self) -> None:
        # Count cursor close calls.
        self.close_calls = 0
        # Allow one test to force cursor cleanup failure.
        self.fail_close = False

    # Close one fake request-owned cursor.
    def close(self) -> None:
        # Count every cleanup attempt.
        self.close_calls += 1
        # Raise when a test exercises forced physical discard.
        if self.fail_close:
            # Surface a synthetic cursor failure only inside the focused test.
            raise RuntimeError("synthetic cursor close failure")


# Define a deterministic connector-owned physical connection for lifecycle tests.
class FakeConnection:
    # Initialize one fake physical session with configurable cleanup behavior.
    def __init__(self, identifier: int) -> None:
        # Store a non-secret test identifier for reuse assertions.
        self.identifier = identifier
        # Start every fake socket alive.
        self.alive = True
        # Start every fake session outside a transaction.
        self.in_transaction = False
        # Allow one test to force session-reset failure.
        self.fail_reset = False
        # Count transaction rollback cleanup calls.
        self.rollback_calls = 0
        # Count session reset calls.
        self.reset_calls = 0
        # Count physical close calls.
        self.close_calls = 0
        # Store cursors created on this physical session.
        self.cursors: list[FakeCursor] = []

    # Open one fake connector cursor.
    def cursor(self, *args: Any, **kwargs: Any) -> FakeCursor:
        # Allocate one request-owned fake cursor.
        cursor = FakeCursor()
        # Retain the cursor for cleanup assertions.
        self.cursors.append(cursor)
        # Return the fake cursor.
        return cursor

    # Prove liveness without reconnecting or replacing this fake session.
    def ping(self, reconnect: bool, attempts: int, delay: int) -> None:
        # Require production to disable connector-managed reconnect.
        assert reconnect is False and attempts == 1 and delay == 0
        # Raise when this fake socket was killed or closed.
        if not self.alive:
            # Surface a synthetic connector failure only inside the focused test.
            raise RuntimeError("synthetic dead socket")

    # Roll back one caller-abandoned fake transaction.
    def rollback(self) -> None:
        # Count exact rollback cleanup.
        self.rollback_calls += 1
        # Mark the transaction ended.
        self.in_transaction = False

    # Reset one reusable fake session.
    def reset_session(self) -> None:
        # Count every attempted reset.
        self.reset_calls += 1
        # Raise when a test exercises fail-closed discard.
        if self.fail_reset:
            # Surface a synthetic connector failure only inside the focused test.
            raise RuntimeError("synthetic reset failure")

    # Close one fake physical session.
    def close(self) -> None:
        # Count physical close calls for shutdown and discard assertions.
        self.close_calls += 1
        # Mark the fake socket dead.
        self.alive = False


# Define a thread-safe physical connection factory for pool tests.
class FakeFactory:
    # Initialize creation tracking and optional failure injection.
    def __init__(self) -> None:
        # Serialize creation counters across concurrent checkouts.
        self.lock = threading.Lock()
        # Store created fake connections in creation order.
        self.connections: list[FakeConnection] = []
        # Record validated connector timeouts without credentials.
        self.timeouts: list[int] = []
        # Allow one test to fail the next physical creation.
        self.fail_next = False

    # Create one fake physical connection under the pool reservation.
    def __call__(self, timeout_seconds: int) -> FakeConnection:
        # Serialize deterministic identifier and failure decisions.
        with self.lock:
            # Record the bounded connector timeout.
            self.timeouts.append(timeout_seconds)
            # Fail exactly one requested creation when armed.
            if self.fail_next:
                # Clear failure injection before raising.
                self.fail_next = False
                # Surface a synthetic connector error only inside this test boundary.
                raise RuntimeError("synthetic connector failure")
            # Allocate a deterministic fake connection identifier.
            connection = FakeConnection(len(self.connections) + 1)
            # Retain the created connection for assertions.
            self.connections.append(connection)
            # Return the connector-owned physical session.
            return connection


# Define a mysql.connector-shaped adapter for storage-provider integration tests.
class FakeConnector:
    # Initialize a reusable fake physical factory and connector-option capture.
    def __init__(self) -> None:
        # Reuse the thread-safe physical factory.
        self.factory = FakeFactory()
        # Record connector keyword names and bounded non-secret values.
        self.calls: list[dict] = []

    # Open one fake physical connection through the mysql.connector signature.
    def connect(self, **options) -> FakeConnection:
        # Record the copied connector options for fixed-seam assertions.
        self.calls.append(dict(options))
        # Delegate creation using only the bounded connection timeout.
        return self.factory(int(options["connection_timeout"]))


# Define the focused STORAGE-010 and TEST-141 pool lifecycle suite.
class MySQLPoolTests(unittest.TestCase):
    # Build a pool with explicit policy for each focused test.
    def build_pool(self, factory: FakeFactory | None = None, capacity: int = 2, wait_ms: int = 100, connect_timeout: int = 3) -> tuple[MySQLConnectionPool, FakeFactory]:
        # Reuse the supplied factory or allocate an isolated one.
        physical_factory = factory or FakeFactory()
        # Build explicit validated policy without reading developer environment variables.
        config = MySQLPoolConfig(capacity=capacity, checkout_wait_ms=wait_ms, connect_timeout_seconds=connect_timeout)
        # Return the production pool and inspectable fake factory.
        return MySQLConnectionPool(physical_factory, config), physical_factory

    # Prove defaults and fail-closed environment validation.
    def test_config_defaults_and_bounds(self) -> None:
        # Clear only pool controls so the default policy is deterministic.
        with patch.dict(os.environ, {}, clear=False):
            # Remove every optional pool control from the patched environment.
            for name in ("CASINO_MYSQL_POOL_SIZE", "CASINO_MYSQL_POOL_WAIT_MS", "CASINO_MYSQL_CONNECT_TIMEOUT_SECONDS"):
                # Delete only the focused non-secret setting.
                os.environ.pop(name, None)
            # Load the reviewed default pool shape for the qualification-grade serving stack.
            config = MySQLPoolConfig.from_env()
        # Require the approved capacity, checkout wait, and physical timeout defaults.
        self.assertEqual((config.capacity, config.checkout_wait_ms, config.connect_timeout_seconds), (16, 500, 3))
        # Reject every out-of-range policy dimension.
        for values in ((0, 500, 3), (65, 500, 3), (2, 0, 3), (2, 10_001, 3), (2, 500, 0), (2, 500, 61)):
            # Require fixed policy validation before any connector call.
            with self.assertRaises(ValueError):
                # Construct one invalid policy tuple.
                MySQLPoolConfig(capacity=values[0], checkout_wait_ms=values[1], connect_timeout_seconds=values[2])
        # Reject malformed environment text without echoing it.
        with patch.dict(os.environ, {"CASINO_MYSQL_POOL_SIZE": "secret-like-invalid"}, clear=False):
            # Require a fixed parser error.
            with self.assertRaisesRegex(ValueError, "^MySQL pool settings must be integers\\.$"):
                # Parse the deliberately malformed non-secret control.
                MySQLPoolConfig.from_env()

    # Prove one physical connection is sanitized and reused.
    def test_reuse_and_secret_free_metrics(self) -> None:
        # Build a two-slot pool without opening a physical connection.
        pool, factory = self.build_pool()
        # Acquire the first request-scoped lease.
        first = pool.acquire()
        # Capture its deterministic physical identifier through delegation.
        first_identifier = first.identifier
        # Return and sanitize the first physical session.
        first.close()
        # Acquire a second request-scoped lease.
        second = pool.acquire()
        # Require the same physical session to be reused.
        self.assertEqual(second.identifier, first_identifier)
        # Return the reused session.
        second.close()
        # Capture the internal low-cardinality snapshot.
        snapshot = pool.snapshot()
        # Require one physical creation, one reuse, and one idle sanitized session.
        self.assertEqual((snapshot["physical_created"], snapshot["reused"], snapshot["idle"], len(factory.connections)), (1, 1, 1, 1))
        # Serialize the complete evidence surface for forbidden-label checks.
        serialized = json.dumps(snapshot, sort_keys=True)
        # Reject every identity, credential, query, host, and connector-text label.
        for forbidden in ("user", "session", "query", "host", "password", "database", "error_text", "exception"):
            # Require the forbidden label to remain absent.
            self.assertNotIn(forbidden, serialized.lower())
        # Close the idle physical connection after evidence.
        pool.close_all()

    # Prove hard capacity blocks and then wakes one bounded waiter.
    def test_capacity_waiter_wakes_and_reuses(self) -> None:
        # Build a single-slot pool with a generous deterministic unit-test deadline.
        pool, factory = self.build_pool(capacity=1, wait_ms=500)
        # Hold the only physical connection.
        first = pool.acquire()
        # Store the waiting thread's lease and any unexpected exception.
        acquired: list[Any] = []
        errors: list[BaseException] = []
        # Define one waiter that closes its eventual lease immediately.
        def wait_for_lease() -> None:
            # Start protected acquisition so test diagnostics retain unexpected failures.
            try:
                # Acquire after the first lease returns.
                lease = pool.acquire()
                # Record the reused physical identifier.
                acquired.append(lease.identifier)
                # Return the second request-scoped lease.
                lease.close()
            # Preserve unexpected worker exceptions for the parent assertion.
            except BaseException as error:
                # Record the exception object without logging connector state.
                errors.append(error)
        # Start one bounded waiting thread.
        thread = threading.Thread(target=wait_for_lease, daemon=True)
        # Launch the waiter.
        thread.start()
        # Poll the sanitized waiter gauge for at most one second.
        deadline = time.monotonic() + 1.0
        # Wait until the production condition reports one blocked checkout.
        while pool.snapshot()["waiting"] != 1 and time.monotonic() < deadline:
            # Yield briefly without opening a listener or external resource.
            time.sleep(0.001)
        # Require the waiter to have reached capacity before releasing the slot.
        self.assertEqual(pool.snapshot()["waiting"], 1)
        # Return the only physical connection and wake the waiter.
        first.close()
        # Wait for the bounded worker to finish.
        thread.join(timeout=1.0)
        # Require clean completion and reuse of the one physical connection.
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(acquired, [factory.connections[0].identifier])
        # Require one wait, no timeout, one physical creation, and one reuse.
        snapshot = pool.snapshot()
        # Compare the low-cardinality counters.
        self.assertEqual((snapshot["wait_count"], snapshot["timeout_count"], snapshot["physical_created"], snapshot["reused"]), (1, 0, 1, 1))
        # Bind the operator-facing saturation counter to the exact checkout-capacity encounter.
        self.assertEqual(snapshot["wait_count"], snapshot["saturation_count"])
        # Require exactly one fixed wait bucket to have been incremented.
        self.assertEqual(sum(snapshot["wait_buckets_ms"].values()), 1)
        # Close the reusable session.
        pool.close_all()

    # Prove checkout exhaustion reaches a fixed bounded error.
    def test_capacity_timeout_fails_closed(self) -> None:
        # Build a single-slot pool with a short deterministic deadline.
        pool, _ = self.build_pool(capacity=1, wait_ms=20)
        # Hold the only physical connection.
        first = pool.acquire()
        # Require the second checkout to fail with only the fixed pool error.
        with self.assertRaisesRegex(MySQLPoolExhaustedError, "^MySQL connection pool checkout timed out\\.$"):
            # Attempt one bounded checkout at hard capacity.
            pool.acquire()
        # Require one wait and one timeout without a leaked waiter.
        snapshot = pool.snapshot()
        # Compare the secret-free wait counters and gauge.
        self.assertEqual((snapshot["wait_count"], snapshot["timeout_count"], snapshot["waiting"]), (1, 1, 0))
        # Require one saturation encounter for the one capacity-bound checkout.
        self.assertEqual(1, snapshot["saturation_count"])
        # Return the original lease after the timeout proof.
        first.close()
        # Close the remaining idle physical connection.
        pool.close_all()

    # Prove capacity-aligned serialized work returns every successful and failed worker lease. (TEST-220)
    def test_capacity_two_serialized_workload_returns_all_leases(self) -> None:
        # Build the exact capacity-two pool with the unchanged bounded checkout deadline.
        pool, factory = self.build_pool(capacity=2, wait_ms=20)
        # Define one test-local worker error distinct from every production pool RuntimeError.
        class SyntheticWorkerError(Exception):
            # Keep the synthetic category behavior-free.
            pass
        # Model one MySQL wallet-row lock shared by every synthetic debit.
        wallet_lock = threading.Lock()
        # Retain successful synthetic action identities only for exact completion evidence.
        completed: list[int] = []
        # Retain the one intentionally failed worker identity without leaking exception text.
        failed: list[int] = []

        # Execute one request-scoped operation that always returns its lease.
        def execute(index: int, fail: bool = False) -> None:
            # Acquire one of the two bounded physical sessions.
            lease = pool.acquire()
            # Start protected row work so success and failure share the same cleanup boundary.
            try:
                # Serialize the money-adjacent resource like a SELECT FOR UPDATE wallet row.
                with wallet_lock:
                    # Hold the row briefly so both pool slots overlap deterministically.
                    time.sleep(0.001)
                    # Trigger one synthetic operation failure after checkout when requested.
                    if fail:
                        # Raise only fixed test-local failure text.
                        raise SyntheticWorkerError("synthetic serialized worker failure")
                    # Record one successful synthetic action identity.
                    completed.append(index)
            # Classify only the deliberate synthetic worker failure.
            except SyntheticWorkerError:
                # Record the failed identity without swallowing pool errors.
                failed.append(index)
            # Always return the request-scoped lease through production cleanup.
            finally:
                # Sanitize and release the physical session.
                lease.close()

        # Repeat the same twenty-operation schedule three times at exact pool capacity.
        for cohort_index in range(3):
            # Use exactly two workers so row-lock contention cannot manufacture checkout starvation.
            with ThreadPoolExecutor(max_workers=pool.config.capacity) as executor:
                # Materialize every worker result so unexpected pool exceptions fail this test.
                list(executor.map(lambda index: execute((cohort_index * 20) + index), range(20)))
        # Run one successful and one failed operation together through the same cleanup path.
        with ThreadPoolExecutor(max_workers=pool.config.capacity) as executor:
            # Wait for both bounded workers and surface any unexpected exception.
            list(executor.map(lambda item: execute(item[0], item[1]), ((60, False), (61, True))))
        # Require sixty-one successes, one classified failure, and no lost synthetic identity.
        self.assertEqual((len(completed), len(set(completed)), failed), (61, 61, [61]))
        # Capture the final secret-free pool state after both executors joined.
        snapshot = pool.snapshot()
        # Require both physical sessions idle with no wait, timeout, discard, or lease residue.
        self.assertEqual((snapshot["capacity"], snapshot["in_use"], snapshot["idle"], snapshot["waiting"], snapshot["wait_count"], snapshot["timeout_count"], snapshot["discarded"]), (2, 0, 2, 0, 0, 0, 0))
        # Require exactly two physical sessions despite repeated work and one worker failure.
        self.assertEqual((snapshot["physical_created"], len(factory.connections)), (2, 2))
        # Close both reusable sessions after the evidence is complete.
        pool.close_all()

    # Prove open transactions are rolled back and sessions reset before reuse.
    def test_transaction_cleanup_before_reuse(self) -> None:
        # Build one physical slot for exact cleanup assertions.
        pool, factory = self.build_pool(capacity=1)
        # Acquire the fake physical session.
        lease = pool.acquire()
        # Simulate a caller that leaves a transaction open.
        factory.connections[0].in_transaction = True
        # Return the lease through production cleanup.
        lease.close()
        # Require rollback and reset before the connection entered the idle set.
        self.assertEqual((factory.connections[0].rollback_calls, factory.connections[0].reset_calls), (1, 1))
        # Require the aggregate rollback cleanup counter.
        self.assertEqual(pool.snapshot()["rollback_cleanup"], 1)
        # Reacquire the sanitized session.
        reused = pool.acquire()
        # Require exact physical reuse only after cleanup.
        self.assertEqual(reused.identifier, factory.connections[0].identifier)
        # Return and shut down the pool.
        reused.close()
        # Close the idle physical session.
        pool.close_all()

    # Prove failed cleanup discards the uncertain connection.
    def test_cleanup_failure_discards_connection(self) -> None:
        # Build one physical slot for deterministic replacement.
        pool, factory = self.build_pool(capacity=1)
        # Acquire the first physical session.
        first = pool.acquire()
        # Force reset failure on lease return.
        factory.connections[0].fail_reset = True
        # Return the uncertain session so production discards it.
        first.close()
        # Require one discard, no idle session, and the first socket closed.
        self.assertEqual((pool.snapshot()["discarded"], pool.snapshot()["idle"], factory.connections[0].close_calls), (1, 0, 1))
        # Acquire again so a replacement physical connection is created.
        second = pool.acquire()
        # Require a distinct physical identity.
        self.assertNotEqual(second.identifier, factory.connections[0].identifier)
        # Return the healthy replacement.
        second.close()
        # Close the pool.
        pool.close_all()

    # Prove request-owned cursors close before reset and force discard on cleanup failure.
    def test_cursor_cleanup_precedes_reuse_and_fails_closed(self) -> None:
        # Build one physical slot for exact cursor cleanup evidence.
        pool, factory = self.build_pool(capacity=1)
        # Acquire one request-scoped connection.
        first = pool.acquire()
        # Open one connector cursor through the tracking lease.
        first_cursor = first.cursor()
        # Return the lease without explicitly closing its cursor.
        first.close()
        # Require lease close to release the cursor before the physical session became idle.
        self.assertEqual((first_cursor.close_calls, pool.snapshot()["idle"]), (1, 1))
        # Acquire the same physical session for a second request.
        second = pool.acquire()
        # Open one cursor that will fail cleanup.
        second_cursor = second.cursor()
        # Arm the cursor cleanup failure.
        second_cursor.fail_close = True
        # Return the second lease so cleanup forces physical discard.
        second.close()
        # Require the failed cursor cleanup to close and discard the uncertain physical session.
        self.assertEqual((second_cursor.close_calls, pool.snapshot()["discarded"], pool.snapshot()["idle"], factory.connections[0].close_calls), (1, 1, 0, 1))
        # Close the now-empty pool.
        pool.close_all()

    # Prove a dead idle connection is never silently reconnected or reused.
    def test_dead_idle_connection_is_discarded(self) -> None:
        # Build one physical slot for deterministic dead-session replacement.
        pool, factory = self.build_pool(capacity=1)
        # Acquire and return the first physical connection.
        first = pool.acquire()
        # Make the first session idle.
        first.close()
        # Simulate server-side socket death while idle.
        factory.connections[0].alive = False
        # Acquire again so the pre-check discards and replaces the dead session.
        second = pool.acquire()
        # Require a new physical identifier.
        self.assertNotEqual(second.identifier, factory.connections[0].identifier)
        # Return the healthy replacement.
        second.close()
        # Require one health discard and two total successful physical creations.
        snapshot = pool.snapshot()
        # Compare the aggregate lifecycle counters.
        self.assertEqual((snapshot["discarded"], snapshot["physical_created"]), (1, 2))
        # Close the pool.
        pool.close_all()

    # Prove connector failures release reservations and surface fixed text.
    def test_connector_failure_is_secret_safe(self) -> None:
        # Arm one factory failure before building the pool.
        factory = FakeFactory()
        # Fail the first physical creation only.
        factory.fail_next = True
        # Build the pool around the armed factory.
        pool, _ = self.build_pool(factory=factory, capacity=1)
        # Require fixed pool-owned failure text with no connector exception chaining.
        with self.assertRaisesRegex(MySQLPoolConnectionError, "^MySQL physical connection could not be created\\.$") as raised:
            # Attempt the failing physical checkout.
            pool.acquire()
        # Require no connector-specific cause to remain attached.
        self.assertIsNone(raised.exception.__cause__)
        # Require the reservation to be released and aggregate error counted.
        self.assertEqual((pool.snapshot()["connector_error"], pool.snapshot()["in_use"], pool.snapshot()["idle"]), (1, 0, 0))
        # Acquire successfully after the one-shot connector failure.
        lease = pool.acquire()
        # Return the replacement connection.
        lease.close()
        # Close the pool.
        pool.close_all()

    # Prove PID changes abandon inherited sockets and rebuild child-local state.
    def test_pid_change_rebuilds_pool(self) -> None:
        # Build one physical slot and create one idle connection.
        pool, factory = self.build_pool(capacity=1)
        # Acquire the first process-bound session.
        lease = pool.acquire()
        # Return the session to the idle set.
        lease.close()
        # Simulate a child process observing an inherited pool object.
        pool._pid = os.getpid() - 1
        # Trigger the production PID guard through the public evidence seam.
        snapshot = pool.snapshot()
        # Require fresh child-local gauges and counters.
        self.assertEqual((snapshot["in_use"], snapshot["idle"], snapshot["physical_created"]), (0, 0, 0))
        # Require the inherited idle socket to have been closed.
        self.assertEqual(factory.connections[0].close_calls, 1)
        # Acquire one fresh child-local physical session.
        child_lease = pool.acquire()
        # Require a new physical identifier after PID reset.
        self.assertNotEqual(child_lease.identifier, factory.connections[0].identifier)
        # Return the child-local lease.
        child_lease.close()
        # Close the pool.
        pool.close_all()

    # Prove shutdown closes idle sessions and rejects new work.
    def test_close_all_is_terminal_and_idempotent(self) -> None:
        # Build a two-slot pool and create one idle physical session.
        pool, factory = self.build_pool()
        # Acquire the physical session.
        lease = pool.acquire()
        # Return it to the idle set.
        lease.close()
        # Close all idle sessions and mark the pool terminal.
        pool.close_all()
        # Repeat shutdown to prove idempotent cleanup.
        pool.close_all()
        # Require exactly one physical close call.
        self.assertEqual(factory.connections[0].close_calls, 1)
        # Require future checkout to fail closed with fixed text.
        with self.assertRaisesRegex(MySQLPoolClosedError, "^MySQL connection pool is closed\\.$"):
            # Attempt one post-shutdown checkout.
            pool.acquire()

    # Prove the storage provider preserves its established connect/close seam over the pool.
    def test_storage_provider_integration_reuses_physical_connection(self) -> None:
        # Build synthetic explicit configuration without touching a real network.
        config = MySQLConfig(host="pool.example.invalid", port=3306, user="pool-user", password="pool-secret", database="pool-db")
        # Build one explicit single-slot pool policy.
        pool_config = MySQLPoolConfig(capacity=1, checkout_wait_ms=100, connect_timeout_seconds=3)
        # Construct the real provider without opening a connector.
        provider = MySQLStorageProvider(config=config, pool_config=pool_config)
        # Build the mysql.connector-shaped fake.
        connector = FakeConnector()
        # Replace only the lazy connector import seam.
        provider._connector = lambda: connector
        # Acquire and close through the established provider seam.
        first = provider.connect()
        # Open one request-owned cursor so lease cleanup can be observed through the provider seam.
        first_cursor = first.cursor()
        # Capture the delegated fake identifier.
        first_identifier = first.identifier
        # Return the first request-scoped connection.
        first.close()
        # Require provider lease close to end the request-owned cursor.
        self.assertEqual(first_cursor.close_calls, 1)
        # Acquire again with the existing readiness-probe timeout override.
        second = provider.connect(connection_timeout=3)
        # Require physical reuse through unchanged close behavior.
        self.assertEqual(second.identifier, first_identifier)
        # Return the second lease.
        second.close()
        # Require one connector call with fixed config and bounded timeout.
        self.assertEqual(len(connector.calls), 1)
        # Require the configured connector values to remain exact inside the connector boundary.
        self.assertEqual(connector.calls[0], {"host": "pool.example.invalid", "port": 3306, "user": "pool-user", "password": "pool-secret", "database": "pool-db", "connection_timeout": 3})
        # Require unsupported caller overrides to fail before connector access.
        with self.assertRaisesRegex(ValueError, "^Unsupported MySQL connection override\\.$"):
            # Attempt to cross the fixed database boundary.
            provider.connect(database="other")
        # Require only secret-free pool evidence from the provider.
        self.assertNotIn("pool-secret", json.dumps(provider.pool_snapshot(), sort_keys=True))
        # Close the provider-owned pool.
        provider.close_pool()

    # Prove the same bounded operation at concurrency 1, 2, 4, and 8.
    def test_concurrency_measurements_1_2_4_8(self) -> None:
        # Build the production-default two-slot pool with a one-second test deadline.
        pool, _ = self.build_pool(capacity=2, wait_ms=1_000)
        # Store sanitized aggregate rows for all required concurrency levels.
        measurements: list[dict[str, float | int]] = []
        # Define one short request-scoped operation.
        def operation(index: int) -> float:
            # Capture the request-local start instant.
            started_at = time.perf_counter()
            # Acquire one bounded request-scoped connection.
            lease = pool.acquire()
            # Start protected synthetic work so every lease is returned.
            try:
                # Simulate a small DB-API operation without a listener or external service.
                time.sleep(0.002)
            # Always sanitize and return the physical session.
            finally:
                # Release the request-scoped lease.
                lease.close()
            # Return only the elapsed milliseconds for aggregate computation.
            return (time.perf_counter() - started_at) * 1000.0
        # Exercise every required concurrency level in ascending order.
        for concurrency in (1, 2, 4, 8):
            # Capture the aggregate run start.
            run_started_at = time.perf_counter()
            # Execute sixteen bounded operations at this concurrency.
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                # Materialize every elapsed result so failures surface.
                elapsed = list(executor.map(operation, range(16)))
            # Capture total wall-clock duration after all leases returned.
            wall_seconds = time.perf_counter() - run_started_at
            # Sort request latencies for deterministic nearest-rank percentiles.
            ordered = sorted(elapsed)
            # Select the median observation.
            p50 = ordered[max(0, int(len(ordered) * 0.50) - 1)]
            # Select the nearest-rank ninety-fifth-percentile observation.
            p95 = ordered[max(0, int((len(ordered) * 0.95) + 0.999999) - 1)]
            # Store only concurrency, aggregate percentiles, throughput, and error count.
            measurements.append({"concurrency": concurrency, "p50_ms": p50, "p95_ms": p95, "throughput_rps": len(elapsed) / wall_seconds, "errors": 0})
        # Require all four governed concurrency rows.
        self.assertEqual([row["concurrency"] for row in measurements], [1, 2, 4, 8])
        # Require zero operation errors at every governed level.
        self.assertTrue(all(row["errors"] == 0 for row in measurements))
        # Require warm single-concurrency targets from the Package B plan.
        self.assertLessEqual(measurements[0]["p50_ms"], 100.0)
        # Require the warm single-concurrency p95 target.
        self.assertLessEqual(measurements[0]["p95_ms"], 200.0)
        # Require the concurrency-four p95 target.
        self.assertLessEqual(measurements[2]["p95_ms"], 250.0)
        # Require every synthetic throughput row to exceed the pre-pool baseline floor.
        self.assertTrue(all(row["throughput_rps"] > 3.37 for row in measurements))
        # Require physical sessions to remain limited to pool warm-up.
        snapshot = pool.snapshot()
        # Require the intended hard capacity and no timeout.
        self.assertEqual((snapshot["capacity"], snapshot["timeout_count"]), (2, 0))
        # Require at least one and at most two physical connections after warm-up.
        self.assertTrue(1 <= snapshot["physical_created"] <= 2)
        # Close the two reusable physical sessions.
        pool.close_all()


# Run the focused suite when invoked directly.
if __name__ == "__main__":
    # Execute unittest with standard failure semantics.
    unittest.main()
