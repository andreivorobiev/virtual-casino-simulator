# PostgreSQL lane 4: complete StorageProvider core parity

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/1058
- Priority: P2
- Assigned author: PostgreSQL provider-core worker
- Authoring system (`Claude`, `Codex`, `human`, or approved other): Codex
- Coordinator: Codex
- Merge executor: Codex
- Branch: `codex/1058-postgres-provider-core`
- Base branch and commit: exact accepted main containing #1055, #1056, and #1057
- Dependency PRs and exact heads: eventual merged PRs for #1055/#1056/#1057
- PR title: `feat: implement PostgreSQL storage provider core`
- Required owner approval or external gate: disposable PostgreSQL reachability marker only
- Coordinator task: release the lane after all three dependencies and shared metadata are accepted
- Worker task: implement the complete live provider contract except the Lane-5 whole-game action mixin

## Goal

- Goal: implement documents, players, ledger, history, first-class sessions, reset, visibility, transaction, schema readiness, and error translation parity.
- Non-goals: no game-action mixin, MySQL/JSON change, call-site/game/API/schema redesign, production, deployment, or release.
- User-visible behavior expected: configured disposable PostgreSQL can execute ordinary persistence with unchanged public shapes.

## Requirements

- Requirement IDs added: reserved `STORAGE-023`, `TEST-255`; reallocate if consumed.
- Requirement IDs changed: none.
- Requirement IDs validated: `STORAGE-001` through `STORAGE-019`, `STORAGE-023`, `TEST-255`.

## Scope

- Impacted modules: core, tests, docs requirement mapping.
- Packaged application release impact: none.
- Independent module revision bumps planned: next unused compatible revisions from accepted dependency base.
- Owned files: `storage/postgres_provider.py`, optional bounded `sessions_postgres.py`, Lane-2 selector seam, narrowly provider-neutral storage/state/session/API-foundation tests.
- Files not to touch: MySQL/JSON implementations, ledger/player call sites, games, contracts, migrations, pools, README/CHANGELOG, deployment/provider/secret files.
- Allowed adjacent files: shared requirements/manifests under exclusive Codex lease.

## Compatibility

- API contract impact: none; frozen shapes unchanged.
- Gameplay impact: none.
- Ledger impact: new backend implements existing atomic ledger contract.
- Bot/autoplay impact: provider compatibility only.
- Data migration impact: uses exact accepted PostgreSQL catalog on disposable targets.
- Security/privacy impact: no psycopg/native exception or SQL/target/credential detail escapes.
- Release/provenance impact: none.
- Deployment/provider impact: none outside disposable tests.

## Required reading

- Complete repository baseline policy set; core/tests/docs nested instructions and manifests.
- Full `storage/base.py`, MySQL provider, JSON provider infrastructure/reset/sessions, pool/migration docs, state-store and storage tests.
- Relevant contracts: current frozen APIs for read-only impact confirmation; no contract edit authorized.

## Validation

- Required tests: documents, players, normalization, ledger/once/economics/sequencing, history, sessions, state-store atomicity, transaction visibility, reset, errors; unchanged JSON/MySQL suites; disposable PostgreSQL.
- Required scripts: requirements, versions, contracts, module boundaries, docs, headers, file length.
- Visual/locales/browser: none.
- Evidence classification: `after_pass`.
- Manual checks: transaction/isolation analysis and SQL parameter audit.
- Disposable state and cleanup: synthetic PostgreSQL schema/data only, destroyed after tests.

## Handback

- Expected PR summary: method inventory, dialect/locking decisions, error mapping, parity evidence, cleanup.
- Final packaged application release impact: none.
- Final module revisions: exact.
- Evidence: listener-free model plus disposable provider suite, unchanged JSON/MySQL.
- PR URL/state/base/head/checks/review: mandatory draft handback.
- Open questions: any contract method or call-site mismatch.
- Stop conditions: incomplete inventory; dependency/base/shared owner drift; call-site/schema/API expansion; native error leakage; non-disposable target.
- Merge recommendation: `Codex review and merge after every exact-head parity and safety gate.`

## Role boundary

- PR author may merge: No
- PR author may enable auto-merge: No
- Claude handback target: not applicable; this Codex-authored head requires independent exact-head review before merge
- Codex merge preconditions: dependencies, complete method inventory, data-integrity review, exact evidence, versions/requirements/checks/review.
- Post-merge verification and issue disposition: verify main and add `Rolled out with #NNN` to #1058.
