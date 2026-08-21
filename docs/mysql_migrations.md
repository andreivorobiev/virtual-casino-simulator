# MySQL migration and DDL-free runtime gate

Requirements `MYSQL-005`, `MYSQL-008`, `MYSQL-009`, `MYSQL-010`, `STORAGE-007`, `STORAGE-013`, `STORAGE-019`, `TEST-048`, `TEST-174`, and `TEST-250` define the repository-side MySQL schema boundary for restricted preview. This packet does not connect to or mutate an existing database, VM, service environment, backup, provider, listener, DNS, TLS, firewall, or deployment.

## Canonical schema contract

`migrations/mysql/catalog.json` is the only executable schema catalog. It lists contiguous immutable JSON migration files and their exact SHA-256 checksums. Each JSON `statements` element is passed to the driver as one statement; the runner never splits SQL on semicolons or accepts client `DELIMITER` directives.

The bridge catalog declares expected migration version `5`, minimum runtime version `2`, and exact `apply_policy=held`. Runtime accepts only initialized clean schema `2`, `3`, `4`, or `5` with the exact checksum-bound migration prefix for that version. Exact clean schema `4` adds inert game-action claim, receipt, and reset-epoch capacity; schemas `4` and `5` are lifecycle eligible while schemas `2` and `3` remain ineligible. Schema `5` adds indexed first-class session rows and retires the per-session compatibility-document prefix after backfill. Schema `1`, future versions, dirty or applying state, gaps, foreign checksums, and an invalid prefix digest fail closed. This migration version is independent of the application version and the JSON document `SCHEMA_VERSION`. Release packaging includes the catalog and migrations, recomputes every checksum, and writes `mysql_schema.expected_version`, `minimum_version`, `apply_policy`, `catalog_sha256`, and `migration_chain_sha256` into `release-manifest.json`.

## Identity and environment boundary

The deployed schema-two application identity remains unchanged and receives no `CREATE`, `ALTER`, `DROP`, `INDEX`, `TRIGGER`, `GRANT OPTION`, account-management, or global privileges. The dormant schema-four design limits claim and receipt tables to `SELECT` plus `INSERT` and limits the singleton reset-epoch table to `SELECT` plus `UPDATE`. The dormant schema-five design grants the mutable `casino_sessions` table only the runtime `SELECT`, `INSERT`, `UPDATE`, and `DELETE` operations its lifecycle requires. Those table grants require a separately governed migration and grant packet and are not applied by this change. Runtime startup reads migration state and applied checksums, requires an exact clean compatible version, and performs no schema DDL or migration-state DML.

The deployment-only runner reads a distinct transient environment:

```text
CASINO_MYSQL_MIGRATION_HOST=<external value>
CASINO_MYSQL_MIGRATION_PORT=<external value>
CASINO_MYSQL_MIGRATION_USER=<deployment-only identity>
CASINO_MYSQL_MIGRATION_PASSWORD=<external secret>
CASINO_MYSQL_MIGRATION_DATABASE=<external value>
CASINO_MYSQL_MIGRATION_TARGET_BINDING_KEY=<independent high-entropy external secret>
```

The binding key must contain at least 32 UTF-8 bytes and must not equal the migration password. It and the migration credentials must be loaded only for the migration command, then removed from the operator session. They must never appear in the application environment file, systemd unit, process arguments, proof file, release artifact, logs, screenshots, issue or PR text, or test output. The tracked service template explicitly unsets all migration-prefixed variables after loading its runtime environment file.

## Backup and clean-restore proof

Any pending apply, including the first migration metadata DDL on an empty target, requires an external `casino-mysql-backup-restore-proof-v1` JSON record. `status` and `check` never require this proof. `dry-run` validates it when work is pending but remains database-read-only.

The proof contains only keyed or checksum identities:

- `target_hmac_sha256` binds normalized target identity using the external binding key; the target values are not persisted;
- `pre_migration` binds the exact version, finite status, and a structural digest covering columns, indexes, engines, collations, constraints, foreign keys, and migration history/state;
- `plan` binds the exact from/to versions and complete immutable migration chain;
- `quiesce` binds the target, pre-state, plan, and quiesced timestamp and declares that the source remains quiesced;
- `backup` binds a completed off-instance artifact by SHA-256 and completion timestamp;
- `restore` binds a successful clean-target restore to that exact artifact and structural digest;
- `proof_hmac_sha256` integrity-protects the complete canonical proof except for the HMAC field itself.

The timestamps must satisfy `quiesced <= backup completed <= restore verified <= apply time <= expiry`, and expiry may be no more than four hours after restore verification. The source must remain quiesced from the recorded boundary until apply completes or fails. Editing any proof section invalidates the complete-proof HMAC. A changed quiesce record also invalidates its separate target/state/plan-bound HMAC.

Issue #205 owns producing an accepted real off-instance backup and clean-target restore record. Repository tests use synthetic proof records only and do not claim that recovery gate is complete.

## Commands

Run the tool from an immutable verified release with migration variables loaded transiently:

```text
python scripts/mysql_migrate.py status
python scripts/mysql_migrate.py check
python scripts/mysql_migrate.py dry-run --backup-proof <external-proof-path>
python scripts/mysql_migrate.py bridge-check-schema2
```

`status`, `check`, and `dry-run` issue only `SELECT` statements and never create migration metadata, acquire advisory locks, or modify application state. Their output is limited to initialized state, numeric versions, finite status, optional applying version, and the public catalog checksum. Target values, credentials, proof paths, SQL, and driver messages are never printed.

`bridge-check-schema2` uses only the existing runtime DML identity, reuses the checksum-prefix runtime verifier, and additionally requires exact clean schema `2`. Deployment binds both its pre-cutover and post-cutover checks to the selected immutable release root. It performs no migration or schema mutation.

`apply` is retained as a fail-closed command name but the held catalog rejects it before migration configuration, connector creation, advisory-lock acquisition, DDL, or migration-state write. The public `apply_migrations` boundary enforces the same ordering. There is no dormant selector, mark-applied path, checksum override, automatic replay, or arbitrary repair command. Enabling schema `3`, `4`, or `5`, including schema-four lifecycle or schema-five session-table grants, requires a separately governed migration, backup, quiesce, grant, drift, and restart packet.

## Upgrade and rollback boundary

The bridge runtime matrix is exact clean schema `2`, `3`, `4`, or `5` prefix restart. The held application boundary performs no transition into schema `3`, `4`, or `5`. Schemas two through four use independently keyed session documents; schema five uses the native indexed table. Exact clean schemas four and five are eligible for the inert game-action lifecycle. Missing metadata, schema `1`, a partial metadata boundary, gaps, checksum drift, future versions, `applying`, and `dirty` all fail before runtime traffic.

Migration files are forward-only. Application rollback is allowed only when the retained predecessor release manifest accepts the already-applied MySQL version. If the predecessor does not accept it, do not repoint the application release. Schema reversal, manual history edits, destructive down migrations, and data restoration remain prohibited without a separate recovery-reviewed packet. For partial DDL, preserve the dirty evidence and ship an explicit forward fix rather than attempting transactional rollback.

## Disposable validation

The CI matrix creates a new ephemeral MySQL 8.4 service, requires an explicit disposable marker, creates separate synthetic administrator, migrator, and runtime accounts, and uses test-suffixed isolated databases only. A private test seam seeds immutable catalog prefixes so live evidence can prove schema `2`, `3`, `4`, and `5` restart compatibility while the public apply path remains held. The matrix proves held refusal before lock or write, checksum/gap/future/dirty refusal, byte-preserving schema-three receipt backfill, exact schema-four lifecycle and reset convergence, schema-four keyed-session to schema-five native-row backfill, concurrent same-user and different-user session lifecycle, capacity-one bootstrap, append-only claim and receipt grants, singleton epoch grants, table-scoped session DML, `SHOW GRANTS`, and actual denied `CREATE`, `ALTER`, `DROP`, `INDEX`, `TRIGGER`, and `GRANT` attempts. It removes every test database and account afterward. It does not open or use protected application ports `8765` or `8877`, and the ephemeral service is destroyed with the CI job.
