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

## Motion reliability remediation through #223

Version `1.0.1` preserves the game and API contract while correcting the browser presentation lifecycle:

- each target is calculated from the prior cumulative angle and advances through at least six complete clockwise turns;
- the painted wheel element receives its target in place, after a committed start frame, instead of being replaced at its final transform;
- the server-authoritative round stays hidden while the wheel moves, wager controls stay locked, and settlement publishes exactly once after presentation;
- reduced motion settles without decorative delay, while resize, locale change, route teardown, background/foreground suspension, and slow-device rendering retain safe ownership;
- the responsive layout stacks before the governed compact-desktop surface becomes cramped.

The integrated descriptor and shared lane now:

- register `big_six_wheel` in the aggregate manifest at catalog sort order 90, with the current revision owned by `modules/module-manifest.json`;
- map permanent `BIG-SIX-001` through `BIG-SIX-006` requirements to API, browser, long-suite, motion-soak, and visual evidence;
- register the additive contract in the shared digest and compatibility inventories;
- discover the backend, lazy frontend, and `tests.game_drivers.big_six_wheel:play` from the module descriptor;
- govern `ready`, `spinning`, `settled`, `motion_qualified`, `reduced_motion`, and `route_restored` visual states for both locales and all four required viewports;
- require real-backend `after_pass` screenshots and exact-head evidence before PR acceptance.

The standalone `tests/browser/big_six_wheel_motion_soak.py` gate performs 100 consecutive authenticated UI spins at each governed viewport. It records live Chromium transform progress and timestamps, checks exact server-selected segment alignment, cycles locale during motion, resizes during motion, freezes and restores one live page, applies four-times CPU throttling, verifies production WSGI `no-store` asset behavior, checks reduced motion, and proves controls and terminal data are scroll-reachable and not covered. Output contains only aggregate timings, counts, one-way uniqueness evidence, and top/stage/lower screenshots; synthetic runtime state is deleted after exact PID and port closure.

Development and production static cache parity discovered during this work is governed separately by `CORE-026` and `TEST-068` through issue #310. Production WSGI cache safety remains a required #223 qualification gate. The game implementation remains isolated from every other game package.
