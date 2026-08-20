# Marble Race shared-lifecycle evidence

Issue #1009 moves Marble Race onto the shared game lifecycle without changing its markets, marble choices, stake controls, 1,300 ms race, settlement, wallet refresh, or repeat behavior. The permanent `BR-MARBLE-RACE-001` Browser case exercises the real game at the governed desktop-primary viewport and records the after-pass surface only after a committed race, canonical route reload, and second repeated race.

Accepted local evidence:

| Artifact | Size | SHA-256 | Proof |
| --- | ---: | --- | --- |
| `issue-1009-after-pass-desktop-en-US.png` | 316,042 bytes | `74c7ffebb04fdcf3c06210a9e420da81b305ea09956499501fc11700a8ffcd64` | The desktop game presents the unchanged dominant six-lane track and 300-pixel control rail, selected Red marble and five-token stake, terminal Red win, and enabled repeat action after the second real race. |

The same case verifies the exact external stylesheet identity, two-column route and lane geometry, semantic Red and Green marble colors, authoritative response-owned wallet after both actions, reload recovery of the repeat action, exactly two Marble Race POST requests for exactly two visible races, and route restoration. `BR-CATALOG-EXPANSION-001` continues to cover Marble Race in both installed locales across desktop-primary, desktop-compact, tablet, and mobile viewports.

The tracked PNG is acceptance evidence, not a before-state or mocked rendering. Hosted Browser qualification must reproduce the executable assertions at the exact PR head; the image alone cannot replace those gates.

Scope remains presentation and lifecycle ownership only. No API or contract, wallet arithmetic, ledger event, wager, outcome, payout, provider, release, or deployment behavior changes.
