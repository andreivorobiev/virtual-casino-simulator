# Issue #91 isolated handoff evidence

Branch: `codex/issue-91-jacks-or-better-video-poker`

Base at implementation start: `0a1ebc2d7d034bb855ad968215bc61adcd18f4c9` (`origin/main`)

## Delivered isolated slice

- Deterministic single-hand 9/6 Jacks-or-Better rules using the completed #96 shared card and poker primitives.
- One-through-five coin selection, a five-card initial hand, reload-safe holds, one draw, and the classic five-column returned-credit paytable.
- Authenticated-player state isolation with caller identity treated only as an overridden compatibility input.
- Retry-safe deal and draw action IDs, persisted recovery markers, one wager debit, at most one payout credit, ledger replay detection, and no direct balance mutation.
- Timer-free, responsive, reduced-motion-aware frontend behavior using the shared accessible card renderer.
- Complete paired EN/RU visible and ARIA resources owned by the game domain.
- An additive OpenAPI v1 contract, an independently versioned catalog descriptor proposal stored as issue evidence, focused tests, and a normalized catalog long driver.

## Requirement traceability

The implemented slice consumes confirmed requirements `CARD-001`, `CARD-002`, `POKER-001`, `POKER-002`, `CORE-011`, `LEDGER-005`, `LEDGER-006`, `LEDGER-007`, `CORE-021`, `CORE-022`, `SESSION-005`, `UX-010`, `I18N-001`, `I18N-002`, and `TEST-042`.

`JOBVP-001` through `JOBVP-005` are an issue-local proposal only. They represent game rules, session/reload safety, ledger retry safety, EN/RU browser behavior, and integration evidence respectively. `API-JOBVP-001` and `BR-JOBVP-001` are likewise proposed focused test mappings. Issue #77 must allocate permanent requirements and test IDs before central traceability can be accepted.

## Shared integration intentionally blocked

The following work remains owned by integration issue #77 and is not performed by this isolated branch:

- Promote `jacks_or_better_video_poker.module.proposal.json` into `modules/jacks_or_better_video_poker.json`, add `jacks_or_better_video_poker: 1.0.0` to `modules/module-manifest.json`, and recompute current shared module revisions from the accepted integration base.
- Allocate permanent game requirement IDs and update `docs/requirements/requirements.json`, `docs/requirements/requirements.md`, and generated requirement documentation.
- Add the game contract to `contracts/compatibility/module-api-matrix.json` and `contracts/compatibility/contract-digests.json`.
- Add the proposed `jacks_or_better_video_poker` surface to `tests/visual/visual_matrix.json`.
- Add central game-specific API/browser requirement mappings or test-runner wiring only if catalog discovery proves a narrow integration gap.
- Capture and accept central real-backend EN/RU browser evidence from the exact integrated head.

The proposal is intentionally stored at `codex/tasks/artifacts/issue-91-jacks-or-better-video-poker/jacks_or_better_video_poker.module.proposal.json` so catalog discovery cannot install it before #77 supplies the aggregate revision and other shared records in one coordinated change. This placement keeps `scripts/validate_versions.py` and `scripts/validate_game_catalog.py` green on the isolated branch while preserving the complete `1.0.0` proposal for integration.

## Proposed visual matrix row for #77

- Surface: `jacks_or_better_video_poker`
- Route: `/games/jacks_or_better_video_poker`
- Selector: `[data-testid='jacks-or-better-video-poker']`
- States: `ready`, `choose_holds`, `settled`, `route_restored`
- Locales: `en-US`, `ru-RU`
- Viewports: `desktop_primary`, `desktop_compact`, `tablet`, `mobile`
- Gates: `VIS-COPY-001`, `VIS-TOKEN-002`, `VIS-LAYOUT-001`, `VIS-LAYOUT-002`, `VIS-LAYOUT-003`, `VIS-HIERARCHY-001`, `VIS-RESPONSIVE-001`, `VIS-EVIDENCE-001`, `VIS-CATALOG-001`

## Evidence classification

No screenshot is presently claimed as central `after_pass` acceptance evidence. Any issue-scoped capture must come from the tested branch at a named locale, viewport, state, and exact commit. Full acceptance remains blocked until #77 adds the shared requirement, compatibility, aggregate-version, and visual-matrix records.

The isolated descriptor uses only existing catalog categories (`machine`, `cards`, `poker`, and `strategy`), so no shared shell locale edit is requested. Port `8765` and shared `data/` remain outside this lane.
