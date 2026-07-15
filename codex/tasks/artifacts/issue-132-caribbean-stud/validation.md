# Issue #132 Shared Integration Validation

Integration owner: #77

Base: `c7f069dc0c0a636d4d27b45fb9f102f7912ec03f`

Validation date: 2026-07-15

## Focused and Governance Checks

| Command | Result |
| --- | --- |
| `python -m unittest tests.games.caribbean_stud.test_engine tests.games.caribbean_stud.test_api tests.games.caribbean_stud.test_resources` | PASS: 15 tests cover rules, qualification, call/fold settlement, session isolation, exact replay, recovery, and EN/RU parity. |
| `node tests/games/caribbean_stud/test_frontend.mjs` | PASS. |
| `node --check web/games/caribbean_stud.js` | PASS. |
| `python scripts/validate_game_catalog.py` | PASS: 26 current games, target 20. |
| `python scripts/validate_contracts.py` | PASS: 8 shared APIs and 26 catalog games. |
| `python scripts/validate_module_boundaries.py` | PASS. |
| `python scripts/validate_requirements.py` | PASS: 515 requirements. |
| `python scripts/validate_versions.py` | PASS: packaged release 9.1.1 and 39 module revisions. |
| `python scripts/generate_docs.py --check` | PASS. |
| `python scripts/check_comment_density.py` | PASS: 100.0 percent; only pre-existing prerender artifact warnings. |
| `python verify_rules.py` | PASS: 32 rule checks. |
| `git diff --check origin/main...HEAD` | PASS. |

## Real-Backend Evidence

- Bootstrap and API/restart suites pass `API-CS-001`, hostile player-id precedence, two-user isolation, hidden dealer cards, exact retry/conflict behavior, ledger event cardinality, and `CS-002` persistence after a real process restart.
- Browser suite passes `BR-CS-001` with `after_pass` evidence for ready, decision, one authoritative call outcome, fold under reduced motion, and route restoration in `en-US` and `ru-RU` at desktop primary, desktop compact, tablet, and mobile viewports.
- Long Suite 100 passes 100 of 100 through the catalog-discovered `tests.game_drivers.caribbean_stud:play` driver in a copied deployment.

## Listener Cleanup

- Bootstrap/API listeners: PIDs `88724`, `63576`, `82536`, and `4036` on ports `58994`, `59088`, `56871`, and `58644`; all ports verified closed.
- Browser listener: PID `29048` on port `64110`; port verified closed.
- Long Suite listener: PID `88496` on port `63066`; port verified closed and copied deployment removed.
- Protected ports `8765` and `8877` and user/shared runtime data were not used or modified.
