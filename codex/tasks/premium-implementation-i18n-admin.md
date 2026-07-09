# Premium I18n and Admin Language/Locale Implementation

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/13
- Parent epic: https://github.com/andreivorobiev/virtual-casino-simulator/issues/11
- Worker chat title: Casino Simulator - Worker - I18n Admin Implementation
- Base branch: `codex/premium-redesign-prerenders`
- Implementation branch: `codex/premium-impl-i18n-admin`
- Coordinator chat: Casino Simulator - Coordinator

## Goal

Implement a frontend i18n runtime, English and Russian resource files, shell/admin string extraction foundation, language switching that does not reset game state, and an Admin Language/Locale section.

## Non-Goals

- Do not translate every game deeply unless explicitly scoped after the runtime lands.
- Do not change gameplay, ledger behavior, or game engines.
- Do not introduce a breaking Admin API or `/api/v1` compatibility change.

## Requirements

- Add or validate: `I18N-001`, `I18N-002`, `I18N-003`.
- Preserve: `ADMIN-013` through `ADMIN-022`, `UX-001` through `UX-009`.

## Owned Files

- `web/core/i18n.js`
- `web/i18n/**`
- `web/admin.html`
- `web/admin.js`
- `casino/admin.py` only if persistence endpoints are implemented
- `contracts/openapi/admin.v1.yaml` only if persistence endpoints are implemented
- `tests/run_tests.py` for Admin/browser/API coverage
- `docs/requirements/requirements.json`
- `docs/requirements/requirements_generated.md`
- `modules/admin.json`
- `modules/application.json`
- `modules/tests.json` if tests change
- `modules/contracts.json` if contracts change
- `modules/module-manifest.json`

## Files Not To Touch

- `web/games/*.js` except tiny localization hooks agreed by the coordinator
- `casino/games/**`
- `casino/core/ledger.py`
- Shared shell/lobby files owned by issue #12 unless coordination is explicit

## Required Reading

- `AGENTS.md`
- `web/AGENTS.md`
- `modules/module-manifest.json`
- `modules/admin.json`
- `contracts/openapi/admin.v1.yaml`
- `docs/requirements/requirements.json`
- `codex/tasks/premium-implementation-epic.md`
- `codex/tasks/premium-implementation-i18n-admin.md`
- `codex/tasks/artifacts/premium-redesign-prerenders/i18n-plan/README.md`
- `codex/tasks/artifacts/premium-redesign-prerenders/i18n-plan/resource-architecture.md`
- `codex/tasks/artifacts/premium-redesign-prerenders/i18n-plan/implementation-test-plan.md`

## Design Source

- `codex/tasks/artifacts/premium-redesign-prerenders/shell-lobby-admin/admin-language-locale.png`
- `codex/tasks/artifacts/premium-redesign-prerenders/i18n-plan/samples/en-US.json`
- `codex/tasks/artifacts/premium-redesign-prerenders/i18n-plan/samples/ru-RU.json`

## Validation

- Validate JSON resource parity and placeholder parity.
- Run Admin API/browser tests when touched.
- Run `python scripts/generate_docs.py` if requirements or module versions affect generated docs.
- Run `python scripts/validate_contracts.py` if Admin contracts change.
- Run `python scripts/validate_requirements.py`.
- Run `python scripts/validate_versions.py`.
- Run `python scripts/check_comment_density.py`.

## Handback

Report resource layout, locale persistence decision, state-preservation behavior, changed files, requirement IDs, module version bumps, validation results, and open questions for game-string extraction.
