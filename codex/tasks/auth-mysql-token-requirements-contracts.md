# Codex Task Packet: Auth/MySQL Requirements and Contracts

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/35
- Branch: codex/auth-db-requirements-contracts
- PR title: Add auth, MySQL, token, and licensing requirements/contracts
- Coordinator chat: Casino Simulator - Coordinator
- Worker chat: Casino Simulator - Worker - Auth DB Requirements

## Goal

- Goal: Add the durable requirements, API contract shape, compatibility metadata, and task packet alignment for the auth, multi-user, MySQL, licensing, and token-model foundation.
- Non-goals: Do not implement runtime auth, storage, frontend login, Admin UI, or game-state behavior.
- User-visible behavior expected: None directly; this creates the governance and contract base for implementation.

## Requirements

- Requirement IDs added: AUTH, USER, STORAGE, MYSQL, SESSION, TERMS, LIC, TOKEN, and TEST IDs as needed.
- Requirement IDs changed: Supersede conflicting unauthenticated/local-only and fake-money wording requirements without deleting them.
- Requirement IDs validated: DOC-016, TOOL-001, relevant CORE/API/ADMIN/TEST governance IDs.

## Durable Requirement/Contract References

- This packet owns creation of AUTH-001 through AUTH-005, SESSION-001 through SESSION-004, USER-001 through USER-005, STORAGE-001 through STORAGE-004, MYSQL-001 through MYSQL-004, TERMS-001 through TERMS-004, LIC-001 through LIC-003, TOKEN-001 through TOKEN-004, API-001 through API-002, and TEST-037 through TEST-040.
- This packet owns `contracts/openapi/auth.v2.yaml`, `contracts/openapi/admin-users.v2.yaml`, and `contracts/compatibility/auth-mysql-token-foundation.json`.
- Runtime implementation remains out of scope.

## Scope

- Impacted modules: docs, contracts, tooling, application.
- Owned files: `docs/requirements/requirements.json`, `docs/requirements/requirements.md`, `docs/requirements/requirements_generated.md`, `contracts/openapi/*.v2.yaml`, `contracts/compatibility/*`, `modules/docs.json`, `modules/contracts.json`, `modules/tooling.json`, `modules/module-manifest.json`, `codex/tasks/auth-mysql-token-*.md`.
- Files not to touch: `casino/**`, `web/**`, `tests/**` except validator metadata if absolutely required.
- Allowed adjacent files: `scripts/validate_requirements.py`, `scripts/validate_contracts.py` only if new requirement or contract validation support is required.

## Compatibility

- API contract impact: Additive `/api/v2` contracts for auth/current-user/admin-user flows; preserve `/api/v1` compatibility notes.
- Gameplay impact: None.
- Ledger impact: Requirements only; no ledger code changes.
- Bot/autoplay impact: Requirements only.
- Data migration impact: Requirements and compatibility notes only.

## Required reading

- `AGENTS.md`
- `docs/AGENTS.md`
- `contracts/AGENTS.md`
- `modules/module-manifest.json`
- `modules/docs.json`, `modules/contracts.json`, `modules/tooling.json`
- Existing `contracts/openapi/*.v1.yaml`
- `docs/codex_parallel_workflow.md`

## Validation

- Required tests: None beyond validators.
- Required scripts: `python scripts/validate_requirements.py`, `python scripts/validate_versions.py`, `python scripts/validate_contracts.py`, `python scripts/check_comment_density.py`.
- Browser evidence: Not required.
- Manual checks: Confirm every child issue has a durable requirement/contract reference.

## Handback

- Expected PR summary: Requirement IDs added/changed, contract files added, compatibility notes, task packet updates.
- Evidence to include: Validator outputs.
- Open questions to report: Any requirement ID naming collision or API contract ambiguity.
- Stop conditions: Stop if runtime code changes become necessary.
