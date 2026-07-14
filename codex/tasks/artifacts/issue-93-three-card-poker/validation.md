# Issue #93 focused validation

Status: focused worker validation passed on `codex/issue-93-three-card-poker` from base `0a1ebc2d7d034bb855ad968215bc61adcd18f4c9`. The only failing probes are the expected #77-owned aggregate revision checks below. This is not shared integration acceptance.

## Passed focused checks

- `python -m unittest discover -s tests/games/three_card_poker -p 'test_*.py' -v`: 14 tests passed for ranking, paytables, dealer qualification, deterministic dealing, session precedence, conflicting retries, Fold forfeiture, insufficient-funds rollback, ledger exactly-once replay, and reload recovery.
- `node tests/games/three_card_poker/test_frontend.mjs`: passed paired EN/RU key and placeholder parity, shared-card reuse, API shape, stable retry lanes, unmount guards, timer absence, reduced-motion, bounded wagers, accessible list semantics, and hard-coded-visible-English checks.
- `python -m unittest tests.card_poker_primitives_tests -v`: 9 shared #96 card/poker primitive tests passed.
- `node tests/card_renderer_tests.js`: shared #96 renderer tests passed.
- Python in-memory compilation: all 8 new backend, Python test, and long-driver files passed without creating bytecode artifacts.
- `node --check web/games/three_card_poker.js`: passed.
- JSON parsing: module descriptor and both paired locale files passed; UTF-8 Russian resources contain Cyrillic text without replacement characters.
- `python verify_rules.py`: 32 rule checks passed.
- `python scripts/validate_contracts.py`: passed for 8 shared APIs and 8 catalog games.
- `python scripts/validate_module_boundaries.py`: passed.
- `python scripts/validate_requirements.py`: passed for 420 requirements.
- `python scripts/check_comment_density.py`: passed at 99.9%; its 11 warnings are pre-existing and confined to `codex/tasks/artifacts/premium-redesign-prerenders/machine-draw-games/source/render-prerenders.js`, with no issue #93 warning.

## Passed safety and scope audits

- All 19 new files are confined to issue-owned game, contract, descriptor proposal, driver, test, documentation, locale, and evidence paths.
- No Three Card Poker backend file imports another game package or mutates player balances directly.
- Every player-visible and accessible game string is sourced from paired EN/RU resources; Fold help explicitly states that Ante and any Pair Plus wager are forfeited.
- No timer primitive, Python bytecode artifact, `data/` change, or `logs/` change remains.
- No listener was started; port 8765 was never used or inspected.
- `git diff --cached --check`: passed with no whitespace or patch-integrity errors before commit.

## Expected #77 integration blockers

Adding the module-owned descriptor is expected to produce only these shared revision failures until #77 updates the forbidden aggregate manifest:

- `python scripts/validate_game_catalog.py`: `catalog game three_card_poker has no canonical module revision`
- `python scripts/validate_versions.py`: `configured games missing canonical module revisions: three_card_poker`
- `python scripts/validate_versions.py`: `module manifests missing from aggregate manifest: three_card_poker`

The worker must not repair these diagnostics by editing `modules/module-manifest.json` or any other shared integration surface.

## Deferred acceptance

- Full API and browser suites, catalog-driven Long Suite 100, permanent requirement mappings, compatibility digests, the visual-matrix row, and real-backend EN/RU `after_pass` evidence require #77 integration.
- Catalog APIs that require a canonical revision may remain unavailable until the aggregate manifest entry lands.
- The packaged application release remains `9.1.1`; formal release work is not assigned.

## Listener safety

No listener was started for this focused validation. If a later integration run requires one, it must bind only to `127.0.0.1` on an ephemeral port other than 8765, record PID and port, stop after validation, and verify the port is closed. Port 8765 and the user's live `data/` remain untouched.
