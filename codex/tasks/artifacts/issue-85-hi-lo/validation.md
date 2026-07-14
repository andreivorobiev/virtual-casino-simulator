# Issue #85 focused validation

Branch: `codex/game-hi-lo`

Validated base: `origin/main` at `153f1e3676e5cec23eef39cbace885a021a03187`

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
| `python scripts/validate_contracts.py` | PASS: 8 shared APIs and 8 integrated catalog games. |
| `python scripts/validate_module_boundaries.py` | PASS. |
| `python scripts/validate_requirements.py` | PASS: 425 requirements. No permanent Hi-Lo IDs are claimed. |
| `python scripts/validate_versions.py` | PASS: packaged release 9.1.1 and 21 integrated module revisions. |
| `python scripts/validate_game_catalog.py` | PASS: 8 current games and target 20. |
| `python scripts/check_comment_density.py` | PASS: 10126/10137 meaningful lines have nearby comments (99.9%); all 11 warnings are pre-existing premium-redesign prerender lines outside this issue. |
| Descriptor hook import (`casino.games.hi_lo.api:register`, `tests.game_drivers.hi_lo:play`) | PASS. |
| UTF-8 JSON parse for the descriptor proposal and both locale files | PASS. |
| `git diff --check` | PASS. |

## CI correction

The unchanged `hi_lo` version `1.0.0` proposal is stored at:

```text
codex/tasks/artifacts/issue-85-hi-lo/hi_lo.module.proposal.json
```

Its SHA-256 before and after relocation is:

```text
F091E3F14476ECA7FEE284A4893D0BE453C0D12AD1078C5DB795DE2760AC42B3
```

`modules/hi_lo.json` is absent. The proposal therefore cannot be auto-installed before #77 promotes it alongside the canonical aggregate revision. This removes the prior `/api/v1/casino/reset` `KeyError: 'hi_lo'` failure without editing shared files.

## Deferred integrated checks

GitHub's current-game API, browser, and Long Suite workflows may run normally because the proposal is not part of integrated descriptor discovery. Hi-Lo-specific versions of the following acceptance checks remain deferred until #77 promotes the proposal with the shared aggregate revision, catalog route, requirement records, compatibility records, and visual-matrix row:

- `python tests/run_tests.py --api`
- `python tests/run_tests.py --browser`
- the catalog-discovered long suite and route-restoration checks
- authenticated real-backend EN/RU browser evidence at every required viewport

`python scripts/bootstrap_repo.py` was not run because this isolated worker was expressly prohibited from overwriting or cleaning the user's live shared `data/` state. No listener was started, so PID and port are not applicable; port 8765 was untouched and no listener cleanup was required.

## Evidence boundary

No screenshot is claimed as integrated `after_pass` evidence. Issue #77 must rerun the deferred checks and capture browser evidence from the exact accepted integration head. This packet demonstrates isolated readiness only and does not claim shared integration acceptance.
