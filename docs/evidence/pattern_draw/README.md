# Pattern Draw shared-lifecycle evidence

Issue #1005 moves Pattern Draw onto the shared game lifecycle without changing its three-by-three grid, pattern catalog, stake controls, 600 ms reveal, exactly-once settlement, wallet refresh, or repeat behavior. The permanent `BR-PATTERN-DRAW-001` Browser case exercises the real game at the governed desktop-primary viewport and records the after-pass surface only after a committed draw, canonical route reload, and second repeated draw.

Accepted local evidence:

| Artifact | Size | SHA-256 | Proof |
| --- | ---: | --- | --- |
| `issue-1005-after-pass-desktop-en-US.png` | 321,957 bytes | `6cf3632c00b4ba8a5eba54d158bbd4c43785aab8c15685c38815b01514bebf2a` | The desktop game presents the unchanged dominant grid and 300-pixel control rail, selected pattern and stake, terminal lit-cell result, and enabled repeat action after the second real draw. |

The same case verifies the exact external stylesheet identity, three-column grid geometry, authoritative response-owned wallet after both actions, reload recovery of the repeat action, exactly two Pattern Draw POST requests for exactly two visible actions, and route restoration. `BR-CATALOG-EXPANSION-001` continues to cover Pattern Draw in both installed locales across desktop-primary, desktop-compact, tablet, and mobile viewports.

The tracked PNG is acceptance evidence, not a before-state or mocked rendering. Hosted Browser qualification must reproduce the executable assertions at the exact PR head; the image alone cannot replace those gates.

Scope remains presentation and lifecycle ownership only. No API or contract, wallet arithmetic, ledger event, wager, outcome, payout, provider, release, or deployment behavior changes.
