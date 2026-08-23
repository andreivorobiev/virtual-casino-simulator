# Local PostgreSQL 16 setup

Requirements `STORAGE-020` through `STORAGE-024` and evidence records `TEST-252` through `TEST-256` define the optional PostgreSQL source boundary. PostgreSQL is never selected implicitly: JSON remains the default when `CASINO_STORAGE_PROVIDER` is absent, MySQL remains unchanged, and only the explicit value `postgres` loads the PostgreSQL provider and its optional driver.

This guide is for a private loopback PostgreSQL 16 target containing synthetic local data. It does not authorize a production database, cloud service, remote listener, firewall change, migration of existing data, release, or deployment. The ordinary application and migration runner do not install PostgreSQL or provision accounts and grants.

## Install the optional driver

Use an isolated Python environment and install the supported optional dependency from the checked-out source:

```text
python -m pip install -e ".[postgres]"
```

The dependency is `psycopg` 3. JSON and MySQL startup do not import it. An explicit PostgreSQL selection with the dependency absent fails through a fixed diagnostic rather than falling back to another provider.

Install PostgreSQL 16 from its official distribution outside the repository. Bind a local developer instance to `127.0.0.1`; do not expose port 5432 through an inbound firewall rule. Keep its data directory, logs, environment files, and credentials outside Git and outside deployment artifacts.

## Separate identities

Use distinct administrator, migration, and runtime roles. The migration role and its target-binding key are transient inputs to the disposable migration runner described in [`postgres_migrations.md`](postgres_migrations.md). They must not enter the application environment.

The runtime role should have only the DML privileges needed by the accepted schema-five tables. It should have no role-management, database-creation, schema-creation, DDL, grant-management, replication, or superuser authority. Grant design and account provisioning remain operator-owned; the repository runner does not create a production role or grant packet.

Generate a strong runtime password and store it in a current-user-only secret location outside the checkout. Never pass it as a command-line argument, paste it into issue or pull-request text, or include it in logs, screenshots, test artifacts, or tracked environment files.

## Runtime configuration

Load runtime variables only into the process that starts the application:

```text
CASINO_STORAGE_PROVIDER=postgres
CASINO_POSTGRES_HOST=127.0.0.1
CASINO_POSTGRES_PORT=5432
CASINO_POSTGRES_USER=<runtime-role>
CASINO_POSTGRES_PASSWORD=<runtime-secret>
CASINO_POSTGRES_DATABASE=<runtime-database>
CASINO_POSTGRES_POOL_SIZE=16
CASINO_POSTGRES_POOL_WAIT_MS=500
CASINO_POSTGRES_CONNECT_TIMEOUT_SECONDS=3
```

The source defaults are host `127.0.0.1`, port `5432`, user `casino`, database `virtual_casino`, pool size `16`, checkout wait `500` milliseconds, and connect timeout `3` seconds. Host, user, and database must be non-empty; the TCP port must be from 1 through 65535. The configuration parser accepts a password string, including the empty default, but a real local target should always use an explicitly provisioned secret.

Pool size accepts 1–64, checkout wait accepts 1–10000 milliseconds, and connect timeout accepts 1–60 seconds. Malformed configuration fails before connector access with fixed value-free diagnostics. See [`postgres_connection_pool.md`](postgres_connection_pool.md) before changing the defaults.

## Schema readiness

The application does not create, alter, repair, or migrate PostgreSQL schema. On the first provider use, its read-only readiness gate requires:

- both migration-control tables with no partial metadata boundary;
- exact clean schema version 5;
- a contiguous immutable version 1–5 history whose checksums match the packaged catalog;
- a valid finite migration state with no applying or dirty version.

Missing metadata, partial metadata, unversioned application tables, gaps, checksum drift, a foreign or future version, and dirty or applying state fail closed before application traffic. The runtime verifier does not read migration credentials, the target-binding key, the disposable marker, or migration environment variables.

## Local validation boundary

Repository PostgreSQL live tests are destructive only to targets they create themselves. Each requires the exact lane-specific authorization marker and `CASINO_POSTGRES_TEST_BIN` pointing at an explicit PostgreSQL 16 binary directory:

| Test | Exact authorization |
| --- | --- |
| `tests/postgres_migration_live.py` | `CASINO_POSTGRES_LIVE_TEST=CASINO-POSTGRES-1057-LIVE` |
| `tests/postgres_provider_live.py` | `CASINO_POSTGRES_LIVE_TEST=CASINO-POSTGRES-1058-LIVE` |
| Native session case, inner gate | `CASINO_POSTGRES_SESSION_LIVE=CASINO-POSTGRES-1058-SESSION-LIVE` |
| `tests/postgres_game_action_live.py` | `CASINO_POSTGRES_GAME_ACTION_LIVE=CASINO-POSTGRES-1059-LIVE` |

These are separate invocations; the reused `CASINO_POSTGRES_LIVE_TEST` name deliberately has a different exact value for the migration and provider lanes. Do not invent a shared alias or set every marker globally.

The native session case is not a standalone `SESSION_LIVE` plus `TEST_BIN` command. Its test-only environment has two layers:

- `CASINO_POSTGRES_SESSION_MANAGED_LIVE=CASINO-POSTGRES-1058-MANAGED-LIVE` selects the outer self-managed runner when `tests/postgres_session_provider_tests.py` is executed directly. Direct managed execution also needs the inner `CASINO_POSTGRES_SESSION_LIVE` value shown above, `CASINO_POSTGRES_LIVE_TEST=CASINO-POSTGRES-1057-LIVE` for the reused migration helper, and `CASINO_POSTGRES_TEST_BIN`.
- The outer runner creates the disposable cluster and schema before injecting `CASINO_POSTGRES_SESSION_HOST`, `CASINO_POSTGRES_SESSION_PORT`, `CASINO_POSTGRES_SESSION_USER`, `CASINO_POSTGRES_SESSION_PASSWORD`, and `CASINO_POSTGRES_SESSION_DATABASE` for the inner native-session case. These five values are ephemeral test internals, not operator runtime configuration, and must never be copied into the application's `CASINO_POSTGRES_*` runtime namespace.
- The central managed storage callback calls the same outer lifecycle directly instead of using `SESSION_MANAGED_LIVE`; it supplies the inner session and migration markers temporarily, while the lifecycle supplies the generated target values. It restores or removes every marker and generated target value after success or failure.

The live helpers create a fresh loopback-only cluster, synthetic issue-suffixed identities, and a temporary data root, then verify process, listener, role, database, pool, and filesystem cleanup. Never point them at an existing database. Successful source evidence is recorded in the rollout comments for [registration](https://github.com/andreivorobiev/virtual-casino-simulator/issues/1055#issuecomment-5382985428), [pooling](https://github.com/andreivorobiev/virtual-casino-simulator/issues/1056#issuecomment-5383101536), [migrations](https://github.com/andreivorobiev/virtual-casino-simulator/issues/1057#issuecomment-5383248847), [provider/session storage](https://github.com/andreivorobiev/virtual-casino-simulator/issues/1058#issuecomment-5383419007), and [game actions](https://github.com/andreivorobiev/virtual-casino-simulator/issues/1059#issuecomment-5383505517).

## Shutdown and rollback

Normal application shutdown calls the provider pool close boundary, wakes bounded waiters, closes idle physical sessions, and prevents new checkouts. Before deleting any disposable target, stop the application and confirm no PostgreSQL process or listener from the test remains.

PostgreSQL migrations are forward-only. Do not edit migration history, run an ad hoc down migration, restore over an active source, or repoint an older application unless its own immutable manifest accepts the already-applied schema. A PostgreSQL application rollback therefore requires a separately reviewed release and recovery packet; this source documentation performs no rollback or target mutation.
