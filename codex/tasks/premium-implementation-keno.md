# Premium Keno Frontend Implementation

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/18
- Parent epic: https://github.com/andreivorobiev/virtual-casino-simulator/issues/11
- Worker chat title: Casino Simulator - Worker - Premium Keno Implementation
- Base branch: wait for `codex/premium-impl-foundation` handback unless the coordinator explicitly provides another base
- Implementation branch: `codex/premium-impl-keno`
- Coordinator chat: Casino Simulator - Coordinator

## Goal

Implement the approved premium Keno frontend with stable number board, spot selection, draw progress, paytable comparison, ticket drawer, bot/autoplay panels, and history surfaces while preserving Keno gameplay and API behavior.

## Non-Goals

- Do not change Keno engine behavior, draw rules, payouts, spot limits, or ledger settlements.
- Do not change other games.
- Do not change `/api/v1` payloads unless coordinator-approved.

## Requirements

- Validate: `KENO-001` through `KENO-022`, `AUTO-012`, `LEDGER-025`, `UX-007`, `UX-008`, `UX-009`.

## Owned Files

- `web/games/keno.js`
- `tests/run_tests.py` only for Keno browser/API coverage
- `modules/keno.json`
- `modules/tests.json` if tests change
- `modules/module-manifest.json`

## Files Not To Touch

- `web/games/*.js` for other games
- `web/styles.css` unless the foundation worker explicitly documents an allowed extension pattern
- `casino/games/keno/**` unless coordinator-approved
- `casino/core/ledger.py`
- `contracts/**`

## Required Reading

- `AGENTS.md`
- relevant nested game `AGENTS.md`
- `modules/keno.json`
- `docs/requirements/requirements.json`
- `contracts/openapi/keno.v1.yaml`
- `codex/tasks/premium-implementation-epic.md`
- `codex/tasks/premium-implementation-keno.md`
- `codex/tasks/artifacts/premium-redesign-prerenders/machine-draw-games/README.md`

## Design Source

- `codex/tasks/artifacts/premium-redesign-prerenders/machine-draw-games/png/keno-spot-selection.png`
- `codex/tasks/artifacts/premium-redesign-prerenders/machine-draw-games/png/keno-draw-in-progress.png`
- `codex/tasks/artifacts/premium-redesign-prerenders/machine-draw-games/png/keno-result-paytable-comparison.png`

## Validation

- Run Keno-specific API/browser tests.
- Run module boundary, requirements, versions, and comment-density checks.

## Handback

Report changed files, requirement IDs, module version bumps, screenshots/browser evidence, validation results, and any deviation from the prerenders.
