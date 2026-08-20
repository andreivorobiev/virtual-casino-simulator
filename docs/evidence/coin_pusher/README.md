# Coin Pusher shared-lifecycle evidence

Issue #1007 moves Coin Pusher onto the shared game lifecycle without changing its machine, payout table, stake controls, 700 ms cascade, exactly-once settlement, wallet refresh, or repeat behavior. The permanent `BR-COIN-PUSHER-001` Browser case exercises the real game at the governed desktop-primary viewport and records the after-pass surface only after a committed drop, canonical route reload, and second repeated drop.

Accepted local evidence:

| Artifact | Size | SHA-256 | Proof |
| --- | ---: | --- | --- |
| `issue-1007-after-pass-desktop-en-US.png` | 285,886 bytes | `7102ac89ef76a5af4143ad481c4d4b46b9165451f95a1284c1ef6c4583e75b64` | The desktop game presents the unchanged dominant machine and 300-pixel control rail, selected five-token stake, terminal nine-of-twelve shelf and loss result, and enabled repeat action after the second real drop. |

The same case verifies the exact external stylesheet identity, two-column route and positioned 120-pixel tray geometry, authoritative response-owned wallet after both actions, reload recovery of the repeat action, exactly two Coin Pusher POST requests for exactly two visible actions, and route restoration. `BR-CATALOG-EXPANSION-001` continues to cover Coin Pusher in both installed locales across desktop-primary, desktop-compact, tablet, and mobile viewports.

The tracked PNG is acceptance evidence, not a before-state or mocked rendering. Hosted Browser qualification must reproduce the executable assertions at the exact PR head; the image alone cannot replace those gates.

Scope remains presentation and lifecycle ownership only. No API or contract, wallet arithmetic, ledger event, wager, outcome, payout, provider, release, or deployment behavior changes.
