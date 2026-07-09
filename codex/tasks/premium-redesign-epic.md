# Premium Casino Redesign Prerender Epic

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/3
- Branch: `codex/premium-redesign-prerenders`
- PR title: Add premium casino redesign prerender plan
- Coordinator chat: Casino Simulator - Coordinator
- Worker chats:
  - Casino Simulator - Worker - Premium Shell Prerenders
  - Casino Simulator - Worker - Premium Table Game Prerenders
  - Casino Simulator - Worker - Premium Machine Draw Prerenders
  - Casino Simulator - Worker - I18n Locale Plan
- Child issues:
  - Shell/lobby/admin prerenders: https://github.com/andreivorobiev/virtual-casino-simulator/issues/7
  - Table game prerenders: https://github.com/andreivorobiev/virtual-casino-simulator/issues/5
  - Machine/draw game prerenders: https://github.com/andreivorobiev/virtual-casino-simulator/issues/6
  - I18n locale plan: https://github.com/andreivorobiev/virtual-casino-simulator/issues/4

## Goal

- Goal: Produce professional, high-fidelity prerenders and implementation-ready specs before any production redesign work begins.
- Non-goals: Do not implement production UI. Do not change gameplay, APIs, ledger behavior, bot behavior, autoplay behavior, tests, contracts, or module versions in this phase.
- User-visible behavior expected: None in the running app until a later approved implementation phase.

## Requirements

- Requirement IDs added: Proposed future IDs only: `UX-007`, `UX-008`, `UX-009`, `I18N-001`, `I18N-002`, `I18N-003`.
- Requirement IDs changed: None.
- Requirement IDs validated: `CORE-005`, `CORE-006`, `CORE-015`, `LEDGER-025`, `UX-001`, `UX-002`, `UX-003`, `UX-004`, `UX-005`, `UX-006`, `ADMIN-013`, `ADMIN-019`.

## Scope

- Impacted modules: docs, UX, application, admin, roulette, slots, keno, bingo, blackjack, baccarat, tests, future i18n.
- Owned files: `codex/tasks/premium-redesign-*.md`, proposal-only artifacts under `codex/tasks/artifacts/premium-redesign-prerenders/`.
- Files not to touch: Production files under `web/`, `casino/`, `contracts/`, `tests/`, `docs/requirements/`, and `modules/` unless a later implementation task is approved.
- Allowed adjacent files: Existing production files may be read for context only.

## Design Direction

- Use the user-approved target image as the canonical reference: premium dark casino shell, gold trim, photographic game imagery, stable topbar, visible balance, status rail, and rich game cards.
- Use AI-generated art where it improves the result, and code-native styled assets where deterministic controls, table surfaces, or animation layers are better.
- Render every major page before implementation: Lobby, Admin including Language/Locale, Roulette, Slots, Keno, Bingo, Blackjack, Baccarat.
- Include state-aware screens, not only empty states.
- Blackjack must show premium controls and multi-hand/split-friendly layout.
- Static game areas are required: action/result changes must not shift major layout regions.
- Animation notes must emphasize transform/opacity and stable reserved regions.

## Validation

- Required tests: None in prerender phase.
- Required scripts: None unless used to render proposal assets.
- Browser evidence: Each prerender worker must provide PNG previews or explain blockers.
- Manual checks: Compare every preview against the target art direction and current app behavior.

## Handback

- Expected PR summary: Epic, issue links, worker links, artifact paths, and implementation readiness assessment.
- Evidence to include: PNG prerenders, source mockups, animation notes, localization plan, requirement mapping, and open questions.
- Open questions to report: Gameplay state ambiguity, asset generation limitations, layout stability risks, or localization resource decisions.
- Stop conditions: Stop before production implementation.
