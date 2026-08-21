# PostgreSQL lane 1: bounded connection pool

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/1056
- Priority: P2
- Assigned author: PostgreSQL pool worker
- Authoring system (`Claude`, `Codex`, `human`, or approved other): Claude
- Coordinator: Codex
- Merge executor: Codex
- Branch: `claude/1056-postgres-pool`
- Base branch and commit: exact accepted protected-main descendant after #1055; intake baseline `667bdf2b4a0b3d997d5bf18f9bf158fa49749c01`
- Dependency PRs and exact heads: the eventual merged PR for #1055; worker records its exact merged head before mutation
- PR title: `feat: add bounded PostgreSQL connection pool`
- Required owner approval or external gate: owner must resolve PostgreSQL capacity 1–16 in the directive versus current MySQL parity at 1–64
- Coordinator task: release the exact base and exclusive metadata lease after #1055 merges
- Worker task: implement the bounded pool and listener-free lifecycle suite without connector or live-target access

## Goal

- Goal: add `casino/core/postgres_pool.py` with bounded checkout/connect deadlines, request-scoped leases, cleanup, fork isolation, public-safe named errors, secret-free metrics, and `atexit` shutdown parity.
- Non-goals: no provider implementation, migrations, MySQL changes, database access, production configuration, deployment, or release.
- User-visible behavior expected: none until later provider lanes compose the pool.

## Requirements

- Requirement IDs added: reserved `STORAGE-021`, `TEST-253`; stop for reallocation if accepted main consumes either ID.
- Requirement IDs changed: none.
- Requirement IDs validated: `STORAGE-010`, `MYSQL-011`, `STORAGE-021`, `TEST-253`.

## Scope

- Impacted modules: core, tests, docs requirement mapping.
- Packaged application release impact: none.
- Independent module revision bumps planned: next unused compatible-addition revisions for core/tests and next requirement-mapping docs revision, recalculated from the accepted execution base.
- Owned files: `casino/core/postgres_pool.py`, `tests/postgres_pool_tests.py`, narrowly required catalog-derived test registration.
- Files not to touch: `casino/core/mysql_pool.py`, concrete providers, migrations, `pyproject.toml`, README, CHANGELOG, contracts, games, deployment, provider, and secret files.
- Allowed adjacent files: requirement sources/generated docs and affected module manifests only under a time-bounded exclusive Codex integration lease.

## Compatibility

- API contract impact: none; `/api/v1` frozen.
- Gameplay impact: none.
- Ledger impact: none.
- Bot/autoplay impact: none.
- Data migration impact: none.
- Security/privacy impact: connector errors, credentials, and targets must never enter messages or metrics.
- Release/provenance impact: source module revisions only; no artifact.
- Deployment/provider impact: none; pool tests are listener-free and use fake connectors.

## Required reading

- `CODEX_START_HERE.md`
- `AGENTS.md`
- `CLAUDE.md` when Claude authors the PR
- `ENGINEERING_PRACTICES.md`
- `docs/engineering_skills.md`
- `docs/claude_codex_work_division.md`
- Relevant nested `AGENTS.md`: `casino/core/AGENTS.md`, `tests/AGENTS.md`, `docs/AGENTS.md`
- Relevant module manifests: `modules/module-manifest.json`, `modules/core.json`, `modules/tests.json`, `modules/docs.json`
- Relevant contracts: none; read the frozen-v1 policy before any adjacent API proposal
- Relevant docs: `docs/commenting_policy.md`, `docs/mysql_connection_pool.md`, issue #1056

## Validation

- Required tests: `tests/postgres_pool_tests.py`, unchanged `tests/mysql_pool_tests.py`.
- Required scripts: requirements, versions, contracts, module boundaries, generated docs, headers, and file length.
- Visual matrix surface/state IDs: none.
- Required locales/viewports: none.
- Browser evidence: none.
- Evidence classification (`before_failure` or `after_pass`): `after_pass` terminal output bound to exact head.
- Manual checks: confirm no connector/network call and no secret/target label or exception text.
- Disposable state and cleanup: fake sockets only; close all leases/waiters and assert zero residue.

## Handback

- Expected PR summary: policy decision, pool invariants, fixed error taxonomy, lifecycle/concurrency evidence, and unchanged MySQL behavior.
- Final packaged application release impact: none.
- Final independent module revision bumps: report exact accepted values.
- Evidence to include: saturation, wakeup, timeout, rollback/reset/discard, fork generation, close-all, idempotent close, and metrics.
- PR URL and state: one draft PR until exact checks and owner decision are satisfied.
- Exact base and head SHA: mandatory.
- Checks and review state: mandatory.
- Open questions to report: capacity 1–16 versus 1–64.
- Stop conditions: unresolved capacity; moved base; shared owner; provider-native leakage; connector/live target; scope expansion.
- Merge recommendation format: `Codex review and merge only after the owner decision and every exact-head gate are green.`

## Role boundary

- PR author may merge: No
- PR author may enable auto-merge: No
- Claude handback target: Codex review and merge when eligible
- Codex merge preconditions: accepted dependency, resolved capacity, exact ownership/requirements/versions, checks, independent review, no external mutation.
- Post-merge verification and issue disposition: verify protected main and add `Rolled out with #NNN` to #1056 before closure.
