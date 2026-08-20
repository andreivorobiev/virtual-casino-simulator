# Crown and Anchor shared-lifecycle evidence

Issue #1035 moves Crown and Anchor onto the shared game lifecycle without changing its six symbol wagers, three server-authoritative dice, hit-count payouts, settlement, wallet refresh, reload recovery, reduced-motion behavior, or repeat flow. The permanent `BR-CAA-001` Browser case executes real rounds and records every governed state in both installed locales at desktop-primary, desktop-compact, tablet, and mobile viewports.

This evidence binds the `crown_and_anchor` row in `tests/visual/visual_matrix.json`, including ready, rolling, settled, reduced-motion, route-restored, and repeat-available presentation.

Accepted local evidence:

| Artifact | Size | SHA-256 | Proof |
| --- | ---: | --- | --- |
| `issue-1035-after-pass-desktop-en-US.png` | 325,561 bytes | `70d3c8ed101d2a7dab277e479cdb4260ad423b6214984fda5ef53fbe27e3b193` | The desktop game preserves its dominant three-die stage, all six symbol hit panels, localized settled outcome, wager and repeat controls, paytable, private recent history, and shared wallet shell after a real ledger-backed round. |

The same Browser case verifies the exact external route stylesheet identity, singleton reuse after reload and remount, absence of inline route CSS, dominant desktop stage, unchanged 42/46-pixel control minima, EN/RU repaint, all four responsive viewports, reduced motion, real settlement, repeat availability, reload recovery, and route teardown without stale game DOM. Listener-free Node evidence additionally pins the strict `caa-<UUID>` identity, immutable ambiguous-retry wager binding, shared busy ownership, scoped dice reveal, and response adoption only while the exact mount session remains current.

The tracked PNG is acceptance evidence, not a before-state or mocked rendering. Hosted Browser qualification must reproduce the executable assertions at the exact PR head; the image alone cannot replace those gates.

Scope remains presentation and lifecycle ownership only. No API or contract, game rule, symbol, payout, wallet arithmetic, ledger event, provider, release, or deployment behavior changes.
