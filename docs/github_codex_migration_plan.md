# GitHub and Codex migration plan

**Historical.** Records the plan as written for the 9.1.1 bootstrap; the migration is complete and the steps below are already done. Retained for provenance and archived at `docs/releases/app/9.1.1/github_codex_migration_plan.md`. For the current operating model see `AGENTS.md` and `CODEX_START_HERE.md`.

This repository was prepared to become the GitHub source of truth for the Virtual Casino Simulator.

## Operating model

1. Push this payload into a GitHub repository named `virtual-casino-simulator`.
2. Enable branch protection on `main`.
3. Require pull requests, approving reviews, CODEOWNERS review, and status checks.
4. Connect Codex to the GitHub repository.
5. Use one issue and one Codex conversation per module change.
6. Require module version bumps, requirement IDs, contracts, tests, and release notes in each PR.

## Bootstrap release

- Application version: `9.1.1`
- Source baseline: `9.1.0`
- Scope: repository governance, API contracts, manifests, tests, comments, workflows, and Codex instructions.
- Gameplay behavior: no intentional changes.

## First Codex task

The bootstrap task was `FIRST_PROMPT_FOR_CODEX.md`, scoped to repository bootstrap validation only. It has been completed; a new agent starts from `CODEX_START_HERE.md` instead.
