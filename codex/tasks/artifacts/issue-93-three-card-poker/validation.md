# Issue #93 focused validation

Status: PR #118 is integrated on `origin/main` at `f8c836163eab3dc92d83e7bf875ee963c11bddcf`. Issue #77 promoted the descriptor into canonical discovery and completed focused, API, browser, Long Suite 100, validator, and EN/RU visual evidence.

## CI correction

- The original `modules/three_card_poker.json` location auto-installed the isolated proposal, so `/api/v1/casino/reset` indexed a game that had no canonical module revision and raised `KeyError: 'three_card_poker'` in CI, Browser Tests, and Long Suite 100.
- The accepted descriptor now lives at `modules/three_card_poker.json` and participates in runtime catalog discovery.
- It retains module `three_card_poker` at version `1.0.0`, sort order `190`, and permanent requirements `TCP-001` through `TCP-005`.
- Exact-head catalog and reset coverage confirms 13 registered games and canonical Three Card Poker discovery.

## Passed focused checks

- `python -m unittest discover -s tests/games/three_card_poker -p 'test_*.py' -v`: 14 tests passed for ranking, paytables, dealer qualification, deterministic dealing, session precedence, conflicting retries, Fold forfeiture, insufficient-funds rollback, ledger exactly-once replay, and reload recovery.
- `node tests/games/three_card_poker/test_frontend.mjs`: passed paired EN/RU key and placeholder parity, shared-card reuse, API shape, stable retry lanes, unmount guards, timer absence, reduced-motion, bounded wagers, accessible list semantics, and hard-coded-visible-English checks.
- The game-local long driver passed against an in-memory registered router, including exact opening-wager and Play-decision replays with stable round, ledger, and balance evidence.
- `python -m unittest tests.card_poker_primitives_tests -v`: 9 shared #96 card/poker primitive tests passed.
- `node tests/card_renderer_tests.js`: shared #96 renderer tests passed.
- Python in-memory compilation: all 8 new backend, Python test, and long-driver files passed without creating bytecode artifacts.
- `node --check web/games/three_card_poker.js`: passed.
- JSON parsing: the module descriptor proposal and both paired locale files passed; UTF-8 Russian resources contain Cyrillic text without replacement characters.
- All four proposal-declared source paths and its one contract path exist.
- Targeted proposal-owned OpenAPI audit passed for the exact three additive v1 routes and standard success/error envelope schemas.
- `python verify_rules.py`: 32 rule checks passed.
- `python scripts/validate_contracts.py`: passed for 8 shared APIs and 13 catalog games.
- `python scripts/validate_module_boundaries.py`: passed.
- `python scripts/validate_requirements.py`: passed for 450 requirements.
- `python scripts/validate_game_catalog.py`: passed for 13 current games and target 20.
- `python scripts/validate_versions.py`: passed for packaged release 9.1.1 and 26 module revisions.
- `python scripts/generate_docs.py --check`: passed with generated requirements documentation current.
- `python scripts/check_comment_density.py`: passed at 13436/13447 meaningful lines (99.9%); its 11 warnings are pre-existing and confined to `codex/tasks/artifacts/premium-redesign-prerenders/machine-draw-games/source/render-prerenders.js`, with no issue #93 warning.

## Passed safety and scope audits

- The correction changes only the descriptor location plus issue-owned documentation/evidence; no shared integration file is edited.
- `modules/three_card_poker.json` is absent, while the issue-owned proposal remains valid JSON at version `1.0.0`.
- No Three Card Poker backend file imports another game package or mutates player balances directly.
- Every player-visible and accessible game string is sourced from paired EN/RU resources; Fold help explicitly states that Ante and any Pair Plus wager are forfeited.
- No timer primitive, Python bytecode artifact, `data/` change, or `logs/` change remains.
- No listener was started; ports 8765 and 8877 were never used or inspected.
- DCO audit passed for both branch commits, with one `Signed-off-by` trailer on each commit.
- `git diff --check origin/main...HEAD`: passed with no whitespace or patch-integrity errors after the current-main rebase.

## #77 promotion gate

Catalog and version validators now pass because the proposal is intentionally outside runtime discovery. When #77 accepts the game, the integration owner must atomically:

- promote the issue-owned proposal to `modules/three_card_poker.json`;
- add the matching `three_card_poker: 1.0.0` canonical revision to `modules/module-manifest.json`; and
- complete the central requirements, compatibility, visual-matrix, runner, and evidence mappings from the accepted main head.

The worker does not edit any of those shared integration surfaces.

## Deferred acceptance

- Full API, Browser Tests, and Long Suite 100 run through the GitHub checks for the pushed PR head without touching the user's live local session.
- The game remains intentionally absent from runtime catalog APIs until #77 promotes the proposal with its canonical revision.
- The packaged application release remains `9.1.1`; formal release work is not assigned.

## Listener safety

No listener was started for this focused validation. If a later integration run requires one, it must bind only to `127.0.0.1` on an ephemeral port other than 8765 or 8877, record PID and port, stop after validation, and verify the port is closed. Ports 8765 and 8877 and the user's live `data/` remain untouched.
