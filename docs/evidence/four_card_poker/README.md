# Four Card Poker shared-lifecycle evidence

Issue #1027 moves Four Card Poker onto the shared game lifecycle without changing its ante, optional Aces Up wager, five-card player hand, private six-card dealer hand, 1x–3x play or fold decision, paytables, settlement, wallet refresh, reload recovery, or repeat behavior. The permanent `BR-FOUR-CARD-POKER-001` Browser case executes a real deal and play decision and records the governed ready and repeat-available states in both installed locales at desktop-primary, desktop-compact, tablet, and mobile viewports.

This evidence binds the `four_card_poker` row in `tests/visual/visual_matrix.json`, including ready and repeat availability.

Accepted local evidence:

| Artifact | Size | SHA-256 | Proof |
| --- | ---: | --- | --- |
| `issue-1027-after-pass-desktop-en-US.png` | 353,828 bytes | `d3260ed1b27cefba9f5037c466d071979a11638ed3e092d576b3fda4b0a79202` | The desktop game preserves its settled player and dealer cards, authoritative terminal result, dominant stage, 300-pixel paytable rail, enabled repeat action, ten combined paytable rows, and shared wallet shell after a real deal/play round. |

The same Browser case verifies the exact external route stylesheet and shared card stylesheet identities, singleton reuse after reload, EN/RU repaint in both registered states, ten paytable rows, all four responsive viewports, and route teardown without stale game DOM. Listener-free Node evidence additionally pins distinct `fcp-deal` and `fcp-decision` fallback identity scopes, unresolved two-wager and decision identity reuse, exact public payloads, and response adoption only while the exact mount session remains current.

The tracked PNG is acceptance evidence, not a before-state or mocked rendering. Hosted Browser qualification must reproduce the executable assertions at the exact PR head; the image alone cannot replace those gates.

Scope remains presentation and lifecycle ownership only. No API or contract, ante or Aces Up content, play or fold decision, card order or privacy, wallet arithmetic, ledger event, payout, provider, release, or deployment behavior changes.
