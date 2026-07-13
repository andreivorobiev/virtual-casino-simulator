# Game Expansion Integration Sequence

Status: approved sequencing contract for GitHub issue #77.

Parent epic: #66. Game expansion parent: #73. Catalog foundation: completed issue #81 and merged pull request #110.

## Purpose

This document gives the #77 integration owner one durable merge order and one shared-file ownership boundary for accepting isolated game pull requests after the catalog foundation. It does not implement game rules and does not make a game pull request ready for review.

## Approved intake order

The Product-approved serialized order is:

1. Pull request #111, Multi-Hand Video Poker for issue #94.
2. Pull request #113, Casino War for issue #82.
3. Pull request #112, Big Six Wheel for issue #86.

All three game pull requests remain draft until the preceding game is accepted, the current branch is rebased onto the resulting `main`, and the game passes the complete integration gate below. A later game must not pre-allocate or edit the shared version values owned by an earlier game.

## Catalog ordering allocation

Existing games retain sort orders 10 through 60. The approved expansion slots are:

| Sort order | Game | Issue | Integration state |
| ---: | --- | ---: | --- |
| 70 | Multi-Hand Video Poker | #94 | Draft PR #111 |
| 80 | Casino War | #82 | Draft PR #113 |
| 90 | Big Six Wheel | #86 | Draft PR #112 |
| 100 | Dragon Tiger | future isolated slice | Reserved |
| 110 | Red Dog | future isolated slice | Reserved |
| 120 | Hi-Lo | future isolated slice | Reserved |
| 130 | Scratch Cards | future isolated slice | Reserved |
| 140 | Sic Bo | future isolated slice | Reserved |
| 150 | Chuck-a-Luck | future isolated slice | Reserved |
| 160 | Craps | future isolated slice | Reserved |
| 170 | Jacks or Better Video Poker | future isolated slice | Reserved |
| 180 | Deuces Wild Video Poker | future isolated slice | Reserved |
| 190 | Three Card Poker | future isolated slice | Reserved |
| 200 | Texas Hold'em Practice Table | future isolated slice | Reserved |

Sort order is catalog presentation metadata, not an authorization to register a placeholder. Only complete game descriptors are loaded.

## Requirement allocation

Permanent game blocks are reserved as follows:

- `MHVP-001` through `MHVP-005` for game rules, additive API and session binding, ledger and retry safety, EN/RU browser behavior, and discovered test/visual evidence.
- `CW-001` through `CW-005` for the same five acceptance dimensions for Casino War.
- `BIG-SIX-001` through `BIG-SIX-005` for the same five acceptance dimensions for Big Six Wheel.

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

Each new game begins at module revision `1.0.0`. The packaged application release remains `9.1.1` unless formal release work is separately assigned. If no intervening pull request changes the shared revisions, the integration sequence reserves:

| Integration | Application module | Tests module | Docs module | Contracts module |
| --- | ---: | ---: | ---: | ---: |
| #111 Multi-Hand Video Poker | 9.4.0 | 1.7.0 | 1.5.0 | 1.2.0 |
| #113 Casino War | 9.5.0 | 1.8.0 | 1.6.0 | 1.3.0 |
| #112 Big Six Wheel | 9.6.0 | 1.9.0 | 1.7.0 | 1.4.0 |

These values are reservations, not permission to overwrite a newer value. The integrator must re-read current `main` immediately before each bump.

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

## Validation and listener gate

The final head runs bootstrap, repository rules, API, browser, full long suite 100, catalog, contract, module-boundary, requirement, version, generated-document, and comment-density validation. Focused smoke checks may run earlier but cannot replace the final set.

Any test listener binds only to `127.0.0.1` on an ephemeral port other than 8765. The validation record names its PID and port, stops it after the run, verifies the port is closed, and makes no broad firewall change.

## Excluded work

This lane does not start #72 Operations, #69 signup, #70 OAuth, public #71 OCI, or #109 Midphase deployment mutation. It does not change game rules outside the accepting game's allocated requirements.
