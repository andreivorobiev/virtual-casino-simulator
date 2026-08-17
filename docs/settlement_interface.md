# Catalog-Wide Settlement Interface

Issue #430 converges all 46 registered game backends on `casino.core.settlement.GameSettlementGateway`. The gateway delegates every production token movement to `SettlementAdapter`, which alone calls the storage-atomic ledger `debit_once` and `credit_once` boundaries. Issue #703 completed the follow-up migration by retiring the gateway's mutation aliases on 2026-08-17.

## Required contract

- The game calls `apply_once` with only `player_id`, `signed_amount`, `transaction_type`, `round_id`, `action_key`, `request_fingerprint`, and optional `details`.
- The adapter records canonical `game_action_key`, `request_fingerprint`, and `round_id` details and preserves additional game evidence.
- Exact retries replay the committed event. Reuse under another player, game, amount, transaction type, round, or fingerprint fails closed.
- Debits still commit when the existing game API accepts a wager, ticket, card, insurance, split, or double. Credits and refunds retain their existing reveal and settlement timing.
- `/api/v1` request and response envelopes are unchanged.

## Migration cohorts

The shared-simple games delegate through `SimpleWagerGame`. Big Six Wheel uses representation adapters, while Sic Bo, Chuck-a-Luck, Over/Under 7, Crown and Anchor, Fan-Tan, and Dragon Tiger additionally use the helper's prepared-state lifecycle protocol; none of these games constructs a settlement gateway or calls `apply_once`. Baccarat, Keno, and Texas Hold'em Practice Table use the gateway directly. Roulette, Bingo, and Blackjack use it for every wager, refund, and settlement path. Scratch Cards and Slots no longer call raw ledger mutation functions. The formerly injected and staged-intent game services also delegate to the same gateway.

Chuck-a-Luck keeps its frozen `request_id`, `cal_` round identity, dice and wager proof details, and direct oldest-to-newest one-hundred-round public history. Its provider-current lifecycle persists private dice before the aggregate debit, recovers exact committed wager and returned-credit evidence after lost responses, and archives only a terminal action through the shared helper.

Over/Under 7 keeps its frozen `action_id`, `ou7_` round identity, dice and wager proof details, and direct oldest-to-newest one-hundred-round public history. Its provider-current lifecycle persists private dice before the aggregate debit, recovers exact committed wager and returned-credit evidence after lost responses, and archives only a terminal action through the shared helper.

Crown and Anchor keeps its frozen `client_request_id`, `caa_` round identity, face and wager proof details, and direct oldest-to-newest one-hundred-round public history. Its provider-current lifecycle persists private faces before the aggregate debit, recovers exact committed wager and returned-credit evidence after lost responses, and archives only a terminal action through the shared helper.

Fan-Tan keeps its frozen `action_id`, `ft_` round identity, pile-count and wager proof details, nested state response, and direct oldest-to-newest one-hundred-round public history. Its provider-current lifecycle persists the private counted pile before the aggregate debit, recovers exact committed wager and returned-credit evidence after lost responses, and archives only a terminal action through the shared helper.

Dragon Tiger keeps its frozen `action_id`, `dt_` round identity, standard eight-deck shoe, card and wager proof details, shoe summary, direct oldest-to-newest fifty-round public history, and unbounded durable action replay index. Its provider-current lifecycle persists dealt cards and rollback proof before the debit, recovers exact committed wager and returned-credit evidence after lost responses, reconstructs historical ledger-only actions without consuming current shoe cards, and archives only a terminal action through the shared helper.

Texas Hold'em Practice Table's fixed opponent accounts are not player wallets and continue to use the separate core practice-account transaction. Every human action uses the common settlement gateway.

## Deprecated paths

Game modules must not import `casino.core.ledger` or call `ledger.debit`, `ledger.credit`, `ledger.debit_once`, or `ledger.credit_once`. Game-owned ledger gateways, process-local idempotency ownership, and direct mutation callbacks are retired as production boundaries. Prepared controller and callback adapters may translate their existing internal state into the canonical call, but the public gateway mutation method accepts no `amount`, `drop_id`, `card_id`, `ledger_action_id`, `action_id`, or `fingerprint` aliases.

Historical ledger rows are immutable. The gateway therefore retains configured game-specific detail keys for read and write audit compatibility while every event written on or after 2026-08-17 also contains the universal `game_action_key`, `request_fingerprint`, and `round_id` identity fields. These detail fields remain ledger evidence only: they are not accepted as mutation-method parameter aliases.

## Prevention and evidence

`scripts/validate_module_boundaries.py` derives the complete game inventory from the runtime catalog and rejects direct game ledger imports or mutation calls. `API-GAMECORE-004` runs that exact gate. `TEST-241` also pins the gateway's canonical keyword-only signature and parses every production game call to reject a retired explicit keyword. The generated server-authority matrix derives each game's `settlement_interface` from checked-in source and fails generation if any registered game cannot prove the shared boundary.

The game API suites, storage concurrency evidence, required contract validation, and normal Browser workflow remain mandatory before merge. This interface migration does not change paytables, house edge, outcomes, or client-visible animation timing.

## Delivery tickets

Issue #430 owns the catalog-wide contract. Its fourteen work items #621 through #634 delivered the shared boundary, and issue #703 subsequently ported the remaining games and retired the transitional mutation aliases. API envelopes, paytables, and immutable historical ledger evidence remain unchanged.
