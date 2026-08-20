# Color Wheel shared-lifecycle evidence

Issue #1019 moves Color Wheel onto the shared game lifecycle without changing its twenty-segment layout, four color bets, stake controls, 3.2-second forward spin, settlement, wallet refresh, or repeat behavior. The permanent `BR-COLOR-WHEEL-001` Browser case exercises the real game at the governed desktop-primary and mobile viewports and records the after-pass surface only after a committed spin.

This evidence binds the `color_wheel` row in `tests/visual/visual_matrix.json`; the shared catalog matrix continues to cover its remaining required locale and viewport combinations.

Accepted local evidence:

| Artifact | Size | SHA-256 | Proof |
| --- | ---: | --- | --- |
| `issue-1019-after-pass-desktop-en-US.png` | 311,853 bytes | `fa4a1362a81a5e3950afcc5d4dfaea6b74749fee912f98c9dd30fc0eb447cfca` | The desktop game preserves the dominant twenty-segment wheel and 300-pixel control rail, semantic color bets, five-token stake, terminal server-owned result, and enabled repeat action after a real spin. |

The same case verifies the exact external stylesheet identity, two-column and mobile single-column geometry, exact 3.2-second transition, installed-locale repaint, authoritative response-owned wallet after both actions, increasing cumulative wheel angle, reload recovery of the repeat action, distinct opaque request identities, report-control clearance, and route teardown without stale game DOM. `BR-CATALOG-EXPANSION-001` continues to cover Color Wheel in both installed locales across desktop-primary, desktop-compact, tablet, and mobile viewports.

The tracked PNG is acceptance evidence, not a before-state or mocked rendering. Hosted Browser qualification must reproduce the executable assertions at the exact PR head; the image alone cannot replace those gates.

Scope remains presentation and lifecycle ownership only. No API or contract, wallet arithmetic, ledger event, wager, segment selection, payout, provider, release, or deployment behavior changes.
