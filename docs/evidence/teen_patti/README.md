# Teen Patti shared-lifecycle evidence

Issue #1033 moves Teen Patti onto the shared game lifecycle without changing its three-card deal, play/fold decision, dealer qualification, Bonus table, card privacy, settlement, wallet refresh, reload recovery, reduced-motion behavior, or repeat flow. The permanent `BR-TEEN-PATTI-001` Browser case executes real deals and decisions and records every governed state in both installed locales at desktop-primary, desktop-compact, tablet, and mobile viewports.

This evidence binds the `teen_patti` row in `tests/visual/visual_matrix.json`, including ready, decision, play-settled, folded, reduced-motion, route-restored, and repeat-available presentation.

Accepted local evidence:

| Artifact | Size | SHA-256 | Proof |
| --- | ---: | --- | --- |
| `issue-1033-after-pass-desktop-en-US.png` | 350,465 bytes | `606a50cc3369c544095ce5fb5a90c76add1dedf5a23d9ad34f029a7efb589b52` | The desktop game preserves its authoritative settled player/dealer cards, localized outcome, dominant stage, ante and repeat controls, Bonus table, hand-ranking reference, and shared wallet shell after real ledger-backed deal and decision actions. |

The same Browser case verifies the exact external route stylesheet identity, singleton reuse after reload and remount, absence of inline route CSS, dominant desktop stage, 44-pixel primary controls, EN/RU repaint, all four responsive viewports, reduced motion, real settlement, card privacy, repeat availability, reload recovery, and route teardown without stale game DOM. Listener-free Node evidence additionally pins separate deal/decision identity scopes, immutable ambiguous-retry contexts, shared busy ownership, and response adoption only while the exact mount session remains current.

The tracked PNG is acceptance evidence, not a before-state or mocked rendering. Hosted Browser qualification must reproduce the executable assertions at the exact PR head; the image alone cannot replace those gates.

Scope remains presentation and lifecycle ownership only. No API or contract, game rule, dealer qualification, Bonus return, wallet arithmetic, ledger event, payout, provider, release, or deployment behavior changes.
