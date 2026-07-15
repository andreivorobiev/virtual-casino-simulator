# Validation Notes

Issue: #130

PR: #177

Branch: `codex/issue-130`

This packet records the integrated working-tree gates. The PR handback records the signed exact head and its fresh GitHub checks.

## Focused and Governance Checks

- PASS: Joker Poker engine, API, resource-parity, descriptor, and contract tests (`11` tests).
- PASS: Joker Poker frontend static contract test.
- PASS: `python scripts/bootstrap_repo.py` and `python verify_rules.py` (`32` rule checks).
- PASS: `python scripts/validate_contracts.py` (`8` shared APIs; `29` catalog games).
- PASS: catalog validator (`29` current games).
- PASS: `python scripts/validate_module_boundaries.py`.
- PASS: `python scripts/validate_requirements.py` (`530` requirements).
- PASS: `python scripts/validate_versions.py` (`42` module revisions; packaged application `9.1.1`).
- PASS: `python scripts/check_comment_density.py`; the remaining `11` warnings are pre-existing prerender-source warnings.
- PASS: `git diff --check`.

## Real-Backend Acceptance

- PASS: full API suite, including `API-JP-001`, session-owned two-user isolation, hostile `player_id` rejection, exactly-once ledger settlement, changed-payload conflict, private draw-pool exclusion, and `API-WALLET-RESTART-001` replay after restart.
- PASS: full browser suite, including `BR-JP-001`, English and Russian copy, all four visual-matrix viewports, ready/hold/win/loss/reduced-motion/route-restored states, catalog discovery, and shared route restoration.
- PASS: Long Suite 100 from a disposable deployment copy: `100/100` scenarios, minimum requirement touches `100`, and Joker Poker plays `100`.
- PASS: browser-audio tail: `10` Baccarat starts, `10` voice ends, `10` speech ends, and no voice cancellations.
- PASS: the 29th catalog entry remains within two rows at the 1366x768 compact desktop breakpoint, preserving the existing Roulette viewport gate.

## Listener Cleanup

- Browser PASS listener: PID `87716`, `127.0.0.1:50272`; process stopped and port closure verified.
- Long Suite PASS listener: PID `45916`, `127.0.0.1:59666`; process stopped and port closure verified.
- Two failed preliminary Long Suite listeners, PIDs `90592` and `90164`, were stopped and their ports closed before the disposable-copy PASS.
- Protected ports `8765` and `8877` were never used or stopped.
- The disposable deployment tree was removed automatically, and the shared checkout/runtime data was never touched.

## Blockers

- None in Joker Poker integration scope. PR #120 remains separately held on issues #189 and #190.
