# Issue #130 Joker Poker Integration Packet

This artifact records the #77-controlled promotion of the issue #130 Joker Poker slice into the canonical catalog. PR #177 preserves the isolated game implementation and adds only the shared surfaces needed to make the game discoverable, traceable, testable, and release-aligned.

## Distinct and Countable Conclusion

Joker Poker is distinct and countable as a casino game module because it freezes a 53-card single-hand video-poker profile with one wild joker. The joker changes the deck, hand evaluator, strategy surface, and return table. It introduces five of a kind, wild royal flush, and Kings-or-Better qualification, none of which are equivalent to Multi-Hand Video Poker's no-joker Jacks-or-Better rules.

## Permanent Requirements

- `JP-001`: deal one 53-card source hand with exactly one wild joker and complete one draw from held positions.
- `JP-002`: bind reload-safe state, hold selections, recent rounds, and route restoration to the authenticated session.
- `JP-003`: debit wagers and credit payouts exactly once through the shared ledger under stable action identifiers and immutable request fingerprints.
- `JP-004`: provide complete English and Russian browser copy with responsive, accessible, reduced-motion-safe behavior.
- `JP-005`: maintain catalog, module/version, requirement, compatibility, visual-matrix, browser, restart, and Long Suite traceability.

## Canonical Allocation

- Catalog id: `joker_poker`
- Route: `/games/joker_poker`
- Sort order: `300`
- Module version: `1.0.0`
- Contract: `contracts/openapi/joker_poker.v1.yaml`
- Browser test id: `BR-JP-001`
- API test id: `API-JP-001`
- Visual surface: `joker_poker`

## Visual Matrix Row

- Selector: `[data-testid='joker-poker']`
- States: `ready`, `choose_holds`, `winning_hand`, `losing_hand`, `reduced_motion`, `route_restored`
- Locales: `en-US`, `ru-RU`
- Viewports: `desktop_primary`, `desktop_compact`, `tablet`, `mobile`
- Gates: `VIS-COPY-001`, `VIS-TOKEN-002`, `VIS-LAYOUT-001`, `VIS-LAYOUT-002`, `VIS-LAYOUT-003`, `VIS-SCROLL-001`, `VIS-SCROLL-002`, `VIS-HIERARCHY-001`, `VIS-RESPONSIVE-001`, `VIS-EVIDENCE-001`, `VIS-CATALOG-001`

## Shared Integration Scope

- Promote `modules/joker_poker.json` into the aggregate manifest and runtime catalog.
- Allocate permanent requirements and regenerate requirement documentation.
- Register the OpenAPI digest and compatibility matrix row.
- Add central API, two-user isolation, restart/replay, browser, route-restoration, and Long Suite discovery coverage.
- Add the visual-matrix row and EN/RU four-viewport after-pass evidence.
- Align application, contract, documentation, and test module versions.
- Keep all unrelated game drafts, including held PR #120, outside this change.
