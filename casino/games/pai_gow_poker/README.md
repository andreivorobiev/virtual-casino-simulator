# Pai Gow Poker

Issue: [#138](https://github.com/andreivorobiev/virtual-casino-simulator/issues/138)

This isolated module implements one Ante-backed seven-card hand, a legal five-card high and two-card low set, and a house-way dealer showdown. It keeps the semi-wild joker, copy-to-dealer rule, and five-percent win commission local while using the shared settlement boundary for every wallet movement.

## Fixed table rules

- One Ante deals seven public player cards and seven private dealer cards.
- The player sets a five-card high hand and two-card low hand, or selects the house way.
- The low hand may never outrank the high hand.
- The dealer always uses the deterministic house way and wins exact copies.
- Winning both hands returns the Ante plus even money minus five-percent commission.
- A split result pushes and a dealer sweep loses the Ante.
- The joker completes straights and flushes and otherwise acts as an ace.

## Public actions

- `GET /api/v1/games/pai-gow-poker/state`
- `POST /api/v1/games/pai-gow-poker/rounds` with `action_id` and `ante`
- `POST /api/v1/games/pai-gow-poker/rounds/{round_id}/decisions` with `action_id` and `set`

The shared HTTP handler supplies the standard `ok/data` or `ok/error` envelope. Game handlers return the data object only.

## Session, persistence, and settlement invariants

- The route adapter binds every action to the authenticated player; body and query player IDs cannot override that session.
- Player state is loaded through `load_player_game_state` and published through provider-current `update_player_game_state` callbacks that compare only the active round, recent rounds, and durable action receipts.
- Stale processes fail closed before overwriting a winning set, while unrelated provider siblings survive preparation, recovery, and rejected-action rollback.
- The complete private table is persisted before the Ante; dealer cards remain hidden until a committed set settles.
- Every client action is bound to a normalized request fingerprint. An altered retry fails closed.
- Ante and returned-token movements use stable ledger action identities and recover immutable proof without repeating a debit or credit.
- Public v1 routes, envelopes, card rules, house way, paytable, and ledger transaction names remain unchanged by provider-atomic state publication.

Shared catalog registration, the aggregate manifest revision for `pai_gow_poker`, compatibility digests, permanent requirements `PGP-001` through `PGP-007`, and catalog-driven discovery are complete on main.
