# Dragon Tiger

Issue: [#83](https://github.com/andreivorobiev/virtual-casino-simulator/issues/83)

This isolated module implements the named `standard-8d` profile: eight standard decks, no jokers, three burned cards on each new shoe, a fifty-two-card cut reserve, Dragon dealt first, Tiger dealt second, ace low, and rank-only comparison.

## Settlement

- Dragon and Tiger wins pay net `1:1`, producing a total credit of twice the wager.
- Tie wins pay net `11:1`, producing a total credit of twelve times the wager.
- Dragon or Tiger bets on a tie return half the wager and therefore record a half-loss.
- Every wager uses one `DRAGON_TIGER_WAGER_DEBIT`; positive returns use at most one `DRAGON_TIGER_SETTLEMENT_CREDIT`.

## Retry and session invariants

- `action_id` is required and matches `^[A-Za-z0-9._:-]{8,128}$`.
- The normalized `{bet, wager}` request has a deterministic fingerprint and player-scoped round ID.
- Prepared cards, results, and pre-movement stages persist before ledger calls; stable ledger evidence recovers completed writes without another deal or balance movement.
- A durable settled-action index preserves exact round and ledger replay beyond the bounded recent-history view.
- If the shared JSON provider changes a balance but fails before appending its evidence, the persisted attempted stage fails closed for reconciliation instead of risking a second debit or credit.
- Reusing an action ID with different input fails closed.
- Shared router/session identity always overrides caller-supplied `player_id` compatibility input.
- Production entropy is never caller-controlled; focused tests inject a complete deterministic standard-8d shoe.

## Public actions

- `GET /api/v1/games/dragon-tiger/state`
- `POST /api/v1/games/dragon-tiger/rounds` with `{action_id, bet, wager}`

The local proposal maps gameplay, session/reload safety, ledger retry safety, EN/RU behavior, and integration evidence to `DT-001` through `DT-005`. Issue #77 owns permanent central requirement registration and shared catalog acceptance.
