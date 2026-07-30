# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-30T12:43:52Z.

## Current branch / active Codex work

- PR #534 merged normally as protected main `f0523cbd` after exact-head JSON-provider review, all nine required workflow families, Browser and Long aggregates, non-closing issue verification, and zero review state.
- `codex/release-v0.9.5.38` serializes the unique immutable patch release from that exact protected main.
- No other merge, release, or deployment lane may advance until v0.9.5.38 is terminal green through the trusted owner/static deployment route.

## Live queue snapshot

- v0.9.5.37 remains the terminal-green production predecessor until v0.9.5.38 completes trusted deployment.
- #435 rank 001 remains externally blocked and #450 remains held/excluded.
- #471 rank 003 remains blocked on the remaining #430 schema-3, MySQL composite, and adoption sequence.
- Issues #430 and #471 remain open after the bounded JSON-provider slice.

## Requirement / version claims

- Merged main owns `STORAGE-011` and central case `STORAGE-GAME-ACTION-ONCE-001`; `CORE-032` remains free and no generic TEST requirement ID was allocated.
- The merged feature revisions remain core `9.31.0`, admin `1.13.3`, and tests/docs `1.64.41`.
- This release packet alone advances package `0.9.5.38`, application `9.53.25`, contracts `1.49.23`, and tests/docs `1.64.42`; tooling and every unrelated module remain unchanged.

## File claims / collision notes

- The release branch contains only the standard release contract, documentation, localization, version, predecessor-test, PWA-version, and coordination surfaces.
- It imports no stale contributor hunk and changes no casino source, runtime API, provider behavior, database schema, game, route, ledger, or production configuration.
- v0.9.5.38 retains exact immutable v0.9.5.37 as its application-only predecessor; MySQL remains schema 2 and database rollback is prohibited.

## Decisions / handbacks

- The release records the accepted JSON-provider journal, immutable replay receipts, cross-process storage gate, and failure-atomic Admin reset boundary.
- MySQL composite execution, schema version three, routes, games, Slots adoption, ledger behavior, provider scaling, and all-provider atomicity remain excluded.
- Hosted publication may create immutable assets, but unchanged hosted SSH activation must be cancelled before cutover; Worker A receives the exact canonical packet for trusted terminal-green deployment.
