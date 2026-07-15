# Joker Poker

Issue: [#130](https://github.com/andreivorobiev/virtual-casino-simulator/issues/130)

Parents: #66, #73

Shared integration lane: #77

## Integrated Scope

Joker Poker is catalog-discovered through `modules/joker_poker.json`, registered at `/games/joker_poker`, and exposed through a frozen additive v1 contract. The module includes player-scoped persistence, a lazy frontend module, paired EN/RU resources, permanent `JP-001` through `JP-005` requirements, focused and central tests, visual-matrix coverage, and a Long Suite driver.

## Rules Profile

- One 53-card source deck contains the standard 52 cards plus exactly one wild joker.
- One five-card hand enters a reload-safe hold phase before a single draw.
- Held positions remain fixed while unheld positions draw from the remaining deck.
- Kings or Better is the lowest paying hand; separate natural royal, five-of-a-kind, and wild royal rows preserve the joker-specific profile.
- The published paytable determines the returned play-token amount after the draw.

## Ledger and Retry Model

The module never mutates balances directly. It uses `JOKER_POKER_WAGER_DEBIT` and `JOKER_POKER_PAYOUT_CREDIT` shared-ledger events. Deal and draw actions use caller-stable `action_id` values; exact retries return the same hand, conflicting reuse fails closed, and durable receipts plus ledger recovery prevent duplicate movements after reload.

## Session and API Boundary

The frozen additive v1 routes are:

- `GET /api/v1/games/joker-poker/state`
- `POST /api/v1/games/joker-poker/rounds`
- `POST /api/v1/games/joker-poker/rounds/{round_id}/holds`
- `POST /api/v1/games/joker-poker/rounds/{round_id}/draw`

All operations use the standard response envelope through the shared API handler. Optional `player_id` fields are compatibility inputs only; authenticated session resolution takes precedence.

## UI and Locale Boundary

The frontend module is `web/games/joker_poker.js`. It owns no timers, clears locale subscriptions on unmount, respects reduced motion, preserves hold state through the public API, and keeps visible and ARIA copy in the paired game locale domains.

## #77 Traceability

Shared integration issue #77 owns the canonical descriptor, manifest and independent revisions, permanent requirements and generated docs, compatibility digest/matrix, visual row, central API/browser/restart coverage, and catalog-discovered Long Suite acceptance. The packaged application remains `9.1.1`; this compatible addition advances only the independent source-module revisions.
