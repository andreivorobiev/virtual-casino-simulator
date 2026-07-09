# Combined Redesign Implementation Base

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/24
- Parent epic: https://github.com/andreivorobiev/virtual-casino-simulator/issues/11
- Worker chat title: Casino Simulator - Worker - Combined Implementation Base
- Base branch: `codex/premium-redesign-prerenders`
- Source branches:
  - `codex/premium-impl-foundation` from PR #22
  - `codex/premium-impl-i18n-admin` from PR #23
- Output branch: `codex/premium-impl-base`
- Coordinator chat: Casino Simulator - Coordinator

## Goal

Create a clean combined implementation base branch that includes both the shared shell/lobby foundation and the i18n/Admin implementation so later game workers can start from one coherent branch.

## Background

PR #22 and PR #23 are both green individually, but a coordinator dry-run merge found expected conflicts in:

- `docs/requirements/requirements.json`
- `docs/requirements/requirements_generated.md`
- `modules/application.json`
- `modules/module-manifest.json`
- `modules/tests.json`
- `tests/run_tests.py`

Resolve these conflicts once, centrally, before game workers begin.

## Non-Goals

- Do not implement game-specific UI redesigns.
- Do not change gameplay, ledger behavior, bots, autoplay, or API contracts.
- Do not rewrite history or force-push PR #22 or PR #23.
- Do not rename the existing `premium-*` coordination artifacts during this active implementation phase.

## Requirements

- Preserve `UX-007`, `UX-008`, `UX-009`.
- Preserve `I18N-001`, `I18N-002`, `I18N-003`.
- Preserve Admin, shell/lobby, browser, and resource-parity coverage from PR #22 and PR #23.

## Owned Files

Only files necessary to resolve the branch combination:

- `docs/requirements/requirements.json`
- `docs/requirements/requirements_generated.md`
- `modules/*.json` only where version/module conflicts require resolution
- `tests/run_tests.py`
- Any files already introduced by PR #22 or PR #23 as part of the merged source branches

## Files Not To Touch

- `web/games/*.js`
- `casino/games/**`
- `casino/core/ledger.py`
- `contracts/**`
- Game engines, bot strategies, and autoplay control logic

## Required Reading

- `AGENTS.md`
- `docs/codex_parallel_workflow.md`
- `modules/module-manifest.json`
- `codex/tasks/premium-implementation-epic.md`
- `codex/tasks/premium-implementation-foundation.md`
- `codex/tasks/premium-implementation-i18n-admin.md`
- PR #22 handback and branch diff
- PR #23 handback and branch diff

## Implementation Guidance

1. Create `codex/premium-impl-base` from `codex/premium-redesign-prerenders`.
2. Merge or cherry-pick PR #22 and PR #23 source branches.
3. Resolve conflicts by keeping both sets of requirements, tests, resources, assets, shell changes, Admin changes, and module ownership metadata.
4. Regenerate `docs/requirements/requirements_generated.md` from `requirements.json`.
5. Make module versions internally consistent after combining both branches.
6. Keep test IDs, API enum values, and gameplay state untouched.

## Validation

Run at minimum:

- `python scripts/bootstrap_repo.py`
- `python tests/run_tests.py --browser`
- `python scripts/validate_requirements.py`
- `python scripts/validate_versions.py`
- `python scripts/check_comment_density.py`

Use bundled Python if `python` is unavailable on PATH.

## Handback

Report:

- Output branch and draft PR URL if opened.
- Combined version/module state.
- Resolved conflict files.
- Validation results.
- Game-worker base instructions, including shell helper/class contract and available i18n resource domains.
