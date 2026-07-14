# Issue #85 Hi-Lo handoff and #77 integration evidence

Integration branch: `codex/issue-77-rebase-117`

Accepted integration base: `727d5cf2a55d627e6b844cc871ff8e6f46a7c0bf` (`origin/main`)

## Delivered game slice

- Two-step Hi-Lo rules using the merged #96 standard-card primitive: deal one visible card, choose higher or lower, compare rank only with ace high.
- Correct guesses return 2 times the wager, equal ranks refund 1 times the wager, and incorrect guesses return zero.
- Authenticated player-scoped API and reload-safe hidden-card state.
- Independent deal and guess action IDs with semantic conflict rejection, process-local serialization, state-before-ledger recovery, and player/game/action ledger scans.
- Ledger-only wager, payout, and refund movements with no direct balance mutation.
- Timer-free EN/RU lazy frontend using the shared accessible card renderer with game-local localized card ARIA labels.
- Additive OpenAPI v1 contract, canonical catalog descriptor, focused engine/API/frontend tests, and catalog long driver.

## Shared integration completed by issue #77

The #77 lane owns and completes these shared actions:

- Allocate permanent requirements `HILO-001` through `HILO-005`.
- Promote the descriptor into `modules/hi_lo.json` and register `hi_lo: 1.0.0` in `modules/module-manifest.json`.
- Add central requirement records and regenerate requirement documentation.
- Add the contract compatibility matrix and digest records.
- Add the `hi_lo` surface to `tests/visual/visual_matrix.json`.
- Run catalog-discovered central API, browser, restart, and Long Suite 100 gates.
- Capture real-backend authenticated `after_pass` EN/RU evidence from the integrated route.

## Registered visual matrix row

- Surface: `hi_lo`
- Route: `/games/hi_lo`
- Selector: `[data-testid='hi-lo']`
- States: `ready`, `choose_higher_or_lower`, `correct_guess`, `incorrect_guess`, `tie_refund`, `reduced_motion`, `route_restored`
- Locales: `en-US`, `ru-RU`
- Viewports: `desktop_primary`, `desktop_compact`, `tablet`, `mobile`
- Gates: `VIS-COPY-001`, `VIS-TOKEN-002`, `VIS-LAYOUT-001`, `VIS-LAYOUT-002`, `VIS-LAYOUT-003`, `VIS-HIERARCHY-001`, `VIS-RESPONSIVE-001`, `VIS-EVIDENCE-001`, `VIS-CATALOG-001`

## Evidence classification

The #77 browser gate generates 56 real-backend `after_pass` images and sidecars covering both locales, all four governed viewports, and every registered state from the integrated catalog route.

Focused commands, shared validators, bootstrap, API, browser, Long Suite 100, visual evidence, and listener cleanup are recorded in `validation.md` and the exact-head pull-request handback.
