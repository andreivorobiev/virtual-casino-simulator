# Hi-Lo integration acceptance for issue #77

The canonical descriptor registers `hi_lo` version `1.0.0`, catalog sort order `120`, route `/games/hi_lo`, API slug `/api/v1/games/hi-lo`, and permanent requirements prefix `HILO`.

## Shared changes supplied by #77

The integration owner:

- allocates permanent requirements `HILO-001` through `HILO-005`;
- registers `hi_lo: 1.0.0` in the aggregate module manifest;
- registers the additive OpenAPI contract in compatibility matrices and digests;
- adds the Hi-Lo visual-matrix row and regenerates requirement documentation;
- lets catalog discovery register the backend, lazy frontend, translations, and long driver;
- runs authenticated real-backend API, browser, route-restoration, and Long Suite 100 acceptance;
- captures `after_pass` EN/RU evidence from the integrated branch.

## Permanent requirement allocation

Issue #77 permanently allocates `HILO-001` through `HILO-005` across five acceptance dimensions:

The allocated block needs five acceptance dimensions:

- two-step ace-high rank-only rules and the correct, tie, and incorrect settlement profile;
- authenticated player isolation and reload-safe active/recent state;
- ledger-only wager, refund, and payout with conflicting retry rejection and exactly-once local action IDs;
- complete EN/RU visible and accessible copy across responsive and reduced-motion states;
- catalog, contract, driver, API, browser, module, version, requirement, and visual traceability.

The central requirement registry records these IDs as `PASS` only with mapped real-backend API, restart, browser, catalog, Long Suite 100, and visual evidence.

## Registered visual matrix row

- Surface: `hi_lo`
- Route: `/games/hi_lo`
- Selector: `[data-testid='hi-lo']`
- States: `ready`, `choose_higher_or_lower`, `correct_guess`, `incorrect_guess`, `tie_refund`, `reduced_motion`, `route_restored`
- Locales: `en-US`, `ru-RU`
- Viewports: `desktop_primary`, `desktop_compact`, `tablet`, `mobile`
- Gates: `VIS-COPY-001`, `VIS-TOKEN-002`, `VIS-LAYOUT-001`, `VIS-LAYOUT-002`, `VIS-LAYOUT-003`, `VIS-HIERARCHY-001`, `VIS-RESPONSIVE-001`, `VIS-EVIDENCE-001`, `VIS-CATALOG-001`

The game owns no timer, so reduced-motion validation covers the CSS preference path and absence of delayed lifecycle work.

## Intake status

Sort order `120` is presentation metadata. PR #117 was accepted; the descriptor, manifest revision, permanent `HILO-001` through `HILO-005` requirements, and visual row are all on main.
