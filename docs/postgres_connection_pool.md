# PostgreSQL connection lifecycle

Requirement `STORAGE-021` defines one lazy, bounded PostgreSQL connection pool per application process. The pool is connector-neutral; the explicitly selected PostgreSQL provider supplies the `psycopg` adapter and connection factory. Constructing the pool opens no connection.

## Lease lifecycle

Each storage operation checks out one request-scoped lease. Closing the lease closes its cursors, rolls back any non-idle transaction, resets reviewed session state, performs a non-reconnecting wire health check, and then returns the same healthy physical connection to the process-local idle set.

An unhealthy connection, failed cursor cleanup, failed rollback, failed reset, failed health check, or uncertain transaction state is closed and removed from capacity. The pool never silently reconnects an idle lease. Native connector failures cross the provider boundary only through fixed secret-free error categories; connector messages, target values, queries, credentials, and exception text are not published in pool evidence.

## Configuration

| Variable | Default | Accepted range | Meaning |
| --- | ---: | ---: | --- |
| `CASINO_POSTGRES_POOL_SIZE` | `16` | `1`–`64` | Maximum physical connections per application process |
| `CASINO_POSTGRES_POOL_WAIT_MS` | `500` | `1`–`10000` | Maximum checkout wait in milliseconds |
| `CASINO_POSTGRES_CONNECT_TIMEOUT_SECONDS` | `3` | `1`–`60` | Physical connection establishment deadline in seconds |

Malformed or out-of-range controls fail before connector access. These non-secret controls do not replace the runtime host, port, role, password, or database settings in [`local_postgres_setup.md`](local_postgres_setup.md).

Capacity is per process, not global. A deployment's theoretical physical-session ceiling is `application processes × CASINO_POSTGRES_POOL_SIZE`, so increasing either dimension requires an explicit target capacity review. When every slot is reserved, a checkout waits only until its monotonic deadline and then fails closed. There is no unbounded queue or retry loop.

## Process and shutdown boundaries

The pool compares its creating process identity before checkout and snapshot operations. A forked child discards inherited idle sockets, installs fresh child-owned synchronization and counters, advances its generation, and creates only child-owned physical sessions. An inherited active lease closes its socket instead of returning it to the child's pool.

`close_all()` makes the pool terminal, wakes current waiters, closes idle sessions, and causes later checkouts to fail closed. Active leases from the retired generation close rather than re-entering reusable state. A physical connection returned after a failed or closed lifecycle is discarded.

## Bounded evidence

The internal snapshot contains only fixed policy, gauges, counters, and wait buckets:

- capacity, in-use, idle, and waiting;
- physical-created, reused, discarded, wait/saturation, timeout, cleanup-rollback, and connector-error counts;
- wait buckets at 1, 5, 25, 100, and 500 milliseconds plus one greater-than bucket.

The snapshot contains no target, role, database, password, SQL, route, player, session, request, free-form label, or native exception. This documentation does not claim a new public API or Admin metric surface.

## Validation and operations

`TEST-253` proves capacity, wait/deadline behavior, lease cleanup ordering, physical-session reuse, failure discard, concurrent idempotent close, fork isolation, shutdown, late factory cleanup, and secret-free evidence with deterministic fakes. The explicit PostgreSQL 16 provider validation then proves the accepted provider and pool together on a fresh loopback-only target.

Keep the default capacity unless target measurements justify a change. A checkout timeout or connector error is an operational failure to investigate; do not hide it by increasing limits or adding retries. Pool changes do not authorize schema DDL, target provisioning, migration, production deployment, or database rollback.
