# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-29T04:55:00Z.

## Current branch / active Codex work

- `codex/430-settlement-core` reconciles preserved checkpoint `6eb83259` with terminal-green v0.9.5.28 main `49bbdcde`.
- Scope is only the independently revertible #430 Phase 0a route-free settlement foundation plus its governed requirement mapping and central listener-free registration.
- Integration Queue remains the sole merge/release/deploy executor; this branch will publish a draft PR only.

## Live queue snapshot

- #430 Phase 0a is the highest actionable queue item after an independent Integration Queue guard.
- Higher P1 #471 is blocked by its missing stack rank and stale/conflicting #473; #433 rank071 remains owner-policy blocked.
- #450 and every Claude-owned or other-worker substantive path remain excluded.

## Requirement / version claims

- `GAMECORE-003` is allocated to the route-free signed-action settlement adapter; no generic TEST ID is allocated.
- Core advances `9.27.3` to `9.28.0` because AGENTS.md classifies compatible additions as minor changes; tests and docs advance `1.64.21` to `1.64.22`.
- Packaged application `0.9.5.28`, application `9.53.15`, contracts `1.49.10`, tooling `1.21.9`, and every unrelated module remain unchanged.

## File claims / collision notes

- Substantive ownership is limited to `casino/core/settlement.py` and `tests/settlement_core_tests.py`.
- Governed integration is limited to the `GAMECORE-003` requirement, `API-GAMECORE-002` central registration, core/tests/docs descriptors and manifest entries, generated requirements documentation, and this Codex-owned coordination record.
- Routes, games, Phase 0b/0c, provider implementations, public deployment, #441, #450, and Claude/other-worker branches remain untouched.

## Decisions / handbacks

- The adapter delegates one signed movement to the existing public storage-atomic `debit_once` or `credit_once` boundary; it does not create a new provider or transaction engine.
- Canonical game action, request fingerprint, and round evidence are additive and caller audit details remain unchanged.
- Provider replay is returned exactly; post-conflict recovery accepts only a fully compatible committed row and otherwise preserves the original conflict.
