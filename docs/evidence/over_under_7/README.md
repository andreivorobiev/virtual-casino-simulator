# Over/Under 7 shared-lifecycle evidence

Issue #1031 moves Over/Under 7 onto the shared game lifecycle without changing its two-dice outcomes, wager map, paytable convention, settlement, wallet refresh, reload recovery, reduced-motion reveal, or repeat behavior. The permanent `BR-OU7-001` Browser case executes real plays and records every governed state in both installed locales at desktop-primary, desktop-compact, tablet, and mobile viewports.

This evidence binds the `over_under_7` row in `tests/visual/visual_matrix.json`, including ready, rolling, settled, reduced-motion, route-restored, and repeat-available presentation.

Accepted local evidence:

| Artifact | Size | SHA-256 | Proof |
| --- | ---: | --- | --- |
| `issue-1031-after-pass-desktop-en-US.png` | 373,070 bytes | `e1df9959beeb16c156aa2dba758d7b747a5e521ed93bad465d7d712bc04a09fd` | The desktop game preserves its settled authoritative dice, total, outcome, net result, dominant center stage, wager rail, return table, recent history, and shared wallet shell after a real ledger-backed play. |

The same Browser case verifies the exact external route stylesheet identity, singleton reuse after reload, computed three-column desktop hierarchy, 44/46-pixel controls, EN/RU repaint, all four responsive viewports, reduced motion, real settlement and history recovery, and route teardown without stale game DOM. Listener-free Node evidence additionally pins the frozen `ou7-<uuid>` identity seam, immutable ambiguous-retry wager payload, shared busy ownership, timer cleanup, and response adoption only while the exact mount session remains current.

The tracked PNG is acceptance evidence, not a before-state or mocked rendering. Hosted Browser qualification must reproduce the executable assertions at the exact PR head; the image alone cannot replace those gates.

Scope remains presentation and lifecycle ownership only. No API or contract, dice rule, wager outcome, paytable, wallet arithmetic, ledger event, payout, provider, release, or deployment behavior changes.
