# Over/Under 7

Issue: #135. Status: catalog-integrated through the serialized #77 acceptance lane.

Over/Under 7 is a distinct countable candidate because it is a two-dice total proposition game. The player covers one or more of three outcomes: totals under seven, exactly seven, or over seven. That rules profile is materially different from the existing wheel, card, draw, reel, and table-card modules.

## Rules Profile

| Outcome | Winning totals | Net odds | Total return |
| --- | --- | ---: | ---: |
| Under 7 | 2, 3, 4, 5, 6 | 1:1 | 2x stake |
| Exactly 7 | 7 | 4:1 | 5x stake |
| Over 7 | 8, 9, 10, 11, 12 | 1:1 | 2x stake |

All wagers and returned play tokens go through `casino.core.ledger`. The game never mutates balances directly. Each play requires a stable `action_id`; exact retries replay the original result, while changed retries fail closed.

## Canonical Integration

The descriptor at `modules/over_under_7.json` owns the module version, route `/games/over_under_7`, sort order `220`, paired EN/RU resources, the additive contract, and `tests.game_drivers.over_under_7:play`. Permanent requirements `OU7-001` through `OU7-005` map rules, session/restart behavior, ledger safety, browser localization, and catalog-wide evidence.

The visual surface `over_under_7` covers `ready`, `rolling`, `settled`, `reduced_motion`, and `route_restored` in both locales at desktop primary, desktop compact, tablet, and mobile viewports. Shared registration remains catalog-driven; no bespoke router, shell, or long-suite allowlist is required.
