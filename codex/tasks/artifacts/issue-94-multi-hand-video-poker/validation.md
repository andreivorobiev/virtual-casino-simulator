# Issue #94 focused validation

Status: focused isolated checks passed on `codex/game-multi-hand-video-poker`; one expected shared-integration validation remains blocked.

## Passed

- `python -m unittest tests.games.multi_hand_video_poker.test_engine tests.games.multi_hand_video_poker.test_api` — PASS, 6 tests. Covers deterministic 3/5/10 modes, shared holds, paytable qualification, session binding, idempotent request replay, simulated post-ledger/pre-marker crash recovery, and exactly-once debit/credit counts.
- `node tests/games/multi_hand_video_poker/test_frontend.mjs` — PASS. Covers EN/RU key parity, catalog export/readiness hook, shared renderer use, localized card labels, required modes, reduced motion, and absence of game-owned timers.
- `python -m py_compile ...` for all new Python source/test/driver files — PASS.
- `node --check web/games/multi_hand_video_poker.js` — PASS.
- Isolated #110 descriptor-hook import/static check — PASS for backend registration, long driver, frontend export, canonical route, and contract path.
- `python -m unittest tests.card_poker_primitives_tests` — PASS, 9 tests.
- `node tests/card_renderer_tests.js` — PASS.
- `python scripts/validate_contracts.py` — PASS for 14 OpenAPI files.
- `python scripts/validate_module_boundaries.py` — PASS.
- `python scripts/validate_requirements.py` — PASS for 410 requirements.
- `python scripts/check_comment_density.py` — PASS at 99.9%; remaining warnings are pre-existing machine-draw prerender artifacts outside issue #94.
- `python verify_rules.py` — PASS, 32/32 checks.
- `git diff --check` — PASS after staging the isolated files.

## Expected integration blocker

- `python scripts/validate_versions.py` — expected FAIL only because `multi_hand_video_poker` is intentionally absent from the forbidden shared `modules/module-manifest.json`. Integration owner #77 must add the `1.0.0` canonical revision after #110 merges.

## Not run on this isolated branch

- Central API/browser/long-suite discovery and real-backend visual evidence require the shared catalog/router/shell/test-discovery changes currently owned by #110/#77.
- No listener was started; PID/port cleanup is not applicable.

No listener is required for the isolated validation plan. If integration validation later starts one, it must bind only to `127.0.0.1`, record PID and port, and verify the port is closed afterward.
