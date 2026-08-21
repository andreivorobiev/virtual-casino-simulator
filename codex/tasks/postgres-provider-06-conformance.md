# PostgreSQL lane 6: provider-agnostic storage conformance kit

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/1060
- Priority: P2
- Assigned author: storage conformance worker
- Authoring system (`Claude`, `Codex`, `human`, or approved other): Claude
- Coordinator: Codex
- Merge executor: Codex
- Branch: `claude/1060-storage-conformance`
- Base branch and commit: early JSON authoring from exact merged Phase-A packet PR; final rebase onto exact accepted merge containing #1059
- Dependency PRs and exact heads: final harness acceptance depends on eventual merged PR for #1059
- PR title: `test: add storage provider conformance kit`
- Required owner approval or external gate: disposable MySQL/PostgreSQL reachability only
- Coordinator task: allow early disjoint JSON cases, hold final integration until #1059, and serialize test/tooling/docs metadata
- Worker task: implement one unchanged A–J suite and three provider-neutral harness registrations

## Goal

- Goal: make `tests/storage_conformance/` the executable backend contract with no capability carve-outs.
- Non-goals: no provider implementation, schema, public API, gameplay, production, or deployment changes.
- User-visible behavior expected: none; backend acceptance becomes consistent and measurable.

## Requirements

- Requirement IDs added: reserved `STORAGE-025`, `TEST-257`; reallocate if consumed.
- Requirement IDs changed: none.
- Requirement IDs validated: all accepted `STORAGE-*` contract IDs and `TEST-257`.

## Scope

- Impacted modules: tests, tooling validator, docs requirement mapping.
- Packaged application release impact: none.
- Independent module revision bumps planned: next unused tests/tooling/docs revisions at final integration.
- Owned files: `tests/storage_conformance/**`, narrowly necessary runner/CI registration, module-boundary validator seam.
- Files not to touch: provider implementations, pools, migrations, contracts, games, ledger/player call sites, pyproject, README/CHANGELOG, deployment/provider/secret files.
- Allowed adjacent files: shared requirements/manifests under exclusive Codex lease.

## Compatibility

- API/gameplay/ledger/data behavior impact: none; tests only.
- Bot/autoplay impact: none.
- Security/privacy impact: no native error/SQL/connection detail in failures or reports.
- Release/provenance impact: none.
- Deployment/provider impact: disposable isolated harnesses only.

## Required reading

- Baseline policy, core/tests/docs instructions and manifests, storage/migration/pool specialized docs.
- Full StorageProvider contract and existing storage, state-store, session, provider-parity, migration-live, and API storage-foundation tests.
- Relevant contracts: no changes; read frozen-v1 policy.

## Validation

- Required tests: A documents, B players, C ledger, D sequencing, E exactly-once, F history, G concurrency, H transactions/visibility, I reset, J errors across JSON/MySQL/PostgreSQL.
- Required scripts: provider-import boundary, requirements, versions, contracts, module boundaries, docs, headers, file length.
- Performance: complete JSON <10s; each reachable local disposable MySQL/PostgreSQL <60s; emit per-group timing and fail overruns.
- Visual/locales/browser: none.
- Evidence classification: `after_pass`.
- Manual checks: no concrete-provider import/branch or capability skip in cases.
- Disposable state and cleanup: isolated temp directory/database/account; reset between cases; destroy on every terminal path.

## Handback

- Expected PR summary: harness protocol/registry, A–J inventory, import gate, timing budgets, provider sections, cleanup.
- Final packaged release impact: none; exact module revisions required.
- PR URL/state/base/head/checks/review: mandatory draft handback.
- Open questions: any provider-specific case need is a contract defect, not a carve-out.
- Stop conditions: concrete import/branch, skipped capability, weakened assertion/budget, residue, live target, dependency/shared owner drift.
- Merge recommendation: `Codex review and merge after all three applicable harnesses pass unchanged and cleanup is proven.`

## Role boundary

- PR author may merge: No
- PR author may enable auto-merge: No
- Claude handback target: Codex review and merge when eligible
- Codex merge preconditions: exact #1059 base, full A–J inventory, no carve-outs, timing/cleanup evidence, requirements/versions/checks/review.
- Post-merge verification and issue disposition: verify main and add `Rolled out with #NNN` to #1060.
