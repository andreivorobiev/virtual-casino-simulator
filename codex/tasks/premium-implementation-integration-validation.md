# Premium Redesign Integration and Visual Validation

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/20
- Parent epic: https://github.com/andreivorobiev/virtual-casino-simulator/issues/11
- Worker chat title: Casino Simulator - Worker - Premium Integration Validation
- Base branch: wait for implementation child PRs unless the coordinator explicitly provides a combined branch
- Implementation branch: `codex/premium-impl-integration-validation`
- Coordinator chat: Casino Simulator - Coordinator

## Goal

Run the final integration pass for the premium redesign: resolve cross-worker visual issues, verify responsive behavior, compare real app screens against approved prerenders, and prepare final production PR evidence.

## Non-Goals

- Do not introduce new gameplay behavior.
- Do not make broad redesign changes outside resolving approved implementation gaps.
- Do not edit module APIs or contracts unless a previous approved child PR left an explicit follow-up.

## Requirements

- Validate: `UX-007`, `UX-008`, `UX-009`, `I18N-001`, `I18N-002`, `I18N-003`, all touched game UI IDs, touched Admin IDs, and module version alignment.

## Owned Files

- `tests/run_tests.py` for final browser coverage
- `docs/release-notes/**` only if a formal release note is requested
- Minimal integration edits in files already changed by child PRs, only after coordinator approval

## Files Not To Touch

- Gameplay engines
- Ledger internals
- `/api/v1` contracts except approved follow-up fixes

## Required Reading

- `AGENTS.md`
- `docs/visual_design_standard.md` and `tests/visual/visual_matrix.json`
- `docs/codex_parallel_workflow.md`
- `modules/module-manifest.json`
- all child task packets for issues #12 through #19
- `codex/tasks/artifacts/premium-redesign-prerenders/README.md`

## Validation

- Run the full validation ladder if environment permits:
  - `python scripts/bootstrap_repo.py`
  - `python verify_rules.py`
  - `python tests/run_tests.py --api`
  - `python tests/run_tests.py --browser`
  - `python scripts/validate_contracts.py`
  - `python scripts/validate_module_boundaries.py`
  - `python scripts/validate_requirements.py`
  - `python scripts/validate_versions.py`
  - `python scripts/check_comment_density.py`
- Capture browser screenshots for lobby, admin, and all six games across desktop and at least one narrow viewport.
- Compare screenshots against approved PR #10 prerenders and document intentional deviations.

## Handback

Report final validation matrix, screenshot evidence paths, residual risks, module versions, and any blockers before merge.
