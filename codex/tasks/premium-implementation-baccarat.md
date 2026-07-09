# Premium Baccarat Frontend Implementation

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/16
- Parent epic: https://github.com/andreivorobiev/virtual-casino-simulator/issues/11
- Worker chat title: Casino Simulator - Worker - Premium Baccarat Implementation
- Base branch: wait for `codex/premium-impl-foundation` handback unless the coordinator explicitly provides another base
- Implementation branch: `codex/premium-impl-baccarat`
- Coordinator chat: Casino Simulator - Coordinator

## Goal

Implement the approved premium Baccarat frontend with wager setup, card reveal, result state, shoe summary, bot/autoplay panels, and road-history drawer while preserving Baccarat gameplay and API behavior.

## Non-Goals

- Do not change Baccarat engine behavior, drawing rules, outcomes, payouts, or ledger settlements.
- Do not change other games.
- Do not change `/api/v1` payloads unless coordinator-approved.

## Requirements

- Validate: `BAC-020` through `BAC-024`, `AUTO-009`, `LEDGER-025`, `UX-007`, `UX-008`, `UX-009`.

## Owned Files

- `web/games/baccarat.js`
- `tests/run_tests.py` only for Baccarat browser/API coverage
- `modules/baccarat.json`
- `modules/tests.json` if tests change
- `modules/module-manifest.json`

## Files Not To Touch

- `web/games/*.js` for other games
- `web/styles.css` unless the foundation worker explicitly documents an allowed extension pattern
- `casino/games/baccarat/**` unless coordinator-approved
- `casino/core/ledger.py`
- `contracts/**`

## Required Reading

- `AGENTS.md`
- relevant nested game `AGENTS.md`
- `modules/baccarat.json`
- `docs/requirements/requirements.json`
- `contracts/openapi/baccarat.v1.yaml`
- `codex/tasks/premium-implementation-epic.md`
- `codex/tasks/premium-implementation-baccarat.md`
- `codex/tasks/artifacts/premium-redesign-prerenders/table-games/README.md`

## Design Source

- `codex/tasks/artifacts/premium-redesign-prerenders/table-games/baccarat-wager-setup.png`
- `codex/tasks/artifacts/premium-redesign-prerenders/table-games/baccarat-card-reveal.png`
- `codex/tasks/artifacts/premium-redesign-prerenders/table-games/baccarat-result-road-history.png`

## Validation

- Run Baccarat-specific API/browser tests.
- Run module boundary, requirements, versions, and comment-density checks.

## Handback

Report changed files, requirement IDs, module version bumps, screenshots/browser evidence, validation results, and any deviation from the prerenders.
