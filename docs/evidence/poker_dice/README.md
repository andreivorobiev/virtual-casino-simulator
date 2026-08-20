# Poker Dice shared-lifecycle evidence

Issue #1003 moves Poker Dice onto the shared game lifecycle without changing its wager, five-die outcome, paytable, settlement, or repeat-bet behavior. The permanent `BR-POKER-DICE-001` Browser case exercises the real game at the governed desktop-primary viewport and records the after-pass surface only after a committed roll.

Accepted local evidence:

| Artifact | Size | SHA-256 | Proof |
| --- | ---: | --- | --- |
| `issue-1003-after-pass-desktop-en-US.png` | 301,130 bytes | `a113b8b5e5f769fa8330046b402dfafffeb5497298eb6a24a4689ff77e8e95e6` | The desktop game presents the exact two-column stage/rail layout, five responsive dice, localized controls, and committed result after a real repeated roll. |

The same case also verifies the external stylesheet identity, a 300-pixel desktop rail, reduced-motion suppression while a roll is pending, reload recovery of the repeat action, a second real repeated roll, one request per action, and the final authoritative wallet. `BR-CATALOG-EXPANSION-001` continues to cover Poker Dice in both installed locales across desktop-primary, desktop-compact, tablet, and mobile viewports.

The tracked PNG is acceptance evidence, not a before-state or mocked rendering. Hosted Browser qualification must reproduce the executable assertions at the exact PR head; the image alone cannot replace those gates.

Scope remains presentation and lifecycle ownership only. No API or contract, wallet arithmetic, ledger event, wager, outcome, payout, provider, release, or deployment behavior changes.
