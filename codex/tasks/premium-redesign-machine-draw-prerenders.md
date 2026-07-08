# Premium Machine and Draw Game Prerender Task Packet

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/6
- Branch: `codex/premium-redesign-prerenders`
- PR title: Add premium machine and draw game prerenders
- Coordinator chat: Casino Simulator - Coordinator
- Worker chat: Casino Simulator - Worker - Premium Machine Draw Prerenders

## Goal

- Goal: Produce high-fidelity prerenders and animation notes for Slots, Keno, and Bingo.
- Non-goals: Do not implement production UI. Do not change game rules, APIs, ledger behavior, bot/autoplay behavior, or module versions in this phase.
- User-visible behavior expected: None until later implementation.

## Requirements

- Requirement IDs added: Proposed future `UX-007`, `UX-008`, `UX-009`.
- Requirement IDs changed: None.
- Requirement IDs validated: `UX-001` through `UX-006`, relevant Slots, Keno, and Bingo requirements, `LEDGER-018` through `LEDGER-023`, `LEDGER-025`.

## Scope

- Impacted modules: slots, keno, bingo, UX.
- Owned files: Proposal artifacts under `codex/tasks/artifacts/premium-redesign-prerenders/machine-draw-games/`.
- Files not to touch: Production source files.
- Allowed adjacent files: Read-only context from `web/games/slots.js`, `web/games/keno.js`, `web/games/bingo.js`, current requirements, and module manifests.

## Required Reading

- `AGENTS.md`
- Relevant nested game `AGENTS.md`
- `codex/tasks/premium-redesign-epic.md`
- `docs/requirements/requirements.json`
- `modules/module-manifest.json`
- `modules/slots.json`
- `modules/keno.json`
- `modules/bingo.json`
- `web/games/slots.js`
- `web/games/keno.js`
- `web/games/bingo.js`
- `web/styles.css`

## Required Prerenders

- Slots: idle reels, spin-in-progress, win/payline reveal, free spin/progressive context.
- Keno: spot selection, draw in progress, result/paytable comparison.
- Bingo: card purchase/ready state, ball call in progress, winning pattern highlight.
- Include bot/autoplay panels where relevant without destabilizing the main play area.

## Animation Notes

- Slots reel blur/stop cadence, payline highlight, win glow.
- Keno number draw sequencing, selected/matched number transitions, ticket persistence.
- Bingo ball call, card daubing, pattern highlight.
- All motion must use transform/opacity and reserved regions.

## Handback

- Expected summary: Preview paths, state coverage, animation plan, implementation risks, requirement mapping.
- Evidence to include: High-fidelity PNG previews and source mockups.
- Open questions to report: Ambiguous game states or layout constraints.
- Stop conditions: Stop before production edits.
