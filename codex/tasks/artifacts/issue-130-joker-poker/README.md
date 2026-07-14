# Issue #130 Joker Poker Isolated Draft

This artifact records the draft-only implementation slice for GitHub issue #130. It intentionally stays outside shared catalog, router, aggregate manifest, central test discovery, permanent requirements, compatibility matrices, visual matrix, and version files.

## Distinct and Countable Conclusion

Joker Poker is distinct and countable as a casino game module because this draft freezes a 53-card single-hand video-poker profile with one wild joker. The joker changes the deck, hand evaluator, strategy surface, and return table. It introduces five of a kind, wild royal flush, and Kings-or-Better qualification, none of which are equivalent to the merged Multi-Hand Video Poker module's no-joker Jacks-or-Better 3/5/10-hand rules.

## Proposed Requirement IDs

- `JP-130-001`: Joker Poker deals one 53-card source hand with exactly one wild joker and completes one draw hand from held positions.
- `JP-130-002`: Authenticated sessions own isolated reload-safe Joker Poker state, hold selections, recent rounds, and route restoration once #77 wires the route.
- `JP-130-003`: Joker Poker wager debits and payout credits use the shared ledger exactly once under stable action identifiers and immutable request fingerprints.
- `JP-130-004`: The Joker Poker browser surface provides complete English and Russian copy and remains responsive, accessible, reduced-motion safe, and timer-clean across the proposed visual row.
- `JP-130-005`: #77-owned integration adds catalog, module/version, requirement, visual-matrix, browser, and long-suite discovery traceability.

## Proposed Visual Matrix Row

- Surface id: `joker_poker`
- Route: `/games/joker_poker`
- Selector: `[data-testid='joker-poker']`
- States: `ready`, `choose_holds`, `settled_wild_royal`, `settled_no_win`, `reduced_motion`, `route_restored`
- Locales: `en-US`, `ru-RU`
- Viewports: `desktop_primary`, `desktop_compact`, `tablet`, `mobile`
- Gates: `VIS-COPY-001`, `VIS-TOKEN-002`, `VIS-LAYOUT-001`, `VIS-LAYOUT-002`, `VIS-LAYOUT-003`, `VIS-SCROLL-001`, `VIS-SCROLL-002`, `VIS-HIERARCHY-001`, `VIS-RESPONSIVE-001`, `VIS-EVIDENCE-001`, `VIS-CATALOG-001`

## Scope Boundary

Owned by this draft:

- `casino/games/joker_poker/`
- `web/games/joker_poker.js`
- `web/i18n/en-US/games/joker_poker.json`
- `web/i18n/ru-RU/games/joker_poker.json`
- `contracts/openapi/joker_poker.v1.yaml`
- Focused tests, driver, and this proposal artifact

Owned later by #77:

- Shared catalog and application routing
- `modules/` and aggregate module manifest
- Permanent requirements and generated requirement docs
- Compatibility matrices and visual matrix
- Central API/browser/long-suite discovery
- Formal version updates and release notes
