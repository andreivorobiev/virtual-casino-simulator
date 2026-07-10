# Codex Task Packet: Play Token Terminology

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/37
- Branch: codex/token-model-terminology
- PR title: Replace dollar wording with play token terminology
- Coordinator chat: Casino Simulator - Coordinator
- Worker chat: Casino Simulator - Worker - Token Terminology

## Goal

- Goal: Replace user-facing money and dollar language with play-token terminology and token mark `◈`.
- Non-goals: Do not change payout math, ledger mutation semantics, game rules, or API compatibility unless explicitly scoped.
- User-visible behavior expected: The app reads as a toy simulator using play tokens, not as a real-money gambling site.

## Requirements

- Requirement IDs added: TOKEN IDs from #35, or add them if #35 has not landed.
- Requirement IDs changed: Supersede fake-money display wording requirements where needed.
- Requirement IDs validated: UX, I18N, DOC, TEST, and token terminology requirements.

## Durable Requirement/Contract References

- Implement TOKEN-001 through TOKEN-004, LIC-002, LIC-003, TERMS-004, API-001, API-002, and TEST-039 where visible token wording is covered by tests.
- New v2 APIs may use token terminology per `contracts/openapi/auth.v2.yaml`; do not rename frozen v1 wire fields.
- Superseded fake-money wording is recorded on CORE-004, LEDGER-001, SLOT-026, KENO-021, and BINGO-024.

## Scope

- Impacted modules: application, docs, tests, tooling, all frontend game modules for visible strings only.
- Owned files: `web/index.html`, `web/app.js`, `web/styles.css`, `web/core/ui.js`, `web/core/i18n.js`, `web/i18n/**`, `web/games/*.js` for visible strings only, `tests/run_tests.py` for assertions, terminology validator files under `scripts/` if required.
- Files not to touch: `casino/games/**/engine.py`, settlement math, ledger balance mutation code, MySQL/auth implementation files.
- Allowed adjacent files: Relevant docs or generated resources that display token terminology.

## Compatibility

- API contract impact: No breaking v1 field rename. New v2 APIs may use token language once #35/#39 define it.
- Gameplay impact: No rule changes.
- Ledger impact: Display terminology only; ledger still accounts for numeric token balances.
- Bot/autoplay impact: Display terminology only.
- Data migration impact: None.

## Required reading

- `AGENTS.md`
- `web/AGENTS.md`
- `modules/application.json`
- `modules/tests.json`
- `web/i18n/manifest.json`
- Existing browser tests in `tests/run_tests.py`

## Validation

- Required tests: Browser tests for token balance, add tokens, and representative game displays.
- Required scripts: Full relevant `AGENTS.md` validation subset plus terminology validator if added.
- Browser evidence: Screenshot or test evidence showing `◈` token balance.
- Manual checks: Search active source/docs/resources for user-facing `$`, `dollars`, `USD`, and unapproved fake-money wording.

## Handback

- Expected PR summary: Files converted, validator behavior, UI screenshots/evidence, exceptions list if any.
- Evidence to include: Search results and browser test output.
- Open questions to report: Any term that cannot be safely changed without API compatibility work.
- Stop conditions: Stop before changing gameplay math or API wire fields.
