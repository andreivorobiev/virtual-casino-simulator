# Game Expansion Integration Sequence

Status: approved sequencing contract for GitHub issue #77.

Parent epic: #66. Game expansion parent: #73. Catalog foundation: completed issue #81 and merged pull request #110.

## Purpose

This document gives the #77 integration owner one durable merge order and one shared-file ownership boundary for accepting isolated game pull requests after the catalog foundation. It does not implement game rules; readiness follows only after the released game passes the complete integration gate.

## Approved intake order

The Product-approved serialized order is:

1. Pull request #111, Multi-Hand Video Poker for issue #94.
2. Pull request #113, Casino War for issue #82.
3. Pull request #112, Big Six Wheel for issue #86.
4. Pull request #116, Red Dog for issue #84, released after the first three accepted games merged.
5. Pull request #127, Dragon Tiger for issue #83, released after Red Dog merged.
6. Pull request #117, Hi-Lo for issue #85, released after Dragon Tiger merged.
7. Pull request #118, Three Card Poker for issue #93, released after Hi-Lo merged.
8. Pull request #115, Jacks or Better Video Poker for issue #91, next after Three Card Poker.
9. Pull request #119, Deuces Wild Video Poker for issue #92, merged after Jacks or Better.
10. Pull request #120, Texas Hold'em Practice Table for issue #95, held on issues #189 and #190.
11. Pull request #123, Scratch Cards for issue #87, released while Texas Hold'em remains held.
12. Pull request #125, Sic Bo for issue #88, merged after Scratch Cards.
13. Pull request #126, Chuck-a-Luck for issue #89, released after Sic Bo merged.
14. Pull request #121, Craps for issue #90, merged after Chuck-a-Luck.
15. Pull request #176, Crown and Anchor for issue #133, merged after Craps while Texas Hold'em remains held.
16. Pull request #171, Over/Under 7 for issue #135, merged after Crown and Anchor.
17. Pull request #175, Plinko for issue #136, released after Over/Under 7 merged.
18. Pull request #174, Fan-Tan for issue #137, released after Plinko merged.
19. Pull request #173, Andar Bahar for issue #140, released after Fan-Tan merged.
20. Pull request #172, Acey-Deucey for issue #149, released after Andar Bahar merged.
21. Pull request #180, Caribbean Stud for issue #132, released after Acey-Deucey merged.
22. Pull request #178, Let It Ride for issue #134, merged after Caribbean Stud.
23. Pull request #179, Casino Hold'em for issue #139, merged after Let It Ride.
24. Pull request #177, Joker Poker for issue #130, released after Casino Hold'em merged.
25. Issue #190, storage-enforced action idempotency, merged before funded opponent work.
26. Issue #189, funded practice-opponent accounts and Admin audit, released after #190.
27. Pull request #120, Texas Hold'em Practice Table for issue #95, released after #191 merged and refreshed to extend the accepted hostile-client certification.

Each game pull request remains draft until the preceding game is accepted, the current branch is rebased onto the resulting `main`, and the game passes the complete integration gate below. A later game must not pre-allocate or edit the shared version values owned by an earlier game.

## Catalog ordering allocation

Existing games retain sort orders 10 through 60. The approved expansion slots are:

| Sort order | Game | Issue | Integration state |
| ---: | --- | ---: | --- |
| 70 | Multi-Hand Video Poker | #94 | Merged PR #111 |
| 80 | Casino War | #82 | Merged PR #113 |
| 90 | Big Six Wheel | #86 | Merged PR #112 |
| 100 | Dragon Tiger | #83 | Merged PR #127 |
| 110 | Red Dog | #84 | Merged PR #116 |
| 120 | Hi-Lo | #85 | Merged PR #117 |
| 130 | Scratch Cards | #87 | Merged PR #123 |
| 140 | Sic Bo | #88 | Merged PR #125 |
| 150 | Chuck-a-Luck | #89 | Merged PR #126 |
| 160 | Craps | #90 | Merged PR #121 |
| 170 | Jacks or Better Video Poker | #91 | Merged PR #115 |
| 180 | Deuces Wild Video Poker | #92 | Merged PR #119 |
| 190 | Three Card Poker | #93 | Released draft PR #118 |
| 200 | Texas Hold'em Practice Table | #95 | Released PR #120 extending accepted #191 certification |
| 210 | Crown and Anchor | #133 | Merged PR #176 |
| 220 | Over/Under 7 | #135 | Merged PR #171 |
| 230 | Plinko | #136 | Merged PR #175 |
| 240 | Fan-Tan | #137 | Merged PR #174 |
| 250 | Andar Bahar | #140 | Merged PR #173 |
| 260 | Acey-Deucey | #149 | Merged PR #172 |
| 270 | Caribbean Stud | #132 | Merged PR #180 |
| 280 | Let It Ride | #134 | Merged PR #178 |
| 290 | Casino Hold'em | #139 | Merged PR #179 |
| 300 | Joker Poker | #130 | Released draft PR #177 |
| 310 | Pai Gow Poker | #138 | Merged |

This table records the slots approved under this lane and stops at sort order 310; further games have since been registered at higher sort orders. The live sort-order allocation is owned by the `game.sort_order` field of each `modules/*.json` descriptor, so read those rather than this table when picking or verifying a sort order.

Sort order is catalog presentation metadata, not an authorization to register a placeholder. Only complete game descriptors are loaded.

## Requirement allocation

Permanent game blocks are reserved as follows:

- `MHVP-001` through `MHVP-005` for game rules, additive API and session binding, ledger and retry safety, EN/RU browser behavior, and discovered test/visual evidence.
- `CW-001` through `CW-005` for the same five acceptance dimensions for Casino War.
- `BIG-SIX-001` through `BIG-SIX-005` for the same five acceptance dimensions for Big Six Wheel.
- `RD-001` through `RD-005` for the same five acceptance dimensions for Red Dog.
- `DT-001` through `DT-005` for the same five acceptance dimensions for Dragon Tiger.
- `HILO-001` through `HILO-005` for the same five acceptance dimensions for Hi-Lo.
- `TCP-001` through `TCP-005` for the same five acceptance dimensions for Three Card Poker.
- `JOBVP-001` through `JOBVP-005` for the same five acceptance dimensions for Jacks or Better Video Poker.
- `DWVP-001` through `DWVP-005` for the same five acceptance dimensions for Deuces Wild Video Poker.
- `SCRATCH-001` through `SCRATCH-005` for the same five acceptance dimensions for Scratch Cards.
- `SIC-BO-001` through `SIC-BO-005` for the same five acceptance dimensions for Sic Bo.
- `CHUCK-001` through `CHUCK-005` for the same five acceptance dimensions for Chuck-a-Luck.
- `CRAPS-001` through `CRAPS-005` for the same five acceptance dimensions for Craps.
- `CAA-001` through `CAA-005` for the same five acceptance dimensions for Crown and Anchor.
- `OU7-001` through `OU7-005` for the same five acceptance dimensions for Over/Under 7.
- `PLINKO-001` through `PLINKO-005` for the same five acceptance dimensions for Plinko.
- `FAN-TAN-001` through `FAN-TAN-005` for the same five acceptance dimensions for Fan-Tan.
- `AB-001` through `AB-005` for the same five acceptance dimensions for Andar Bahar.
- `AD-001` through `AD-005` for the same five acceptance dimensions for Acey-Deucey.
- `CS-001` through `CS-005` for the same five acceptance dimensions for Caribbean Stud.
- `LIR-001` through `LIR-005` for the same five acceptance dimensions for Let It Ride.
- `CH-001` through `CH-005` for the same five acceptance dimensions for Casino Hold'em.
- `JP-001` through `JP-005` for the same five acceptance dimensions for Joker Poker.
- `PGP-001` through `PGP-005` for the same five acceptance dimensions for Pai Gow Poker.
- `TEENP-001` and `TEENP-002` for Teen Patti rules/state authority and exactly-once settlement, paired with `TEST-116` for listener-free and governed Browser evidence.
- `THPT-001` through `THPT-005` for rules, session privacy and restart, four-wallet ledger settlement, EN/RU browser behavior, and discovered test/visual/security evidence for Texas Hold'em Practice Table.

New entries begin as `PLANNED`. The integration owner changes an entry to `PASS` only when its mapped real-backend tests and visual evidence have passed. Requirement IDs are never reused or renumbered after allocation.

## Shared-file ownership

The #77 integration owner alone edits these collision surfaces while the three drafts are active:

- `modules/module-manifest.json` and the directly affected shared module descriptors.
- `docs/requirements/requirements.json`, `docs/requirements/requirements.md`, and generated requirement documentation.
- `tests/visual/visual_matrix.json`.
- Shell EN/RU category resources when a descriptor introduces a catalog category.
- Contract compatibility matrices and digests.
- Shared registry, application shell, validators, central test runners, or long-suite discovery only if catalog discovery fails and a narrowly proven correction is required.

Game workers continue to own their isolated backend package, frontend module, game EN/RU domain, OpenAPI file, module descriptor proposal, game-specific tests, long driver, and evidence record. A shared-file commit may be added to a game branch only by the #77 owner after that branch is rebased onto the accepted base.

## Branch and merge choreography

For each approved game in order:

1. Rebase the draft branch onto the accepted `main` with force-with-lease protection.
2. Normalize its descriptor, canonical `/games/<id>` route, unique sort order, backend registration callable, lazy frontend export, readiness selector, contract declaration, and `tests.game_drivers.<id>:play` reference.
3. Run focused engine, API, frontend, catalog, session-isolation, and ledger-replay checks before touching shared acceptance files.
4. Add the permanent requirements, aggregate module revision, compatibility metadata, visual row, generated docs, and any required shell category labels.
5. Run the full integration gate and capture named after-pass evidence from that exact head.
6. Keep the game PR draft and request the coordinator's explicit acceptance release.
7. After merge, rebase the next draft onto the new `main` and recalculate shared module revisions from that accepted state.

No game branch is retargeted to another game branch. Every game PR continues to target `main`, which prevents hidden cross-game implementation dependencies.

## Version sequencing

Each new game begins at module revision `1.0.0`. The packaged application release is owned by `pyproject.toml` and `modules/module-manifest.json` and does not change unless formal release work is separately assigned; report release impact as `None` by default. If no intervening pull request changes the shared revisions, the integration sequence reserves:

| Integration | Application module | Tests module | Docs module | Contracts module |
| --- | ---: | ---: | ---: | ---: |
| #111 Multi-Hand Video Poker | 9.4.0 | 1.7.0 | 1.6.0 | 1.2.0 |
| #113 Casino War | 9.5.0 | 1.8.0 | 1.7.0 | 1.3.0 |
| #112 Big Six Wheel | 9.6.0 | 1.9.0 | 1.8.0 | 1.4.0 |
| #116 Red Dog | 9.7.0 | 1.10.0 | 1.9.0 | 1.5.0 |
| #127 Dragon Tiger | 9.8.0 | 1.11.0 | 1.10.0 | 1.6.0 |
| #117 Hi-Lo | 9.9.0 | 1.12.0 | 1.11.0 | 1.7.0 |
| #118 Three Card Poker | 9.10.0 | 1.13.0 | 1.12.0 | 1.8.0 |
| #115 Jacks or Better Video Poker | 9.11.0 | 1.14.0 | 1.13.0 | 1.9.0 |
| #119 Deuces Wild Video Poker | 9.12.0 | 1.15.0 | 1.14.0 | 1.10.0 |
| #123 Scratch Cards | 9.13.0 | 1.16.0 | 1.15.0 | 1.11.0 |
| #125 Sic Bo | 9.14.0 | 1.17.0 | 1.16.0 | 1.12.0 |
| #126 Chuck-a-Luck | 9.15.0 | 1.18.0 | 1.17.0 | 1.13.0 |
| #121 Craps | 9.16.0 | 1.19.0 | 1.18.0 | 1.14.0 |
| #176 Crown and Anchor | 9.17.0 | 1.20.0 | 1.19.0 | 1.15.0 |
| #171 Over/Under 7 | 9.18.0 | 1.21.0 | 1.20.0 | 1.16.0 |
| #175 Plinko | 9.19.0 | 1.22.0 | 1.21.0 | 1.17.0 |
| #174 Fan-Tan | 9.20.0 | 1.23.0 | 1.22.0 | 1.18.0 |
| #173 Andar Bahar | 9.21.0 | 1.24.0 | 1.23.0 | 1.19.0 |
| #172 Acey-Deucey | 9.22.0 | 1.25.0 | 1.24.0 | 1.20.0 |
| #180 Caribbean Stud | 9.23.0 | 1.26.0 | 1.25.0 | 1.21.0 |
| #178 Let It Ride | 9.24.0 | 1.27.0 | 1.26.0 | 1.22.0 |
| #179 Casino Hold'em | 9.25.0 | 1.28.0 | 1.27.0 | 1.23.0 |
| #177 Joker Poker | 9.26.0 | 1.29.0 | 1.28.0 | 1.24.0 |
| #190 Storage action idempotency | 9.27.0 | 1.30.0 | 1.29.0 | 1.24.0 |
| #189 Funded practice opponents | 9.28.0 | 1.31.0 | 1.30.0 | 1.25.0 |
| #191 Server authority | 9.28.0 | 1.32.0 | 1.31.0 | 1.26.0 |
| #120 Texas Hold'em Practice integration | 9.29.0 | 1.33.0 | 1.32.0 | 1.27.0 |

These values are reservations, not permission to overwrite a newer value. The integrator must re-read current `main` immediately before each bump.

## Funded practice-opponent prerequisite

Issue #189 allocates `bot_1`, `bot_2`, and `bot_3` as the fixed server-managed accounts for the held Texas Hold'em Practice Table. Admin and the refreshed #120 controller reuse one storage-enforced funding identity per account. The controller reserves each opponent's maximum hand exposure through `casino.core.practice_accounts`, applies automated decisions through the game's existing shared action validator, and returns unused escrow plus any payout through distinct storage-enforced credit actions. Every movement retains bot, game, hand, controller action, component, action key, and owning human session context in append-only ledger details. Normal user responses do not expose account ids, another session's owner correlation, or private hand state.

## Hostile-client certification extension

Issue #191 is accepted in protected main and supplies permanent `SEC-001` through `SEC-009`, the generated per-action inventory, raw hostile-field dispatch probes, two-user and Admin boundaries, provider concurrency/restart evidence, and authoritative browser refresh checks. Pull request #120 extends that exact framework to every Texas Hold'em mutation route and maps its focused game, ledger, replay, restart, browser, and Long Suite evidence into the matrix. The `THPT-*` requirements move to `PASS` only with a green exact-head certification artifact and complete #95 acceptance evidence.

## Acceptance evidence matrix

Every game must prove the following from its real registered backend and authenticated shared shell:

- Catalog API count and metadata, lobby search, category filtering, direct route, reload, Back, and Forward restoration.
- A hostile caller-supplied player ID cannot override the authenticated session-bound player.
- Wagers and settlements use only the shared ledger; identical retries do not duplicate balance movement, while conflicting retry payloads fail closed.
- The catalog-discovered long driver completes one full public-action scenario and appears in every full-casino long-suite scenario.
- EN/RU copy contains no resource keys, invalid encoding, debug labels, or real-money wording.
- Desktop primary, desktop compact, tablet, and mobile evidence satisfies the assigned visual-matrix row.

Required visual states are:

- Multi-Hand Video Poker: `ready`, `choose_holds`, `settled_3_hands`, `settled_5_hands`, `settled_10_hands`, and `route_restored`.
- Casino War: `accepting_wager`, `initial_result`, `war_decision`, `war_result`, and `route_restored`.
- Big Six Wheel: `ready`, `spinning`, `settled`, `reduced_motion`, and `route_restored`.
- Red Dog: `ready`, `spread_decision`, `pair_settled`, `consecutive_push`, `third_card_settled`, and `route_restored`.
- Dragon Tiger: `ready`, `settled`, `tie_half_loss`, `exact_replay`, `reduced_motion`, and `route_restored`.
- Hi-Lo: `ready`, `choose_higher_or_lower`, `correct_guess`, `incorrect_guess`, `tie_refund`, `reduced_motion`, and `route_restored`.
- Three Card Poker: `ready`, `decision`, `player_win`, `dealer_win`, `dealer_not_qualified`, `folded`, `reduced_motion`, and `route_restored`.
- Jacks or Better Video Poker: `ready`, `choose_holds`, `winning_hand`, `losing_hand`, `reduced_motion`, and `route_restored`.
- Deuces Wild Video Poker: `ready`, `choose_holds`, `winning_hand`, `losing_hand`, `reduced_motion`, and `route_restored`.
- Scratch Cards: `ready`, `revealing`, `settled_win`, `settled_no_win`, `reduced_motion`, and `route_restored`.
- Sic Bo: `ready`, `wagers_selected`, `rolling`, `settled`, `reduced_motion`, and `route_restored`.
- Chuck-a-Luck: `ready`, `rolling`, `settled`, `reduced_motion`, and `route_restored`.
- Craps: `ready`, `come_out`, `point_active`, `settled`, `reduced_motion`, and `route_restored`.
- Crown and Anchor: `ready`, `rolling`, `settled`, `reduced_motion`, and `route_restored`.
- Over/Under 7: `ready`, `rolling`, `settled`, `reduced_motion`, and `route_restored`.
- Plinko: `ready`, `path_replay`, `settled`, `reduced_motion`, and `route_restored`.
- Fan-Tan: `ready`, `counting`, `settled`, `reduced_motion`, and `route_restored`.
- Andar Bahar: `ready`, `settled`, `reduced_motion`, and `route_restored`.
- Acey-Deucey: `ready`, `boundaries_dealt`, `settled`, `passed`, `reduced_motion`, and `route_restored`.
- Caribbean Stud: `ready`, `decision`, `dealer_not_qualified`, `player_win`, `push`, `dealer_win`, `fold`, `reduced_motion`, and `route_restored`.
- Let It Ride: `ready`, `first_decision`, `second_decision`, `settled`, `reduced_motion`, and `route_restored`.
- Casino Hold'em: `ready`, `decision`, `dealer_not_qualified`, `player_win`, `dealer_win`, `push`, `folded`, `reduced_motion`, and `route_restored`.
- Joker Poker: `ready`, `choose_holds`, `winning_hand`, `losing_hand`, `reduced_motion`, and `route_restored`.
- Texas Hold'em Practice Table: `ready`, `preflop_decision`, `flop_decision`, `turn_decision`, `river_decision`, `showdown`, `folded`, `settled`, `reduced_motion`, and `route_restored`.

## Validation and listener gate

The final head runs bootstrap, repository rules, API, browser, full long suite 100, catalog, contract, module-boundary, requirement, version, generated-document, and comment-density validation. Focused smoke checks may run earlier but cannot replace the final set. Two members of that set do not gate a new game on their own: `scripts/check_comment_density.py` prints warnings and always exits `0`, so it is advisory only, and `verify_rules.py` imports and exercises only the six original engines (roulette, slots, blackjack, baccarat, keno, bingo), so it validates no expansion-game rules. A new game's rule evidence must come from its own engine/API tests and the catalog-discovered long driver.

Any test listener binds only to `127.0.0.1` on an ephemeral port other than 8765. The validation record names its PID and port, stops it after the run, verifies the port is closed, and makes no broad firewall change.

## Excluded work

This lane does not start #72 Operations, #69 signup, #70 OAuth, public #71 OCI, or #109 Midphase deployment mutation. It does not change game rules outside the accepting game's allocated requirements.
