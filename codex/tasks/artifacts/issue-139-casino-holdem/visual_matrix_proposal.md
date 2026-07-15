# Issue #139 Visual Matrix Promotion

The isolated proposal below is now promoted into `tests/visual/visual_matrix.json` by shared integration issue #77.

Canonical #77 row:

- Surface id: `casino_holdem`
- Route: `/games/casino_holdem`
- Selector: `[data-testid='casino-holdem']`
- States: `ready`, `decision`, `dealer_not_qualified`, `player_win`, `dealer_win`, `push`, `folded`, `reduced_motion`, `route_restored`
- Locales: `en-US`, `ru-RU`
- Viewports: `desktop_primary`, `desktop_compact`, `tablet`, `mobile`
- Gates: `VIS-COPY-001`, `VIS-TOKEN-002`, `VIS-LAYOUT-001`, `VIS-LAYOUT-002`, `VIS-LAYOUT-003`, `VIS-SCROLL-001`, `VIS-SCROLL-002`, `VIS-HIERARCHY-001`, `VIS-RESPONSIVE-001`, `VIS-EVIDENCE-001`, `VIS-CATALOG-001`

Evidence note: the exact integrated head passes the real-backend browser suite and emits after-pass PNG/JSON evidence for both locales at desktop primary, desktop compact, tablet, and mobile. The frontend remains timer-free, reduced-motion safe, responsive, touch-target compliant, and locale-key paired.
