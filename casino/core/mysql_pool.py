# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Import annotations so lease and pool type hints can refer to classes declared later.
from __future__ import annotations

# Import dataclass support for immutable pool configuration.
from dataclasses import dataclass
# Import operating-system helpers for process-boundary checks and environment configuration.
import os
# Import threading primitives for bounded concurrent checkout and idempotent lease close.
import threading
# Import monotonic time for deadline and low-cardinality wait measurements.
import time
# Import generic callable and connection types without binding core code to mysql.connector classes.
from typing import Any, Callable


# Define the fixed public-safe error raised when every bounded pool slot is busy.
class MySQLPoolExhaustedError(RuntimeError):
    # Keep a named error type so callers and tests never need connector-specific exception text.
    pass


# Define the fixed public-safe error raised when a physical connection cannot be created.
class MySQLPoolConnectionError(RuntimeError):
    # Keep a named error type so connector details remain outside application responses and metrics.
    pass


# Define the fixed public-safe error raised after deliberate pool shutdown.
class MySQLPoolClosedError(RuntimeError):
    # Keep a named error type so shutdown races fail closed without leaking internal state.
    pass


# Define the validated per-process MySQL pool policy.
@dataclass(frozen=True)
class MySQLPoolConfig:
    # Limit simultaneously open physical connections in one application process.
    capacity: int = 16
    # Bound how long one checkout may wait for a busy connection.
    checkout_wait_ms: int = 500
    # Bound how long the connector may spend opening a physical connection.
    connect_timeout_seconds: int = 3

    # Validate every pool policy value before the provider can open a connection.
    def __post_init__(self) -> None:
        # Reject capacities outside the approved one-to-sixty-four process-local range.
        if not 1 <= self.capacity <= 64:
            # Raise a fixed validation message that contains no environment value.
            raise ValueError("MySQL pool capacity must be between 1 and 64.")
        # Reject unbounded or non-positive checkout waits.
        if not 1 <= self.checkout_wait_ms <= 10_000:
            # Raise a fixed validation message that contains no environment value.
            raise ValueError("MySQL pool checkout wait must be between 1 and 10000 milliseconds.")
        # Reject connector timeouts outside a short operational bound.
        if not 1 <= self.connect_timeout_seconds <= 60:
            # Raise a fixed validation message that contains no environment value.
            raise ValueError("MySQL connect timeout must be between 1 and 60 seconds.")

    # Read the three non-secret pool controls from the process environment.
    @classmethod
    def from_env(cls) -> MySQLPoolConfig:
        # Start protected integer parsing so malformed values produce one fixed failure.
        try:
            # Parse the bounded process-local capacity without reading any credential variable.
            capacity = int(os.getenv("CASINO_MYSQL_POOL_SIZE", "16"))
            # Parse the bounded checkout deadline without reading any credential variable.
            checkout_wait_ms = int(os.getenv("CASINO_MYSQL_POOL_WAIT_MS", "500"))
            # Parse the physical connector deadline without reading any credential variable.
            connect_timeout_seconds = int(os.getenv("CASINO_MYSQL_CONNECT_TIMEOUT_SECONDS", "3"))
        # Convert malformed text into a stable secret-free configuration error.
        except (TypeError, ValueError):
            # Avoid echoing the offending environment value.
            raise ValueError("MySQL pool settings must be integers.") from None
        # Return the immutable configuration after range validation.
        return cls(capacity=capacity, checkout_wait_ms=checkout_wait_ms, connect_timeout_seconds=connect_timeout_seconds)


# Define the request-scoped wrapper whose close returns a physical connection to its owning pool.
class MySQLConnectionLease:
    # Store the pool, physical connection, process identity, and pool generation for one checkout.
    def __init__(self, pool: MySQLConnectionPool, connection: Any, owner_pid: int, generation: int) -> None:
        # Retain the pool that owns cleanup and reuse policy.
        self._pool = pool
        # Retain the physical DB-API connection without exposing it in metrics.
        self._connection = connection
        # Bind this lease to the process that acquired the connection.
        self._owner_pid = owner_pid
        # Bind this lease to the pool generation active at checkout.
        self._generation = generation
        # Track connector cursors so the lease can close them before session reset and reuse.
        self._cursors: list[Any] = []
        # Track idempotent close state across repeated finally blocks.
        self._closed = False
        # Serialize same-process duplicate close calls.
        self._close_lock = threading.Lock()

    # Delegate the existing DB-API surface to the physical connection.
    def __getattr__(self, name: str) -> Any:
        # Return connector-owned methods and properties without wrapping transaction semantics.
        return getattr(self._connection, name)

    # Open and track one connector cursor within this request-scoped lease.
    def cursor(self, *args: Any, **kwargs: Any) -> Any:
        # Serialize cursor creation against lease close.
        with self._close_lock:
            # Refuse cursor creation after this request-scoped lease was returned.
            if self._closed:
                # Raise fixed internal text without connector or infrastructure detail.
                raise MySQLPoolClosedError("MySQL connection lease is closed.")
            # Open the connector-owned cursor on the physical session.
            cursor = self._connection.cursor(*args, **kwargs)
            # Retain the cursor so close can end it before session reset and reuse.
            self._cursors.append(cursor)
            # Return the unchanged connector cursor surface to existing storage code.
            return cursor

    # Return this lease from a context-manager entry.
    def __enter__(self) -> MySQLConnectionLease:
        # Preserve the familiar DB-API context-manager shape.
        return self

    # Release this lease on context-manager exit.
    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> bool:
        # Return or discard the connection through the same cleanup path as explicit close.
        self.close()
        # Never suppress an exception from the caller-owned transaction.
        return False

    # Return the physical connection to the pool exactly once.
    def close(self) -> None:
        # Detect a post-fork inherited lease before touching a possibly inherited locked mutex.
        if self._owner_pid != os.getpid():
            # Close the inherited socket directly once because it must never re-enter the child pool.
            if not self._closed:
                # Mark the inherited lease closed before invoking connector code.
                self._closed = True
                # Close the inherited physical connection without surfacing shutdown errors.
                self._pool.close_physical_quietly(self._connection)
            # Finish the child-side close without acquiring the parent-created mutex.
            return
        # Serialize ordinary same-process close calls.
        with self._close_lock:
            # Return immediately when another close already completed.
            if self._closed:
                # Preserve DB-API close idempotency.
                return
            # Mark closed before connector cleanup so a cleanup exception cannot trigger double release.
            self._closed = True
            # Detach every cursor opened during this lease.
            cursors = tuple(self._cursors)
            # Clear tracked references before invoking connector cleanup.
            self._cursors = []
        # Assume every connector cursor closes cleanly.
        cursor_cleanup_failed = False
        # Close each cursor before resetting the physical session.
        for cursor in cursors:
            # Start protected cursor cleanup because uncertain state must discard rather than leak text.
            try:
                # Release result and statement resources owned by this request.
                cursor.close()
            # Convert every cursor cleanup failure into a forced physical discard.
            except Exception:
                # Prevent the uncertain session from re-entering the idle set.
                cursor_cleanup_failed = True
        # Let the pool sanitize, validate, and either reuse or discard the physical connection.
        self._pool.release(self._connection, self._generation, force_discard=cursor_cleanup_failed)


# Define the bounded process-local MySQL physical connection pool.
class MySQLConnectionPool:
    # Keep wait histograms fixed and low-cardinality.
    WAIT_BUCKET_LIMITS_MS = (1, 5, 25, 100, 500)

    # Initialize one lazy pool around a connector factory.
    def __init__(self, factory: Callable[[int], Any], config: MySQLPoolConfig | None = None) -> None:
        # Store the connector factory that accepts only a bounded connection timeout.
        self._factory = factory
        # Store validated non-secret policy derived from explicit config or environment.
        self.config = config or MySQLPoolConfig.from_env()
        # Bind inherited sockets and locks to the current process.
        self._pid = os.getpid()
        # Create the condition that serializes capacity, idle, and waiter state.
        self._condition = threading.Condition(threading.RLock())
        # Store sanitized idle physical connections available for checkout.
        self._idle: list[Any] = []
        # Count physical connections reserved, active, or idle in this generation.
        self._total = 0
        # Count request-scoped leases currently checked out.
        self._in_use = 0
        # Count threads currently waiting at the hard capacity limit.
        self._waiting = 0
        # Advance this generation whenever inherited or closed state is abandoned.
        self._generation = 0
        # Track deliberate shutdown so new checkouts fail closed.
        self._closed = False
        # Initialize fixed low-cardinality counters without any identity or connector text.
        self._metrics = self._new_metrics()

    # Build a fresh sanitized metric set for one process.
    def _new_metrics(self) -> dict[str, Any]:
        # Return fixed counters and fixed wait buckets only.
        return {
            # Count successfully opened physical connections.
            "physical_created": 0,
            # Count successful checkouts from the idle set.
            "reused": 0,
            # Count physical connections removed after failed validation or cleanup.
            "discarded": 0,
            # Count checkouts that encountered the hard capacity limit.
            "wait_count": 0,
            # Count checkouts that reached their bounded deadline.
            "timeout_count": 0,
            # Count returned transactions that required an automatic rollback.
            "rollback_cleanup": 0,
            # Count connector factory failures without preserving exception text or type.
            "connector_error": 0,
            # Count completed waits in fixed public-safe millisecond buckets.
            "wait_buckets_ms": {"le_1": 0, "le_5": 0, "le_25": 0, "le_100": 0, "le_500": 0, "gt_500": 0},
        }

    # Close one connector-owned physical connection without leaking cleanup failures.
    @staticmethod
    def close_physical_quietly(connection: Any) -> None:
        # Start protected close so discard and shutdown remain fail-safe.
        try:
            # Ask the connector to release its socket and session.
            connection.close()
        # Suppress connector-specific cleanup exceptions at this internal boundary.
        except Exception:
            # Keep connector details out of application responses and logs.
            pass

    # Reset inherited synchronization and sockets when a child process first touches the pool.
    def _ensure_process(self) -> None:
        # Return immediately while this pool remains in its creating process.
        if self._pid == os.getpid():
            # Preserve the active process-local condition and connections.
            return
        # Preserve inherited idle connections so their sockets can be closed in the child.
        inherited_idle = tuple(self._idle)
        # Bind subsequent state to the child process.
        self._pid = os.getpid()
        # Replace a potentially inherited locked condition with a fresh child-local condition.
        self._condition = threading.Condition(threading.RLock())
        # Remove every inherited connection from the child pool.
        self._idle = []
        # Reset capacity accounting because active parent leases cannot enter the child generation.
        self._total = 0
        # Reset checked-out accounting for the fresh child generation.
        self._in_use = 0
        # Reset waiter accounting because parent threads do not survive the fork.
        self._waiting = 0
        # Advance the generation so inherited leases close their sockets instead of returning.
        self._generation += 1
        # Permit fresh child-local checkouts even if the parent was shutting down.
        self._closed = False
        # Start fresh process-local metrics that cannot combine parent and child activity.
        self._metrics = self._new_metrics()
        # Close every inherited idle socket outside any inherited synchronization primitive.
        for connection in inherited_idle:
            # Ensure the child never reuses a parent-created MySQL session.
            self.close_physical_quietly(connection)

    # Return whether one physical connection is alive without allowing connector reconnection.
    @staticmethod
    def _is_healthy(connection: Any) -> bool:
        # Start protected ping because a dead socket is an expected discard path.
        try:
            # Require the existing socket to answer without silently replacing the server session.
            connection.ping(reconnect=False, attempts=1, delay=0)
        # Treat every connector failure as an unhealthy connection without retaining its details.
        except Exception:
            # Refuse reuse after any liveness-check failure.
            return False
        # Return healthy only after the non-reconnecting ping succeeds.
        return True

    # Record one completed bounded wait into a fixed low-cardinality histogram.
    def _record_wait_locked(self, elapsed_ms: float) -> None:
        # Walk the fixed bucket limits from narrowest to widest.
        for limit in self.WAIT_BUCKET_LIMITS_MS:
            # Select the first bucket containing the observed wait.
            if elapsed_ms <= limit:
                # Increment the fixed bucket without storing an exact duration.
                self._metrics["wait_buckets_ms"][f"le_{limit}"] += 1
                # Stop after assigning exactly one bucket.
                return
        # Count waits beyond the final fixed boundary without recording the exact value.
        self._metrics["wait_buckets_ms"]["gt_500"] += 1

    # Acquire one request-scoped lease under the hard process-local capacity.
    def acquire(self, connect_timeout_seconds: int | None = None) -> MySQLConnectionLease:
        # Rebuild child-local synchronization before touching capacity state.
        self._ensure_process()
        # Use the configured physical deadline unless the established provider seam supplies one.
        physical_timeout = self.config.connect_timeout_seconds if connect_timeout_seconds is None else connect_timeout_seconds
        # Reject caller overrides outside the same short bounded connector range.
        if not isinstance(physical_timeout, int) or not 1 <= physical_timeout <= 60:
            # Raise a fixed validation error without echoing the caller value.
            raise ValueError("MySQL connect timeout must be between 1 and 60 seconds.")
        # Capture one monotonic start for the checkout deadline and wait histogram.
        started_at = time.monotonic()
        # Convert the bounded policy into one absolute monotonic deadline.
        deadline = started_at + (self.config.checkout_wait_ms / 1000.0)
        # Track whether this checkout ever encountered full capacity.
        waited = False
        # Retry after wakeups and unhealthy-idle discards until success or deadline.
        while True:
            # Serialize capacity inspection, reservations, and waiter state.
            with self._condition:
                # Refuse new work after deliberate shutdown.
                if self._closed:
                    # Raise a fixed error that exposes no pool internals.
                    raise MySQLPoolClosedError("MySQL connection pool is closed.")
                # Inspect idle connections before reserving a new physical slot.
                while self._idle:
                    # Remove one idle connection while capacity accounting remains reserved.
                    connection = self._idle.pop()
                    # Reuse only after a non-reconnecting liveness check.
                    if self._is_healthy(connection):
                        # Count the request-scoped lease now holding the existing physical connection.
                        self._in_use += 1
                        # Count successful idle reuse.
                        self._metrics["reused"] += 1
                        # Record one fixed wait bucket when this checkout previously blocked.
                        if waited:
                            # Store only the bounded bucket, never an exact request timestamp.
                            self._record_wait_locked((time.monotonic() - started_at) * 1000.0)
                        # Return a lease bound to the current process and pool generation.
                        return MySQLConnectionLease(self, connection, self._pid, self._generation)
                    # Remove the dead physical connection from capacity accounting.
                    self._total -= 1
                    # Count the secret-free discard reason as one aggregate.
                    self._metrics["discarded"] += 1
                    # Close the dead socket before considering a replacement.
                    self.close_physical_quietly(connection)
                # Reserve one physical slot when the hard capacity permits creation.
                if self._total < self.config.capacity:
                    # Count the reservation immediately so concurrent creators cannot exceed capacity.
                    self._total += 1
                    # Preserve the generation owning this reservation.
                    generation = self._generation
                    # Leave the condition before performing connector I/O.
                    break
                # Calculate the remaining bounded wait.
                remaining = deadline - time.monotonic()
                # Fail closed once no checkout time remains.
                if remaining <= 0:
                    # Count the bounded exhaustion without recording request identity or pool configuration.
                    self._metrics["timeout_count"] += 1
                    # Raise a fixed error with no connector or infrastructure detail.
                    raise MySQLPoolExhaustedError("MySQL connection pool checkout timed out.")
                # Count one waiter encounter per checkout rather than per spurious wakeup.
                if not waited:
                    # Mark this checkout as having encountered full capacity.
                    waited = True
                    # Count the low-cardinality capacity wait event.
                    self._metrics["wait_count"] += 1
                # Publish the current waiter gauge while this thread sleeps.
                self._waiting += 1
                # Start protected waiting so the gauge is restored after wakeup or interruption.
                try:
                    # Release the condition until a return, discard, shutdown, or timeout notifies it.
                    self._condition.wait(timeout=remaining)
                # Always remove this thread from the waiter gauge.
                finally:
                    # Restore exact current waiter accounting.
                    self._waiting -= 1
        # Start protected physical creation after reserving one hard-capacity slot.
        try:
            # Open one physical connection using only the validated bounded timeout.
            connection = self._factory(physical_timeout)
        # Convert every connector-specific failure into one fixed internal error.
        except Exception:
            # Re-enter capacity accounting to release the failed reservation.
            with self._condition:
                # Release only when shutdown or process reset has not replaced this generation.
                if generation == self._generation and self._total > 0:
                    # Return the failed reservation to capacity.
                    self._total -= 1
                    # Count the aggregate connector failure without exception text or type.
                    self._metrics["connector_error"] += 1
                    # Wake one waiter that may now reserve the released slot.
                    self._condition.notify()
            # Raise a stable secret-free error and suppress connector exception chaining.
            raise MySQLPoolConnectionError("MySQL physical connection could not be created.") from None
        # Publish the created physical connection under the reservation's generation.
        with self._condition:
            # Discard a connection created concurrently with shutdown or generation replacement.
            if self._closed or generation != self._generation:
                # Close the orphaned physical connection immediately.
                self.close_physical_quietly(connection)
                # Raise the stable shutdown error.
                raise MySQLPoolClosedError("MySQL connection pool is closed.")
            # Count the request-scoped lease now holding the newly created connection.
            self._in_use += 1
            # Count successful physical creation.
            self._metrics["physical_created"] += 1
            # Record one fixed wait bucket when this checkout previously blocked.
            if waited:
                # Store only the bounded bucket, never an exact request timestamp.
                self._record_wait_locked((time.monotonic() - started_at) * 1000.0)
            # Return a lease bound to the current process and pool generation.
            return MySQLConnectionLease(self, connection, self._pid, self._generation)

    # Sanitize and return one physical connection after request-scoped use.
    def release(self, connection: Any, generation: int, force_discard: bool = False) -> None:
        # Close a connection directly when this pool has moved to another process.
        if self._pid != os.getpid():
            # Prevent parent-created sessions from crossing a process boundary.
            self.close_physical_quietly(connection)
            # Finish without touching inherited synchronization.
            return
        # Check whether this lease still belongs to an active pool generation.
        with self._condition:
            # Discard leases from shutdown or replaced generations.
            if self._closed or generation != self._generation:
                # Close the stale physical connection.
                self.close_physical_quietly(connection)
                # Finish without changing current-generation counters.
                return
        # Track whether cleanup had to roll back an unfinished transaction.
        rolled_back = False
        # Start reusable only when request-owned cursor cleanup was complete.
        reusable = not force_discard
        # Start protected transaction and session cleanup.
        try:
            # Roll back only when the connector reports an active transaction.
            if bool(getattr(connection, "in_transaction", False)):
                # End the caller-abandoned transaction before reuse.
                connection.rollback()
                # Record that rollback cleanup occurred after the lock is reacquired.
                rolled_back = True
            # Reset and validate only when cursor cleanup left the session eligible for reuse.
            if reusable:
                # Clear connector session variables, temporary state, and transaction attributes.
                connection.reset_session()
                # Require the same physical session to answer after cleanup.
                reusable = self._is_healthy(connection)
        # Discard on every connector cleanup failure.
        except Exception:
            # Prevent any uncertain session state from re-entering the idle set.
            reusable = False
        # Publish cleanup and capacity changes atomically.
        with self._condition:
            # Close directly when shutdown raced with cleanup.
            if self._closed or generation != self._generation:
                # Close the now-stale physical session.
                self.close_physical_quietly(connection)
                # Finish without changing current-generation counters.
                return
            # Remove this request-scoped lease from the active gauge.
            self._in_use -= 1
            # Count automatic rollback cleanup without transaction identity.
            if rolled_back:
                # Increment the aggregate rollback-cleanup counter.
                self._metrics["rollback_cleanup"] += 1
            # Return only fully sanitized and healthy sessions to the idle set.
            if reusable:
                # Make the physical connection available for a future checkout.
                self._idle.append(connection)
            # Discard every uncertain or unhealthy physical session.
            else:
                # Remove the discarded session from hard-capacity accounting.
                self._total -= 1
                # Count the aggregate discard without connector detail.
                self._metrics["discarded"] += 1
                # Close the physical socket before releasing capacity.
                self.close_physical_quietly(connection)
            # Wake one bounded waiter after a return or discard.
            self._condition.notify()

    # Return a secret-free instantaneous pool snapshot for internal evidence.
    def snapshot(self) -> dict[str, Any]:
        # Rebuild child-local state before reading metrics.
        self._ensure_process()
        # Serialize gauges and counters under the same condition as checkout.
        with self._condition:
            # Copy the fixed bucket map so callers cannot mutate pool state.
            wait_buckets = dict(self._metrics["wait_buckets_ms"])
            # Return only low-cardinality numeric policy, gauges, counters, and fixed buckets.
            return {
                # Report the configured hard capacity.
                "capacity": self.config.capacity,
                # Report current request-scoped leases.
                "in_use": self._in_use,
                # Report currently reusable physical sessions.
                "idle": len(self._idle),
                # Report threads currently waiting at capacity.
                "waiting": self._waiting,
                # Report successful physical connection creations.
                "physical_created": self._metrics["physical_created"],
                # Report successful idle reuse.
                "reused": self._metrics["reused"],
                # Report health or cleanup discards.
                "discarded": self._metrics["discarded"],
                # Report checkouts that encountered capacity.
                "wait_count": self._metrics["wait_count"],
                # Publish the same capacity-encounter counter under its operator-facing saturation name.
                "saturation_count": self._metrics["wait_count"],
                # Report bounded checkout timeouts.
                "timeout_count": self._metrics["timeout_count"],
                # Report automatic rollback cleanups.
                "rollback_cleanup": self._metrics["rollback_cleanup"],
                # Report connector creation failures without error detail.
                "connector_error": self._metrics["connector_error"],
                # Report the copied fixed wait histogram.
                "wait_buckets_ms": wait_buckets,
            }

    # Close every idle physical connection and make future checkouts fail closed.
    def close_all(self) -> None:
        # Rebuild child-local state before deliberate shutdown.
        self._ensure_process()
        # Serialize shutdown against checkout, return, and waiting threads.
        with self._condition:
            # Preserve idle connections for close after removing them from reusable state.
            idle_connections = tuple(self._idle)
            # Remove every idle session immediately.
            self._idle = []
            # Mark future checkouts closed before waking waiters.
            self._closed = True
            # Advance the generation so active leases close directly when returned.
            self._generation += 1
            # Reset current-generation capacity accounting.
            self._total = 0
            # Reset current-generation in-use accounting because outstanding leases are now stale.
            self._in_use = 0
            # Wake every waiter so it observes the closed state.
            self._condition.notify_all()
        # Close idle sockets outside the pool condition.
        for connection in idle_connections:
            # Release each connector session without surfacing shutdown failures.
            self.close_physical_quietly(connection)
