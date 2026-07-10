# Codex Task Packet: Storage Provider and MySQL Schema

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/38
- Branch: codex/mysql-storage-provider
- PR title: Add JSON storage provider abstraction and MySQL schema
- Coordinator chat: Casino Simulator - Coordinator
- Worker chat: Casino Simulator - Worker - MySQL Storage

## Goal

- Goal: Introduce a storage provider abstraction with JSON fallback and MySQL schema support for multi-user persistence.
- Non-goals: Do not implement login UI, Admin user UI, or game API current-user routing.
- User-visible behavior expected: Default local JSON behavior remains available; configured MySQL can start with fresh seed/bootstrap data.

## Requirements

- Requirement IDs added: STORAGE and MYSQL IDs from #35, or add them if #35 has not landed.
- Requirement IDs changed: Supersede JSON-only persistence assumptions where needed.
- Requirement IDs validated: CORE, LEDGER, PLAYER, STORAGE, MYSQL, TEST.

## Durable Requirement/Contract References

- Implement STORAGE-001 through STORAGE-004, MYSQL-001 through MYSQL-004, USER-001, USER-003, SESSION-001, SESSION-004, TOKEN-004, and TEST-038.
- Preserve API-001 and API-002 envelope expectations if storage errors surface through API responses.
- Do not add new contract files unless storage-specific envelope behavior cannot be represented by the existing v1 or v2 contracts.

## Scope

- Impacted modules: core, ledger, players, tooling, tests.
- Owned files: `casino/core/storage*`, `casino/core/players.py`, `casino/core/ledger.py`, `casino/core/state_store.py`, `casino/core/settings.py`, `casino/core/history.py`, `casino/config.py`, MySQL schema/migration docs or scripts, runtime dependency metadata, storage-focused tests, relevant module JSON files.
- Files not to touch: `web/**`, `casino/games/**/engine.py`, `casino/admin.py` unless consuming a public storage service is coordinated.
- Allowed adjacent files: `tests/run_tests.py`, `tests/long_suites.py` only for storage parity tests.

## Compatibility

- API contract impact: None unless storage errors require documented envelope behavior.
- Gameplay impact: None.
- Ledger impact: Ledger must remain the single mutation point and become atomic under MySQL.
- Bot/autoplay impact: Storage compatibility only.
- Data migration impact: MySQL starts fresh; no import of current local data required.

## Required reading

- `AGENTS.md`
- `casino/core/AGENTS.md`
- `modules/core.json`, `modules/ledger.json`, `modules/players.json`, `modules/tooling.json`, `modules/tests.json`
- `casino/core/players.py`, `casino/core/ledger.py`, `casino/core/state_store.py`
- Relevant contracts for players and ledger

## Validation

- Required tests: JSON provider parity; MySQL schema/provider tests where environment allows.
- Required scripts: API tests plus contract/module/requirement/version/comment validations.
- Browser evidence: Not required unless UI-visible storage behavior changes.
- Manual checks: Verify default run still works without MySQL configuration.

## Handback

- Expected PR summary: Provider interface, JSON fallback behavior, MySQL schema, dependency/config changes, tests.
- Evidence to include: Test outputs and schema notes.
- Open questions to report: MySQL service availability or dependency install blockers.
- Stop conditions: Stop before changing game rules or frontend routing.
