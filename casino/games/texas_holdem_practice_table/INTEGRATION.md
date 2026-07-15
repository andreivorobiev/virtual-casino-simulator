# Texas Hold'em Practice Table integration handoff for #77

Issue #95 is refreshed on pull request #120 after the accepted issue #190 storage-action primitive and issue #189 funded-opponent account seam. The draft now carries its canonical module descriptor, permanent planned requirements, compatibility metadata, visual row, central API/browser/restart discovery, and catalog long driver.

## Canonical catalog identity

- Module: `texas_holdem_practice_table` `1.0.0`.
- Route: `/games/texas_holdem_practice_table`.
- Sort order: `200`.
- Backend: `casino.games.texas_holdem_practice_table.api:register`.
- Frontend: `TexasHoldemPracticeTableGame` with `[data-testid='texas-holdem-practice-table']`.
- Long driver: `tests.game_drivers.texas_holdem_practice_table:play`.
- Contract: `contracts/openapi/texas_holdem_practice_table.v1.yaml`.
- Packaged application impact: none; the packaged version remains `9.1.1`.

Catalog discovery remains descriptor-driven. No game-specific registry, router, shell, validator, or long-suite allowlist is introduced.

## Permanent requirement allocation

`THPT-001` through `THPT-005` cover rules, authenticated privacy/restart, four-wallet settlement, EN/RU browser behavior, and discovered evidence. They remain `PLANNED` because issue #191 is a durable acceptance blocker; this refresh does not claim that certification or count the game toward issue #73.

## Funded opponent settlement

The fixed seats map privately to the accepted issue #189 accounts:

- `opponent_1` to `bot_1` (Ava).
- `opponent_2` to `bot_2` (Mia).
- `opponent_3` to `bot_3` (Zoe).

Before a hand reserves exposure, the controller replays the same one-time funding identities used by Admin. The human and all three bot accounts then reserve five wager units through storage-enforced ledger actions. Calls consume only the reserved table stack. Settlement returns each seat's unused escrow and credits each pot share through distinct storage-enforced actions.

Opponent movements use `casino.core.practice_accounts` and include bot, game, hand, controller action, component, action key, and owning human session context in Admin-visible ledger details. Normal game responses expose only seat labels, redacted or revealed cards, table stacks, contribution totals, and settlement counts; bot wallet ids and owner correlation are not projected.

## Retry, restart, and concurrency boundary

Human and bot money movements consume the issue #190 `debit_once` and `credit_once` storage boundary. Exact action semantics replay the original ledger event, changed key reuse fails closed, and the accepted JSON/MySQL provider evidence covers restart, lost-response, and cross-process uniqueness. Player-scoped hand state is prepared before settlement and recovers committed ledger markers after reload.

The separately owned issue #191 still requires the complete hostile-client and server-authority certification for the then-current catalog, including this game. This draft does not invent that implementation or weaken its raw mutation, cross-user, replay, concurrency, restart, multi-process, and client-tamper matrix.

## Visual matrix

Surface `texas_holdem_practice_table` requires `en-US` and `ru-RU` at desktop primary, desktop compact, tablet, and mobile for:

- `ready`
- `preflop_decision`
- `flop_decision`
- `turn_decision`
- `river_decision`
- `showdown`
- `folded`
- `settled`
- `reduced_motion`
- `route_restored`

Only exact-head `after_pass` evidence from the registered real backend may be used in the pull-request handoff.

## Acceptance boundary

Pull request #120 remains draft. Do not mark it ready, merge it, close #95, or count Texas Hold'em until issue #191 is separately implemented and accepted for the current catalog and #120 extends and passes the applicable certification matrix. Issues #122 and #124 remain held.
