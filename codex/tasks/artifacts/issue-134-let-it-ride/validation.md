# Issue #134 Validation Notes

Status: #77 shared integration validation passed from current worktree content refreshed onto `bdf666f7404f64ddd10061b840d2b88cf1e697e3`.

The canonical descriptor, permanent requirements, compatibility metadata, central API/browser/restart coverage, visual row, independent revisions, and catalog-discovered Long Suite driver are now integrated for Let It Ride only.

## Passed Checks

- `C:\Users\andre\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest tests.games.let_it_ride.test_engine tests.games.let_it_ride.test_api tests.games.let_it_ride.test_resources`
- `C:\Users\andre\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe tests/games/let_it_ride/test_frontend.mjs`
- `C:\Users\andre\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe scripts/validate_contracts.py`
- `C:\Users\andre\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe scripts/validate_module_boundaries.py`
- `C:\Users\andre\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe scripts/validate_requirements.py`
- `C:\Users\andre\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe scripts/validate_versions.py`
- `C:\Users\andre\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe scripts/check_comment_density.py`
- `C:\Users\andre\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe scripts/bootstrap_repo.py`
- `C:\Users\andre\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tests/run_tests.py --api`
- `C:\Users\andre\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tests/run_tests.py --browser`
- `C:\Users\andre\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tests/long_suites.py --suite 100`

## Integration Evidence

- Catalog and contract validators pass for 27 current games, 40 module revisions, and the additive `let_it_ride.v1.yaml` digest.
- `API-LIR-001` proves hostile compatibility identities cannot override either authenticated session, opening debits and pull refunds are exactly once, optional payouts cannot duplicate, changed action reuse conflicts, and both users recover their own settled round after process restart.
- `BR-LIR-001` passes ready, first-decision, second-decision, settled, reduced-motion, and route-restored states in `en-US` and `ru-RU` at desktop primary, desktop compact, tablet, and mobile viewports.
- The browser gate also passes catalog discovery, EN/RU shell copy, canonical route restoration, and the downstream 1366 by 768 compact-shell fold after the catalog-growth navigation correction.
- Long Suite 100 passes 100 full-casino scenarios and discovers `tests.game_drivers.let_it_ride:play` from `modules/let_it_ride.json`.

## Listener And Runtime Cleanup

- API listener ports `58070`, `58378`, `49766`, and `50077`, final browser listener port `50712`, and Long Suite port `50215` were bound only to `127.0.0.1`, stopped by their owning runners, and verified closed.
- A copied-deployment Long Suite attempt bound `127.0.0.1:56584` and encountered a Windows atomic-rename permission lock in the disposable Dragon Tiger data directory; the listener stopped and the copied directory was removed before the clean worktree-local Long Suite passed.
- Ports `8765` and `8877` were never used or stopped. Generated runtime data was removed and the six tracked fixture files were restored from this worktree's own `HEAD` only.
- Bundled Codex Python and Node runtimes were used because those commands were not on this shell's PATH.
