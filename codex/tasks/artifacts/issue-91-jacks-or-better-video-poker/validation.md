# Issue #91 focused validation

Status: **CI CORRECTION LOCAL PASS / REMOTE CHECKS PENDING** on `codex/issue-91-jacks-or-better-video-poker`.

## Focused checks completed

- `python -m unittest discover -s tests/games/jacks_or_better_video_poker -p 'test_*.py' -v`: **PASS**, 11 tests.
- `node tests/games/jacks_or_better_video_poker/test_frontend.mjs`: **PASS**.
- `python -m py_compile casino/games/jacks_or_better_video_poker/__init__.py casino/games/jacks_or_better_video_poker/engine.py casino/games/jacks_or_better_video_poker/api.py tests/games/jacks_or_better_video_poker/test_engine.py tests/games/jacks_or_better_video_poker/test_api.py tests/game_drivers/jacks_or_better_video_poker.py`: **PASS**.
- `node --check web/games/jacks_or_better_video_poker.js`: **PASS**.
- `python -m unittest tests.card_poker_primitives_tests`: **PASS**, 9 tests.
- `node tests/card_renderer_tests.js`: **PASS**.
- `python scripts/validate_contracts.py`: **PASS**, 8 shared APIs and 7 integrated catalog games.
- `python scripts/validate_module_boundaries.py`: **PASS**.
- `python scripts/validate_requirements.py`: **PASS**, 420 requirements.
- `python scripts/validate_versions.py`: **PASS**, packaged release `9.1.1` and 20 module revisions.
- `python scripts/validate_game_catalog.py`: **PASS**, 7 current games and target 20.
- `python scripts/check_comment_density.py`: **PASS**, 99.9%; the 11 reported warnings are pre-existing premium prerender lines outside this game slice.
- `python verify_rules.py`: **PASS**, 32 checks.
- `git diff --check`: **PASS**.
- `git hash-object` against the prior committed descriptor blob: **PASS**, both are `a7bd9802f5c3e0df20a905882115c978cbe6c336`.

The focused game suite and frontend static suite were rerun after moving the descriptor proposal out of automatic catalog discovery.

## Shared-integration boundary

- The unchanged `1.0.0` descriptor proposal now lives under this evidence directory, outside automatic `modules/*.json` discovery, until issue #77 can promote it together with the canonical aggregate revision.
- `python scripts/validate_versions.py` and `python scripts/validate_game_catalog.py` both pass on the isolated branch after that relocation.
- Central requirements, compatibility metadata, visual-matrix registration, central browser/API mappings, and accepted real-backend evidence remain issue #77 work.

The central API, browser, and long suites were not run locally because those flows bootstrap shared runtime `data/`. Their GitHub workflows must rerun on the corrected head; accepted real-backend game evidence still belongs on the exact #77 integration head after shared registration.

## Listener and runtime safety

No listener was started. There is no worker PID or port to clean up; port `8765` and shared `data/` were untouched. Any later real-backend check must bind `127.0.0.1` on an ephemeral port other than `8765`, record PID and port, stop the listener, verify closure, and leave shared `data/` untouched.
