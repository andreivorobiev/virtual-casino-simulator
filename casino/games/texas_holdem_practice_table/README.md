# Texas Hold'em Practice Table

Issue: [#95](https://github.com/andreivorobiev/virtual-casino-simulator/issues/95)

This isolated slice provides one authenticated human with three server-managed practice opponents. It is intentionally not true multiplayer; that remains owned by #79. The engine uses `casino.core.cards.shuffled_deck` and `casino.core.poker.evaluate_hand` from #96 instead of defining another card or poker model.

## Practice profile

- One standard 52-card deck deals two private cards per seat, burns before each street, and reveals a three-card flop, one turn, and one river.
- The table has one human seat and three localized server-managed practice seats.
- Each seat begins with a fixed ante. Four later fixed-limit rounds offer the human `call` or `fold`; the practice opponents automatically call through the same `engine.apply_action` validation path.
- Raises, side pots, all-in play, cash-game buy-ins, spectators, sockets, and human-versus-human play are intentionally outside this issue's narrow practice profile.
- Every showdown uses the shared seven-card evaluator and splits tied pots to exact cents in stable seat order.

## Ledger and retry invariants

The human selects one `base_wager`. Starting a hand reserves five wager units—one ante plus four possible calls—with one `TEXAS_HOLDEM_ESCROW_DEBIT`. Later calls allocate only already-reserved table tokens, so they never mutate the wallet directly. At settlement:

- unused escrow returns through one `TEXAS_HOLDEM_ESCROW_REFUND_CREDIT`;
- a human pot share returns through one `TEXAS_HOLDEM_PAYOUT_CREDIT`;
- every movement includes player, game, hand, transaction type, amount, and a unique `texas_holdem_action_id` detail;
- prepared private state is saved before the ledger call, and retry recovery scans append-only ledger evidence before issuing a movement;
- a process-local lock serializes normal duplicate commands while the supported single-process local simulator remains running.

Every start and decision command requires an `action_id`. Identical retries return the same logical hand, including after that hand leaves the 20-item public history window; compact sanitized terminal snapshots remain available for durable request receipts without retaining every full private hand. Reusing one id for another wager, hand, or action fails closed. The API never accepts a card seed; deterministic cards exist only through injected focused-test dependencies.

This game-local algorithm does not make the shared JSON balance update and ledger append crash-atomic, and the process-local lock does not enforce action-key uniqueness across server processes. Atomic storage-level uniqueness remains a shared #77 acceptance blocker and is not claimed by this isolated slice.

## Session and privacy invariants

- `context.resolved_player_id` or `context.bound_player_id` takes precedence over compatibility body/query ids.
- State is stored through `load_player_game_state` and `save_player_game_state` under the authenticated human.
- Active opponent hole cards, the complete community plan, burns, remaining deck, policies, and ledger intents are excluded by a strict public whitelist.
- Opponent cards appear only after a fully reconciled showdown.

## Public actions

- `GET /api/v1/games/texas-holdem-practice-table/state`
- `POST /api/v1/games/texas-holdem-practice-table/hands`
- `POST /api/v1/games/texas-holdem-practice-table/hands/{hand_id}/actions`

Every decision body includes the client-observed `expected_phase`; a delayed or remounted surface cannot spend one intended click on a later street. The game can register these routes on an isolated `casino.router.Router` for focused tests. Catalog materialization remains owned by #77.

## Requirement mapping

- Game/module and API seams: `CORE-008`, `CORE-009`, `CORE-011`, `CORE-012`, `CORE-022`.
- Session isolation: `SESSION-003`, `SESSION-004`, `SESSION-005`.
- Ledger-only wallet movement: `LEDGER-005`, `LEDGER-006`, `LEDGER-007`, `LEDGER-009`, `LEDGER-023`.
- Shared primitives: `CARD-001`, `CARD-002`, `POKER-001`, `POKER-002`.
- Fake-token and private-balance language: `TOKEN-001`, `TOKEN-004`.
- Locale and layout: `I18N-001`, `I18N-002`, `UX-001`, `UX-002`, `UX-003`, `UX-004`, `UX-006`.
- Focused isolation/replay evidence: `TEST-012`, `TEST-039`; descriptor discovery under `TEST-042` remains blocked on #77.
- Bot governance boundary: `BOT-001` through `BOT-007` are not accepted by this slice; see `INTEGRATION.md`.

Permanent `THPT-001` through `THPT-005` entries are proposed, not allocated. The central requirements owner must allocate them during #77 integration.

## Focused validation

```powershell
python -m unittest discover -s casino/games/texas_holdem_practice_table/tests -p "test_*.py"
node casino/games/texas_holdem_practice_table/tests/test_frontend.mjs
node --check web/games/texas_holdem_practice_table.js
python scripts/validate_contracts.py
python scripts/validate_module_boundaries.py
python scripts/validate_requirements.py
python scripts/validate_versions.py
python scripts/check_comment_density.py
```
