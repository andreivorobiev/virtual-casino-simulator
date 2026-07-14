# Over/Under 7

Issue: #135. Status: isolated draft implementation slice pending #77 shared integration.

Over/Under 7 is a distinct countable candidate because it is a two-dice total proposition game. The player covers one or more of three outcomes: totals under seven, exactly seven, or over seven. That rules profile is materially different from the existing wheel, card, draw, reel, and table-card modules.

## Rules Profile

| Outcome | Winning totals | Net odds | Total return |
| --- | --- | ---: | ---: |
| Under 7 | 2, 3, 4, 5, 6 | 1:1 | 2x stake |
| Exactly 7 | 7 | 4:1 | 5x stake |
| Over 7 | 8, 9, 10, 11, 12 | 1:1 | 2x stake |

All wagers and returned play tokens go through `casino.core.ledger`. The game never mutates balances directly. Each play requires a stable `action_id`; exact retries replay the original result, while changed retries fail closed.

## Integration Boundary

This worker does not register the module in `modules/`, `modules/module-manifest.json`, the visual matrix, compatibility digests, central runners, or shared shell catalogs. The parked descriptor lives at `codex/tasks/artifacts/issue-135-over-under-7/over_under_7.module.proposal.json` for #77.
