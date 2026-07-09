# Codex Task Packet: Frontend Login, Terms, and Current User Shell

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/40
- Branch: codex/frontend-auth-current-user
- PR title: Add login gate, terms acceptance, and current-user shell
- Coordinator chat: Casino Simulator - Coordinator
- Worker chat: Casino Simulator - Worker - Frontend Auth

## Goal

- Goal: Add browser login, terms acceptance, current-user session handling, token balance display, add-token flow, and logout.
- Non-goals: Do not implement backend auth/storage internals or game rule changes.
- User-visible behavior expected: A logged-out user sees login/terms before the casino; logged-in users see current-user token balance with `◈`.

## Requirements

- Requirement IDs added: AUTH UI, TERMS UI, TOKEN UI, I18N IDs from #35/#37, or add them if not landed.
- Requirement IDs changed: Supersede visible unauthenticated/local-only assumptions.
- Requirement IDs validated: UX, I18N, ADMIN as applicable, CORE, TOKEN.

## Scope

- Impacted modules: application, admin frontend as entry point only, tests.
- Owned files: `web/index.html`, `web/app.js`, `web/styles.css`, `web/core/api.js`, `web/core/ui.js`, `web/core/i18n.js`, `web/i18n/**`, auth/terms browser tests, relevant module JSON files.
- Files not to touch: Backend auth internals, storage provider internals, game engines.
- Allowed adjacent files: `web/games/*.js` only to consume current-user token formatting if coordinated with #37/#42.

## Compatibility

- API contract impact: Consumes `/api/v2/auth/*` and `/api/v2/me*`; no contract changes unless coordinated.
- Gameplay impact: No rule changes.
- Ledger impact: Add-token UI must call ledger-backed endpoint.
- Bot/autoplay impact: Must not start autoplay actions while logged out.
- Data migration impact: None.

## Required reading

- `AGENTS.md`
- `web/AGENTS.md`
- `modules/application.json`, `modules/tests.json`
- `web/core/api.js`, `web/core/ui.js`, `web/app.js`
- Auth/current-user contracts from #39

## Validation

- Required tests: Browser tests for login gate, terms acceptance, token balance, add tokens, logout, locale switching, and state preservation.
- Required scripts: Browser tests plus relevant full validators.
- Browser evidence: Screenshots or Playwright evidence for login and shell.
- Manual checks: Refresh while logged in and logged out.

## Handback

- Expected PR summary: Login/terms UX, session state flow, token display, tests.
- Evidence to include: Browser test output and screenshots.
- Open questions to report: Any copy or layout ambiguity.
- Stop conditions: Stop before changing backend auth/storage contracts without coordinator approval.
