# Codex Task Packet: Private User Game Sessions

**Historical.** This packet records the plan for issue #42 as written under epic #34, when the catalog held six games. It is not an active instruction. The current catalog is whatever `casino/games/` contains, which is now much larger, so the six-game enumerations below are the original scope rather than today's. For current requirement status see `docs/requirements/requirements.json`.

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/42
- Branch: codex/private-user-game-sessions
- PR title: Isolate game state and play APIs per authenticated user
- Coordinator chat: Casino Simulator - Coordinator
- Worker chat: Casino Simulator - Worker - Private Sessions

## Goal

- Goal: Adapt all six games so authenticated users have private in-progress state, token balances, and game histories.
- Non-goals: Do not change game rules, payouts, animations, or table/machine designs unless required to pass current-user state.
- User-visible behavior expected: User A and User B can play every game without sharing game state or token balances.

## Requirements

- Requirement IDs added: PRIVATE SESSION and per-game current-user IDs from #35/#39, or add them if not landed.
- Requirement IDs changed: Supersede hardcoded single-human assumptions.
- Requirement IDs validated: ROU, SLOT, BJ, BAC, KENO, BINGO, LEDGER, BOT, AUTO, AUTH.

## Durable Requirement/Contract References

- Implement USER-003, USER-005, TOKEN-004, STORAGE-002, MYSQL-002, API-001, API-002, and TEST-039.
- Consume `contracts/openapi/auth.v2.yaml` for current-user/player identity and token-balance shape.
- Preserve v1 compatibility unless the coordinator approves an explicit v2-only game API adaptation or compatibility shim.

## Scope

- Impacted modules: roulette, slots, blackjack, baccarat, keno, bingo, ledger, autoplay, bots, tests.
- Owned files: `casino/games/*/api.py`, `web/games/*.js` only to remove hardcoded `human` player assumptions, `casino/core/state_store.py` public helpers if coordinated with #38, game API/browser tests, relevant module JSON files.
- Files not to touch: `casino/games/*/engine.py` unless a current-user integration bug cannot be fixed at API/state layer and coordinator approves.
- Allowed adjacent files: `web/core/api.js`, `web/core/ui.js` only if current-user helper usage requires it and #40 is coordinated.

## Compatibility

- API contract impact: Prefer `/api/v2` current-user behavior or compatibility shims; do not break `/api/v1` old clients unexpectedly.
- Gameplay impact: No rule changes.
- Ledger impact: All token movement remains through `casino/core/ledger.py`.
- Bot/autoplay impact: Bots/autoplay must not cross human user sessions.
- Data migration impact: Private state keyed by user/player through storage provider.

## Required reading

- `AGENTS.md`
- Each `casino/games/<game>/AGENTS.md`
- `casino/core/AGENTS.md`
- Game module JSON files
- Relevant game v1 contracts and v2 additions from #35/#39
- `casino/core/ledger.py`, `casino/core/state_store.py`

## Validation

- Required tests: Two authenticated users play each game; balances/state/history remain isolated; bots/autoplay remain scoped.
- Required scripts: Full relevant API/browser/contract/module/requirement/version/comment validations.
- Browser evidence: Multi-user scenario evidence for representative games.
- Manual checks: Refresh and continue in-progress game per user.

## Handback

- Expected PR summary: Per-game changes, state-keying model, ledger integrity, tests.
- Evidence to include: Multi-user test output.
- Open questions to report: Any game-specific state that cannot be isolated without engine changes.
- Stop conditions: Stop before changing payout/game rules.
