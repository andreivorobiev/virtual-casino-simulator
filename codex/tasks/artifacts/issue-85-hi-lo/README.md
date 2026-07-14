# Issue #85 isolated handoff evidence

Branch: `codex/game-hi-lo`

Base at implementation start: `0a1ebc2d7d034bb855ad968215bc61adcd18f4c9` (`origin/main`)

## Delivered isolated slice

- Two-step Hi-Lo rules using the merged #96 standard-card primitive: deal one visible card, choose higher or lower, compare rank only with ace high.
- Correct guesses return 2 times the wager, equal ranks refund 1 times the wager, and incorrect guesses return zero.
- Authenticated player-scoped API and reload-safe hidden-card state.
- Independent deal and guess action IDs with semantic conflict rejection, process-local serialization, state-before-ledger recovery, and player/game/action ledger scans.
- Ledger-only wager, payout, and refund movements with no direct balance mutation.
- Timer-free EN/RU lazy frontend using the shared accessible card renderer with game-local localized card ARIA labels.
- Additive OpenAPI v1 contract, artifact-scoped catalog descriptor proposal, focused engine/API/frontend tests, and catalog long driver.

## Shared integration intentionally blocked

The following actions remain owned by issue #77 and are not performed here:

- Allocate permanent Hi-Lo requirement IDs; current issue #85 and main have none.
- Promote `hi_lo.module.proposal.json` into `modules/hi_lo.json` and add `hi_lo: 1.0.0` to `modules/module-manifest.json` in the same integration change.
- Add central requirement records and regenerate requirement documentation.
- Add the contract compatibility matrix and digest records.
- Add the `hi_lo` surface to `tests/visual/visual_matrix.json`.
- Run catalog-discovered central API/browser/long suites after the aggregate revision makes runtime registration valid.
- Capture real-backend authenticated `after_pass` EN/RU evidence from the integrated route.

## Proposed visual matrix row

- Surface: `hi_lo`
- Route: `/games/hi_lo`
- Selector: `[data-testid='hi-lo']`
- States: `ready`, `choose_higher_or_lower`, `correct_guess`, `incorrect_guess`, `tie_refund`, `reduced_motion`, `route_restored`
- Locales: `en-US`, `ru-RU`
- Viewports: `desktop_primary`, `desktop_compact`, `tablet`, `mobile`
- Gates: `VIS-COPY-001`, `VIS-TOKEN-002`, `VIS-LAYOUT-001`, `VIS-LAYOUT-002`, `VIS-LAYOUT-003`, `VIS-HIERARCHY-001`, `VIS-RESPONSIVE-001`, `VIS-EVIDENCE-001`, `VIS-CATALOG-001`

## Evidence classification

No screenshot from this isolated branch is claimed as `after_pass`. The shared aggregate manifest and visual row are intentionally absent, so issue #77 must first activate the real catalog route and then capture acceptance images from the exact integrated head.

Focused command evidence, the descriptor-proposal relocation, and green catalog/version validation are recorded in `validation.md`. No listener is required for this isolated plan.
