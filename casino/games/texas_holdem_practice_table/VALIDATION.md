# Issue #95 integrated validation evidence

Validation date: 2026-07-15

Branch: `codex/game-texas-holdem-practice-table`

Reconciled base: `origin/main` at `1ca0cc030cf8cd5c7ba2a443a6b388ec592d96cb`

Readiness state: the separately accepted issue #191 hostile-client/server-authority certification is consumed and extended for Texas Hold'em Practice. The packet is eligible for coordinator acceptance after fresh exact-head GitHub checks.

## Focused game and certification evidence

| Command | Result |
| --- | --- |
| `python -m unittest casino.games.texas_holdem_practice_table.tests.test_engine casino.games.texas_holdem_practice_table.tests.test_api casino.games.texas_holdem_practice_table.tests.test_contract` | PASS: 20 tests covering session override, two-player isolation, replay/conflict semantics, reload recovery, privacy, human and funded-opponent ledger intents, and EN/RU contract parity. |
| `python tests/server_authority_tests.py` | PASS: the generated current-catalog matrix includes 30 games and both Texas Hold'em mutation actions with all nine mandatory assurances. |
| `node casino/games/texas_holdem_practice_table/tests/test_frontend.mjs` | PASS. |
| `node --check web/games/texas_holdem_practice_table.js` | PASS. |
| `python scripts/bootstrap_repo.py` | PASS: compilation, rules, API/security/restart coverage, contracts, module boundaries, catalog, requirements, versions, and comment density. |
| `python verify_rules.py` | PASS: 32 rule checks. |
| `python scripts/generate_server_authority_matrix.py --check` | PASS: generated compatibility matrix is current. |
| `python scripts/generate_docs.py --check` | PASS: generated requirements documentation is current. |
| `python scripts/validate_contracts.py` | PASS: 8 shared APIs and 30 catalog games. |
| `python scripts/validate_module_boundaries.py` | PASS. |
| `python scripts/validate_requirements.py` | PASS: 552 requirements. |
| `python scripts/validate_versions.py` | PASS: packaged release 9.1.1 and 43 module revisions. |
| `python scripts/validate_game_catalog.py` | PASS: 30 current catalog descriptors and target 20. |
| `python scripts/check_comment_density.py` | PASS: 27,571/27,582 meaningful lines; the 11 warnings remain pre-existing generated design artifacts. |

## Hostile-client and real-backend evidence

| Command | Result |
| --- | --- |
| `python tests/run_tests.py --api` | PASS. `API-SEC-001` covers SEC-001 through SEC-009 across the current catalog. `API-THPT-001` rejects stale/future phase actions, ignores protected identity/role/card/deck/RNG/outcome/payout/settlement fields, binds the authenticated player, proves two-user isolation, replays exact retries, conflicts changed payloads, settles only the server-computed pot through the ledger, and retains restart recovery plus Admin-auditable funded-opponent movements. |
| `python tests/run_tests.py --storage` | PASS: JSON parity, cross-process storage-enforced idempotency/concurrency, practice-opponent accounting, and MySQL schema-provider coverage. |
| `python tests/run_tests.py --browser` | PASS: 56/56. `BR-SEC-001` and `BR-THPT-001` cover client wallet/game-state tampering and canonical refresh recovery. Texas Hold'em evidence covers EN/RU at desktop-primary, desktop-compact, tablet, and mobile across ready, preflop, flop, turn, river, showdown/settled, folded, reduced-motion, and route-restored post-tamper states. |
| `python tests/long_suites.py --suite 100 --copy-deployment --deployment-root <temp>` | PASS: 100/100 scenarios; Texas Hold'em Practice played 100 times; all 552 requirements received 100 touches against a required floor of 10; 10/10 browser-audio starts completed with zero cancellation. |

## Ledger, identity, and storage evidence

- The authenticated human reserves five units through one storage-enforced ledger debit and receives only storage-enforced refunds or payouts.
- Each server-controlled seat resolves to the funded `bot_1`, `bot_2`, or `bot_3` player account created by issue #189; its escrow, refund, and payout use the public practice-opponent controller and remain visible through Admin audit endpoints.
- Every wallet action uses the issue #190 storage uniqueness key and immutable semantic fingerprint, so exact retries replay and changed payloads conflict across restart/process boundaries.
- Protected client fields cannot choose identity, role, cards, deck, RNG seed, outcome, payout, settlement total, phase, or turn; the router and engine derive them from the authenticated session and server state.
- Public table state retains seat labels but omits bot player IDs and hidden cards before showdown.
- The canonical `/api/v1` envelope and route restoration behavior remain compatible.

## Visual evidence

- Evidence root: `logs/test-runs/after-pass-texas-holdem-practice-*.png` with adjacent JSON metadata.
- Representative EN desktop showdown/settled and RU mobile route-restored post-tamper frames were visually inspected after the browser pass.
- No inspected frame showed horizontal overflow, clipped controls, untranslated game copy, stale attacker-supplied state, or opponent-card exposure before showdown.

## Listener and runtime cleanup

- API listeners: PIDs `93016`/`91388` on ports `53316`/`53648`; both processes and listeners were verified absent after the passing run.
- Bootstrap listeners: PIDs `62620`/`73628` on ports `62282`/`52475`; both processes and listeners were verified absent after the passing run.
- Browser listener: runner-managed listener on port `63587`; the listener was verified absent after 56/56 passed.
- Long Suite passing listener: PID `75808` on port `54639`; process and listener verified absent.
- Two non-acceptance Long Suite infrastructure attempts were cleaned: PID `66528` on port `59664` hit the initial wrapper timeout, and PID `5456` on port `57299` completed scenarios but could not overwrite the report under the sandbox. Both processes and listeners were explicitly stopped and verified absent; neither result is counted as acceptance evidence.
- The passing Long Suite disposable deployment was removed after the run; its empty named parent was removed separately.
- Test-created files under this separate worktree's `data/` directory were restored/removed. The user's shared checkout, runtime data, and ports `8765`/`8877` were untouched.

## Acceptance handoff

Issue #191 is accepted in `origin/main`, and this branch extends its SEC-001 through SEC-009 certification without weakening issue #190 storage idempotency or issue #189 funded-opponent settlement. PR #120 should remain draft until the coordinator verifies this exact refreshed head and all eight GitHub checks are green.
