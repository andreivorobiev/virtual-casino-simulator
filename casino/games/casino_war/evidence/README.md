# Casino War isolated evidence

Evidence class: development validation only. This directory contains no `after_pass` acceptance screenshot because the game is deliberately not registered in the shared catalog/router/web shell while #110/#77 own those files. A screenshot from a hand-wired or stale page would violate `docs/visual_design_standard.md`.

## Implemented surfaces

- Engine states: initial player win, initial dealer win, tie decision, surrender, war win, second-tie win, and war loss.
- API commands: state recovery, start round, surrender, and war.
- Ledger sequence: ante debit; optional war debit; optional surrender or settlement credit.
- Browser states prepared for matrix integration: accepting wager, initial result, war decision, and war result.
- Locales: key-parity EN/RU resources with localized visible and accessible game-owned copy.
- Motion: no game-owned timers; shared card CSS and scoped transitions respect reduced motion.

## Validation record

Validated on branch `codex/game-casino-war` from the isolated worker checkout:

- `python -m unittest discover -s casino/games/casino_war/tests -p "test_*.py"` — PASS, 13 tests.
- `node casino/games/casino_war/tests/frontend_module_tests.mjs` — PASS.
- `node --check web/games/casino_war.js` — PASS.
- Python compilation for the game package and focused Python tests — PASS.
- `python verify_rules.py` — PASS, 32 checks.
- `python scripts/validate_module_boundaries.py` — PASS.
- `python scripts/validate_contracts.py` — PASS, 14 OpenAPI files.
- `python scripts/validate_requirements.py` — PASS, 410 requirements.
- `python scripts/validate_versions.py` — PASS, packaged release 9.1.1 and 19 module revisions.
- `python scripts/check_comment_density.py` — PASS, 99.9%; warnings are only in pre-existing premium prerender artifacts outside the owned files.
- `git diff --check` — PASS after all owned files were included in the diff.

The central API runner, browser runner, catalog validator, long-suite driver, visual matrix, and real-backend screenshots require the descriptor/registration work reserved for #110/#77. They are integration dependencies, not acceptance evidence for this isolated branch.
