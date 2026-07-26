# AGENTS.md - Scratch Cards module

Scope future changes to the isolated `scratch_cards` game unless the #77 integration owner explicitly assigns shared files.

## Rules

- Read the root `AGENTS.md`, this file, `README.md`, `docs/games/scratch_cards.md`, and `modules/scratch_cards.json` before editing.
- Preserve the documented 3-by-3 match-three prize profile or version and document an intentional rules change.
- Keep this package independent from every other game package.
- Route every wager and payout through `casino/core/ledger.py`; never mutate balances directly.
- Preserve required purchase and scratch action identifiers, request fingerprints, and deterministic ledger action keys.
- Treat the authenticated session player resolved by the shared router as authoritative over caller-supplied IDs.
- Never expose an unrevealed prize through API state, HTML, ARIA text, logs, or test fixtures presented as production evidence.
- Keep all player-visible and accessible frontend strings in the paired EN/RU game domain files.
- Keep reveal presentation timer-free and disable decorative transitions for reduced-motion users.
- Reference issue #87 and only coordinator-allocated permanent requirement IDs; `SCRATCH` remains a provisional descriptor prefix until #77 allocates the block.
- Preserve dense adjacent-purpose comments for executable Python and JavaScript.

## Validation

Run focused engine, service, API, frontend, and isolated-browser tests plus contracts, module boundaries, requirements, versions, and comment density. Real-backend catalog evidence remains mandatory after #77 integrates the shared manifest and visual row.
