# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-31T02:04:54Z.

## Current branch / active Codex work

- Terminal-green protected/released/live production is exact v0.9.5.41 `1248b94a`; MySQL remains clean at schema 2 and the held schema-3 migration was not invoked.
- Durable #524/#333 disposition closes external #524 without a second content merge after its accepted controller content shipped through #542 and v0.9.5.41.
- `codex/528-enrollment-admin-controller` now preserves exact v41 as first ancestry and immutable contributor head `792621ef` as second ancestry while rebuilding only the bounded owner enrollment-policy transaction.

## Live queue snapshot

- #435 rank 001 remains externally blocked; #471 rank 003 remains architecture-blocked on separately governed #430 work.
- #333 rank 007 remains open after bounded signup/invitation enforcement; #528 is the active slice-3 owner Admin transaction and must pass independent pre-push review.
- Open #518, #539, #525, and every older shared-governance head remain held and must rebase or serialize later.
- #450 remains held/excluded; no provider, OAuth, Admin-write, child-stack, public-enable, or production configuration worktree is part of this release lane.

## Requirement / version claims

- The controller allocates only `AUTH-014` beside retained `AUTH-013` on existing listener-free case `API-ENROLLMENT-POLICY-001`; no generic TEST or other permanent ID is allocated.
- Proposed compatible source revisions are core `9.35.0`, admin `1.14.0`, contracts `1.53.0`, and tests/docs `1.64.50`.
- Package `0.9.5.41`, application `9.53.28`, tooling `1.23.0`, and every unrelated module remain unchanged.

## File claims / collision notes

- The controller ancestry merge imports no contributor tree content; all source, tests, contracts, requirements, versions, generated docs, and coordination are rebuilt from exact v41.
- Direct source changes stay within `casino/admin.py`, `casino/core/enrollment_policy.py`, the provider-neutral strict seam in `casino/core/storage.py`, and their two focused test files; shared Admin/requirements/manifest collisions with #518/#539 serialize later.
- No app, public route, global ordinary-document behavior, UI, provider selection, migration, ledger, grant, secret, release, or production workflow is changed.

## Decisions / handbacks

- The owner-only GET/preview/apply boundary resolves current platform-owner authority; an exact audit-bound revision, exact confirmation, and a bounded reason are mandatory for apply.
- Strict provider reads preserve missing-document compatibility while refusing malformed schema-owned bytes, duplicate keys, access failures, or audit mismatch without fallback, backup, normalization, or read-side write.
- Preview and apply share one capability computation; apply compares the revision inside the provider transaction before proposal or side effects, and policy plus hash-linked opaque-actor audit then commit together. The response returns the exact prior policy, consumed revision, and new revision for an explicit rollback.
- Operational public-decision JSONL remains distinct from provider-backed owner actor/change audit; existing login, signup/invitation envelopes, legacy non-mapping/unowned-schema fallback, and frozen `/api/v1` remain unchanged.
- This controller does not invoke a live policy change and adds no readiness, UI, OAuth/provider, mail, DNS, billing, public exposure, release, deployment, issue closure, or held #450 authority.
