# Mississippi Stud shared-lifecycle evidence

Issue #1021 moves Mississippi Stud onto the shared game lifecycle without changing its ante, three street decisions, progressive community-card reveal, fold privacy, paytable, settlement, wallet refresh, reload recovery, or repeat behavior. The permanent `BR-MSTUD-001` Browser case exercises the real game through all three street bets and records every governed state in both installed locales at desktop-primary, desktop-compact, tablet, and mobile viewports.

This evidence binds the `mississippi_stud` row in `tests/visual/visual_matrix.json`, including ready, all three decision streets, settlement, reduced motion, route restoration, and repeat availability.

Accepted local evidence:

| Artifact | Size | SHA-256 | Proof |
| --- | ---: | --- | --- |
| `issue-1021-after-pass-desktop-en-US.png` | 348,023 bytes | `1089de5cff558f55534e9d426adbf423a288a6fff8ce17068e2288c267baf3a9` | The desktop game preserves its complete settled five-card hand, authoritative terminal outcome, dominant stage, 300-pixel paytable rail, full-width Deal again and Repeat bet actions, and the shared wallet shell after a real four-action round. |

The same Browser case verifies the exact external route stylesheet and shared card stylesheet identities, singleton reuse after reload, EN/RU repaint at every state, nine paytable rows, all four responsive viewports, fixed-feedback clearance, progressive card counts of zero through three, and route teardown without stale game DOM. Listener-free Node evidence additionally pins the distinct `ms-deal` and `ms-decision` fallback identity scopes, unresolved-response identity reuse, and response adoption only while the exact mount session remains current.

The tracked PNG is acceptance evidence, not a before-state or mocked rendering. Hosted Browser qualification must reproduce the executable assertions at the exact PR head; the image alone cannot replace those gates.

Scope remains presentation and lifecycle ownership only. No API or contract, ante or multiplier, card order, privacy, wallet arithmetic, ledger event, payout, provider, release, or deployment behavior changes.
