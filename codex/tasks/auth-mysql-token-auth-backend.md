# Codex Task Packet: Auth Backend and Current User APIs

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/39
- Branch: codex/auth-session-backend
- PR title: Add login sessions, bootstrap admin, and current-user APIs
- Coordinator chat: Casino Simulator - Coordinator
- Worker chat: Casino Simulator - Worker - Auth Backend

## Goal

- Goal: Require authenticated sessions for app/API access and add backend auth/current-user APIs.
- Non-goals: Do not build the full frontend login UI, Admin user table UI, or per-game private session conversion.
- User-visible behavior expected: Unauthenticated protected requests are rejected; authenticated sessions expose current user/player data.

## Requirements

- Requirement IDs added: AUTH, SESSION, USER, TERMS API IDs from #35, or add them if #35 has not landed.
- Requirement IDs changed: Supersede unauthenticated Admin/local API assumptions where needed.
- Requirement IDs validated: CORE, ADMIN, PLAYERS, LEDGER, API, AUTH.

## Scope

- Impacted modules: core, players, admin, contracts, tests.
- Owned files: `casino/app.py`, `casino/router.py`, `casino/errors.py`, `casino/config.py`, new `casino/core/auth*`, `casino/core/players.py` for user/player binding, auth/current-user contracts if not already added, auth API tests, relevant module JSON files.
- Files not to touch: `web/**` beyond API test fixtures, game engines, visual token terminology work.
- Allowed adjacent files: `casino/admin.py` only for minimal protected-route integration if required.

## Compatibility

- API contract impact: Add `/api/v2/auth/*` and `/api/v2/me*`; protect APIs while preserving standard response envelopes.
- Gameplay impact: None.
- Ledger impact: Current user binds to player, but token mutation remains in ledger.
- Bot/autoplay impact: Auth guards only unless explicitly scoped.
- Data migration impact: Session/user data through configured storage provider.

## Required reading

- `AGENTS.md`
- `casino/core/AGENTS.md`
- `contracts/AGENTS.md`
- `modules/core.json`, `modules/players.json`, `modules/admin.json`, `modules/contracts.json`
- `casino/app.py`, `casino/router.py`, `casino/core/players.py`
- Auth/current-user contracts from #35

## Validation

- Required tests: Login, logout, session lookup, current user, unauthorized access, bootstrap admin, inactive user, terms status.
- Required scripts: API tests, contract validation, module boundary, requirements, versions, comment density.
- Browser evidence: Not required.
- Manual checks: Cookies/session headers do not break static asset serving.

## Handback

- Expected PR summary: Auth design, session behavior, bootstrap env vars, API contract impact, tests.
- Evidence to include: API test output and contract validation.
- Open questions to report: Password policy or session TTL ambiguity.
- Stop conditions: Stop before adding frontend UI or changing game APIs beyond auth protection.
