# Codex Task Packet: Admin User Management

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/41
- Branch: codex/admin-user-management
- PR title: Add Admin user management and terms status controls
- Coordinator chat: Casino Simulator - Coordinator
- Worker chat: Casino Simulator - Worker - Admin Users

## Goal

- Goal: Extend Admin with user creation, deactivate/reactivate, password reset, token balance/state inspection, terms acceptance status, and preserved locale controls.
- Non-goals: Do not implement public self-signup or external identity providers.
- User-visible behavior expected: Admin can manage beta users for the first authenticated multi-user release.

## Requirements

- Requirement IDs added: ADMIN USER and TERMS ADMIN IDs from #35/#39, or add them if not landed.
- Requirement IDs changed: Supersede unauthenticated Admin assumptions.
- Requirement IDs validated: ADMIN, AUTH, USER, TOKEN, I18N.

## Scope

- Impacted modules: admin, core auth/user services, tests.
- Owned files: `casino/admin.py`, `web/admin.html`, `web/admin.js`, `web/i18n/**/admin.json`, Admin v2 contracts if applicable, Admin API/browser tests, relevant module JSON files.
- Files not to touch: Game engines, storage provider internals except public service consumption, general frontend shell except Admin links.
- Allowed adjacent files: `casino/core/auth*` only if a public Admin service hook is missing and coordinated with #39.

## Compatibility

- API contract impact: Add or consume Admin v2 user-management endpoints.
- Gameplay impact: None.
- Ledger impact: Admin balance display only unless add-token action is explicitly ledger-backed.
- Bot/autoplay impact: Existing Admin telemetry must remain visible.
- Data migration impact: User records through storage provider.

## Required reading

- `AGENTS.md`
- `web/AGENTS.md`
- `casino/core/AGENTS.md`
- `modules/admin.json`, `modules/core.json`, `modules/tests.json`
- `casino/admin.py`, `web/admin.js`, `web/admin.html`
- Auth/user contracts from #35/#39

## Validation

- Required tests: Admin create user, deactivate user, reset password, terms status, locale controls, unauthorized Admin access.
- Required scripts: API/browser/contract/module/requirement/version/comment validations.
- Browser evidence: Admin user management screenshot or test evidence.
- Manual checks: Existing Admin telemetry still renders.

## Handback

- Expected PR summary: Admin features, APIs consumed/added, tests, screenshots.
- Evidence to include: API/browser test output.
- Open questions to report: Any Admin audit-log requirement gap.
- Stop conditions: Stop before adding self-signup or external identity providers.
