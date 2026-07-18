# Agent task packet template

Use this packet to start a human, Claude, Codex, or other approved worker task.
The legacy path is retained for compatibility. Fill every section or write
`None`.

## Task

- Issue:
- Priority:
- Assigned author:
- Authoring system (`Claude`, `Codex`, `human`, or approved other):
- Coordinator: Codex
- Merge executor: Codex
- Branch:
- Base branch and commit:
- Dependency PRs and exact heads:
- PR title:
- Required owner approval or external gate:
- Coordinator task:
- Worker task:

## Goal

- Goal:
- Non-goals:
- User-visible behavior expected:

## Requirements

- Requirement IDs added:
- Requirement IDs changed:
- Requirement IDs validated:

## Scope

- Impacted modules:
- Packaged application release impact:
- Independent module revision bumps planned:
- Owned files:
- Files not to touch:
- Allowed adjacent files:

## Compatibility

- API contract impact:
- Gameplay impact:
- Ledger impact:
- Bot/autoplay impact:
- Data migration impact:
- Security/privacy impact:
- Release/provenance impact:
- Deployment/provider impact:

## Required reading

- `CODEX_START_HERE.md`
- `AGENTS.md`
- `CLAUDE.md` when the authoring system is Claude
- `ENGINEERING_PRACTICES.md`
- `docs/engineering_skills.md`
- `docs/claude_codex_work_division.md`
- `docs/visual_design_standard.md` for browser-visible tasks
- `tests/visual/visual_matrix.json` for browser-visible tasks
- Relevant nested `AGENTS.md`:
- Relevant module manifests:
- Relevant contracts:
- Relevant docs:

## Validation

- Required tests:
- Required scripts:
- Visual matrix surface/state IDs:
- Required locales/viewports:
- Browser evidence:
- Evidence classification (`before_failure` or `after_pass`):
- Manual checks:
- Disposable state and cleanup:

## Handback

- Expected PR summary:
- Final packaged application release impact:
- Final independent module revision bumps:
- Evidence to include:
- PR URL and state:
- Exact base and head SHA:
- Checks and review state:
- Open questions to report:
- Stop conditions:
- Merge recommendation format:

## Role boundary

- PR author may merge: No
- PR author may enable auto-merge: No
- Claude handback target: Codex review and merge when eligible
- Codex merge preconditions:
- Post-merge verification and issue disposition:
