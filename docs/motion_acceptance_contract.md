# Deterministic motion acceptance contract

Status: shared foundation implemented; Roulette and Slots adoption accepted at the exact PR head.

Related issues: #74, #168, #169, and #170. Existing timer-safe primitives originated in #97.

## Authority and boundary

Motion presents an outcome that the server or game engine has already committed. It never chooses randomness, changes a wager or payout, mutates a wallet, writes a ledger event, or creates a replacement result. Frozen `/api/v1` game contracts remain unchanged.

The active shared primitive in `web/core/motion.js` is `createMotionTimerScope`. It owns cancellable asynchronous callbacks, live reduced-motion resolution, and route/reload teardown without choosing or mutating an outcome. Game routes continue to own their deterministic presentation phases, reviewed timing budgets, result binding, and cleanup.

The earlier unused `createMotionLifecycle` and `createMotionTimingProfile` exports were retired by issue #711 before catalog-wide adoption. Their permanent requirement IDs remain in the registry as retired history and cannot be reused.

## Permanent requirement allocation

The shared family is `MOTION-004` through `MOTION-011`.

- `MOTION-004`, `MOTION-005`, and `TEST-100` are retired historical allocations for the unused lifecycle/profile prototype.
- `MOTION-006` through `MOTION-011` remain `PLANNED` until every adopted game proves authoritative result agreement, non-overlap, recovery, layout and performance, accessibility, localization, and governed evidence.

Roulette owns `ROU-063` through `ROU-068`. Slots owns `SLOT-030` through `SLOT-035`. These IDs are permanent and must not be renumbered or reused. Their exact-head unit and Browser evidence is required in addition to earlier existence-only requirements such as `ROU-042`, `ROU-054`, and `SLOT-020`.

## Roulette adopted profiles

Roulette preserves the frozen API and existing game mathematics while proving:

- one session-bound authoritative pocket and one settlement across wheel, ball, table, result, history, voice, wallet, ledger, and Admin telemetry;
- default Authentic timing of 15–18 seconds, optional Quick timing of 8–10 seconds, autoplay timing of 6–8 seconds, and a 400–800 ms non-spinning reduced-motion path;
- opposite rotor and ball travel, progressive ball deceleration, at least 16 Authentic-mode track circuits, bounded rim departure and deflector contacts, pocket-relative capture, and at least one second of co-rotation;
- visible control locking, result reveal only after capture, route/refresh/error recovery, exact-once announcement, and zero stale timer, sound, glow, or disabled-control residue; and
- deterministic mapping tests plus exact-SHA EN/RU motion evidence at all governed viewports, normal and reduced motion, with frame, transform, alignment, layout, and cleanup traces.

## Slots adopted profiles

Slots preserves the frozen API, reel mathematics, and paytable while proving:

- one authoritative set of reel stops, grid, wins, bonus/progressive state, round, wallet, ledger, history, and telemetry for each non-overlapping spin;
- continuous independent reels with no whole-grid swap, blank seam, reverse jump, frozen placeholder, or symbol change after a reel stops;
- final-stop budgets of 3.8–4.8 seconds for Slow, 2.8–3.6 seconds for Medium, 1.6–2.2 seconds for Fast, and 400–800 ms for reduced motion;
- adjacent stop staggering of 140–240 ms, exact one-pixel final cell alignment, win treatment only after the final stop, and safe autoplay, free-spin, refresh, route, locale, and API-error recovery; and
- deterministic result coverage plus exact-SHA EN/RU motion evidence at all governed viewports, normal and reduced motion, with transform, alignment, layout, and cleanup traces.

## Required acceptance sequence

1. A game-owned PR adopts the shared lifecycle and timing profile without broadening `/api/v1`.
2. Deterministic unit tests use injected clocks and authoritative outcomes; arbitrary real-time sleeps are not acceptance proof.
3. Browser tests cover repeated input, autoplay stop, navigation, refresh, locale change, reduced motion, API failure, wallet/history/ledger agreement, and listener cleanup.
4. The affected rows in `tests/visual/visual_matrix.json` name every new state, locale, and viewport.
5. Exact-head after-pass videos and JSON sidecars prove timing, phase order, geometry, frame intervals, final alignment, cleanup, and provenance.
6. Independent visual review accepts the exact head before the requirements move from `PLANNED` to `PASS`.

Static screenshots, concept art, known-failing captures, generic suite success, and the shared foundation alone cannot complete #169 or #170.
