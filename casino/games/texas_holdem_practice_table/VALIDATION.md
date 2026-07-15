# Issue #95 integrated validation evidence

Validation date: 2026-07-15

Branch: `codex/game-texas-holdem-practice-table`

Reconciled base: `origin/main` at `1aa1930d9e3783fc8d0f0207b988df0acbe2e72c`

Readiness state: draft-held on the separately owned issue #191 hostile-client/server-authority certification gate. This packet does not implement, accept, or claim that certification.

## Focused game evidence

| Command | Result |
| --- | --- |
| `python -m unittest casino.games.texas_holdem_practice_table.tests.test_engine casino.games.texas_holdem_practice_table.tests.test_api casino.games.texas_holdem_practice_table.tests.test_contract` | PASS: 20 tests covering session override, two-player isolation, replay/conflict semantics, reload recovery, privacy, human and funded-opponent ledger intents, and EN/RU contract parity. |
| `node casino/games/texas_holdem_practice_table/tests/test_frontend.mjs` | PASS. |
| `node --check web/games/texas_holdem_practice_table.js` | PASS. |
| `python scripts/bootstrap_repo.py` | PASS, including the full API and governance sequence. |
| `python verify_rules.py` | PASS: 32 rule checks. |
| `python scripts/generate_docs.py --check` | PASS: generated requirements documentation is current. |
| `python scripts/validate_contracts.py` | PASS: 8 shared APIs and 30 catalog games. |
| `python scripts/validate_module_boundaries.py` | PASS. |
| `python scripts/validate_requirements.py` | PASS: 543 requirements. |
| `python scripts/validate_versions.py` | PASS: packaged release 9.1.1 and 43 module revisions. |
| `python scripts/validate_game_catalog.py` | PASS: 30 current catalog descriptors and target 20. |
| `python scripts/check_comment_density.py` | PASS: 27,426/27,437 meaningful lines; the 11 warnings remain pre-existing generated design artifacts. |

## Real-backend and restart evidence

| Command | Result |
| --- | --- |
| `python tests/run_tests.py --api` | PASS. `API-THPT-001` proves authenticated-player binding, two-user isolation, storage-enforced action replay/conflict, all streets, terminal replay, exact human ledger movements, and Admin-auditable opponent movements. `API-WALLET-RESTART-001` reloads both retained hands after a real server restart. |
| `python tests/run_tests.py --storage` | PASS: JSON parity, JSON storage-enforced idempotency, practice-opponent accounting, and MySQL schema-provider coverage. |
| `python tests/run_tests.py --browser` | PASS. `BR-THPT-001` covers EN/RU at desktop-primary, desktop-compact, tablet, and mobile across ready, preflop, flop, turn, river, showdown/settled, folded, reduced-motion, and route-restored states. |
| `python tests/long_suites.py --suite 100 --copy-deployment --deployment-root <temp>` | PASS: 100/100 scenarios; Texas Hold'em Practice played 100 times; all 543 requirements received 100 touches against a required floor of 10; 10/10 browser-audio starts completed with zero cancellation. |

## Ledger, identity, and storage evidence

- The authenticated human reserves five units through one storage-enforced ledger debit and receives only storage-enforced refunds or payouts.
- Each server-controlled seat resolves to the funded `bot_1`, `bot_2`, or `bot_3` player account created by issue #189; its escrow, refund, and payout use the public practice-opponent controller and remain visible through Admin audit endpoints.
- Every wallet action uses the issue #190 storage uniqueness key and immutable semantic fingerprint, so exact retries replay and changed payloads conflict across restart/process boundaries.
- Public table state retains seat labels but omits bot player IDs and hidden cards before showdown.
- The canonical `/api/v1` envelope and route restoration behavior remain compatible.

## Visual evidence

- Evidence root: `logs/test-runs/after-pass-texas-holdem-practice-*.png` with adjacent JSON metadata.
- Representative EN desktop ready/decision and RU desktop settled frames were visually inspected after the browser pass.
- Representative EN and RU mobile decision frames were visually inspected after the browser pass.
- No inspected frame showed horizontal overflow, clipped controls, untranslated game copy, or opponent-card exposure before showdown.

## Listener and runtime cleanup

- API listeners: PIDs `94620`/`72168` on ports `51332`/`58446`; both processes and listeners were verified absent after the passing run.
- Bootstrap API listeners: PIDs `90576`/`87780` on ports `64394`/`64736`; both processes and listeners were verified absent.
- Browser listener: PID `63636` on port `65229`; process and listener verified absent.
- Long Suite listener: PID `67148` on port `49698`; process and listener verified absent.
- The Long Suite disposable deployment root was removed after the pass.
- Test-created files under this separate worktree's `data/` directory were restored/removed. The user's shared checkout, runtime data, and ports `8765`/`8877` were untouched.

## Remaining acceptance blocker

Issue #191 remains a hard external gate. PR #120 must stay draft and must not be marked ready, merged, closed, or counted until the current catalog has separately accepted hostile-client/server-authority certification and this game extends and passes the applicable matrix. No #191 implementation ownership is claimed by this branch.
