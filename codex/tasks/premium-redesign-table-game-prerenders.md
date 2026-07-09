# Premium Table Game Prerender Task Packet

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/5
- Branch: `codex/premium-redesign-prerenders`
- PR title: Add premium table game prerenders
- Coordinator chat: Casino Simulator - Coordinator
- Worker chat: Casino Simulator - Worker - Premium Table Game Prerenders

## Goal

- Goal: Produce high-fidelity prerenders and animation notes for Roulette, Blackjack, and Baccarat.
- Non-goals: Do not implement production UI. Do not change game rules, APIs, ledger behavior, bot/autoplay behavior, or module versions in this phase.
- User-visible behavior expected: None until later implementation.

## Requirements

- Requirement IDs added: Proposed future `UX-007`, `UX-008`, `UX-009`.
- Requirement IDs changed: None.
- Requirement IDs validated: `UX-001` through `UX-006`, relevant Roulette, Blackjack, and Baccarat requirements, `LEDGER-005`, `LEDGER-006`, `LEDGER-025`.

## Scope

- Impacted modules: roulette, blackjack, baccarat, UX.
- Owned files: Proposal artifacts under `codex/tasks/artifacts/premium-redesign-prerenders/table-games/`.
- Files not to touch: Production source files.
- Allowed adjacent files: Read-only context from `web/games/roulette.js`, `web/games/blackjack.js`, `web/games/baccarat.js`, current requirements, and module manifests.

## Required Reading

- `AGENTS.md`
- Relevant nested game `AGENTS.md`
- `codex/tasks/premium-redesign-epic.md`
- `docs/requirements/requirements.json`
- `modules/module-manifest.json`
- `modules/roulette.json`
- `modules/blackjack.json`
- `modules/baccarat.json`
- `web/games/roulette.js`
- `web/games/blackjack.js`
- `web/games/baccarat.js`
- `web/styles.css`

## Required Prerenders

- Roulette: betting setup, spinning/reveal state, settled result with stable bet slip/stat regions.
- Blackjack: initial deal, active decision, split or multi-hand layout, settled result; premium buttons for Hit, Stand, Double, Split, Surrender, Insurance where applicable.
- Baccarat: wager setup, card reveal, result/road history state.
- Include bot/autoplay panels where relevant without destabilizing the main table area.

## Animation Notes

- Roulette wheel and ball motion, result lock-in, chip placement, stat update.
- Blackjack card deal, active hand highlight, button feedback, multi-hand/split transitions.
- Baccarat card peel/reveal, road update, result settlement.
- All motion must use transform/opacity and reserved regions.

## Handback

- Expected summary: Preview paths, state coverage, animation plan, implementation risks, requirement mapping.
- Evidence to include: High-fidelity PNG previews and source mockups.
- Open questions to report: Ambiguous gameplay states or layout constraints.
- Stop conditions: Stop before production edits.
