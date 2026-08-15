# Casino Hold'em

Issue: [#139](https://github.com/andreivorobiev/virtual-casino-simulator/issues/139)

This isolated module implements an Ante-backed two-card hand, a three-card flop, one `call` or `fold` decision, and a dealer-qualified five-card showdown. It reuses shared card evaluation and settlement services while retaining Casino Hold'em qualification and Ante-return rules locally.

## Fixed table rules

- The Ante reveals two player cards and the three-card flop.
- Call costs two additional Ante units and reveals the turn, river, and dealer cards.
- Fold forfeits the Ante without a second wager or settlement credit.
- The dealer qualifies with a pair of fours or better.
- A non-qualifying dealer returns the Call and pays the Ante through the documented Ante schedule.
- Qualified wins, pushes, and losses use the server-owned evaluator and returned-token settlement values.

## Public actions

- `GET /api/v1/games/casino-holdem/state`
- `POST /api/v1/games/casino-holdem/rounds` with `action_id` and `wager`
- `POST /api/v1/games/casino-holdem/rounds/{round_id}/decision` with `action_id` and `decision` (`call` or `fold`)

The shared HTTP handler supplies the standard `ok/data` or `ok/error` envelope. Game handlers return the data object only.

## Session, persistence, and settlement invariants

- The route adapter binds every action to the authenticated player; body and query player IDs cannot override that session.
- Player state is loaded through `load_player_game_state` and published through provider-current `update_player_game_state` callbacks that compare only the active round, recent rounds, and durable action receipts.
- Stale processes fail closed before overwriting a winning decision, while unrelated provider siblings survive preparation, recovery, and rejected-action rollback.
- The complete private table is persisted before the Ante; dealer cards, turn, and river remain hidden until a committed Call settles.
- Every client action is bound to a normalized request fingerprint. An altered retry fails closed.
- Ante, Call, and returned-token movements use stable ledger action identities and recover immutable proof without repeating a debit or credit.
- Public v1 routes, envelopes, card rules, paytables, and ledger transaction names remain unchanged by provider-atomic state publication.

Shared catalog registration, the aggregate manifest revision for `casino_holdem`, compatibility digests, permanent requirements `CH-001` through `CH-007`, and catalog-driven discovery are complete on main.
