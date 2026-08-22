# PostgreSQL lane 3: migrations and deployment-only runner

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/1057
- Priority: P2
- Assigned author: PostgreSQL migrations worker
- Authoring system (`Claude`, `Codex`, `human`, or approved other): Codex
- Coordinator: Codex
- Merge executor: Codex
- Branch: `codex/1057-postgres-migrations`
- Base branch and commit: exact merged head of #1055 after Phase-A packet integration
- Dependency PRs and exact heads: eventual merged PR for #1055; record before mutation
- PR title: `feat: add PostgreSQL migration catalog and runner`
- Required owner approval or external gate: explicit disposable marker for live CI; no non-disposable target is authorized
- Coordinator task: serialize shared metadata with #1056 and release it only immediately before ready state
- Worker task: translate the current 0001–0005 chain, runner, tests, and disposable PostgreSQL 16 evidence

## Goal

- Goal: add a checksum-bound PostgreSQL migration chain and secret-safe deployment-only runner with disposable apply evidence.
- Non-goals: no MySQL byte/policy change, production migration, grants, provider console, deployment, or release.
- User-visible behavior expected: none until provider core composes the migrated schema.

## Requirements

- Requirement IDs added: reserved `STORAGE-022`, `TEST-254`; stop for reallocation if consumed.
- Requirement IDs changed: none.
- Requirement IDs validated: `MYSQL-005`, `MYSQL-007` through `MYSQL-010`, `STORAGE-022`, `TEST-254` as parity references only.

## Scope

- Impacted modules: core, tooling, tests, docs requirement mapping.
- Packaged application release impact: none.
- Independent module revision bumps planned: next unused compatible revisions from the accepted merge base.
- Owned files: `casino/core/postgres_migrations.py`, `migrations/postgres/**`, `scripts/postgres_migrate.py`, `tests/postgres_migration_tests.py`, narrowly scoped disposable-live test/helper registration.
- Files not to touch: MySQL catalog/runner/provider, JSON provider, pools, public contracts, games, deployment units, production/provider/secret files.
- Allowed adjacent files: CI registration and shared metadata only under exclusive Codex lease.

## Compatibility

- API contract impact: none.
- Gameplay impact: none.
- Ledger impact: no runtime change; schema supports existing ledger and action contracts.
- Bot/autoplay impact: none.
- Data migration impact: new immutable PostgreSQL 0001–0005 descriptors, applied only to newly created disposable targets.
- Security/privacy impact: separate migration identity/key; sanitized output; no target, credential, SQL, or driver text.
- Release/provenance impact: no artifact.
- Deployment/provider impact: runner source only; no target mutation outside explicit disposable CI.

## Required reading

- Repository baseline policy set and core/tests/docs nested instructions.
- Module manifests: aggregate, core, tooling, tests, docs.
- Relevant contracts: none changed.
- Relevant docs: commenting policy, local MySQL setup, MySQL migrations, recovery boundary, issue #1057.
- Relevant source: current MySQL 0001–0005 catalog, `mysql_migrations.py`, `mysql_migrate.py`, and migration tests in full.

## Validation

- Required tests: catalog/checksum/hostile-state tests, DDL translation, secret-safe failures, disposable PostgreSQL 16 apply/restart/cleanup when available, unchanged MySQL migration suites.
- Required scripts: requirements, versions, contracts, module boundaries, docs, headers, file length.
- Visual/locales/browser: none.
- Evidence classification: `after_pass`.
- Manual checks: audit every translated index/constraint and absence of interpolated SQL.
- Disposable state and cleanup: explicit test-suffixed database/account only; remove on success/failure and prove residue zero.

## Handback

- Expected PR summary: dialect decisions, immutable chain, runner safety, disposable evidence, MySQL non-impact.
- Final packaged application release impact: none.
- Final independent module revision bumps: exact values.
- Evidence to include: checksums, DDL inventory, hostile matrix, live disposable report and cleanup.
- PR URL/state/base/head/checks/review: mandatory draft handback.
- Open questions to report: any schema fork or non-disposable need.
- Stop conditions: dependency/base/owner drift; schema rename/timestamp fork; MySQL edit; secrets; non-disposable target.
- Merge recommendation format: `Codex review and merge after exact-head gates and disposable evidence.`

## Role boundary

- PR author may merge: No
- PR author may enable auto-merge: No
- Claude handback target: not applicable; this Codex-authored head requires independent exact-head review before merge
- Codex merge preconditions: dependencies, exact catalog/dialect audit, cleanup, ownership, requirements/versions, checks and review.
- Post-merge verification and issue disposition: verify main and add `Rolled out with #NNN` to #1057.
