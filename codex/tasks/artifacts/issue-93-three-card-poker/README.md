# Issue #93 isolated handoff evidence

Branch: `codex/issue-93-three-card-poker`

Integration base: `f8c836163eab3dc92d83e7bf875ee963c11bddcf` (`origin/main`)

## Delivered game and shared integration

- One-deck Three Card Poker engine using the shared #96 card primitives and the selected Maryland Version 1.4 profile.
- Ante/Play decisions, Ante Bonus Paytable A, optional Pair Plus Paytable C, queen-high dealer qualification, and straight-over-flush ordering.
- Session-bound, player-scoped, reload-safe API state with dealer cards hidden until settlement.
- Ledger-only opening wager, Play wager, and payout orchestration with stable request/action identities and conflict-safe replay recovery.
- Catalog-shaped module descriptor proposal parked in this issue artifact directory as `three_card_poker.module.proposal.json`, outside auto-discovered `modules/`, with version `1.0.0`; the slice also includes an additive v1 OpenAPI contract, game-specific long driver, responsive frontend module, and complete EN/RU game domains.
- Focused engine, API, frontend, shared-primitive, syntax, and repository validation coverage recorded separately in `validation.md`.

## Shared integration intentionally blocked

The following remain owned by issue #77 and are not acceptance claims for this worker:

- Promote `three_card_poker.module.proposal.json` to `modules/three_card_poker.json`, add `three_card_poker: 1.0.0` to `modules/module-manifest.json`, and reconcile all shared module versions in the same #77 integration change.
- Allocate permanent `TCP-001` through `TCP-005` entries and update central/generated requirement documents.
- Register the contract in `contracts/compatibility/module-api-matrix.json` and `contracts/compatibility/contract-digests.json`.
- Add game-specific central API/browser cases and the visual-matrix row.
- Run full catalog, real-backend API/browser, and Long Suite 100 acceptance from the integrated head.
- Capture EN/RU `after_pass` evidence from the real authenticated shell.

## Proposed visual matrix row for #77

- Surface: `three_card_poker`
- Route: `/games/three_card_poker`
- Selector: `[data-testid='three-card-poker']`
- States: `ready`, `decision`, `folded`, `settled`, `route_restored`
- Locales: `en-US`, `ru-RU`
- Viewports: `desktop_primary`, `desktop_compact`, `tablet`, `mobile`
- Gates: `VIS-COPY-001`, `VIS-TOKEN-002`, `VIS-LAYOUT-001`, `VIS-LAYOUT-002`, `VIS-LAYOUT-003`, `VIS-SCROLL-001`, `VIS-SCROLL-002`, `VIS-HIERARCHY-001`, `VIS-RESPONSIVE-001`, `VIS-EVIDENCE-001`, `VIS-CATALOG-001`

## Evidence classification

No screenshot in this isolated branch is classified as `after_pass`. Real acceptance evidence requires the #77-owned aggregate revision, visual row, central test mappings, and an authenticated real-backend route. Known-failing, manually assembled, or stale imagery is intentionally absent.
