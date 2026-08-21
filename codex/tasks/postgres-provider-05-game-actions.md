# PostgreSQL lane 5: exactly-once game-action executor

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/1059
- Priority: P2
- Assigned author: PostgreSQL exactly-once worker
- Authoring system (`Claude`, `Codex`, `human`, or approved other): Claude
- Coordinator: Codex
- Merge executor: Codex
- Branch: `claude/1059-postgres-game-actions`
- Base branch and commit: exact accepted merge containing #1058
- Dependency PRs and exact heads: eventual merged PRs for #1057 and #1058
- PR title: `feat: add PostgreSQL exactly-once game actions`
- Required owner approval or external gate: disposable PostgreSQL marker only
- Coordinator task: confirm exact schema/provider base and release shared metadata lease
- Worker task: implement PostgreSQL claims, receipts, resolution, reset epoch, and atomic action publication

## Goal

- Goal: match accepted JSON/MySQL exactly-once game-action behavior under PostgreSQL row locking and transaction semantics.
- Non-goals: no schema, game, call-site, settlement gateway, paytable, contract, MySQL/JSON, production, or deployment change.
- User-visible behavior expected: exact retry replays the committed result rather than redrawing or moving money twice.

## Requirements

- Requirement IDs added: reserved `STORAGE-024`, `TEST-256`; reallocate if consumed.
- Requirement IDs changed: none.
- Requirement IDs validated: `STORAGE-005`, `STORAGE-006`, `STORAGE-011`, `STORAGE-013`, `MYSQL-007` through `MYSQL-009`, `STORAGE-024`, `TEST-256`.

## Scope

- Impacted modules: core, tests, docs requirement mapping.
- Packaged application release impact: none.
- Independent module revision bumps planned: next unused compatible revisions.
- Owned files: `storage/game_actions_postgres.py`, minimal provider composition seam, focused action/resolver/reset tests.
- Files not to touch: JSON/MySQL mixins/codecs unless separately approved, all games, settlement/ledger call sites, migrations, contracts, paytables, deployment/provider/secret files.
- Allowed adjacent files: shared requirements/manifests under exclusive Codex lease.

## Compatibility

- API/gameplay public shape impact: none.
- Ledger impact: new provider atomic implementation only.
- Bot/autoplay impact: none.
- Data migration impact: none; consume accepted schema 4/5 structures.
- Security/privacy impact: fail closed and sanitize provider-native details.
- Release/provenance/deployment/provider impact: none outside disposable tests.

## Required reading

- Baseline policy, core/tests/docs instructions/manifests, commenting/file-length policy.
- Full base contract, action codecs, JSON/MySQL action mixins, MySQL provider and migrations 0002–0005, lifecycle requirements/issues #683/#688, focused tests.
- Relevant contracts: frozen APIs for non-impact confirmation.

## Validation

- Required tests: replay/conflict, executor-first/resolver-first/pending, crash/rollback windows, late executor, paid/zero-cost, reset/restart, planner/RNG at-most-once, concurrent same-key; unchanged JSON/MySQL.
- Required scripts: requirements, versions, contracts, boundaries, docs, headers, file length.
- Visual/locales/browser: none.
- Evidence classification: `after_pass`.
- Manual checks: append-only claim/receipt and isolation reasoning.
- Disposable state and cleanup: synthetic target only; destroy and prove zero residue.

## Handback

- Expected PR summary: lifecycle state machine, dialect decisions, atomicity, replay bytes, tests and risks.
- Final packaged release impact: none; exact module revisions required.
- PR URL/state/base/head/checks/review: mandatory draft handback.
- Open questions: any required schema/call-site change blocks.
- Stop conditions: dependency/shared owner drift; schema/game/API expansion; update/delete of immutable lifecycle; non-disposable target.
- Merge recommendation: `Codex review and merge only after exact-head money/retry/concurrency evidence.`

## Role boundary

- PR author may merge: No
- PR author may enable auto-merge: No
- Claude handback target: Codex review and merge when eligible
- Codex merge preconditions: exact dependencies, money/retry audit, requirements/versions, checks/review, cleanup.
- Post-merge verification and issue disposition: verify main and add `Rolled out with #NNN` to #1059.
