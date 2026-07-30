# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-30T21:31:35Z.

## Current branch / active Codex work

- PR #540 merged normally as protected main `28b2283a` after exact-head controller review, all nine required workflow families, source-bound Browser/Long/release-candidate artifacts, and zero review state.
- Terminal-green published/released/live production remains exact v0.9.5.39 `9de0d53c`, with MySQL clean at schema 2 and the held schema-3 migration uninvoked.
- `codex/release-v0.9.5.40` serializes the unique immutable release for the accepted read-only enrollment-policy foundation. No other merge may advance until v0.9.5.40 is terminal green through the trusted deployment route.

## Live queue snapshot

- #435 rank 001 remains externally blocked; #471 rank 003 remains architecture-blocked on separately governed #430 work.
- #333 rank 007 remains open after the bounded root slice; stacked #524/#528 remain held and untouched until v0.9.5.40 deploys terminal green.
- GitHub automatically marked external #520 merged when its immutable contributor head became reachable through the audited controller ancestry. Durable comments on #520 and #333 record that #540 is the sole content integration and no second #520 content merge occurred.
- #450 remains held/excluded; no child-stack, provider, public, or production configuration worktree is part of this release lane.

## Requirement / version claims

- Merged main owns `AUTH-013` through existing listener-free case `API-ENROLLMENT-POLICY-001`; no generic TEST or other permanent ID was allocated.
- The merged policy revisions remain core `9.33.0` and contracts `1.51.0`, with tests/docs `1.64.46`.
- This release packet alone advances package `0.9.5.40`, application `9.53.27`, contracts `1.51.1`, and tests/docs `1.64.47`; tooling `1.23.0` and every unrelated module remain unchanged.

## File claims / collision notes

- The release branch contains only the standard release contract, documentation, localization, version, predecessor-test, PWA-version, and coordination surfaces.
- It imports no stale contributor hunk and changes no casino source, policy implementation, route, provider, migration, ledger, grant, secret, or production workflow.
- Open PR #539 and every stacked or shared-governance head remain held and must rebase/recalculate after terminal deployment.

## Decisions / handbacks

- v0.9.5.40 packages the accepted read-only policy while public enrollment methods remain default-off and `/api/v1` remains unchanged.
- Its compatibility record binds exact immutable v0.9.5.39 as the application-only schema-2 predecessor; database rollback is prohibited and schema migration remains held.
- Hosted publication may create immutable assets, but unchanged hosted SSH activation must be cancelled before cutover. Trusted deployment must prove schema 2 before and after activation and invoke no migration.
- Enforcement, audit, Admin mutation, readiness, RBAC, UI, provider/signup/OAuth/mail/invitation/public enablement, MySQL composite execution, schema-3 activation, and issue closure remain separately governed.
