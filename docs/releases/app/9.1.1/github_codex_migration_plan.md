# GitHub and Codex migration plan

This repository is prepared to become the GitHub source of truth for the Virtual Casino Simulator.

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

Use `FIRST_PROMPT_FOR_CODEX.md`. The first task is repository bootstrap validation only.
