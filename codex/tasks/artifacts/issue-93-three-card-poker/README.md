# Issue #93 isolated handoff evidence

**Historical.** Records the isolated #93 slice at handoff to #77. Three Card Poker has since been integrated; for current state see `modules/three_card_poker.json`, `modules/module-manifest.json`, `docs/requirements/requirements.json`, and `tests/visual/visual_matrix.json`.

Branch: `codex/issue-93-three-card-poker`

Integration base: `f8c836163eab3dc92d83e7bf875ee963c11bddcf` (`origin/main`)

## Delivered game and shared integration

- One-deck Three Card Poker engine using the shared #96 card primitives and the selected Maryland Version 1.4 profile.
- Ante/Play decisions, Ante Bonus Paytable A, optional Pair Plus Paytable C, queen-high dealer qualification, and straight-over-flush ordering.
- Session-bound, player-scoped, reload-safe API state with dealer cards hidden until settlement.
- Ledger-only opening wager, Play wager, and payout orchestration with stable request/action identities and conflict-safe replay recovery.
- Catalog module descriptor promoted by #77 to `modules/three_card_poker.json` at version `1.0.0`; the slice also includes an additive v1 OpenAPI contract, game-specific long driver, responsive frontend module, and complete EN/RU game domains.
- Focused engine, API, frontend, shared-primitive, syntax, and repository validation coverage recorded separately in `validation.md`.

## Shared integration completed by #77

The following were owned by issue #77, not by this worker, and are complete on main:

- Promotion of the proposal to `modules/three_card_poker.json`, the matching `three_card_poker` revision in `modules/module-manifest.json`, and reconciliation of shared module versions in the same integration change.
- Allocation of permanent `TCP-001` through `TCP-005` entries and updates to central/generated requirement documents.
- Registration of the contract in `contracts/compatibility/module-api-matrix.json` and `contracts/compatibility/contract-digests.json`.
- Game-specific central API/browser cases and the visual-matrix row.
- Full catalog, real-backend API/browser, and Long Suite 100 acceptance from the integrated head.
- EN/RU `after_pass` evidence from the real authenticated shell.

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
