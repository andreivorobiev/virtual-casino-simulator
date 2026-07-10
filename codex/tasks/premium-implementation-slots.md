# Premium Slots Frontend Implementation

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/17
- Parent epic: https://github.com/andreivorobiev/virtual-casino-simulator/issues/11
- Worker chat title: Casino Simulator - Worker - Premium Slots Implementation
- Base branch: wait for `codex/premium-impl-foundation` handback unless the coordinator explicitly provides another base
- Implementation branch: `codex/premium-impl-slots`
- Coordinator chat: Casino Simulator - Coordinator

## Goal

Implement the approved premium Slots frontend with stable reels, spin-in-progress, win/payline reveal, free-spin/progressive context, recent spins, paytable, bot/autoplay panels, and fixed result regions while preserving Slots gameplay and API behavior.

## Non-Goals

- Do not change slot engine behavior, reel strips, payouts, paylines, free-spin rules, progressive logic, or ledger settlements.
- Do not change other games.
- Do not change `/api/v1` payloads unless coordinator-approved.

## Requirements

- Validate: `SLOT-001` through `SLOT-026`, `AUTO-010`, `LEDGER-025`, `UX-007`, `UX-008`, `UX-009`.

## Owned Files

- `web/games/slots.js`
- `tests/run_tests.py` only for Slots browser/API coverage
- `modules/slots.json`
- `modules/tests.json` if tests change
- `modules/module-manifest.json`

## Files Not To Touch

- `web/games/*.js` for other games
- `web/styles.css` unless the foundation worker explicitly documents an allowed extension pattern
- `casino/games/slots/**` unless coordinator-approved
- `casino/core/ledger.py`
- `contracts/**`

## Required Reading

- `AGENTS.md`
- `docs/visual_design_standard.md` and `tests/visual/visual_matrix.json`
- relevant nested game `AGENTS.md`
- `modules/slots.json`
- `docs/requirements/requirements.json`
- `contracts/openapi/slots.v1.yaml`
- `codex/tasks/premium-implementation-epic.md`
- `codex/tasks/premium-implementation-slots.md`
- `codex/tasks/artifacts/premium-redesign-prerenders/machine-draw-games/README.md`

## Design Source

- `codex/tasks/artifacts/premium-redesign-prerenders/machine-draw-games/png/slots-idle-reels.png`
- `codex/tasks/artifacts/premium-redesign-prerenders/machine-draw-games/png/slots-spin-in-progress.png`
- `codex/tasks/artifacts/premium-redesign-prerenders/machine-draw-games/png/slots-win-payline-reveal.png`
- `codex/tasks/artifacts/premium-redesign-prerenders/machine-draw-games/png/slots-free-spin-progressive-context.png`

## Validation

- Run Slots-specific API/browser tests.
- Run module boundary, requirements, versions, and comment-density checks.

## Handback

Report changed files, requirement IDs, module version bumps, screenshots/browser evidence, validation results, and any deviation from the prerenders.
