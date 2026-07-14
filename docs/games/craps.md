# Craps isolated game slice

Issue: [#90](https://github.com/andreivorobiev/virtual-casino-simulator/issues/90)

Parents: #66 and #73. Shared integration owner: #77. Dice and motion dependency: completed #97.

## Bounded rules profile

This simulator intentionally implements only Pass Line and Don't Pass play. It does not claim support for odds, Come, Don't Come, Place, Field, proposition, Fire, Bonus, or Dice-Ology wagers.

The rule profile follows the [Maryland State Lottery and Gaming Control Agency Craps Standard Rules, version 1.5](https://www.mdgaming.com/wp-content/uploads/2024/06/Craps-Standard-Rules-Version-1.5.pdf):

- A Pass Line wager wins on a come-out total of 7 or 11 and loses on 2, 3, or 12.
- A Don't Pass wager wins on a come-out total of 2 or 3, loses on 7 or 11, and is void and refunded on 12.
- A come-out total of 4, 5, 6, 8, 9, or 10 establishes the point.
- After a point is established, Pass Line wins when the point repeats before 7 and Don't Pass wins when 7 arrives before the point; the opposing line wager loses.
- A win returns the original stake plus a one-to-one win. A Don't Pass come-out 12 returns only the original stake.

Dice are selected only by the backend. The public API accepts no forced dice, seed, or result field. Focused tests inject deterministic entropy behind the service boundary.

## Additive API

The game owns three additive `/api/v1` operations:

| Method | Path | Behavior |
| --- | --- | --- |
| `GET` | `/api/v1/games/craps/state` | Returns the authenticated player's active round, recent rounds, player snapshot, and supported line bets. |
| `POST` | `/api/v1/games/craps/rounds` | Creates or replays one wagered round from `request_id`, `bet_type`, and `wager`. |
| `POST` | `/api/v1/games/craps/rounds/{round_id}/rolls` | Creates or replays one server-authoritative roll from a new action `request_id`. |

An optional `player_id` remains documented only for focused-test and legacy compatibility. The shared authenticated-session resolver overwrites caller body and query identities before a game handler sees them. Every external response uses the standard `ok/data` or `ok/error` envelope.

## Reload-safe state

One round persists its authenticated player, start request identity, line bet, wager, phase, point, ordered rolls, terminal outcome, ledger markers, and timestamps. The active round survives browser reloads and backend restarts through the player-game state store. Terminal rounds remain in a private durable action journal so a request identity does not expire when it leaves the UI; the public `recent_rounds` projection exposes only the newest 20. A repeated terminal roll request returns the original dice and resolution rather than advancing the game.

The public phases are:

- `come_out`: the line wager is committed and the next roll can decide immediately or establish a point;
- `point`: subsequent rolls continue until the point or 7 appears;
- `settled`: the terminal result and any required credit or refund are durable.

## Ledger and retry safety

Game code never mutates a player balance directly.

1. The service persists a pending round before applying `CRAPS_WAGER_DEBIT` through `casino/core/ledger.py`.
2. The wager action uses deterministic identity `<round_id>:wager`, records the semantic request fields in ledger details, and caches verified ledger proof in private game state.
3. Every roll request identity and dice result are persisted before any terminal credit is attempted.
4. A winning round applies one `CRAPS_PAYOUT_CREDIT` for twice the wager with identity `<round_id>:settlement`.
5. A Don't Pass come-out 12 applies one `CRAPS_PUSH_REFUND` for the original wager under the same terminal identity.
6. A losing round writes no zero-value credit and marks settlement complete after its terminal roll is durable.
7. Pending crash markers search the complete same-player ledger history, while completed markers use durable cached proof and never authorize a replacement movement.
8. Exact retries recover committed ledger events and state even after the round leaves public history. Reusing an action identity with conflicting settings fails closed.

The private journal intentionally trades local state growth for durable action ownership. The read-before-write ledger guard is protected by one process-local lock and is appropriate for this local single-process simulator. A future multi-process deployment must add a durable storage-level unique idempotency constraint before claiming cross-process exactly-once behavior.

## Frontend and motion

The lazy `CrapsGame` module owns its responsive three-zone layout, all game-visible styling, and every visible or ARIA string in paired EN/RU resources. Decorative dice frames use the shared `web/core/dice.js` helpers, but the final faces always come from the backend response. Motion timing uses `web/core/motion.js`, collapses under reduced-motion preferences, and disposes all scheduled callbacks on route exit or reload.

The intended stage keeps the current point, two dice, primary action, and wager controls visible at the desktop-primary viewport. Tablet and mobile stack controls, stage, and history without horizontal overflow.

## Requirement mapping proposal

The game descriptor carries the provisional `CRAPS` prefix. Only #77 may allocate these permanent central entries and change them from `PLANNED` to `PASS` after integrated evidence succeeds.

| Proposed ID | Acceptance dimension | Existing requirements also exercised |
| --- | --- | --- |
| `CRAPS-001` | Pass Line and Don't Pass come-out, point, win, loss, and refund rules | — |
| `CRAPS-002` | Additive API, authenticated player binding, reload-safe state, and deterministic test seams | `API-001`, `SESSION-005` |
| `CRAPS-003` | Ledger-only wager, payout, refund, conflict detection, and single-process retry recovery | `LEDGER-005`, `LEDGER-006`, `LEDGER-007`, `LEDGER-009`, `LEDGER-023` |
| `CRAPS-004` | Complete EN/RU visible and ARIA copy, responsive layout, shared dice presentation, reduced motion, and timer cleanup | `DICE-001`, `I18N-001`, `I18N-002`, `MOTION-001`, `MOTION-002`, `MOTION-003` |
| `CRAPS-005` | Catalog, contract, long-driver, browser, visual, version, and evidence discovery | `TEST-042` |

## Shared integration handoff for #77

This isolated descriptor proposes module version `1.0.0`, route `/games/craps`, catalog sort order `160`, and only existing `table`, `numbers`, and `strategy` categories. It deliberately does not edit shared catalog, router, shell, test-runner, requirement, compatibility, visual-matrix, or aggregate-version files.

#77 must later:

- add `craps: 1.0.0` to `modules/module-manifest.json` and recalculate shared application, tests, docs, and contracts revisions from the then-current accepted base;
- allocate `CRAPS-001` through `CRAPS-005`, update central and generated requirement documents, and map permanent API/browser test IDs;
- add `contracts/openapi/craps.v1.yaml` to the compatibility module matrix and contract digest inventory;
- add the visual-matrix `craps` surface with `ready`, `come_out`, `point_active`, `settled`, `reduced_motion`, and `route_restored` states for both locales and all four standard viewports;
- run real authenticated catalog/API/browser/long-suite acceptance and capture evidence from the exact integrated head;
- keep the game pull request draft until the coordinator explicitly releases readiness.

Before that shared revision entry exists, `scripts/validate_versions.py` is expected to report `module manifests missing from aggregate manifest: craps`, catalog validation is expected to report that Craps has no canonical module revision, and the shared shell cannot honestly be claimed as integrated acceptance.
