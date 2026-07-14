# Issue #139 Visual Matrix Proposal

No `tests/visual/visual_matrix.json` changes were made in this isolated worker slice.

Proposed future #77 row:

- Surface id: `casino_holdem`
- Route: `/games/casino_holdem`
- Selector: `[data-testid='casino-holdem']`
- States: `ready`, `decision`, `dealer_not_qualified`, `player_win`, `dealer_win`, `push`, `folded`, `reduced_motion`, `route_restored`
- Locales: `en-US`, `ru-RU`
- Viewports: `desktop_primary`, `desktop_compact`, `tablet`, `mobile`
- Gates: `VIS-COPY-001`, `VIS-TOKEN-002`, `VIS-LAYOUT-001`, `VIS-LAYOUT-002`, `VIS-LAYOUT-003`, `VIS-SCROLL-001`, `VIS-SCROLL-002`, `VIS-HIERARCHY-001`, `VIS-RESPONSIVE-001`, `VIS-EVIDENCE-001`, `VIS-CATALOG-001`

Evidence note: this PR includes no acceptance screenshots and makes no #77 visual-matrix acceptance claim. The frontend module is static-tested for no timers, reduced-motion CSS, responsive control-stage-data order, touch target height, localized card labels, and EN/RU key parity.
