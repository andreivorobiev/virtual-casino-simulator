# PostgreSQL migrations and DDL-free runtime gate

Requirements `STORAGE-022`, `STORAGE-026`, `TEST-254`, and `TEST-258` define the repository's PostgreSQL 16 schema boundary. The migration runner is limited to a newly created, explicitly authorized, loopback-only target: either an issue-owned disposable test target or the one-time empty production bootstrap described in [`oci_postgres_preview.md`](oci_postgres_preview.md). It is never an upgrade, adoption, repair, or startup migration tool.

## Immutable schema catalog

`migrations/postgres/catalog.json` is the only executable PostgreSQL catalog. It declares `apply_policy=guarded-empty-target-only`, minimum runtime version 5, expected version 5, and five contiguous checksum-bound JSON descriptors:

1. `0001_initial.json` — `initial-storage-schema`
2. `0002_action_identity.json` — `ledger-action-identity`
3. `0003_game_action_receipts.json` — `game-action-receipts`
4. `0004_game_action_claims.json` — `game-action-claims`
5. `0005_first_class_sessions.json` — `first-class-sessions`

The loader validates catalog shape, contiguous versions, stable names, exact descriptor bytes and SHA-256 checksums, and PostgreSQL statement form, then computes the complete chain digest before reading migration environment or importing the optional driver. Descriptors use PostgreSQL 16 identity columns, `JSONB`, constraints, explicit indexes, `ON CONFLICT`, `RETURNING`, and row locks. The runner passes each fixed descriptor statement directly to the driver and does not accept arbitrary SQL or repair commands.

## Separate migration authority

The runner reads only this deployment-owned namespace:

```text
CASINO_POSTGRES_MIGRATION_HOST=127.0.0.1
CASINO_POSTGRES_MIGRATION_PORT=<disposable-port>
CASINO_POSTGRES_MIGRATION_USER=<name-ending-in-_1057>
CASINO_POSTGRES_MIGRATION_PASSWORD=<migration-secret>
CASINO_POSTGRES_MIGRATION_DATABASE=<name-ending-in-_1057>
CASINO_POSTGRES_MIGRATION_TARGET_BINDING_KEY=<independent-secret-at-least-32-UTF-8-bytes>
CASINO_POSTGRES_MIGRATION_DISPOSABLE=CASINO-POSTGRES-1057-DISPOSABLE
```

Every value is required except the port, which defaults to 5432. Before connector import or access, the public boundary requires literal host `127.0.0.1`, a valid TCP port, bounded lowercase role and database identifiers ending in `_1057`, the exact disposable marker, a non-empty migration password, and a separate target-binding key of at least 32 UTF-8 bytes. The key must not equal the password.

The target binding is an HMAC over normalized endpoint and database identity; raw target values are not persisted in migration state. Never store migration configuration in the application environment, pass secrets on the command line, or place them in Git, artifacts, logs, screenshots, issues, pull requests, or evidence reports. Remove the variables after the command completes.

The production mode is mutually exclusive with the disposable marker and additionally requires:

```text
CASINO_POSTGRES_MIGRATION_USER=casino_migrate
CASINO_POSTGRES_MIGRATION_DATABASE=virtual_casino
CASINO_POSTGRES_MIGRATION_PRODUCTION=CASINO-POSTGRES-1078-NEW-PRODUCTION
CASINO_POSTGRES_MIGRATION_RELEASE_SHA=<lowercase-40-hex-release-commit>
```

Production `apply` also requires `--release-manifest <verified-release-manifest.json>`. The manifest's source commit must exactly match `CASINO_POSTGRES_MIGRATION_RELEASE_SHA` before the connector is imported. The connected role must have no superuser, role-creation, database-creation, replication, or row-security-bypass powers. The target must have no migration controls and no table of any name; an initialized, partially initialized, foreign, dirty, or upgraded target fails closed.

## Commands

Run the tool only from an immutable verified source tree with the disposable variables loaded transiently:

```text
python scripts/postgres_migrate.py status
python scripts/postgres_migrate.py check
python scripts/postgres_migrate.py dry-run
python scripts/postgres_migrate.py apply
python scripts/postgres_migrate.py apply --release-manifest /root/release-manifest.json
```

`status` inspects target-bound metadata with `SELECT` statements and reports only finite state, numeric versions, catalog identity, and apply policy. `check` requires a clean compatible schema and the exact keyed target binding. `dry-run` returns the immutable pending descriptor identities without schema mutation. All three roll back their read-only transaction.

`apply` is available only after the complete target guard. Disposable mode preserves the `_1057` identity and exact marker boundary. Production mode is one-shot and empty-target-only. Both modes obtain a target-scoped PostgreSQL session advisory lock, initialize the two control tables only on an empty target, write a committed `applying` marker before each descriptor, apply each descriptor in its own transaction, record its exact checksum, and return the state to `clean`. A descriptor failure rolls back its DDL transaction and records the exact dirty version; subsequent execution fails closed and requires a separately reviewed forward-fix packet. Lock release is verified before success.

All CLI output is sanitized JSON. It excludes target values, credentials, binding keys, paths, SQL, and connector messages. Unexpected connector failures collapse to one fixed diagnostic.

## Runtime compatibility

Ordinary application runtime does not use `MigrationConfig` and never reads migration credentials, the HMAC key, disposable marker, or migration environment. Its separate `verify_runtime_compatibility(connection)` function performs only checksum-bound reads and requires exact initialized, clean schema version 5. It verifies both control tables, a contiguous applied 1–5 prefix, exact names and checksums, the chain digest, a finite state, and a canonical opaque target binding.

Incomplete control metadata, missing state, unversioned application tables, gaps, foreign checksums, a malformed digest, future versions, dirty or applying state, and any version other than 5 fail closed. The runtime never creates metadata, applies a migration, repairs history, or changes schema.

## Disposable proof and cleanup

The migration live test runs only when both of these explicit inputs are present:

```text
CASINO_POSTGRES_TEST_BIN=<official-PostgreSQL-16-bin-directory>
CASINO_POSTGRES_LIVE_TEST=CASINO-POSTGRES-1057-LIVE
```

It creates a new private cluster, selects a temporary loopback port, creates synthetic `_1057` role and database identities, applies versions 1–5, exercises PostgreSQL identity, `JSONB`, `ON CONFLICT`, `RETURNING`, constraints, row-lock contention, dict-row runtime readiness, and restart, then removes the database, role, process, listener, and temporary root. The marker is test authorization, not a general migration switch. Never use this helper with an existing target.

Provider, session, and game-action live tests use separate exact markers documented in [`local_postgres_setup.md`](local_postgres_setup.md); do not substitute or globally combine them.

## Upgrade and rollback boundary

The catalog is forward-only and currently accepts exactly clean schema 5 at runtime. There is no down migration, checksum override, mark-applied command, arbitrary repair path, or automatic startup migration. Do not edit control rows, reverse descriptor DDL, or restore over an active target.

If a migration becomes dirty or interrupted, preserve its evidence and deliver an explicit forward fix. Repointing an older application is allowed only when that immutable release explicitly accepts the applied PostgreSQL version. Production bootstrap, privilege separation, backup/restore, and stop/rollback operations are restricted to the reviewed issue #1078 runbook. Any later schema transition or repair requires a new reviewed forward-fix packet; this runner will not adopt or upgrade the initialized target.
