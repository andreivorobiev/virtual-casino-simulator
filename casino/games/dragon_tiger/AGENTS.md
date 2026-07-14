# AGENTS.md - Dragon Tiger module

Scope work in this directory to the isolated Dragon Tiger module.

## Allowed area

- `casino/games/dragon_tiger/`

## Rules

- Read the repository-root `AGENTS.md` before editing.
- Keep the game independent from every other game package.
- Reuse `casino.core.cards`, the shared ledger, and player-scoped state persistence.
- Never mutate balances directly or accept caller-controlled production randomness.
- Preserve session-bound player resolution and retry-safe action identities.
- Keep every meaningful executable Python line inline-commented or immediately preceded by a purpose comment.
- Leave shared catalog, aggregate manifest, requirements, compatibility, visual-matrix, and test-runner files to issue #77.

## Validation

Run focused Dragon Tiger tests plus the repository module-boundary and comment-density validators.
