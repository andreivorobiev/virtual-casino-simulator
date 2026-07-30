# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-30T12:16:47Z.

## Current branch / active Codex work

- `codex/430-json-game-action-journal` qualifies the independently accepted JSON-provider Phase 0c checkpoint from exact terminal-green v0.9.5.37 main `7fd02841`.
- The substantive checkpoint remains isolated in commit `dc8c1999`; the follow-up commit adds only current-main governance, central listener-free test registration, version fixtures, and coordination.
- The branch remains draft-only and non-closing; Integration alone may ready, merge, release, or deploy it.

## Live queue snapshot

- #435 rank 001 remains externally blocked and #450 remains held/excluded.
- #471 rank 003 remains blocked on the remaining #430 composite sequence after this JSON-provider prerequisite.
- Existing #520/#524/#528 remain contributor-owned and held; #526 remains held under its owner.
- Issues #430 and #471 remain open after this bounded slice.

## Requirement / version claims

- This branch owns `STORAGE-011` and central case `STORAGE-GAME-ACTION-ONCE-001`; `CORE-032` remains free and no generic TEST requirement ID is allocated.
- Target revisions are core `9.31.0`, admin `1.13.3`, and tests/docs `1.64.41`.
- Packaged application `0.9.5.37`, application `9.53.24`, contracts `1.49.22`, tooling `1.21.12`, and every unrelated module remain unchanged.

## File claims / collision notes

- Substantive ownership is limited to `casino/core/storage.py`, `casino/app.py`, `casino/admin.py`, and `tests/json_game_action_provider_tests.py`.
- Governance ownership is limited to the canonical/generated requirements, core/admin/tests/docs descriptors and aggregate manifest, central storage registration, the exact version fixture, and Codex coordination files.
- Shared governance was regenerated from exact v0.9.5.37; no stale contributor hunk was imported.

## Decisions / handbacks

- The JSON provider now owns journal recovery and cross-process serialization for the provider-neutral game-action contract, including immutable replay receipts and failure-atomic reset visibility.
- MySQL composite execution, schema version three, routes, games, Slots adoption, ledger behavior, and any all-provider atomicity claim remain excluded.
- The production one-worker/two-thread posture remains unchanged; this slice neither authorizes scaling nor changes production configuration.
