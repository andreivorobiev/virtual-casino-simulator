# Caribbean Stud

Issue: [#132](https://github.com/andreivorobiev/virtual-casino-simulator/issues/132)

Parents: #66, #73

Shared integration lane: #77

## Draft Scope

This isolated draft implements a countable Caribbean Stud module without shared catalog or router registration. The game exposes a player-scoped service, additive v1 contract proposal, lazy frontend module, paired EN/RU resources, focused tests, and evidence artifacts. Shared integration remains intentionally blocked for #77.

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

The draft routes are:

- `GET /api/v1/games/caribbean-stud/state`
- `POST /api/v1/games/caribbean-stud/rounds`
- `POST /api/v1/games/caribbean-stud/rounds/{round_id}/call`
- `POST /api/v1/games/caribbean-stud/rounds/{round_id}/fold`

All operations use the standard `{ ok: true, data: ... }` / `{ ok: false, error: ... }` envelope when integrated through the shared API handler. Optional `player_id` fields are compatibility inputs only; the authenticated session resolver takes precedence.

## UI and Locale Boundary

The frontend module is `web/games/caribbean_stud.js`. It uses no game timers, clears locale subscriptions on unmount, respects reduced motion in route-local CSS, uses the shared accessible card renderer, and keeps all visible and ARIA copy in `web/i18n/en-US/games/caribbean_stud.json` and `web/i18n/ru-RU/games/caribbean_stud.json`.

## #77 Integration Blocker

This branch does not register Caribbean Stud in shared manifests, routing, shell navigation, requirement matrices, compatibility digests, visual matrix rows, long-suite discovery, or release/version files. Those are owned by #77 after the isolated draft is reviewed.
