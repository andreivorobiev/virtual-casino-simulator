# Three Card Poker

Issue: [#93](https://github.com/andreivorobiev/virtual-casino-simulator/issues/93)

This isolated module implements a required Ante, an optional Pair Plus wager, a three-card deal, and one `play` or `fold` decision. It reuses `casino.core.cards` for normalized cards and deterministic test shuffles while keeping the game-specific three-card evaluator local.

## Fixed table rules

- Hand order: straight flush, three of a kind, straight, flush, pair, high card.
- `A-2-3` is the lowest straight and `A-K-Q` is the highest straight.
- The dealer qualifies with queen-high or better.
- Play costs one additional Ante.
- Fold forfeits both Ante and Pair Plus.
- Ante Bonus A uses profit odds: straight flush `5:1`, three of a kind `4:1`, straight `1:1`.
- Pair Plus C uses profit odds: straight flush `40:1`, three of a kind `30:1`, straight `6:1`, flush `3:1`, pair `1:1`.

## Public actions

- `GET /api/v1/games/three-card-poker/state`
- `POST /api/v1/games/three-card-poker/rounds` with `request_id`, `ante`, and optional `pair_plus`
- `POST /api/v1/games/three-card-poker/rounds/{round_id}/decisions` with `action_id` and `decision` (`play` or `fold`)

The shared HTTP handler supplies the standard `ok/data` or `ok/error` envelope. Game handlers return the data object only.

## Session, persistence, and settlement invariants

- The route adapter calls the shared authenticated-player resolver; body and query player IDs cannot override a bound session.
- Player state is loaded and saved through `load_player_game_state` and `save_player_game_state`.
- The complete deal is persisted before the initial aggregate debit; the public state hides all dealer cards until the decision settles.
- Every client identifier is bound to a normalized command fingerprint. An altered retry fails closed.
- Ledger movement uses deterministic per-movement identifiers stored in event details. Recovery matches player, game, round, transaction type, and action identifier before issuing a debit or credit.
- One initial debit covers Ante plus Pair Plus, one optional Play debit equals the Ante, and at most one aggregate payout credit returns all due stakes and winnings.
- Tests may inject IDs, clocks, and shuffle seeds. Public API requests cannot choose a seed.

Shared catalog registration, the aggregate manifest revision for `three_card_poker`, compatibility digests, permanent requirements `TCP-001` through `TCP-005`, and catalog-driven discovery are all complete on main.
