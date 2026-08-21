# PostgreSQL lane 2: configuration and provider registration

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/1055
- Priority: P2
- Assigned author: PostgreSQL registration worker
- Authoring system (`Claude`, `Codex`, `human`, or approved other): Claude
- Coordinator: Codex
- Merge executor: Codex
- Branch: `claude/1055-postgres-registration`
- Base branch and commit: accepted protected-main descendant after PR #1051 and this Phase-A packet PR; intake baseline `667bdf2b4a0b3d997d5bf18f9bf158fa49749c01`
- Dependency PRs and exact heads: PR #1051 exact proposed head `db0f4d08caa0e49199f7ab530d364709eea22ab2`, then this packet PR
- PR title: `feat: register PostgreSQL storage configuration`
- Required owner approval or external gate: none beyond ordinary review; selecting PostgreSQL remains disabled/incomplete until provider core lands
- Coordinator task: record the accepted base and release shared metadata ownership after packet integration
- Worker task: add configuration, optional driver extra, lazy selection seam, and focused tests

## Goal

- Goal: add `PostgresConfig`, `DEFAULT_POSTGRES_*`, `postgres` provider selection, and the lazy psycopg optional extra without changing JSON/MySQL behavior.
- Non-goals: no pool, migrations, provider implementation, database access, production, deployment, or release.
- User-visible behavior expected: none in default JSON/MySQL modes; explicit incomplete PostgreSQL selection fails closed with fixed secret-free diagnostics until Lane 4.

## Requirements

- Requirement IDs added: reserved `STORAGE-020`, `TEST-252`; stop for reallocation if accepted main consumes either ID.
- Requirement IDs changed: none.
- Requirement IDs validated: `STORAGE-001` through `STORAGE-004`, `STORAGE-020`, `TEST-252`.

## Scope

- Impacted modules: core, application, tests, docs requirement mapping.
- Packaged application release impact: none.
- Independent module revision bumps planned: core 10.14.0 and application 9.73.0 from intake baseline; tests/docs next unused revisions; recalculate after dependencies.
- Owned files: `casino/core/storage/base.py`, `casino/config.py`, `casino/core/storage/__init__.py`, `pyproject.toml`, focused configuration/selection tests.
- Files not to touch: Postgres pool/migrations/provider/action files, MySQL/JSON implementations, contracts, games, README, CHANGELOG, deployment, provider, and secret files.
- Allowed adjacent files: requirement sources/generated docs and affected manifests under exclusive Codex integration lease.

## Compatibility

- API contract impact: none; `/api/v1` frozen.
- Gameplay impact: none.
- Ledger impact: none.
- Bot/autoplay impact: none.
- Data migration impact: none.
- Security/privacy impact: malformed values and absent driver fail before connector access and reveal no environment values.
- Release/provenance impact: no artifact or packaged release.
- Deployment/provider impact: repository selector only; no external provider action.

## Required reading

- `CODEX_START_HERE.md`
- `AGENTS.md`
- `CLAUDE.md` when Claude authors the PR
- `ENGINEERING_PRACTICES.md`
- `docs/engineering_skills.md`
- `docs/claude_codex_work_division.md`
- Relevant nested `AGENTS.md`: `casino/core/AGENTS.md`, `tests/AGENTS.md`, `docs/AGENTS.md`
- Relevant module manifests: aggregate, core, application, tests, docs
- Relevant contracts: none; frozen-v1 policy applies
- Relevant docs: `docs/commenting_policy.md`, `docs/local_mysql_setup.md`, issue #1055

## Validation

- Required tests: config defaults/overrides/malformed values, lazy import, absent-driver fail-closed behavior, JSON default, MySQL selector regression.
- Required scripts: requirements, versions, contracts, module boundaries, generated docs, headers, file length.
- Visual matrix surface/state IDs: none.
- Required locales/viewports: none.
- Browser evidence: none.
- Evidence classification (`before_failure` or `after_pass`): `after_pass`.
- Manual checks: prove psycopg is not imported for JSON/MySQL.
- Disposable state and cleanup: environment patching only; restore all variables/modules.

## Handback

- Expected PR summary: exact environment names/defaults, lazy selector design, disabled-until-Lane-4 boundary, tests, and no behavior drift.
- Final packaged application release impact: none.
- Final independent module revision bumps: exact recalculated values.
- Evidence to include: focused test output and standard validators.
- PR URL and state: one draft PR.
- Exact base and head SHA: mandatory.
- Checks and review state: mandatory.
- Open questions to report: any need for a placeholder provider is a stop, not worker scope.
- Stop conditions: dependency/base/shared owner/version/ID drift; placeholder provider; connector or external target; API change.
- Merge recommendation format: `Codex review and merge when exact-head checks and ordinary approvals are satisfied.`

## Role boundary

- PR author may merge: No
- PR author may enable auto-merge: No
- Claude handback target: Codex review and merge when eligible
- Codex merge preconditions: exact base, disjoint ownership, requirements/versions, checks, independent review, no provider mutation.
- Post-merge verification and issue disposition: verify protected main, release #1056/#1057 bases, and add `Rolled out with #NNN` to #1055.
