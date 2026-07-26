# Casino Hold'em

Issue: [#139](https://github.com/andreivorobiev/virtual-casino-simulator/issues/139)

Parents: #66, #73

Shared integration lane: #77

## Integrated Scope

Casino Hold'em is catalog-discovered through `modules/casino_holdem.json`, registered at `/games/casino_holdem`, and exposed through a frozen additive v1 contract. The module includes player-scoped persistence, a lazy frontend module, paired EN/RU resources, permanent `CH-001` through `CH-005` requirements, focused and central tests, visual-matrix coverage, and a Long Suite driver.

## Rules Profile

- An ante deals two private player cards and a three-card community flop.
- The player folds or calls for twice the ante after seeing the flop.
- A call reveals the turn, river, and dealer cards before the best five-card hands are compared.
- The dealer qualifies with a pair of fours or better.
- The ante paytable and call return follow the additive v1 contract for dealer qualification, player wins, pushes, and dealer wins.

## Ledger and Retry Model

The module never mutates balances directly. It uses `CASINO_HOLDEM_ANTE_DEBIT`, `CASINO_HOLDEM_CALL_DEBIT`, and `CASINO_HOLDEM_SETTLEMENT_CREDIT` shared-ledger events. Every public action has a caller-stable `action_id`; exact retries return the same round, conflicting reuse fails closed, and durable receipt plus ledger recovery prevents duplicate movements after reload.

## Session and API Boundary

The frozen additive v1 routes are:

- `GET /api/v1/games/casino-holdem/state`
- `POST /api/v1/games/casino-holdem/rounds`
- `POST /api/v1/games/casino-holdem/rounds/{round_id}/decision`

All operations use the standard response envelope through the shared API handler. Optional `player_id` fields are compatibility inputs only; authenticated session resolution takes precedence.

## UI and Locale Boundary

The frontend module is `web/games/casino_holdem.js`. It owns no timers, clears locale subscriptions on unmount, respects reduced motion, uses the shared accessible card renderer, and keeps visible and ARIA copy in the paired game locale domains.

## #77 Traceability

Shared integration issue #77 owns the canonical descriptor, manifest and independent revisions, permanent requirements and generated docs, compatibility digest/matrix, visual row, central API/browser/restart coverage, and catalog-discovered Long Suite acceptance. The packaged application release is owned by `pyproject.toml` and `modules/module-manifest.json`; this compatible addition advanced only the independent source-module revisions.
