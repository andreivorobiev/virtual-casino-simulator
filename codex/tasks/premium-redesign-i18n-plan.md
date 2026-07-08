# Premium Redesign I18n Resource Plan Task Packet

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/4
- Branch: `codex/premium-redesign-prerenders`
- PR title: Add i18n resource extraction plan
- Coordinator chat: Casino Simulator - Coordinator
- Worker chat: Casino Simulator - Worker - I18n Locale Plan

## Goal

- Goal: Design the resource-file architecture and implementation plan for extracting all UI strings, adding English and Russian resources, and adding an Admin Language/Locale section.
- Non-goals: Do not extract strings or implement i18n yet. Do not edit production source files in this phase.
- User-visible behavior expected: None until later implementation.

## Requirements

- Requirement IDs added: Proposed future `I18N-001`, `I18N-002`, `I18N-003`.
- Requirement IDs changed: None.
- Requirement IDs validated: `CORE-005`, `CORE-006`, `ADMIN-013`, `ADMIN-019`, `UX-001` through `UX-006`.

## Scope

- Impacted modules: future i18n, application, admin, all frontend game modules, tests.
- Owned files: Proposal artifacts under `codex/tasks/artifacts/premium-redesign-prerenders/i18n-plan/`.
- Files not to touch: Production source files.
- Allowed adjacent files: Read-only context from current `web/`, `casino/`, `docs/requirements/`, and `tests/` files.

## Required Reading

- `AGENTS.md`
- `codex/tasks/premium-redesign-epic.md`
- `docs/requirements/requirements.json`
- `modules/module-manifest.json`
- `web/app.js`
- `web/admin.js`
- `web/games/*.js`
- `tests/run_tests.py`

## Required Plan

- Recommended resource file structure for English and Russian.
- Key naming conventions and fallback behavior.
- How to avoid resetting game state when language changes.
- Where the Admin Language/Locale section should live and what controls it includes.
- Which strings are static, dynamic, or generated from game state.
- Initial Russian localization tone: polished casino-style Russian without over-optimizing.
- Future expansion path for top 20 languages.
- Browser/API test strategy for language toggle and persistence.

## Handback

- Expected summary: Resource architecture, extraction phases, file ownership splits, risks, proposed tests, and implementation worker breakdown.
- Evidence to include: String inventory map and sample English/Russian resource entries.
- Open questions to report: Locale persistence, date/number formatting scope, and whether backend error strings are in phase one.
- Stop conditions: Stop before production edits.
