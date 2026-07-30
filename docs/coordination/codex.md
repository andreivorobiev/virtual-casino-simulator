# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-30T23:37:25Z.

## Current branch / active Codex work

- PR #542 merged normally as protected main `b7f2fe1c` after exact-head controller review, all nine required workflow families, source-bound Browser/Long/release-candidate artifacts, and zero review state.
- Terminal-green published/released/live production remains exact v0.9.5.40 `3d769813`; MySQL remains clean at schema 2 and the held schema-3 migration was not invoked.
- `codex/release-v0.9.5.41` serializes the unique immutable release for the accepted bounded enrollment-policy enforcement slice. No other merge may advance until v0.9.5.41 is terminal green through the trusted deployment route.

## Live queue snapshot

- #435 rank 001 remains externally blocked; #471 rank 003 remains architecture-blocked on separately governed #430 work.
- #333 rank 007 remains open after bounded signup/invitation enforcement; external #524 remains open and stacked #528 remains held and untouched until v0.9.5.41 deploys terminal green.
- Open #539, #525, and every older shared-governance head remain held and must rebase or serialize later.
- #450 remains held/excluded; no provider, OAuth, Admin-write, child-stack, public-enable, or production configuration worktree is part of this release lane.

## Requirement / version claims

- Merged main owns the accepted `AUTH-013` enforcement evidence through existing listener-free case `API-ENROLLMENT-POLICY-001`; no generic TEST or other permanent ID was allocated.
- The merged enrollment revisions remain core `9.34.0` and contracts `1.52.0`, with tests/docs `1.64.48`.
- This release packet alone advances package `0.9.5.41`, application `9.53.28`, contracts `1.52.1`, and tests/docs `1.64.49`; tooling `1.23.0` and every unrelated module remain unchanged.

## File claims / collision notes

- The release branch contains only the standard release contract, documentation, localization, version, predecessor-test, PWA-version, and coordination surfaces.
- It imports no stale contributor hunk and changes no casino source, enrollment implementation, route, provider, migration, ledger, grant, secret, or production workflow.
- Every open shared or stacked head must rebase and recalculate after terminal deployment.

## Decisions / handbacks

- v0.9.5.41 packages policy enforcement only at public signup and invitation redemption; existing login and frozen `/api/v1` remain unchanged.
- Bounded operational decision logging must succeed before mutation and is not immutable provider-backed actor/change audit; that remains deferred to #528.
- Its compatibility record binds exact immutable v0.9.5.40 as the application-only schema-2 predecessor; database rollback is prohibited and schema migration remains held.
- Hosted publication may create immutable assets, but unchanged hosted SSH activation must be cancelled before cutover. Trusted deployment must prove schema 2 before and after activation and invoke no migration.
- Admin mutation, readiness, RBAC, UI, OAuth/provider, live enablement, provider network, public exposure, MySQL composite execution, schema-3 activation, issue closure, and #528 remain separately governed.
