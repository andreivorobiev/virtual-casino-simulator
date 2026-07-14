# Issue #95 validation evidence

Validation date: 2026-07-14

Branch: `codex/game-texas-holdem-practice-table`

Reconciled base: `origin/main` at `f8c836163eab3dc92d83e7bf875ee963c11bddcf`

## Focused game evidence

| Command | Result |
| --- | --- |
| `python -m unittest discover -s casino/games/texas_holdem_practice_table/tests -p "test_*.py" -v` | PASS: 20 tests, including session override, two-player isolation, strict action-id/wager types, exact replay beyond the 20-hand public history window, replay conflict, stale-phase rejection, reload recovery, privacy, ledger intents, 90-key EN/RU parity and encoding safety, and runtime/contract timestamp alignment. |
| `node casino/games/texas_holdem_practice_table/tests/test_frontend.mjs` | PASS. |
| `node --check web/games/texas_holdem_practice_table.js` | PASS. |
| `python -c "from tests.game_drivers.texas_holdem_practice_table import play; assert callable(play)"` | PASS: the proposed real-backend driver imports and now repeats start and decision payloads while asserting unchanged hand, pot, phase, and balance. Actual registered execution remains #77 acceptance work. |

## Repository and shared-primitive evidence

| Command | Result |
| --- | --- |
| `python verify_rules.py` | PASS: 32 rule checks. |
| `python scripts/validate_contracts.py` | PASS: 8 shared APIs and 12 currently registered games. The isolated contract is additionally checked by the focused suite because #77 has not registered it. |
| `python scripts/validate_module_boundaries.py` | PASS. |
| `python scripts/validate_requirements.py` | PASS: 445 central requirements. Proposed `THPT-*` IDs remain intentionally unallocated. |
| `python scripts/validate_versions.py` | PASS: packaged release 9.1.1 and 25 current module revisions. The proposed game module remains intentionally unmaterialized. |
| `python scripts/generate_docs.py --check` | PASS: generated requirements documentation is current. |
| `python scripts/validate_game_catalog.py` | PASS: 12 current games and target 20. Texas Hold'em discovery remains intentionally deferred to #77. |
| `python scripts/check_comment_density.py` | PASS at 13,404/13,415 meaningful lines; all 11 warnings remain pre-existing under `codex/tasks/artifacts/premium-redesign-prerenders/`. |
| `python -m unittest tests.card_poker_primitives_tests` | PASS: 9 shared #96 card/poker tests. |
| `node tests/card_renderer_tests.js` | PASS. |

## Safety and scope evidence

- No listener was started. Ports `8765` and `8877` and the user's live Casino session were untouched.
- No shared `data/` path was read, cleaned, restored, staged, or overwritten.
- No forbidden registry, router, shell, global locale/style, manifest, central requirement, compatibility, runner, or visual-matrix file was edited.
- Browser code owns no timer or animation loop, uses the shared card renderer, localizes visible and ARIA copy in EN/RU, includes reduced-motion handling, and has compact-height plus stacked responsive rules.
- No screenshot is labeled `after_pass`. Real registered browser evidence cannot exist until #77 materializes catalog and visual-matrix discovery.

## Required #77 acceptance work

This evidence proves only the isolated slice. Shared acceptance remains blocked on descriptor/manifest materialization, permanent requirements and test mappings, compatibility digest/matrix updates, central API/browser/long discovery, shared version bumps, and exact integrated EN/RU visual evidence.

Two additional hard gates remain explicit:

1. Practice opponents currently use virtual contributions and the same game-engine action validator, not funded bot player accounts through the shared public bot controller. This does not claim `BOT-001..007` or platform all-wager acceptance.
2. Prepared state, ledger scanning, and the process-local lock cover normal duplicate requests while one process remains running. Shared JSON balance mutation plus ledger append is not crash-atomic, and multiple processes do not share an action-key lock. Exactly-once acceptance therefore requires a shared storage-level unique action key committed atomically with balance and ledger insertion.

After registration, #77 must also repeat envelope/authentication, two-user isolation, real-ledger restart/replay, long-driver, route restoration, responsive, reduced-motion, and EN/RU checks against the real HTTP server and configured store.
