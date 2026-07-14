# AGENTS.md - Big Six Wheel module

Scope future changes to the isolated `big_six_wheel` game unless a coordinator explicitly assigns shared integration files.

## Rules

- Read the root `AGENTS.md`, `docs/games/big_six_wheel.md`, and the game descriptor before editing.
- Preserve the 54-segment profile or document and version an intentional profile change.
- Keep game code independent of every other game package.
- Route all play-token movement through `casino/core/ledger.py`; never mutate balances directly.
- Preserve required `client_request_id` conflict detection and deterministic ledger action keys.
- Treat the authenticated player id as upstream session-bound; never honor a competing browser identity after routing.
- Preserve reduced-motion scheduling and timer-scope disposal on every frontend exit path.
- Keep all visible frontend strings in the EN/RU game domain files.
- Reference issue #86 plus the permanent requirement IDs allocated by #77.
- Preserve dense adjacent-purpose comments for executable Python and JavaScript.

## Validation

Run the focused Python engine/service and API suites, the Node frontend suite, module boundaries, contracts, requirements, versions, and comment density. Real-backend browser and visual evidence remain mandatory after shared catalog integration.
