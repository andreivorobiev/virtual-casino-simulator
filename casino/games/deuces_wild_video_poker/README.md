# Deuces Wild Video Poker

Issue: [#92](https://github.com/andreivorobiev/virtual-casino-simulator/issues/92)

This isolated module implements single-hand, five-card draw poker with every physical deuce acting as a wild card. It uses the full-pay returned-credit profile documented by [Wizard of Odds](https://wizardofodds.com/games/video-poker/strategy/deuces-wild/full-pay/optimal/): natural royal 800, four deuces 200, wild royal 25, five of a kind 15, straight flush 9, four of a kind 5, full house 3, flush 2, straight 2, and three of a kind 1. The values are multipliers of the wager returned after the wager has already been debited.

The engine reuses `casino.core.cards` for card normalization, deck construction, and deterministic test shuffles. Deuce-free hands use `casino.core.poker.evaluate_five`; wild substitution, five of a kind, four deuces, and the game paytable stay local as required by the #96 primitive contract.

## Session and settlement invariants

- The API calls the shared authenticated-player resolver, so a bound session overrides body and query `player_id` values.
- Every POST requires an `action_id`. The normalized action semantics are persisted and conflicting reuse fails closed.
- The round ID is a stable digest of the resolved player and deal action ID. Ledger details use `<round_id>:wager` and `<round_id>:payout` idempotency keys.
- The initial hand and private replacement plan are persisted before the wager debit. Final cards and outcome are persisted before any payout credit.
- The wager fingerprint includes a private digest of that complete deal plan. Hold and draw actions revalidate the debit, and a new deal cannot enter while any retained payout still needs recovery.
- One `DWVP_WAGER_DEBIT` covers the round wager. At most one `DWVP_PAYOUT_CREDIT` returns qualifying credits; losing rounds never create a zero ledger event.
- Recovery scans only the resolved player's ledger and validates game, round, transaction type, signed amount, idempotency key, and semantic fingerprint before accepting a prior event.
- The process-local lock makes the read-before-write recovery path exactly once for the supported single-process local simulator. A future multi-process deployment must add a shared unique ledger idempotency constraint before extending that claim.
- The game never mutates a player balance or storage-provider balance field directly.

## Public actions

- `GET /api/v1/games/deuces-wild-video-poker/state`
- `POST /api/v1/games/deuces-wild-video-poker/rounds`
- `POST /api/v1/games/deuces-wild-video-poker/rounds/{round_id}/holds`
- `POST /api/v1/games/deuces-wild-video-poker/rounds/{round_id}/draw`

The handlers register into an isolated `casino.router.Router` for focused tests. Catalog/version/requirements/visual acceptance remains owned by issue #77 and is not claimed by this worker slice.
