# Caribbean Stud

Issue: [#132](https://github.com/andreivorobiev/virtual-casino-simulator/issues/132)

Parents: #66, #73

Shared integration lane: #77

## Integrated Scope

Caribbean Stud is catalog-discovered through `modules/caribbean_stud.json`, registered at `/games/caribbean_stud`, and exposed through a frozen additive v1 contract. The integrated module includes a player-scoped service, lazy frontend module, paired EN/RU resources, permanent `CS-001` through `CS-005` requirements, focused and central tests, visual-matrix coverage, and a Long Suite driver.

## Rules Profile

- One standard 52-card deck is shuffled for each heads-up player-vs-dealer round.
- The player receives five cards. The dealer receives five cards with one upcard visible before the player decision.
- The player antes first, then chooses `call` or `fold`.
- `fold` forfeits the ante and does not reveal dealer hole cards.
- `call` costs exactly two times the ante and reveals the dealer hand.
- Dealer qualification is ace-king high or better.
- If the dealer does not qualify, the ante pays even money and the call wager pushes.
- If the dealer qualifies and the player wins, the ante pays even money and the call wager pays the published odds table.
- Exact ties push both ante and call wagers.
- A qualified dealer win returns no play tokens.

## Ledger and Retry Model

The module never mutates balances directly. The service uses the shared ledger for:

- `CARIBBEAN_STUD_ANTE_DEBIT` on deal;
- `CARIBBEAN_STUD_CALL_DEBIT` on call;
- `CARIBBEAN_STUD_SETTLEMENT_CREDIT` when a call returns stake, winnings, or both.

Each public action has a caller-stable `action_id`. Deal, call, and settlement ledger movements use distinct game-local action keys, semantic fingerprints, and append-only proof lookup before any write. Exact retries return the same round and ledger evidence. Conflicting action-id reuse fails closed. If the current JSON provider reports an attempted movement with no append-only proof, the action fails closed for reconciliation rather than repeating a possibly completed movement.

## Session and API Boundary

The frozen additive v1 routes are:

- `GET /api/v1/games/caribbean-stud/state`
- `POST /api/v1/games/caribbean-stud/rounds`
- `POST /api/v1/games/caribbean-stud/rounds/{round_id}/call`
- `POST /api/v1/games/caribbean-stud/rounds/{round_id}/fold`

All operations use the standard `{ ok: true, data: ... }` / `{ ok: false, error: ... }` envelope when integrated through the shared API handler. Optional `player_id` fields are compatibility inputs only; the authenticated session resolver takes precedence.

## UI and Locale Boundary

The frontend module is `web/games/caribbean_stud.js`. It uses no game timers, clears locale subscriptions on unmount, respects reduced motion in route-local CSS, uses the shared accessible card renderer, and keeps all visible and ARIA copy in `web/i18n/en-US/games/caribbean_stud.json` and `web/i18n/ru-RU/games/caribbean_stud.json`.

## #77 Traceability

Shared integration issue #77 owns the canonical descriptor, manifest and independent revisions, permanent requirements and generated docs, compatibility digest/matrix, visual row, central API/browser/restart coverage, and catalog-discovered Long Suite acceptance. The packaged application release is owned by `pyproject.toml` and `modules/module-manifest.json`; this compatible addition advanced only the independent source-module revisions.
