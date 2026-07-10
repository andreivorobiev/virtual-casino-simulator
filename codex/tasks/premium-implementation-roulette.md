# Premium Roulette Frontend Implementation

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/14
- Parent epic: https://github.com/andreivorobiev/virtual-casino-simulator/issues/11
- Worker chat title: Casino Simulator - Worker - Premium Roulette Implementation
- Base branch: wait for `codex/premium-impl-foundation` handback unless the coordinator explicitly provides another base
- Implementation branch: `codex/premium-impl-roulette`
- Coordinator chat: Casino Simulator - Coordinator

## Goal

Implement the approved premium Roulette frontend with stable betting, spin/reveal, settled-result, bet slip, stats, bot, and autoplay regions while preserving existing Roulette gameplay and API behavior.

## Non-Goals

- Do not change Roulette rules, payouts, zero behavior, or ledger settlements.
- Do not change other games.
- Do not change `/api/v1` payloads unless the coordinator explicitly scopes an additive display-only field.

## Requirements

- Validate: `ROU-040` through `ROU-056`, `AUTO-003`, `AUTO-010`, `LEDGER-025`, `UX-007`, `UX-008`, `UX-009`.

## Owned Files

- `web/games/roulette.js`
- `tests/run_tests.py` only for Roulette browser/API coverage
- `modules/roulette.json`
- `modules/tests.json` if tests change
- `modules/module-manifest.json`

## Files Not To Touch

- `web/games/*.js` for other games
- `web/styles.css` unless the foundation worker explicitly documents an allowed extension pattern
- `casino/games/roulette/**` unless coordinator-approved
- `casino/core/ledger.py`
- `contracts/**`

## Required Reading

- `AGENTS.md`
- `docs/visual_design_standard.md` and `tests/visual/visual_matrix.json`
- relevant nested game `AGENTS.md`
- `modules/roulette.json`
- `docs/requirements/requirements.json`
- `contracts/openapi/roulette.v1.yaml`
- `codex/tasks/premium-implementation-epic.md`
- `codex/tasks/premium-implementation-roulette.md`
- `codex/tasks/artifacts/premium-redesign-prerenders/table-games/README.md`

## Design Source

- `codex/tasks/artifacts/premium-redesign-prerenders/table-games/roulette-betting-setup.png`
- `codex/tasks/artifacts/premium-redesign-prerenders/table-games/roulette-spinning-reveal.png`
- `codex/tasks/artifacts/premium-redesign-prerenders/table-games/roulette-settled-result.png`

## Validation

- Run Roulette-specific API/browser tests.
- Run module boundary, requirements, versions, and comment-density checks.

## Handback

Report changed files, requirement IDs, module version bumps, screenshots/browser evidence, validation results, and any deviation from the prerenders.
