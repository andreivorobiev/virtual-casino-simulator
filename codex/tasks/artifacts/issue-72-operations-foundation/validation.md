# Issue #72 focused validation

Status: focused isolated checks passed on `codex/issue-72-operations-foundation`; shared integration remains serialized under #77 without making central validation fail.

## Passed

- `python scripts/bootstrap_repo.py` — PASS, including compilation, API, rules, contracts, boundaries, catalog, requirements, versions, and comment density.
- `python -m unittest discover -s tests/operations -p "test_*.py" -v` — PASS, 18 tests. Covers storage-free liveness, canonical app version use, SHA sanitization, concrete temporary JSON plus readable/writable/corrupt JSON readiness boundaries, fresh MySQL `SELECT 1`, resource cleanup, live/degraded states, completion-time and monotonic retained heartbeat tracking, provider/build/unexpected-service error suppression, imported-error sanitizer bypass prevention, provider allowlisting, exact routes, endpoint-specific fixed 503 schemas, precise compatibility, and module ownership.
- `python tests/run_tests.py --api` — PASS, all 22 current mapped API regression cases.
- `python tests/run_tests.py --browser` — PASS, all 31 current mapped browser regression cases.
- `python tests/long_suites.py --suite 100 --copy-deployment` — PASS, 100 full-casino scenarios plus browser-audio verification from an automatically removed disposable deployment.
- `python -m py_compile` for all new Operations source and focused test files — PASS.
- `python scripts/validate_contracts.py` — PASS for the existing eight shared APIs and seven catalog games; the Operations OpenAPI file is additionally covered by the focused static contract test until #77 adds central discovery.
- `python scripts/validate_module_boundaries.py` — PASS.
- `python scripts/validate_requirements.py` — PASS for 420 current requirements.
- `python scripts/validate_versions.py` — PASS after preserving the Operations 1.0.0 descriptor as `operations.module.proposal.json` outside #77-owned central module discovery.
- `python scripts/check_comment_density.py` — PASS at 99.9%; the eleven warnings are pre-existing machine-draw prerender lines outside issue #72.
- `python verify_rules.py` — PASS, 32/32 checks.
- `python scripts/generate_docs.py --check` — PASS; generated requirements are current.

## Serialized shared-integration gate

- #77 must promote `operations.module.proposal.json` to `modules/operations.json` and add `operations: 1.0.0` to the aggregate manifest in one serialized integration change.

## Not run on this isolated branch

- The central API and browser regression suites pass, but they cannot yet discover or authenticate the Operations routes until #77 edits the shared router, auth allowlist, and central test discovery.
- Real Admin UI and visual evidence require the shared shell, i18n, and visual-matrix integration owned by #77.
- The general copied-deployment Long Suite 100 passes; Operations-specific copied-deployment smoke still requires the integrated endpoints and must run later on a tracked dynamically allocated loopback port other than 8765.

## Listener safety

Focused tests and policy validators start no server. API, browser, and copied long-suite regressions use OS-assigned free ports on `127.0.0.1`, track their child processes, terminate and wait during cleanup, and leave no active Python TCP listener. Port 8765 is not used or stopped.
