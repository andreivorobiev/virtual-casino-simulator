# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-30T07:18:19Z.

## Current branch / active Codex work

- Worker B owns the bounded #430 Phase 0b governance lane on `codex/430-player-state-atomic`.
- The preserved source/test checkpoint is exact `bf69083b` with exact protected v0.9.5.35 main `c500b6dd` as its merge base.
- The substantive scope is only `casino/core/state_store.py` and `tests/state_store_atomic_tests.py`; shared requirements, modules, generated docs, storage test registration, and Codex coordination are the governed integration surfaces.
- Integration remains the sole merge, release, and deployment executor.

## Live queue snapshot

- #435 rank 001 remains externally blocked and #450 remains held/excluded.
- #471 rank 003 remains blocked on #430 Phase 0c; Phase 0b is now the owner-released prerequisite lane.
- Existing enrollment PRs #520/#524/#528 are substantively separate but overlap shared governance and must reconcile after the serialized #430 decision.
- #526 remains under owner repair and is monitored only when its exact head changes.

## Requirement / version claims

- `CORE-030` is reserved for the player-game-state atomic update requirement after exact protected-main and all-open-head collision readback.
- No generic TEST requirement ID is allocated; central storage case `STORAGE-PLAYER-STATE-ATOMIC-001` maps the focused proof.
- The compatible public core addition advances core `9.28.0` to `9.29.0`; tests/docs advance from `1.64.35` to `1.64.36`.
- Packaged application `0.9.5.35`, application, contracts, tooling, storage, every game module, and every unrelated module remain unchanged.

## File claims / collision notes

- No open PR touches either Phase 0b substantive path at the live guard.
- Shared requirements, `modules/module-manifest.json`, `tests/run_tests.py`, generated docs, and coordination records overlap other proposals only at governance level; normal serialized rebasing is required.
- #434, #441, #450, Phase 0c source work, routes, games, provider implementations, ledger, contracts, app, tooling, production, release, DNS, ingress, secrets, signup, OAuth, mail, and invitation files are excluded.

## Decisions / handbacks

- Phase 0b preserves the legacy-human fallback and delegates complete read/mutate/normalize/write behavior through the existing JSON/MySQL atomic document boundary.
- Focused proof covers lazy defaults, concurrent distinct JSON updates, byte-identical rollback, non-human isolation, legacy compatibility, and exact MySQL delegation.
- The draft is non-closing: #430 remains open for Phase 0c and later explicitly governed game adoption.
