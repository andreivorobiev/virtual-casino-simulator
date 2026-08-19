# Let It Ride

Issue: [#134](https://github.com/andreivorobiev/virtual-casino-simulator/issues/134)

This catalog-integrated module implements Let It Ride as a staged five-card poker table. The player starts each round with three equal play-token wagers, receives three player cards, then makes two decisions to either pull one eligible wager back or let the remaining wagers ride before the two community cards complete the hand.

The engine uses `casino.core.cards` and `casino.core.poker` from #96. A seed exists only as an injected Python test hook; the API never accepts caller-controlled seeds.

## Distinct Countable Module

Let It Ride is distinct from the existing poker/card modules because its rule nucleus is the staged withdrawal of two of three equal wagers before evaluating three player cards plus two community cards. Multi-Hand Video Poker deals and redraws independent poker hands, Red Dog and Acey-Deucey resolve spread/in-between decisions, Casino War and Dragon Tiger compare high cards, and Hi-Lo predicts one higher/lower card. None of those modules implement three equal base wagers with two player withdrawal beats and a shared-community five-card poker result.

## Session and Settlement Invariants

- The API reads the player ID already resolved by the shared router/session context. Body or query compatibility IDs do not choose state or wallet ownership.
- `action_id` is required for the opening wager and each staged decision.
- One `LET_IT_RIDE_WAGER_DEBIT` covers all three equal opening wagers.
- Each pulled wager prepares one `LET_IT_RIDE_REFUND_CREDIT`.
- One optional `LET_IT_RIDE_PAYOUT_CREDIT` returns active riding stakes plus qualifying profit after the final reveal.
- State is persisted before any play-token movement, and retry recovery searches ledger events by player, game, round, and game-owned action id before issuing a movement.
- A bounded player-scoped stripe serializes each wallet's state/ledger recovery path without blocking unrelated MySQL wallets.
- The game module never mutates `player.balance` or any storage-provider balance field directly.

## Public Actions

- `GET /api/v1/games/let-it-ride/state`
- `POST /api/v1/games/let-it-ride/rounds`
- `POST /api/v1/games/let-it-ride/rounds/{round_id}/first-decision`
- `POST /api/v1/games/let-it-ride/rounds/{round_id}/second-decision`

The handlers can be registered into an isolated `casino.router.Router` for focused tests and are discovered globally from `modules/let_it_ride.json`.
