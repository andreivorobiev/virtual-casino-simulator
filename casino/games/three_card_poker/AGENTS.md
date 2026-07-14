# AGENTS.md - Three Card Poker module

Scope work in this directory to the isolated Three Card Poker slice for GitHub issue #93.

## Allowed areas

- `casino/games/three_card_poker/`
- Game-specific tests under `tests/games/three_card_poker/` when the task explicitly includes them.

## Rules

- Read the repository-root `AGENTS.md` before editing.
- Reuse `casino.core.cards`; keep Three Card Poker ranking and paytables game-local.
- Resolve every player through the authenticated request context before state or ledger access.
- Persist prepared state before ledger movement and reconcile stable action identifiers on retries.
- Never mutate a player balance directly; all debits and credits go through `casino.core.ledger`.
- Keep production randomness private while exposing only injected deterministic seams to tests.
- Do not edit shared registry, router, application, manifest, requirements, compatibility, or test-runner files from this lane.
- Preserve dense adjacent comments for every meaningful executable Python line.

## Requirements and integration

The implemented shared invariants map to `API-001`, `CARD-001`, `SESSION-005`, `STORAGE-001`, `STORAGE-002`, `LEDGER-005`, `LEDGER-006`, `LEDGER-007`, and `LEDGER-009`. A permanent Three Card Poker requirement block and aggregate registration remain owned by issue #77.
