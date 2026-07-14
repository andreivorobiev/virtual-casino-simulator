# Big Six Wheel

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

The game follows the frozen v1 handler shape and consumes the shared authenticated request context before compatible body or query values. Normal-user session identity therefore wins over hostile caller input. All state documents, ledger lookups, and response history are scoped to that resolved player.

## Shared integration through #77

The integrated descriptor remains version `1.0.0` and the shared lane:

- registers `big_six_wheel: 1.0.0` in the aggregate manifest at catalog sort order 90;
- maps permanent `BIG-SIX-001` through `BIG-SIX-005` requirements to API, browser, long-suite, and visual evidence;
- registers the additive contract in the shared digest and compatibility inventories;
- discovers the backend, lazy frontend, and `tests.game_drivers.big_six_wheel:play` from the module descriptor;
- governs `ready`, `spinning`, `settled`, `reduced_motion`, and `route_restored` visual states for both locales and all four required viewports;
- requires real-backend `after_pass` screenshots and exact-head evidence before PR acceptance.

The game implementation remains isolated from every other game package; only the #77 lane owns these shared integration records.
