# Issue #139 / PR #179 Integration Validation

Validated in the dedicated #77 worktree on branch `codex/issue-77-rebase-179`, refreshed from accepted main `19d3af4f0107c348a188280901fb238cb327d981`.

## Focused and governance checks

- Casino Hold'em engine, API, and resource tests: PASS, 14 tests.
- Casino Hold'em frontend static test: PASS.
- Repository bootstrap and 32 rule checks: PASS.
- Contract validation: PASS, 8 shared APIs and 28 catalog games.
- Game catalog validation: PASS, 28 current games against target 20.
- Module boundaries: PASS.
- Requirements: PASS, 525 permanent requirements.
- Versions: PASS, packaged release `9.1.1` and 41 module revisions.
- Comment density: PASS, 25048/25059 meaningful lines with nearby comments; 11 pre-existing prerender warnings remain outside issue #139.
- `git diff --check`: PASS.

## Real-backend API and restart evidence

`API-CH-001` passes through the central API runner for two authenticated users. Hostile body and query `player_id` values cannot override either session. Each user receives an independent private decision round; unrevealed dealer, turn, and river cards remain private. Exact deal and call retries replay the same response, changed deal meaning fails with `CONFLICT`, and the replayed called round contains one `CASINO_HOLDEM_ANTE_DEBIT`, one `CASINO_HOLDEM_CALL_DEBIT`, and at most one `CASINO_HOLDEM_SETTLEMENT_CREDIT`.

`API-WALLET-RESTART-001` passes after a real backend restart and restores each user's settled Casino Hold'em history without cross-user leakage.

## Browser and visual evidence

The full real-backend browser suite passes `BR-CH-001` and all existing browser cases. Casino Hold'em evidence covers `ready`, `decision`, one authoritative called outcome, `folded`, `reduced_motion`, and `route_restored` in `en-US` and `ru-RU` at desktop primary, desktop compact, tablet, and mobile viewports. Forty after-pass PNG/JSON evidence pairs were produced for the five captured state groups across both locales and four viewports.

The first browser attempt identified a test-interaction race: changing the wager rerendered the control rail before Playwright's click. The acceptance test now commits the field with Tab and clicks the newly rendered Deal control. The corrected full suite passes.

## Long Suite 100

`tests/long_suites.py --suite 100` passes all 100 local scenarios with browser-audio verification enabled. The report records minimum requirement touches `100` against required `10`, Casino Hold'em plays `100` against required `10`, and catalog discovery of `tests.game_drivers.casino_holdem:play`. The driver proves exact deal and terminal decision replays.

## Listener and runtime cleanup

- API listeners: `127.0.0.1:64206` (PID 12032) and `127.0.0.1:64524` (PID 74044).
- Timed-out browser attempt: `127.0.0.1:49828` (PID 88248), already closed when checked.
- Corrected browser run: `127.0.0.1:57037` (PID 87804).
- Long Suite 100: `127.0.0.1:60897` (PID 76100).
- A prior failed browser run used `127.0.0.1:52379` (PID 69704).

All named ports were independently verified closed after their runs. Ports `8765` and `8877` were not used or inspected. Generated runtime directories were removed and the six tracked data fixtures were restored from this worktree's HEAD.
