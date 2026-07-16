# Codex start here

This repository is the current GitHub source for the Virtual Casino Simulator. It includes work completed after the original repository-bootstrap payload.

## Mandatory first steps for Codex

1. Read `AGENTS.md` before modifying any file.
2. Read the assigned issue or task packet and preserve its boundaries.
3. Read `modules/module-manifest.json` and the manifest for every module you will touch.
4. Read the relevant `contracts/openapi/*.v1.yaml` files before changing API behavior.
5. Run the task packet's focused checks while developing and its required validation set before handoff.
6. Treat GitHub issues, requirements, manifests, contracts, pull requests, and release artifacts as durable sources of truth rather than chat history.
7. Work through issues and pull requests. Do not push directly to `main`.

## Version sources

- Packaged application release: `9.2.0`
- Historical source baseline: `9.1.0`
- Canonical aggregate source: `modules/module-manifest.json`
- Independent module revisions: the manifest's `modules` object and matching `modules/*.json` files

The top-level manifest `application` value is the formal packaged application release used by runtime, API, browser, and Admin surfaces. Do not bump it for ordinary source work. Each `modules.<name>` value is an independent module revision and must be bumped when that module's owned source changes. `modules.application` is therefore allowed to be newer than the packaged application release. A release workflow must deliberately update every packaged-release surface and produce the corresponding artifact.

## Critical rules

- Every change must reference requirement IDs.
- Every changed module must bump its own module revision.
- Every API change must update OpenAPI contracts, compatibility manifests, tests, docs, and release notes.
- Every money movement must go through the ledger service.
- Game modules must not import other game modules.
- Game modules must not own bot strategy logic.
- Bots are controllers for player accounts and must use public game actions.
- Python and JavaScript code must use dense line-level comments for every meaningful executable line.
