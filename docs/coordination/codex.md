# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-31T03:18:11Z.

## Current branch / active Codex work

- PR #544 merged normally as protected main `8c8f3efa` after exact-head controller review, all nine required workflow families, source-bound Browser/Long/release-candidate artifacts, and zero review state.
- Terminal-green published/released/live production remains exact v0.9.5.41 `1248b94a`; MySQL remains clean at schema 2 and the held schema-3 migration was not invoked.
- `codex/release-v0.9.5.42` serializes the unique immutable release for the accepted owner-only enrollment-policy transaction. No other merge may advance until v0.9.5.42 is terminal green through the trusted deployment route.

## Live queue snapshot

- #435 rank 001 remains externally blocked; #471 rank 003 remains architecture-blocked on separately governed #430 work.
- #333 rank 007 remains open after the owner-only policy transaction; external #528 remains open pending terminal release and durable ancestry disposition.
- Open #518, #539, #526, #525, and every older shared-governance head remain held and must rebase or serialize later.
- #450 remains held/excluded; no provider, OAuth, live policy change, child-stack, public-enable, or production configuration worktree is part of this release lane.

## Requirement / version claims

- Merged main owns `AUTH-014` beside retained `AUTH-013` on existing listener-free case `API-ENROLLMENT-POLICY-001`; no generic TEST, STORAGE, or other permanent ID was allocated.
- The merged enrollment revisions remain core `9.35.0`, admin `1.14.0`, and contracts `1.53.0`, with tests/docs `1.64.50`.
- This release packet alone advances package `0.9.5.42`, application `9.53.29`, contracts `1.53.1`, and tests/docs `1.64.51`; tooling `1.23.0` and every unrelated module remain unchanged.

## File claims / collision notes

- The release branch contains only the standard release contract, documentation, localization, version, predecessor-test, PWA-version, and coordination surfaces.
- It imports no stale contributor hunk and changes no casino source, enrollment implementation, route, provider, migration, ledger, grant, secret, or production workflow.
- Every open shared or stacked head must rebase and recalculate after terminal deployment.

## Decisions / handbacks

- v0.9.5.42 packages the owner-only GET/preview/apply boundary with its strict provider read and revision-bound actor/change audit; it invokes no live policy change.
- Existing login, public signup/invitation enforcement, operational decision logging, legacy non-mapping/unowned-schema fallback, and frozen `/api/v1` remain unchanged.
- Its compatibility record binds exact immutable v0.9.5.41 as the application-only schema-2 predecessor; database rollback is prohibited and schema migration remains held.
- Hosted publication may create immutable assets, but unchanged hosted SSH activation must be cancelled before cutover. Trusted deployment must prove schema 2 before and after activation and invoke no migration.
- Readiness, UI, OAuth/provider, live enablement, provider network, public exposure, MySQL composite execution, schema-3 activation, issue closure, and held #450 remain separately governed.
