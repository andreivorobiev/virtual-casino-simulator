# Premium Shared Shell, Lobby, and Visual Foundation Implementation

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/12
- Parent epic: https://github.com/andreivorobiev/virtual-casino-simulator/issues/11
- Worker chat title: Casino Simulator - Worker - Premium Foundation Implementation
- Base branch: `codex/premium-redesign-prerenders`
- Implementation branch: `codex/premium-impl-foundation`
- Coordinator chat: Casino Simulator - Coordinator

## Goal

Implement the approved premium shared visual foundation in the production app: shell, top navigation, wallet, lobby game cards, status rail, responsive behavior, asset placement, and reusable UI helpers/classes needed by later game workers.

## Non-Goals

- Do not redesign individual game screens beyond minimal shell integration.
- Do not change gameplay, ledger, bots, autoplay behavior, or `/api/v1` payloads.
- Do not implement Admin Language/Locale functionality beyond leaving a clean hook for issue #13.

## Requirements

- Add or validate: `UX-007`, `UX-008`, `UX-009`.
- Preserve: `UX-001`, `UX-002`, `UX-003`, `UX-004`, `UX-005`, `UX-006`, `CORE-005`, `CORE-006`, `CORE-015`, `LEDGER-025`.

## Owned Files

- `web/index.html`
- `web/app.js`
- `web/styles.css`
- `web/core/ui.js` if shared helpers are needed
- `web/assets/**` or another approved static asset location
- `tests/run_tests.py` only for shell/lobby browser coverage
- `docs/requirements/requirements.json`
- `docs/requirements/requirements_generated.md`
- `modules/application.json`
- `modules/docs.json`
- `modules/tests.json` if tests change
- `modules/module-manifest.json`

## Files Not To Touch

- `web/games/*.js` except minimal, coordinator-approved class/hook integration
- `casino/games/**`
- `casino/core/ledger.py`
- `contracts/**`
- `web/admin.html`
- `web/admin.js`

## Required Reading

- `AGENTS.md`
- `docs/visual_design_standard.md` and `tests/visual/visual_matrix.json`
- `web/AGENTS.md`
- `modules/module-manifest.json`
- `modules/application.json`
- `modules/docs.json`
- `docs/requirements/requirements.json`
- `codex/tasks/premium-implementation-epic.md`
- `codex/tasks/premium-implementation-foundation.md`
- `codex/tasks/artifacts/premium-redesign-prerenders/README.md`
- `codex/tasks/artifacts/premium-redesign-prerenders/shell-lobby-admin/README.md`

## Design Source

- `codex/tasks/artifacts/premium-redesign-prerenders/reference/target-lobby.png`
- `codex/tasks/artifacts/premium-redesign-prerenders/shell-lobby-admin/premium-lobby.png`
- `codex/tasks/artifacts/premium-redesign-prerenders/shell-lobby-admin/shared-shell-wallet.png`
- `codex/tasks/artifacts/premium-redesign-prerenders/shell-lobby-admin/responsive-narrow.png`

## Validation

- Run relevant browser tests for lobby/shell.
- Run `python scripts/generate_docs.py` if requirements or module versions affect generated docs.
- Run `python scripts/validate_requirements.py`.
- Run `python scripts/validate_versions.py`.
- Run `python scripts/check_comment_density.py`.
- Run `python tests/run_tests.py --browser` if environment permits.

## Handback

Report changed files, requirement IDs, module version bumps, screenshots/browser evidence, validation results, and any reserved class/helper contract game workers should use.
