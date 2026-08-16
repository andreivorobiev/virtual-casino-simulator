# Scratch Cards

Issue: [#87](https://github.com/andreivorobiev/virtual-casino-simulator/issues/87)

This isolated module implements one server-owned 3-by-3 instant card. A player starts a card with a 1, 2, 5, or 10 play-token wager and reveals cells through retry-safe public actions. Exactly three matching prize cells win that displayed prize. A losing card contains pairs and singletons only, so no accidental third match exists.

The explicit toy outcome profile is 70% no win, 18% 1x, 7% 2x, 3% 5x, 1% 10x, and 1% 25x. That profile has an 82% theoretical return. It is simulator documentation, not a fairness or real-money claim. The API never accepts a seed, forced result, hidden prize, or payout.

## Session and ledger invariants

- Every handler accepts the shared router context and gives `resolved_player_id` or `bound_player_id` precedence over caller input.
- `client_request_id` is required to start a card. Reusing a retained identity with the same wager recovers the original card; changed wagers and identities older than retained private state fail closed without rerolling or moving tokens.
- Each scratch request requires an `action_id` and a normalized position set. Conflicting reuse fails closed.
- One `SCRATCH_CARD_WAGER_DEBIT` funds a card and at most one `SCRATCH_CARD_PAYOUT_CREDIT` settles its match-three prize.
- Private board data is persisted before debit so a post-debit crash cannot reroll the card, while player-visible ledger details remain free of covered values.
- Final reveal intent is persisted before any payout credit, allowing a restart retry to recover without duplicate movement.
- The game never mutates a player balance or storage-provider balance field directly.
- Private card preparation, reveal progress, replay records, settlement state, and action-owned cleanup publish through provider-current callbacks that preserve unrelated player-document fields and reject stale writers. Ledger movement remains a separate durable boundary, so production multiworker activation stays blocked until state and money share a cross-process transaction.

## Public actions

- `GET /api/v1/games/scratch-cards/state`
- `POST /api/v1/games/scratch-cards/cards`
- `POST /api/v1/games/scratch-cards/cards/{card_id}/scratches`

Handlers register against an isolated `casino.router.Router` for focused tests. Global manifest, compatibility, requirement, and visual acceptance remains owned by issue #77.
