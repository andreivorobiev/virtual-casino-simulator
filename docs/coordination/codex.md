# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-30T19:13:19Z.

## Current branch / active Codex work

- PR #537 merged normally as protected main `2a28ef52` after exact-head bridge review, all nine required workflow families, source-bound Browser and Long artifacts, non-closing issue verification, and zero review state.
- Terminal-green published/released/live production remains exact v0.9.5.38 `69995920`; the v0.9.5.39 tag and release remain unused.
- `codex/release-v0.9.5.39-bridge` serializes the unique immutable bridge release from exact protected main. No other merge, release, or deployment lane may advance until v0.9.5.39 is terminal green through the trusted owner/static route.

## Live queue snapshot

- #435 rank 001 remains externally blocked and #450 remains held/excluded.
- #471 rank 003 remains blocked on the remaining #430 schema-3 production migration, MySQL composite, and adoption sequence.
- Issues #430 and #471 remain open after the bounded bridge merge.
- Existing open contributor and stacked PRs remain held; the frozen unsafe pre-bridge release-v39 worktree remains untouched and excluded.

## Requirement / version claims

- Merged main owns `MYSQL-008` and `TOOL-011` through the existing migration, recovery, predecessor, and deployment cases; no generic TEST or other requirement ID was allocated.
- The merged bridge revisions remain core `9.32.0`, tooling `1.23.0`, and contracts `1.50.0`, with tests/docs `1.64.44`.
- This release packet alone advances package `0.9.5.39`, application `9.53.26`, contracts `1.50.1`, and tests/docs `1.64.45`; every unrelated module remains unchanged.

## File claims / collision notes

- The release branch contains only the standard release contract, documentation, localization, version, predecessor-test, PWA-version, and coordination surfaces.
- It imports no stale contributor hunk and changes no casino source, migration, provider, route, game, ledger, grant, secret, or production workflow.
- The unsafe uncommitted standard release packet remains preserved in its separate worktree and contributes no bytes to this clean rebuild.

## Decisions / handbacks

- v0.9.5.39 packages the accepted runtime bridge while keeping `apply_policy=held`.
- Its compatibility record declares unchanged rollback schema `2`, binds exact immutable v0.9.5.38 as the application-only predecessor, and prohibits database rollback.
- Hosted publication may create immutable assets, but unchanged hosted SSH activation must be cancelled before cutover. Trusted deployment must prove schema `2` before and after activation and invoke no migration.
- MySQL composite execution, receipt-table grant and drift hardening, schema-3 production activation, routes, games, Slots adoption, ledger behavior, provider scaling, and all-provider atomicity remain separately governed.
