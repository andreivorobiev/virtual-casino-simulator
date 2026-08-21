# PostgreSQL lane 7: documentation and metadata integration

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/1061
- Priority: P2
- Assigned author: PostgreSQL docs and metadata worker
- Authoring system (`Claude`, `Codex`, `human`, or approved other): Claude
- Coordinator: Codex
- Merge executor: Codex
- Branch: `claude/1061-postgres-docs-metadata`
- Base branch and commit: exact accepted merge containing #1060 and every prior lane
- Dependency PRs and exact heads: verified merged PRs/rollout links for #1055 through #1060
- PR title: `docs: document PostgreSQL storage provider`
- Required owner approval or external gate: none; no release/deployment/live claim authorized
- Coordinator task: verify every preceding rollout link and grant the final exclusive metadata lease
- Worker task: document exact accepted behavior and reconcile generated docs/metadata without source implementation

## Goal

- Goal: update README persistence, PostgreSQL environment/migration/pool docs, changelog, generated catalog, conformance README, and final metadata consistency.
- Non-goals: no runtime/test/provider implementation, release artifact/version, deployment, database, provider console, or secrets.
- User-visible behavior expected: accurate source documentation only.

## Requirements

- Requirement IDs added: none planned.
- Requirement IDs changed: none planned.
- Requirement IDs validated: `STORAGE-020` through `STORAGE-025`, `TEST-252` through `TEST-257`.

## Scope

- Impacted modules: application docs surface, docs; tooling only if generator source changes.
- Packaged application release impact: none; remain `0.9.5.84` absent separate release authority.
- Independent module revision bumps planned: next unused application/docs documentation revisions; tooling only if source changes.
- Owned files: `README.md`, `CHANGELOG.md`, new/updated PostgreSQL docs, generated `CODEX_START_HERE.md`, conformance README, final metadata/requirements reconciliation under exclusive lease.
- Files not to touch: runtime/provider/pool/migration/test source, contracts, games, deployment, release artifacts/manifests/notes, provider/secret files.
- Allowed adjacent files: affected module descriptors and aggregate manifest under exclusive Codex lease.

## Compatibility

- API/gameplay/ledger/data/security behavior impact: none; documentation only.
- Bot/autoplay impact: none.
- Release/provenance impact: no artifact or packaged-release bump.
- Deployment/provider impact: none; docs must not claim an unperformed live operation.

## Required reading

- Baseline policy, docs/tests nested instructions and manifests.
- Exact merged lane issues/PRs/evidence, README, changelog, MySQL/PostgreSQL docs, conformance README, versioning policy.
- Relevant contracts: no change; frozen-v1 non-impact confirmation.

## Validation

- Required tests: relevant accepted storage/conformance smoke only where docs assertions map exact behavior.
- Required scripts: generated docs check, requirements, versions, contracts, module boundaries, game catalog, headers, terminology.
- Visual/locales/browser: none.
- Evidence classification: `after_pass`.
- Manual checks: env-name/link/schema/version/pool-bound/secret scan and rollout-link inventory.
- Disposable state and cleanup: none.

## Handback

- Expected PR summary: exact accepted source behavior, doc inventory, generated output, version/requirement reconciliation, no release/live claim.
- Final packaged application release impact: none.
- Final module revisions: exact application/docs and any justified tooling revision.
- PR URL/state/base/head/checks/review: mandatory draft handback.
- Open questions: any implementation/doc mismatch returns to originating lane.
- Stop conditions: missing lane merge/rollout, live/release claim, shared owner/version conflict, secret/target data, implementation change.
- Merge recommendation: `Codex review and merge after every prior rollout and exact docs/metadata gate.`

## Role boundary

- PR author may merge: No
- PR author may enable auto-merge: No
- Claude handback target: Codex review and merge when eligible
- Codex merge preconditions: all dependencies/rollout links, exact docs truth, exclusive metadata, checks/review, no release/live mutation.
- Post-merge verification and issue disposition: verify main, add `Rolled out with #NNN` to #1061, then close #1054 only after all seven rollout links are verified.
