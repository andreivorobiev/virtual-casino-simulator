# Premium Shell, Lobby, Admin Prerender Task Packet

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/7
- Branch: `codex/premium-redesign-prerenders`
- PR title: Add premium shell lobby admin prerenders
- Coordinator chat: Casino Simulator - Coordinator
- Worker chat: Casino Simulator - Worker - Premium Shell Prerenders

## Goal

- Goal: Produce high-fidelity prerenders for the premium shared app shell, lobby, admin dashboard, and admin Language/Locale section.
- Non-goals: Do not implement production UI. Do not edit `web/app.js`, `web/styles.css`, `web/admin.js`, or production assets.
- User-visible behavior expected: None until later implementation.

## Requirements

- Requirement IDs added: Proposed future `UX-007`, `UX-008`, `I18N-002`.
- Requirement IDs changed: None.
- Requirement IDs validated: `CORE-005`, `CORE-006`, `CORE-015`, `LEDGER-025`, `ADMIN-013`, `ADMIN-019`, `UX-001` through `UX-006`.

## Scope

- Impacted modules: application, admin, UX, future i18n.
- Owned files: Proposal artifacts under `codex/tasks/artifacts/premium-redesign-prerenders/shell-lobby-admin/`.
- Files not to touch: Production source files.
- Allowed adjacent files: Read-only context from `web/app.js`, `web/styles.css`, `web/admin.html`, `web/admin.js`.

## Required Reading

- `AGENTS.md`
- `web/AGENTS.md`
- `docs/codex_parallel_workflow.md`
- `codex/tasks/premium-redesign-epic.md`
- `docs/requirements/requirements.json`
- `modules/module-manifest.json`
- `web/app.js`
- `web/styles.css`
- `web/admin.html`
- `web/admin.js`

## Required Prerenders

- Premium lobby based on the user-approved target direction.
- Shared topbar/navigation/wallet shell.
- Admin dashboard with premium but still utilitarian control-plane layout.
- Admin Language/Locale section with English and Russian options, future top-20 language scalability, and locale controls.
- Responsive narrow-width sketch or second preview if feasible.

## Handback

- Expected summary: Preview paths, design rationale, implementation file list, proposed strings/resource considerations, and risks.
- Evidence to include: High-fidelity PNG previews and source mockup files.
- Open questions to report: Shell behavior, language persistence, or admin layout decisions.
- Stop conditions: Stop before production edits.
