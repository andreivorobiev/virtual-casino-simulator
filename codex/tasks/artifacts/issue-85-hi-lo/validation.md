# Issue #85 / #77 integrated validation

Branch: `codex/issue-77-rebase-117`

Accepted base: `origin/main` at `727d5cf2a55d627e6b844cc871ff8e6f46a7c0bf`

Validation date: 2026-07-14

## Focused and static checks

| Command | Result |
| --- | --- |
| `python -m unittest tests.games.hi_lo.test_engine tests.games.hi_lo.test_api` | PASS: 13 tests covering rules, session isolation, semantic retry conflicts, restart recovery, durable receipts, and ledger settlement shapes. |
| `node --check web/games/hi_lo.js` | PASS. |
| `node tests/games/hi_lo/test_frontend.mjs` | PASS: localized visible/ARIA copy, shared card renderer, retry-stable IDs, responsive/reduced-motion CSS, and timer-free lifecycle checks. |
| `python verify_rules.py` | PASS: 32 rule checks. |
| `python scripts/validate_game_catalog.py` | PASS: 12 integrated games and target 20. |
| `python scripts/validate_contracts.py` | PASS: 8 shared APIs and 12 catalog games. |
| `python scripts/validate_module_boundaries.py` | PASS. |
| `python scripts/validate_requirements.py` | PASS: 445 requirements. |
| `python scripts/validate_versions.py` | PASS: packaged release 9.1.1 and 25 module revisions. |
| `python scripts/check_comment_density.py` | PASS: 12528/12539 meaningful lines have nearby comments; all 11 warnings are pre-existing premium-redesign prerender lines outside this scope. |
| `git diff --check` | PASS. |

## Integrated real-backend gates

- `python scripts/bootstrap_repo.py`: PASS in a disposable deployment.
- `python tests/run_tests.py --api`: PASS, including `API-HILO-001`, authenticated hostile-player override checks, exact deal and guess replay, changed-wager conflict rejection, hidden-card protection, ledger-only debit/refund/payout, and `API-WALLET-RESTART-001` history persistence.
- `python tests/run_tests.py --browser`: PASS, including catalog discovery, canonical route restoration, `BR-HILO-001`, complete EN/RU copy, four governed viewports, and every registered Hi-Lo state.
- `python tests/long_suites.py --suite 100 --copy-deployment`: PASS with `hi_lo: 100` plays across 100 full-casino scenarios and all 445 requirements touched at least 100 times.

## Visual evidence

`BR-HILO-001` generates 56 PNGs and 56 self-describing JSON sidecars under `logs/test-runs`:

- states: `ready`, `choose_higher_or_lower`, `correct_guess`, `incorrect_guess`, `tie_refund`, `reduced_motion`, and `route_restored`;
- locales: `en-US` and `ru-RU`;
- viewports: `desktop_primary`, `desktop_compact`, `tablet`, and `mobile`;
- source: the real catalog-registered backend and authenticated shared shell, with no forced-card or public test seam.

The test rejects English game leakage in Russian, page-level horizontal overflow, hidden or clipped active navigation, and an unlocalized catalog label. Representative English desktop choice and Russian mobile tie-refund images were visually inspected after the automated pass.

## Listener and runtime safety

All validation runs in disposable copies outside the shared checkout. Smoke listeners use ephemeral loopback ports only and every recorded PID is stopped before the next run. Ports `8765` and `8877` and the user-owned shared `data/` state are never contacted, stopped, cleaned, staged, restored, or overwritten. The exact pushed-head listener table and closure checks are recorded in the pull request handback.

The disposable Long Suite deployment cleans itself after success. Temporary validation copies are removed after the exact-head GitHub handoff is complete.
