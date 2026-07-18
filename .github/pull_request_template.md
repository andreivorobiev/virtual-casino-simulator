# Pull request

## Summary

## Authorship and merge handback

- PR author:
- Authoring system (`Claude`, `Codex`, `human`, or approved other):
- Merge executor: Codex
- Base branch and commit:
- Exact head commit:
- Required owner approval or external gate:

- [ ] The author has not merged or enabled auto-merge.
- [ ] If Claude-authored, the PR is handed back to Codex for independent review and merge.

## Coordination

- Issue:
- Task packet:
- Branch:
- Parallel workers or stacked PRs:
- Dependency PRs and exact heads:
- Owned files:
- No-touch files honored:

## Impacted modules

- Packaged application release impact:
- Independent modules and version changes:
- Module manifests read:
- Cross-module rationale or `None`:
- Modules explicitly not affected:

## Requirement IDs

Added:
Changed:
Validated:

## API contract impact

- [ ] No API contract changes
- [ ] Additive v1 change
- [ ] Breaking change requiring v2 or compatibility shim
- [ ] Contract files updated
- [ ] Compatibility matrix updated

## Gameplay impact

- [ ] No gameplay behavior changed
- [ ] Gameplay behavior changed as required by listed requirement IDs
- [ ] Browser-visible behavior changed and browser evidence is included

## Data, security, release, and deployment impact

- Storage or migration impact:
- Authentication, privacy, or security impact:
- Ledger, retry, or idempotency impact:
- Release artifact or provenance impact:
- Deployment, provider, DNS, mail, public-exposure, or spend impact:
- Required owner approval or external gate:

## Visual governance

- [ ] No browser-visible behavior changed
- [ ] Read `docs/visual_design_standard.md`
- [ ] Visual matrix surface/state IDs are listed below
- [ ] Required locales and viewports from `tests/visual/visual_matrix.json` were checked
- [ ] Evidence is classified as `after_pass`; known-failing screenshots are not presented as acceptance evidence

Visual matrix rows:
Evidence classification, locale, viewport, and paths:
Intentional exceptions and follow-up issue:

## Version bumps

## Tests run

- [ ] python scripts/bootstrap_repo.py
- [ ] python verify_rules.py
- [ ] python tests/run_tests.py --api
- [ ] python tests/run_tests.py --browser
- [ ] python scripts/validate_contracts.py
- [ ] python scripts/validate_module_boundaries.py
- [ ] python scripts/validate_game_catalog.py
- [ ] python scripts/validate_requirements.py
- [ ] python scripts/validate_versions.py
- [ ] python scripts/generate_docs.py --check
- [ ] python scripts/check_comment_density.py

## Screenshots or evidence

## Risks, decisions, and follow-up issues

## Codex merge review

- [ ] Exact head, base, and dependency order verified
- [ ] Required checks and acceptance evidence pass for the exact head
- [ ] Requirements, contracts, module versions, generated files, and docs align
- [ ] Required owner approvals and protected-branch rules are satisfied
- [ ] No unresolved requested changes or material decisions remain
- [ ] Merge method and expected-head protection are selected

Merge recommendation and rationale:

## Codex post-merge verification

- Merged commit and method:
- Required checks on merged state:
- Issue disposition and next dependency:
- Residual risk, rollback, or follow-up:
