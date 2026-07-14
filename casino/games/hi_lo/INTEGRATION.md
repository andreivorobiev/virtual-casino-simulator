# Hi-Lo integration handoff for issue #77

The isolated module descriptor proposes `hi_lo` version `1.0.0`, catalog sort order `120`, canonical route `/games/hi_lo`, API slug `/api/v1/games/hi-lo`, and requirements prefix `HILO`.

## Shared changes reserved for #77

The integration owner must:

- allocate permanent Hi-Lo requirement IDs before adding them to the central registry;
- add `hi_lo: 1.0.0` to `modules/module-manifest.json` from the then-current accepted base;
- add the OpenAPI contract to compatibility matrices and contract digests;
- add the Hi-Lo visual-matrix row and regenerate requirements documentation;
- let catalog discovery register the backend, lazy frontend, translations, and long driver;
- run real-backend authenticated API, browser, route-restoration, and long-suite acceptance;
- capture `after_pass` EN/RU evidence from the exact integrated head.

No worker commit in this branch edits those shared files.

## Requirement allocation needed

Current main, issue #85, and the #77 sequencing contract do not allocate numbered Hi-Lo requirements. The descriptor's `HILO` prefix is provisional metadata only; the coordinator must choose the permanent IDs without this worker inventing them.

The allocated block needs five acceptance dimensions:

- two-step ace-high rank-only rules and the correct, tie, and incorrect settlement profile;
- authenticated player isolation and reload-safe active/recent state;
- ledger-only wager, refund, and payout with conflicting retry rejection and exactly-once local action IDs;
- complete EN/RU visible and accessible copy across responsive and reduced-motion states;
- catalog, contract, driver, API, browser, module, version, requirement, and visual traceability.

New entries must begin as `PLANNED` and become `PASS` only after #77 records real integrated evidence.

## Proposed visual matrix row

- Surface: `hi_lo`
- Route: `/games/hi_lo`
- Selector: `[data-testid='hi-lo']`
- States: `ready`, `choose_higher_or_lower`, `correct_guess`, `incorrect_guess`, `tie_refund`, `reduced_motion`, `route_restored`
- Locales: `en-US`, `ru-RU`
- Viewports: `desktop_primary`, `desktop_compact`, `tablet`, `mobile`
- Gates: `VIS-COPY-001`, `VIS-TOKEN-002`, `VIS-LAYOUT-001`, `VIS-LAYOUT-002`, `VIS-LAYOUT-003`, `VIS-HIERARCHY-001`, `VIS-RESPONSIVE-001`, `VIS-EVIDENCE-001`, `VIS-CATALOG-001`

The game owns no timer, so reduced-motion validation covers the CSS preference path and absence of delayed lifecycle work.

## Intake order

Sort order `120` is presentation metadata, not merge authorization. Keep this PR draft while #77 completes the currently released sequence. Rebase and validate Hi-Lo only after the coordinator explicitly assigns its intake step from the then-current `main`.
