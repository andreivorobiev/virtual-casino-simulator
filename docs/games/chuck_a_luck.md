# Chuck-a-Luck isolated game slice

Issue: [#89](https://github.com/andreivorobiev/virtual-casino-simulator/issues/89)

Parents: #66, #73

Shared integration lane: #77

Dice and motion dependency: #97

## Provisional requirement boundary

This isolated proposal uses the provisional `CHUCK` requirement prefix only. It does not allocate or claim permanent requirement IDs. Issue #77 must allocate permanent mappings for rules and deterministic outcomes, ledger and retry safety, session-bound API behavior, localized responsive browser behavior, and reduced-motion/timer cleanup before integration.

## Rules profile

This simulator exposes the traditional number wagers only: a player may cover any of faces one through six, then the server rolls three six-sided dice. One matching die pays 1 to 1 net, two matching dice pay 2 to 1 net, and three matching dice pay 3 to 1 net. Each winning return also includes the original stake. Unselected faces and side bets are deliberately outside this game profile.

The profile follows the Chuck-a-Luck rules in the public [Seneca Nation Tribal-State Gaming Compact](https://www.bia.gov/sites/default/files/dup/assets/as-ia/oig/pdf/508_compliant_2002.12.09_seneca_nation_of_indians_tribal_state_gaming_compact_0.pdf), which specifies the same one-, two-, and three-die number payouts. All visible copy uses fake-money play-token terminology.

## Deterministic and reload-safe model

- `engine.roll_dice` accepts an injected bounded random callable and validates exactly three ordered faces from one through six.
- `engine.settle` is pure for a normalized wager map and committed dice vector.
- The public API never accepts forced dice. Focused tests inject entropy at the service boundary.
- The round id is a stable digest of the authenticated player id and required `request_id`.
- The committed wager debit stores the authoritative dice, so retry recovery cannot replace an already chosen result.
- Player-owned state retains bounded settled history and reload restores the latest server result without client recomputation.

## Ledger and retry-safe settlement

One roll is one atomic game action:

1. Normalize the complete one-through-six wager map and derive a semantic request fingerprint.
2. Choose the three server-authoritative dice before debit and place them in the wager debit's ledger details.
3. Apply one aggregate `CHUCK_A_LUCK_WAGER_DEBIT` through `casino/core/ledger.py` with action key `<round_id>:wager`.
4. Calculate every return from the committed wagers and dice.
5. When at least one wager wins, apply one aggregate `CHUCK_A_LUCK_SETTLEMENT_CREDIT` containing returned stakes plus net winnings with action key `<round_id>:settlement`.
6. Persist the settled player-owned state only after all required ledger actions commit.

On retry, the game scans only that player's ledger under a process lock. A committed debit supplies the original dice after a post-debit interruption, and a committed settlement credit is returned instead of repeated. Reusing one `request_id` with different wagers fails closed. The adapter provides this exactly-once behavior for the intended single-process local simulator; any future multi-process deployment must enforce a unique ledger idempotency key in shared storage before making the same claim.

Game code never writes balances directly. Insufficient funds, balance mutation, event creation, and provider persistence remain owned by the shared ledger.

## Session boundary and additive v1 API

The game owns additive `GET /api/v1/games/chuck-a-luck/state` and `POST /api/v1/games/chuck-a-luck/rolls` handlers. Both return data through the shared `{ ok: true, data: ... }` or `{ ok: false, error: ... }` envelope. The shared authenticated router binds the effective player identity before dispatch; a compatibility `player_id` field cannot override that identity. State documents, ledger proof, player snapshots, and recent rounds remain scoped to the bound player.

## Browser behavior

The game-local frontend and paired `en-US` / `ru-RU` resources provide:

- a control rail for face wagers, a stable three-die stage, paytable, result status, and recent history;
- server-authoritative settlement with decorative dice preview only;
- responsive desktop-primary, desktop-compact, tablet, and mobile layouts without horizontal overflow;
- reduced-motion behavior that reveals the result without decorative delay;
- one owned timer scope that survives locale-only rerenders, releases completed reveals, and cancels every pending callback on route teardown;
- retained `request_id` and wagers after an ambiguous network failure so retry reuses the exact action.

The dice preview, deterministic motion seam, reduced-motion branch, and timer ownership follow the shared primitives established by issue #97.

## Integration handoff for #77

The isolated descriptor proposes module version `1.0.0` and reserved sort order `150`. Integration must:

- add `chuck_a_luck: 1.0.0` to `modules/module-manifest.json`;
- allocate permanent Chuck-a-Luck API/browser/test requirement IDs and replace the provisional `CHUCK` mapping;
- register the contract in the shared compatibility or digest inventory;
- let catalog discovery register `casino.games.chuck_a_luck.api:register`, `ChuckALuckGame`, both locale resources, and `tests.game_drivers.chuck_a_luck:play`;
- add the `chuck_a_luck` visual-matrix surface with `ready`, `rolling`, `settled`, `reduced_motion`, and `route_restored` states for `en-US` and `ru-RU` at all four required viewports;
- capture and review real-backend `after_pass` evidence after the shared route and catalog entry are integrated.

No shared catalog, router, configuration, shell, global i18n, test runner, long-suite registry, visual matrix, central requirement registry, generated documentation, compatibility matrix, or aggregate manifest file is changed by this isolated slice.
