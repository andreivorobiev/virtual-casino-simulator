# Lucky Grid shared-lifecycle evidence

Issue #1017 moves Lucky Grid onto the shared game lifecycle without changing its nine-cell board, three-pick selection, stake controls, 600 ms reveal, settlement, wallet refresh, or repeat behavior. The permanent `BR-LUCKY-GRID-001` Browser case exercises the real game at the governed desktop-primary viewport and records the after-pass surface only after a committed reveal, canonical route reload, and second repeated reveal.

This evidence binds the `lucky_grid` row in `tests/visual/visual_matrix.json`; the shared catalog matrix continues to cover its remaining required locale and viewport combinations.

Accepted local evidence:

| Artifact | Size | SHA-256 | Proof |
| --- | ---: | --- | --- |
| `issue-1017-after-pass-desktop-en-US.png` | 319,722 bytes | `ac040aa1b799f1b84c21f4222f1e36346dcee735cca4698007c375a56fce8db5` | The desktop game presents the unchanged dominant three-by-three prize board and 300-pixel control rail, selected three-cell wager and five-token stake, terminal server-owned prize/match state, and enabled repeat action after the second real reveal. |

The same case verifies the exact external stylesheet identity, two-column route and board geometry, authoritative response-owned wallet after both actions, reload recovery of the repeat action, and exactly two Lucky Grid POST requests with identical reviewed picks/stake and distinct opaque request identities. `BR-CATALOG-EXPANSION-001` continues to cover Lucky Grid in both installed locales across desktop-primary, desktop-compact, tablet, and mobile viewports.

The tracked PNG is acceptance evidence, not a before-state or mocked rendering. Hosted Browser qualification must reproduce the executable assertions at the exact PR head; the image alone cannot replace those gates.

Scope remains presentation and lifecycle ownership only. No API or contract, wallet arithmetic, ledger event, wager, outcome, payout, provider, release, or deployment behavior changes.
