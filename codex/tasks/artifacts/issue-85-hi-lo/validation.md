# Issue #85 focused validation

Branch: `codex/game-hi-lo`

Validated base: `origin/main` at `0a1ebc2d7d034bb855ad968215bc61adcd18f4c9`

Validation date: 2026-07-14

## Passing focused checks

| Command | Result |
| --- | --- |
| `python -m unittest tests.games.hi_lo.test_engine tests.games.hi_lo.test_api` | PASS: 13 tests, including session isolation, semantic retry conflicts, restart recovery, crash-before-wager recovery, durable action receipts, and ledger settlement shapes. |
| `node --check web/games/hi_lo.js` | PASS. |
| `node tests/games/hi_lo/test_frontend.mjs` | PASS: localized visible/ARIA copy, shared card renderer, retry-stable IDs, responsive/reduced-motion CSS, and timer-free lifecycle checks. |
| `python -m unittest tests.card_poker_primitives_tests` | PASS: 9 shared #96 card-primitive tests. |
| `node tests/card_renderer_tests.js` | PASS: shared card-renderer checks. |
| `python verify_rules.py` | PASS: 32 rule checks. |
| `python scripts/validate_contracts.py` | PASS: 8 shared APIs and 8 catalog games. |
| `python scripts/validate_module_boundaries.py` | PASS. |
| `python scripts/validate_requirements.py` | PASS: 420 requirements. No permanent Hi-Lo IDs are claimed. |
| `python scripts/check_comment_density.py` | PASS: 9456/9467 meaningful lines have nearby comments (99.9%); all 11 warnings are pre-existing premium-redesign prerender lines outside this issue. |
| Descriptor hook import (`casino.games.hi_lo.api:register`, `tests.game_drivers.hi_lo:play`) | PASS. |
| UTF-8 JSON parse for the descriptor and both locale files | PASS. |
| `git diff --check` | PASS. |

## Expected shared-integration blockers

`python scripts/validate_versions.py` exits 1 with only:

```text
Version validation failed:
 - module manifests missing from aggregate manifest: hi_lo
 - configured games missing canonical module revisions: hi_lo
```

`python scripts/validate_game_catalog.py` exits 1 with only:

```text
Game catalog validation failed:
 - catalog game hi_lo has no canonical module revision
```

Both failures require the forbidden `modules/module-manifest.json` integration edit and belong to issue #77. The worker-owned backend/frontend hooks, descriptor, contract, locales, driver, and focused tests are present.

## Deferred integrated checks

The following commands are intentionally deferred until #77 activates the shared aggregate revision, catalog route, requirement records, compatibility records, and visual-matrix row:

- `python tests/run_tests.py --api`
- `python tests/run_tests.py --browser`
- the catalog-discovered long suite and route-restoration checks
- authenticated real-backend EN/RU browser evidence at every required viewport

`python scripts/bootstrap_repo.py` was not run because this isolated worker was expressly prohibited from overwriting or cleaning the user's live shared `data/` state. No listener was started, so PID and port are not applicable; port 8765 was untouched and no listener cleanup was required.

## Evidence boundary

No screenshot is claimed as integrated `after_pass` evidence. Issue #77 must rerun the deferred checks and capture browser evidence from the exact accepted integration head. This packet demonstrates isolated readiness only and does not claim shared integration acceptance.
