# Issue #91 focused validation

Status: **FOCUSED PASS / EXPECTED SHARED BLOCKERS** on `codex/issue-91-jacks-or-better-video-poker`.

## Focused checks completed

- `python -m unittest discover -s tests/games/jacks_or_better_video_poker -p 'test_*.py' -v`: **PASS**, 11 tests.
- `node tests/games/jacks_or_better_video_poker/test_frontend.mjs`: **PASS**.
- `python -m py_compile casino/games/jacks_or_better_video_poker/__init__.py casino/games/jacks_or_better_video_poker/engine.py casino/games/jacks_or_better_video_poker/api.py tests/games/jacks_or_better_video_poker/test_engine.py tests/games/jacks_or_better_video_poker/test_api.py tests/game_drivers/jacks_or_better_video_poker.py`: **PASS**.
- `node --check web/games/jacks_or_better_video_poker.js`: **PASS**.
- `python -m unittest tests.card_poker_primitives_tests`: **PASS**, 9 tests.
- `node tests/card_renderer_tests.js`: **PASS**.
- `python scripts/validate_contracts.py`: **PASS**, 8 shared APIs and 8 catalog games.
- `python scripts/validate_module_boundaries.py`: **PASS**.
- `python scripts/validate_requirements.py`: **PASS**, 420 requirements.
- `python scripts/check_comment_density.py`: **PASS**, 99.9%; the 11 reported warnings are pre-existing premium prerender lines outside this game slice.
- `python verify_rules.py`: **PASS**, 32 checks.
- `git diff --check`: **PASS**.

The two focused game suites were rerun after the final ledger-audit assertions and frontend comment-density cleanup.

## Expected shared-integration blockers

- `python scripts/validate_versions.py`: **EXPECTED FAIL** with only `module manifests missing from aggregate manifest: jacks_or_better_video_poker` and `configured games missing canonical module revisions: jacks_or_better_video_poker`. The allowed descriptor is intentionally absent from forbidden `modules/module-manifest.json`.
- `python scripts/validate_game_catalog.py`: **EXPECTED FAIL** with only `catalog game jacks_or_better_video_poker has no canonical module revision`. Issue #77 has not assigned the canonical aggregate revision.
- Central requirements, compatibility metadata, visual-matrix registration, central browser/API mappings, and accepted real-backend evidence remain issue #77 work.

The central `tests/run_tests.py --api` and `--browser` suites were not run from this isolated lane because the game is intentionally absent from the shared manifest/router and those flows bootstrap shared runtime `data/`. Real-backend browser evidence belongs on the exact #77 integration head after shared registration.

## Listener and runtime safety

No listener was started. There is no worker PID or port to clean up; port `8765` and shared `data/` were untouched. Any later real-backend check must bind `127.0.0.1` on an ephemeral port other than `8765`, record PID and port, stop the listener, verify closure, and leave shared `data/` untouched.
