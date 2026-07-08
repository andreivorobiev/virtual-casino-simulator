# Codex start here

This repository is the GitHub-ready source payload for the Virtual Casino Simulator.

## Mandatory first steps for Codex

1. Read `AGENTS.md` before modifying any file.
2. Read `FIRST_PROMPT_FOR_CODEX.md` before starting the first task.
3. Read `modules/module-manifest.json` and the manifest for the module you will touch.
4. Read the relevant `contracts/openapi/*.v1.yaml` files before changing API behavior.
5. Run `python scripts/bootstrap_repo.py` before proposing a first pull request.
6. Do not change gameplay behavior during the bootstrap task unless a validation script requires it.
7. Treat GitHub as the source of truth after this payload is pushed to a repository.
8. Work through issues and pull requests. Do not push directly to `main`.

## Baseline

- Application bootstrap version: `9.1.1`
- Source baseline: `9.1.0`
- Purpose: repository bootstrap, Codex migration, governance, contracts, module manifests, CI, and commenting policy.

## Critical rules

- Every change must reference requirement IDs.
- Every changed module must bump its own module version.
- Every API change must update OpenAPI contracts, compatibility manifests, tests, docs, and release notes.
- Every money movement must go through the ledger service.
- Game modules must not import other game modules.
- Game modules must not own bot strategy logic.
- Bots are controllers for player accounts and must use public game actions.
- Python and JavaScript code must use dense line-level comments for every meaningful executable line.
