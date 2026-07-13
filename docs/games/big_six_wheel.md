# Big Six Wheel isolated game slice

Issue: [#86](https://github.com/andreivorobiev/virtual-casino-simulator/issues/86)

Parents: #66, #73

Shared integration lane: #77

Wave 0 dependency: #81 / draft PR #110

## Rules profile

This simulator uses one explicit 54-segment profile rather than claiming that every venue uses the same wheel. Clockwise from the Joker, the wheel follows the regulated order represented by `WHEEL_SEGMENTS`. Counts are 23 One, 15 Two, 8 Five, 4 Ten, 2 Twenty, 1 Joker, and 1 Crest. Net payouts are respectively 1, 2, 5, 10, 20, 45, and 45 to 1.

The profile is based on the public [Maryland Big Six standard rules](https://www.mdgaming.com/wp-content/uploads/2016/06/Big-Six-Standard-Rules-Final.pdf) and the matching [Pennsylvania wheel layout](https://www.law.cornell.edu/regulations/pennsylvania/58-Pa-Code-SS-619a-1) and [payout table](https://www.law.cornell.edu/regulations/pennsylvania/58-Pa-Code-SS-619a-3). Visible simulator copy uses symbol names and play-token terminology, not currency.

## Deterministic model

- `engine.select_index` accepts an injected `randbelow` callable and validates the exact `0..53` boundary.
- `engine.settle` is pure for a normalized wager map and selected index.
- The public API never accepts a forced result. Focused tests inject the entropy seam at the service boundary.
- A round id is a stable digest of the authenticated player id and required `client_request_id`.

## Ledger and exactly-once design

One spin is one atomic game action:

1. Normalize the complete wager map and derive a semantic request fingerprint.
2. Select the wheel index before debit and persist it in the wager debit's ledger details.
3. Apply one total `BIG_SIX_WAGER_DEBIT` through `casino/core/ledger.py` with action key `<round_id>:wager`.
4. Calculate all winning and losing rows from that committed index.
5. When applicable, apply one `BIG_SIX_SETTLEMENT_CREDIT` containing stake plus net winnings with action key `<round_id>:settlement`.
6. Persist the settled player-owned state only after required ledger actions commit.

On retry, the game scans that player's ledger under a process lock. A committed debit supplies the original result index, so a crash after debit cannot change the outcome. A committed settlement credit is returned instead of repeated. Reusing a `client_request_id` with different wagers fails closed. This exactly-once adapter assumes the intended single-process local simulator runtime; a future multi-process deployment must enforce a unique ledger idempotency key in shared storage before claiming the same guarantee.

Game code never writes balances directly. Insufficient funds, balance mutation, event creation, and atomic provider persistence remain owned by the shared ledger.

## Session boundary

The game follows existing v1 handler shape while expecting #81 to bind `body.player_id` from the authenticated request context before dispatch. Body precedence is deliberate: the shared router overwrites caller input for `/api/v1/games/*`; query/default handling remains only for Admin-compatible and focused-test use. All state documents, ledger lookups, and response history are scoped to that resolved player.

## Integration handoff for #77

The isolated descriptor is version `1.0.0`. Integration must:

- add `big_six_wheel: 1.0.0` to `modules/module-manifest.json` after #110 releases that file;
- allocate permanent Big Six API/browser/test requirement IDs and replace the descriptor's provisional `BIG-SIX` prefix mapping;
- register the new contract in any shared digest/compatibility inventory required after #110;
- let catalog discovery register the backend, lazy frontend, and `tests.game_drivers.big_six_wheel:play` without hard-coded shell edits;
- add the `big_six_wheel` visual-matrix surface with `ready`, `spinning`, and `settled` states for en-US and ru-RU at desktop primary, desktop compact, tablet, and mobile;
- capture real-backend `after_pass` screenshots and motion/reduced-motion evidence only after the shared route is reachable.

No shared catalog, router, shell, test runner, visual matrix, requirements registry, generated docs, or aggregate manifest file is changed by this slice.
