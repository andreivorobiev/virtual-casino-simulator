# Premium Blackjack Frontend Implementation

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/15
- Parent epic: https://github.com/andreivorobiev/virtual-casino-simulator/issues/11
- Worker chat title: Casino Simulator - Worker - Premium Blackjack Implementation
- Base branch: wait for `codex/premium-impl-foundation` handback unless the coordinator explicitly provides another base
- Implementation branch: `codex/premium-impl-blackjack`
- Coordinator chat: Casino Simulator - Coordinator

## Goal

Implement the approved premium Blackjack frontend with stable multi-hand lanes, premium buttons, visible dealer/player hands, split state, insurance/surrender/double/split affordances, and settlement drawer while preserving Blackjack rules and API behavior.

## Non-Goals

- Do not change Blackjack engine behavior, payouts, dealer behavior, split rules, or ledger settlements.
- Do not change other games.
- Do not change `/api/v1` payloads unless coordinator-approved.

## Requirements

- Validate: `BJ-008` through `BJ-030`, `BJ-031` if present, `LEDGER-025`, `UX-007`, `UX-008`, `UX-009`.

## Owned Files

- `web/games/blackjack.js`
- `tests/run_tests.py` only for Blackjack browser/API coverage
- `modules/blackjack.json`
- `modules/tests.json` if tests change
- `modules/module-manifest.json`

## Files Not To Touch

- `web/games/*.js` for other games
- `web/styles.css` unless the foundation worker explicitly documents an allowed extension pattern
- `casino/games/blackjack/**` unless coordinator-approved
- `casino/core/ledger.py`
- `contracts/**`

## Required Reading

- `AGENTS.md`
- `docs/visual_design_standard.md` and `tests/visual/visual_matrix.json`
- relevant nested game `AGENTS.md`
- `modules/blackjack.json`
- `docs/requirements/requirements.json`
- `contracts/openapi/blackjack.v1.yaml`
- `codex/tasks/premium-implementation-epic.md`
- `codex/tasks/premium-implementation-blackjack.md`
- `codex/tasks/artifacts/premium-redesign-prerenders/table-games/README.md`

## Design Source

- `codex/tasks/artifacts/premium-redesign-prerenders/table-games/blackjack-initial-deal.png`
- `codex/tasks/artifacts/premium-redesign-prerenders/table-games/blackjack-active-decision.png`
- `codex/tasks/artifacts/premium-redesign-prerenders/table-games/blackjack-split-multi-hand.png`
- `codex/tasks/artifacts/premium-redesign-prerenders/table-games/blackjack-settled-result.png`

## Validation

- Run Blackjack-specific API/browser tests.
- Run module boundary, requirements, versions, and comment-density checks.

## Handback

Report changed files, requirement IDs, module version bumps, screenshots/browser evidence, validation results, and any deviation from the prerenders.
