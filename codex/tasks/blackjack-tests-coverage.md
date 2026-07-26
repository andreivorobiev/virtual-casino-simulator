# Blackjack Tests-First Coverage

## Task
- GitHub issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/8
- Branch: `codex/blackjack-tests-coverage`
- PR title: `Add deterministic Blackjack rules coverage`
- Coordinator chat: Casino Simulator - Coordinator
- Worker chat: Audit requirements backlog / Blackjack tests-first follow-up

## Goal
- Add deterministic API-suite coverage for under-tested Blackjack table rules.
- Keep the change tests-first; do not alter Blackjack gameplay unless tests expose a confirmed defect.
- Preserve `/api/v1` compatibility and existing fake-money behavior.

## Requirements
- Validated IDs: `BJ-002`, `BJ-003`, `BJ-004`, `BJ-005`, `BJ-006`, `BJ-007`, `BJ-012`, `BJ-015`, `BJ-016`, `BJ-017`, `BJ-018`, `BJ-019`, `BJ-026`.
- Module/version impact: patch bump of the tests module, starting from whatever `modules/tests.json`
  currently holds (authoritative; do not hardcode a version in this packet).

## Scope
- Impacted modules: tests.
- Owned files:
  - `tests/run_tests.py`
  - `modules/tests.json`
  - `modules/module-manifest.json`
- Files not to touch:
  - `casino/games/blackjack/*` unless a failing test proves a gameplay bug.
  - `web/games/blackjack.js`
  - `contracts/*`
  - runtime `data/*`

## Compatibility
- API contract impact: None expected.
- Gameplay impact: None expected.
- Ledger impact: None.
- Bot/autoplay impact: None.
- Data migration impact: None.

## Required Reading
- `AGENTS.md`
- `modules/module-manifest.json`
- `docs/requirements/requirements.json`
- `tests/run_tests.py`
- `casino/games/blackjack/`

## Validation
- Required:
  - `python tests/run_tests.py --api`
  - `python scripts/validate_requirements.py`
  - `python scripts/validate_versions.py`
  - `python scripts/validate_contracts.py`
  - `python scripts/validate_module_boundaries.py`
  - `python scripts/check_comment_density.py`
- Browser validation:
  - `python tests/run_tests.py --browser`, currently blocked in worker shells until Python Playwright is installed.

## Handback
- Summarize exact requirements covered.
- Report whether validations passed or were blocked.
- Restore any generated runtime `data/*` changes before final handback.
