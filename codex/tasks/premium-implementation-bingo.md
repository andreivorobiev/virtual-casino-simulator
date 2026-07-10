# Premium Bingo Frontend Implementation

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/19
- Parent epic: https://github.com/andreivorobiev/virtual-casino-simulator/issues/11
- Worker chat title: Casino Simulator - Worker - Premium Bingo Implementation
- Base branch: wait for `codex/premium-impl-foundation` handback unless the coordinator explicitly provides another base
- Implementation branch: `codex/premium-impl-bingo`
- Coordinator chat: Casino Simulator - Coordinator

## Goal

Implement the approved premium Bingo frontend with stable card purchase, ball-call progress, pattern highlight, cards-in-play drawer, bot/autoplay panels, and recent sessions while preserving Bingo gameplay and API behavior.

## Non-Goals

- Do not change Bingo engine behavior, patterns, payouts, ball calls, or ledger settlements.
- Do not change other games.
- Do not change `/api/v1` payloads unless coordinator-approved.

## Requirements

- Validate: `BINGO-001` through `BINGO-024`, `AUTO-013`, `LEDGER-025`, `UX-007`, `UX-008`, `UX-009`.

## Owned Files

- `web/games/bingo.js`
- `tests/run_tests.py` only for Bingo browser/API coverage
- `modules/bingo.json`
- `modules/tests.json` if tests change
- `modules/module-manifest.json`

## Files Not To Touch

- `web/games/*.js` for other games
- `web/styles.css` unless the foundation worker explicitly documents an allowed extension pattern
- `casino/games/bingo/**` unless coordinator-approved
- `casino/core/ledger.py`
- `contracts/**`

## Required Reading

- `AGENTS.md`
- `docs/visual_design_standard.md` and `tests/visual/visual_matrix.json`
- relevant nested game `AGENTS.md`
- `modules/bingo.json`
- `docs/requirements/requirements.json`
- `contracts/openapi/bingo.v1.yaml`
- `codex/tasks/premium-implementation-epic.md`
- `codex/tasks/premium-implementation-bingo.md`
- `codex/tasks/artifacts/premium-redesign-prerenders/machine-draw-games/README.md`

## Design Source

- `codex/tasks/artifacts/premium-redesign-prerenders/machine-draw-games/png/bingo-card-purchase-ready.png`
- `codex/tasks/artifacts/premium-redesign-prerenders/machine-draw-games/png/bingo-ball-call-in-progress.png`
- `codex/tasks/artifacts/premium-redesign-prerenders/machine-draw-games/png/bingo-winning-pattern-highlight.png`

## Validation

- Run Bingo-specific API/browser tests.
- Run module boundary, requirements, versions, and comment-density checks.

## Handback

Report changed files, requirement IDs, module version bumps, screenshots/browser evidence, validation results, and any deviation from the prerenders.
