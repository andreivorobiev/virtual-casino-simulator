# Joker Poker

Issue: [#130](https://github.com/andreivorobiev/virtual-casino-simulator/issues/130)

This isolated draft freezes a distinct Joker Poker profile: one 53-card deck, one wild joker, one five-card draw hand, Kings-or-Better high-pair qualification, and joker-only paytable rows for five of a kind and wild royal flush. That makes it materially different from Multi-Hand Video Poker, which is Jacks-or-Better, no-joker, and multiplies one common hand across 3, 5, or 10 result lanes.

The engine reuses `casino.core.cards` for natural cards and `casino.core.poker` for standard five-card evaluations. Joker substitution and the return table remain game-owned because wild-card rules are not part of the shared standard evaluator.

## Session and settlement invariants

- The API resolves the player through the authenticated router context before any state or ledger access.
- `action_id` is required for both deal and draw actions. Reusing an action with the same semantic payload recovers the original result; reusing it with changed wager, round, or hold data fails closed.
- One `JOKER_POKER_WAGER_DEBIT` debits the single-hand wager.
- One optional `JOKER_POKER_PAYOUT_CREDIT` returns the final hand payout.
- State is persisted before either ledger movement, and retry recovery searches ledger events by player, game, round, and action identity before issuing a movement.
- The game module never mutates `player.balance` or any storage-provider balance field directly.

## Public actions

- `GET /api/v1/games/joker-poker/state`
- `POST /api/v1/games/joker-poker/rounds`
- `POST /api/v1/games/joker-poker/rounds/{round_id}/holds`
- `POST /api/v1/games/joker-poker/rounds/{round_id}/draw`

The handlers can be registered into an isolated `casino.router.Router` for focused tests. Shared catalog, global app registration, permanent requirements, and visual matrix integration remain owned by #77.
