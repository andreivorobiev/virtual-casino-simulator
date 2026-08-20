# Double Bonus Video Poker shared-lifecycle evidence

Issue #1025 moves Double Bonus Video Poker onto the shared game lifecycle without changing its bet, five-card deal, hold selection, replacement draw, Double Bonus paytable, settlement, wallet refresh, reload recovery, or repeat behavior. The permanent `BR-DBVP-001` Browser case exercises a real deal and draw and records every governed state in both installed locales at desktop-primary, desktop-compact, tablet, and mobile viewports.

This evidence binds the `double_bonus_video_poker` row in `tests/visual/visual_matrix.json`, including ready, choose-holds, settlement, reduced motion, route restoration, and repeat availability.

Accepted local evidence:

| Artifact | Size | SHA-256 | Proof |
| --- | ---: | --- | --- |
| `issue-1025-after-pass-desktop-en-US.png` | 369,977 bytes | `3f01098b4101833ac7860d0cfc98884cf00e1ae1c80e400ca71dc6f2527f9a99` | The desktop game preserves its complete settled five-card hand, authoritative terminal outcome, dominant stage, 300-pixel paytable rail, full-width Deal again and Repeat bet actions, and the shared wallet shell after a real deal/draw round. |

The same Browser case verifies the exact external route stylesheet and shared card stylesheet identities, singleton reuse after reload, EN/RU repaint at every state, eleven paytable rows, all four responsive viewports, fixed-feedback clearance, five keyboard-addressable hold controls, and route teardown without stale game DOM. Listener-free Node evidence additionally pins the distinct `dbvp-deal` and `dbvp-draw` fallback identity scopes, unresolved-response identity reuse, sorted hold fingerprints, and response adoption only while the exact mount session remains current.

The tracked PNG is acceptance evidence, not a before-state or mocked rendering. Hosted Browser qualification must reproduce the executable assertions at the exact PR head; the image alone cannot replace those gates.

Scope remains presentation and lifecycle ownership only. No API or contract, bet or hold content, card order or privacy, wallet arithmetic, ledger event, payout, provider, release, or deployment behavior changes.
