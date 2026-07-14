# AGENTS.md - Chuck-a-Luck module

Scope future changes to the isolated `chuck_a_luck` game unless a coordinator explicitly assigns shared integration files.

## Rules

- Read the root `AGENTS.md`, the game rules documentation, and `codex/tasks/artifacts/issue-89-chuck-a-luck/chuck_a_luck.module.proposal.json` before editing.
- Preserve the three-six-sided-dice profile and the one-through-six wager catalog unless a versioned rule change is approved.
- Keep game code independent of every other game package.
- Route every play-token debit and credit through `casino/core/ledger.py`; never mutate balances directly.
- Preserve required `request_id` conflict detection, player-scoped round IDs, and deterministic ledger action keys.
- Store the committed dice in wager-ledger details so interrupted settlements recover the original result.
- Treat the player id as upstream session-bound and never honor a competing browser identity after routing.
- Keep visible frontend strings in the paired EN/RU game-domain resources.
- Reference issue #89 plus the permanent requirement IDs allocated by #77.
- Preserve dense adjacent-purpose comments for executable Python and JavaScript.

## Validation

Run focused engine, service, API, and frontend checks plus module-boundary, contract, requirement, version, and comment-density validation when the corresponding integration files are available.
