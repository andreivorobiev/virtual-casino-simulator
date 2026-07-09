# Codex Task Packet: Integration Validation

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/43
- Branch: codex/auth-db-validation
- PR title: Add integration validation for auth, MySQL, tokens, and private sessions
- Coordinator chat: Casino Simulator - Coordinator
- Worker chat: Casino Simulator - Worker - Auth DB Validation

## Goal

- Goal: Add and run integration validation for the complete auth, multi-user, MySQL, licensing, and token-model implementation.
- Non-goals: Do not implement feature behavior except test-only helpers approved by the coordinator.
- User-visible behavior expected: Final evidence shows the complete implementation works from copied deployment environments.

## Requirements

- Requirement IDs added: TEST IDs for auth, MySQL, token terminology, private sessions, copied deployment validation.
- Requirement IDs changed: None unless validation policy needs superseding.
- Requirement IDs validated: All new epic IDs plus existing game, ledger, bot, autoplay, admin, API, UX, I18N, and long-suite IDs.

## Scope

- Impacted modules: tests, tooling, docs, CI.
- Owned files: `tests/run_tests.py`, `tests/long_suites.py`, new `tests/**` helpers, CI workflow files if needed, `docs/long_test_suites.md`, `scripts/*` validation helpers, relevant module JSON files.
- Files not to touch: Runtime implementation except test-only hooks approved by coordinator.
- Allowed adjacent files: Requirements docs only for test IDs.

## Compatibility

- API contract impact: None.
- Gameplay impact: None.
- Ledger impact: Validation only.
- Bot/autoplay impact: Validation only.
- Data migration impact: Validation only.

## Required reading

- `AGENTS.md`
- `tests/AGENTS.md`
- `modules/tests.json`, `modules/tooling.json`, `modules/docs.json`
- `tests/run_tests.py`, `tests/long_suites.py`
- `docs/long_test_suites.md`

## Validation

- Required tests: Full `AGENTS.md` validation set, auth/API/browser tests, MySQL path tests, terminology tests, copied-deployment long suite 100.
- Required scripts: All repo validation commands.
- Browser evidence: Auth/login/terms/token/private-session screenshots or Playwright artifacts when UI changes are included.
- Manual checks: Coordinator asks user before long suite 300 or 500.

## Handback

- Expected PR summary: Test coverage added, copied deployment results, any MySQL environment notes, unresolved failures.
- Evidence to include: Report paths and pass/fail summary.
- Open questions to report: Any flaky scenario or environment dependency.
- Stop conditions: Stop before mutating production behavior to make tests pass without coordinator approval.
