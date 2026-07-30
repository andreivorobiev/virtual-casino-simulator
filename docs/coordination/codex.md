# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-30T09:48:56Z.

## Current branch / active Codex work

- Codex owns the bounded #430 Phase 0c core-contract controller on `codex/430-game-action-contract-controller`.
- Exact protected and deployed v0.9.5.36 main is `ab7a5450`; the controller preserves independently accepted checkpoint `dd36a198` as its second-parent ancestry.
- Substantive scope is only `casino/core/game_action.py` and `tests/game_action_contract_tests.py`; shared requirements, modules, generated docs, central test registration, the tests/docs version fixture, and Codex coordination are the governed integration surfaces.
- Integration remains the sole merge, release, and deployment executor.

## Live queue snapshot

- #435 rank 001 remains externally blocked and #450 remains held/excluded.
- #471 rank 003 is blocked on the independently governed #430 provider-owned composite sequence; this contract-only slice is its highest executable prerequisite.
- Existing #520/#524/#528 remain contributor-owned and held; #526 remains held under its owner.
- #434 and #441 remain separate frozen checkpoints and are excluded from this controller.

## Requirement / version claims

- `CORE-031` is reserved for the provider-neutral game-action contract after exact protected-main and all-open-head collision readback.
- No generic TEST requirement ID is allocated; central listener-free case `API-GAMECORE-003` maps the focused proof.
- The compatible public core addition advances core `9.29.0` to `9.30.0`; tests/docs advance from `1.64.38` to `1.64.39`.
- Packaged application `0.9.5.36`, application, contracts, tooling, storage, every game module, and every unrelated module remain unchanged.

## File claims / collision notes

- Protected main and every open PR leave both substantive paths and `CORE-031` free at the live guard.
- Shared requirements, module descriptors, manifest, central runner, generated docs, fixture, and coordination records overlap stale or contributor proposals only at governance level; no shared hunk is imported.
- Provider implementations, JSON journal/gate, schema-3 migration, MySQL composite work, routes, games, Slots, ledger, app, API, contracts, tooling, production, release, #434, #441, and #450 are excluded.

## Decisions / handbacks

- The abstract contract validates bounded immutable identity/resources/snapshots/plans/receipts and canonical request fingerprints; a fake provider proves the contract semantics without claiming a production implementation.
- The draft is non-closing: #430 and #471 remain open for provider implementations and later route/game adoption.
- The accepted production posture remains one worker/two threads; this slice makes no multi-process or current-production atomicity claim.
