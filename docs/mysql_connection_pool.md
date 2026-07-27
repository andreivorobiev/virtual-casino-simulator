# MySQL connection lifecycle

Requirement `STORAGE-010` replaces one physical MySQL connection per storage operation with one
lazy, bounded pool per application process. The JSON provider, MySQL schema, migration ownership,
runtime grants, transaction statements, and application rollback boundary do not change.

## Process and request boundaries

The production service currently runs one Gunicorn `gthread` worker with two threads, so each
process defaults to two physical MySQL slots. A storage operation receives a request-scoped lease.
Calling the existing `connection.close()` seam does not close a healthy socket immediately; it
closes request-owned cursors, rolls back an unfinished transaction, resets connector session state,
performs a non-reconnecting liveness check, and returns the physical connection to that process's
idle set.

An unhealthy connection, failed reset, or failed cleanup is closed and removed from capacity. An
idle connection is reused only after `ping(reconnect=False, attempts=1, delay=0)` succeeds. The
pool never lets the connector silently replace an idle session. When every slot is in use, checkout
waits only to its configured deadline and then fails with fixed internal text. Connector exception
text is not copied into application errors or pool evidence.

The pool compares its creating PID before every checkout and metric snapshot. A forked child closes
inherited idle sockets, creates fresh synchronization state, resets its counters, and opens only
child-owned physical sessions. A lease inherited across a fork closes its socket directly instead
of returning it to the child's pool. Provider replacement in tests and process exit close cached
idle sessions; `close_all()` wakes waiters and makes later checkout fail closed.

## Configuration

Only these non-secret controls are added:

| Variable | Default | Accepted range | Meaning |
| --- | ---: | ---: | --- |
| `CASINO_MYSQL_POOL_SIZE` | `2` | `1`–`16` | Maximum physical connections per application process |
| `CASINO_MYSQL_POOL_WAIT_MS` | `500` | `1`–`10000` | Maximum checkout wait in milliseconds |
| `CASINO_MYSQL_CONNECT_TIMEOUT_SECONDS` | `3` | `1`–`60` | Physical connection establishment deadline |

Malformed or out-of-range values stop provider construction before a connector call. These controls
do not replace `CASINO_MYSQL_HOST`, port, database, user, or password. Credential and target values
remain private runtime configuration and are never included in metrics or errors.

Capacity is per process, not global. The total possible physical connection count is therefore
`worker processes × CASINO_MYSQL_POOL_SIZE`. Worker-count or thread-count tuning must account for
the database connection budget and remains outside this change.

## Internal observability

The first Package B observability seam is intentionally internal and testable. It exposes only:

- capacity, in-use, idle, and waiting gauges;
- physical-created, reused, discarded, wait, timeout, rollback-cleanup, and connector-error
  counters;
- fixed checkout-wait buckets at 1, 5, 25, 100, and 500 milliseconds plus one greater-than bucket.

It has no player, account, user, session, request, query, route, host, network, database, credential,
exception, or free-form error labels. No public Operations or readiness contract changes in this
slice.

## Measurement and acceptance

`TEST-141` runs the same bounded constant operation at concurrency 1, 2, 4, and 8. The listener-free
fake-connector suite proves capacity and lifecycle deterministically. The existing disposable MySQL
8.4 migration matrix runs the live packet through `MySQLStorageProvider`, verifies that connector
session state does not cross lease boundaries, and emits only aggregate p50, p95, throughput, error
count, and the fixed pool snapshot.

Acceptance requires:

- warm concurrency-1 p50 at or below 100 ms and p95 at or below 200 ms;
- concurrency-4 p95 at or below 250 ms;
- throughput above the recorded 3.37 requests/second floor at every measured level;
- zero measurement errors and zero checkout timeouts;
- physical connection creation bounded by the configured capacity;
- no in-use lease or waiter residue after the packet.

The live gate uses only the disposable workflow database. It does not target production or user
data, open a browser or public listener, change schema, or tune Gunicorn. Package A edge timing can
be correlated with these low-cardinality storage aggregates during a separately authorized
production observation; raw request identity remains excluded.

## Rollback and operations

This is an application-only lifecycle change over unchanged MySQL schema version 2. Database
rollback remains prohibited. The retained immutable predecessor remains the rollback target for a
release containing this change. A deployment must preserve existing provider, private-access,
readiness, monitoring, and rollback gates; this repository change performs no host or provider
mutation.
