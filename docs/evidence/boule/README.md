# Boule shared-lifecycle evidence

Issue #1011 moves Boule onto the shared game lifecycle without changing its nine-number board, even-money and straight markets, stake controls, 800 ms spin, settlement, wallet refresh, or repeat behavior. The permanent `BR-BOULE-001` Browser case exercises the real game at the governed desktop-primary viewport and records the after-pass surface only after a committed spin, canonical route reload, and second repeated spin.

Accepted local evidence:

| Artifact | Size | SHA-256 | Proof |
| --- | ---: | --- | --- |
| `issue-1011-after-pass-desktop-en-US.png` | 313,005 bytes | `ba80de24a1fa3b9d695870a2b9fbca44d7b0e094be7396da30ceea04a2bd58ed` | The desktop game presents the unchanged dominant drum and nine-number board, 300-pixel control rail, selected Even market and five-token stake, terminal server-owned number, and enabled repeat action after the second real spin. |

The same case verifies the exact external stylesheet identity, two-column route and board geometry, reduced-motion suppression, authoritative response-owned wallet after both actions, reload recovery of the repeat action, and exactly two Boule POST requests with distinct opaque action identities for exactly two visible spins. `BR-CATALOG-EXPANSION-001` continues to cover Boule in both installed locales across desktop-primary, desktop-compact, tablet, and mobile viewports.

The tracked PNG is acceptance evidence, not a before-state or mocked rendering. Hosted Browser qualification must reproduce the executable assertions at the exact PR head; the image alone cannot replace those gates.

Scope remains presentation and lifecycle ownership only. No API or contract, wallet arithmetic, ledger event, wager, outcome, payout, provider, release, or deployment behavior changes.
