# Multi-Hand Video Poker

Issue: [#94](https://github.com/andreivorobiev/virtual-casino-simulator/issues/94)

This isolated module implements Jacks-or-Better with 3, 5, and 10 final hands. One five-card source hand is dealt first. Held positions are copied into every final hand, while each hand receives replacements from its own independently shuffled copy of the remaining 47 cards.

The engine uses `casino.core.cards` and `casino.core.poker` from #96. A seed exists only as an injected Python test hook; the API never accepts caller-controlled seeds.

## Session and settlement invariants

- The API reads the player ID already replaced by the current router or the #81 session-bound resolver. It does not trust a frontend identity to select state or a wallet.
- `request_id` is required when starting a round. Reusing it with the same settings returns the original round; reusing it with different wager settings fails.
- One aggregate `MHVP_WAGER_DEBIT` covers `hand_count * wager_per_hand`.
- One aggregate `MHVP_PAYOUT_CREDIT` returns all qualifying hand credits.
- State is persisted before either movement, and retry recovery searches ledger events by player, game, round, and transaction type before issuing a movement.
- A process-local settlement lock serializes the state/ledger recovery path used by this local simulator.
- The game module never mutates `player.balance` or any storage-provider balance field directly.

## Public actions

- `GET /api/v1/games/multi-hand-video-poker/state`
- `POST /api/v1/games/multi-hand-video-poker/rounds`
- `POST /api/v1/games/multi-hand-video-poker/rounds/{round_id}/holds`
- `POST /api/v1/games/multi-hand-video-poker/rounds/{round_id}/draw`

The handlers can be registered into an isolated `casino.router.Router` for focused tests. Global registration is catalog-driven from `modules/multi_hand_video_poker.json`.
