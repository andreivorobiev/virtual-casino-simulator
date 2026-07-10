# Codex Task Packet: Licensing and Toy-Simulator Terms

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/36
- Branch: codex/auth-db-licensing-terms
- PR title: Add Apache license and private beta toy simulator terms
- Coordinator chat: Casino Simulator - Coordinator
- Worker chat: Casino Simulator - Worker - Licensing Terms

## Goal

- Goal: Add Apache-2.0 source-code licensing and end-user private beta toy-simulator terms/privacy docs.
- Non-goals: Do not implement login, terms acceptance runtime, storage, or UI copy changes outside legal/docs references.
- User-visible behavior expected: Repo clearly states code license and running-app terms. Terms clearly state this is a toy simulator, not a gambling site, not real-money play, and tokens have no cash value.

## Requirements

- Requirement IDs added: Use LIC and TERMS IDs from #35, or add them if #35 has not landed.
- Requirement IDs changed: Supersede any docs wording that implies real-money or gambling-site behavior.
- Requirement IDs validated: DOC-016 and relevant docs governance IDs.

## Durable Requirement/Contract References

- Implement LIC-001 through LIC-003, TERMS-004, TOKEN-001, and DOC-016.
- Superseded no-real-money wording is recorded on CORE-004, SLOT-026, KENO-021, and BINGO-024; preserve the policy while using toy-simulator/play-token language.
- No API contract changes are expected for this packet.

## Scope

- Impacted modules: docs, application metadata.
- Owned files: `LICENSE`, `NOTICE` if needed, `docs/legal/*`, `README.md`, `CONTRIBUTING.md`, `pyproject.toml`, `modules/docs.json`, `modules/module-manifest.json`.
- Files not to touch: `casino/**`, `web/**`, `tests/**`, game modules, contracts except requirement references if coordinated.
- Allowed adjacent files: Release/docs index files if needed.

## Compatibility

- API contract impact: None.
- Gameplay impact: None.
- Ledger impact: None.
- Bot/autoplay impact: None.
- Data migration impact: None.

## Required reading

- `AGENTS.md`
- `docs/AGENTS.md`
- `modules/docs.json`
- `docs/requirements/requirements.json`
- Apache-2.0 license text from the official Apache/OSI/SPDX source used by the repo.

## Validation

- Required tests: None.
- Required scripts: `python scripts/validate_requirements.py`, `python scripts/validate_versions.py`, `python scripts/check_comment_density.py`.
- Browser evidence: Not required.
- Manual checks: Legal docs must avoid presenting the app as a gambling product.

## Handback

- Expected PR summary: License chosen, legal docs added, terms/privacy scope, docs version bump.
- Evidence to include: Validator outputs.
- Open questions to report: Any copyright holder ambiguity.
- Stop conditions: Stop if custom legal language beyond the approved private beta toy-simulator scope is requested.
