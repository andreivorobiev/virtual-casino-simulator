# Let It Ride

Issue: [#134](https://github.com/andreivorobiev/virtual-casino-simulator/issues/134)

Parents: #66, #73

Shared integration lane: #77

## Integrated Scope

Let It Ride is catalog-discovered through `modules/let_it_ride.json`, registered at `/games/let_it_ride`, and exposed through a frozen additive v1 contract. The integrated module includes player-scoped persistence, a lazy frontend module, paired EN/RU resources, permanent `LIR-001` through `LIR-005` requirements, focused and central tests, visual-matrix coverage, and a Long Suite driver.

## Rules Profile

- Every round commits three equal base-wager units through one opening ledger debit.
- Three player cards are visible before the first ride-or-pull decision.
- The first decision reveals one community card; the second reveals the final community card and settles the round.
- Each pull returns exactly one eligible wager unit through the ledger.
- Remaining units settle against the documented five-card poker paytable, beginning at a pair of tens.

## Ledger and Retry Model

The module never mutates balances directly. It uses `LET_IT_RIDE_WAGER_DEBIT`, `LET_IT_RIDE_REFUND_CREDIT`, and `LET_IT_RIDE_PAYOUT_CREDIT` shared-ledger events. Every public action has a caller-stable `action_id`; exact retries return the same round, conflicting reuse fails closed, and append-only proof lookup prevents duplicate movements after reload.

## Session and API Boundary

The frozen additive v1 routes are:

- `GET /api/v1/games/let-it-ride/state`
- `POST /api/v1/games/let-it-ride/rounds`
- `POST /api/v1/games/let-it-ride/rounds/{round_id}/first-decision`
- `POST /api/v1/games/let-it-ride/rounds/{round_id}/second-decision`

All operations use the standard response envelope through the shared API handler. Optional `player_id` fields are compatibility inputs only; authenticated session resolution takes precedence.

## UI and Locale Boundary

The frontend module is `web/games/let_it_ride.js`. It owns no timers, clears locale subscriptions on unmount, respects reduced motion, uses the shared accessible card renderer, and keeps visible and ARIA copy in the paired game locale domains.

## #77 Traceability

Shared integration issue #77 owns the canonical descriptor, manifest and independent revisions, permanent requirements and generated docs, compatibility digest/matrix, visual row, central API/browser/restart coverage, and catalog-discovered Long Suite acceptance. The packaged application remains `9.1.1`; this compatible addition advances only the independent source-module revisions.
