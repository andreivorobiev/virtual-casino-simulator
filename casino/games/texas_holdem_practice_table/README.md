# Texas Hold'em Practice Table

Issue: [#95](https://github.com/andreivorobiev/virtual-casino-simulator/issues/95)

This draft integrated module provides one authenticated human with three funded server-managed practice opponents. It is intentionally not true multiplayer; that remains owned by #79. The engine reuses `casino.core.cards.shuffled_deck` and `casino.core.poker.evaluate_hand` from #96 instead of defining another card or poker model.

## Practice profile

- One standard 52-card deck deals two private cards per seat, burns before each street, and reveals a three-card flop, one turn, and one river.
- The table has one human seat and three localized server-managed practice seats.
- Each seat begins with a fixed ante. Four later fixed-limit rounds offer the human `call` or `fold`; practice opponents automatically call through the same `engine.apply_action` validation path.
- Raises, side pots, all-in play, cash-game buy-ins, spectators, sockets, and human-versus-human play remain outside this narrow practice profile.
- Every showdown uses the shared seven-card evaluator and splits tied pots to exact cents in stable seat order.

## Ledger and retry invariants

The human selects one `base_wager`. Starting a hand reserves five wager units—one ante plus four possible calls—for the authenticated human and each of the three funded bot player accounts. Later calls allocate only already-reserved table tokens and never mutate a wallet directly.

At settlement:

- unused human escrow returns through `TEXAS_HOLDEM_ESCROW_REFUND_CREDIT` and each bot refund uses `PRACTICE_OPPONENT_ESCROW_REFUND`;
- human pot shares use `TEXAS_HOLDEM_PAYOUT_CREDIT` and funded bot shares use `PRACTICE_OPPONENT_PAYOUT`;
- every movement includes player, game, hand, transaction type, amount, component, and a storage-enforced action identity;
- opponent events also include the bot account, controller action, fixed policy, and owning human session context for Admin audit;
- prepared private state is saved before settlement reconciliation, and recovery reuses committed ledger evidence before issuing a movement.

Every start and decision command requires an `action_id`. Identical retries return the same logical hand, including after that hand leaves the 20-item public history window; compact sanitized terminal snapshots preserve durable request receipts without retaining every full private hand. Reusing one id for another wager, hand, or action fails closed. The API never accepts a card seed; deterministic cards exist only through injected focused-test dependencies.

Human actions use `ledger.debit_once` and `ledger.credit_once`; opponent movements use `casino.core.practice_accounts`, which consumes the same accepted issue #190 storage transaction. Exact semantics replay the original ledger event, changed key reuse fails closed, and the accepted JSON/MySQL evidence covers restart, lost-response, and process concurrency.

## Session and privacy invariants

- `context.resolved_player_id` or `context.bound_player_id` takes precedence over compatibility body/query ids.
- State is stored through `load_player_game_state` and `save_player_game_state` under the authenticated human.
- Active opponent hole cards, player-account ids, the complete community plan, burns, remaining deck, policies, ledger intents, and owner correlation are excluded by a strict public whitelist.
- Opponent cards appear only after fully reconciled settlement.

## Public actions

- `GET /api/v1/games/texas-holdem-practice-table/state`
- `POST /api/v1/games/texas-holdem-practice-table/hands`
- `POST /api/v1/games/texas-holdem-practice-table/hands/{hand_id}/actions`

Every decision body includes the client-observed `expected_phase`; a delayed or remounted surface cannot spend one intended click on a later street. The canonical module descriptor registers these routes through catalog discovery.

## Requirement mapping

- Permanent game block: `THPT-001` through `THPT-005`.
- Session isolation: `SESSION-003`, `SESSION-004`, `SESSION-005`.
- Ledger-only settlement: `LEDGER-005`, `LEDGER-006`, `LEDGER-007`, `LEDGER-009`, `LEDGER-023`, `LEDGER-026`, `STORAGE-005`, `STORAGE-006`.
- Funded-opponent and Admin audit boundary: `BOT-009`, `BOT-010`, `BOT-011`, `ADMIN-023`.
- Shared primitives: `CARD-001`, `CARD-002`, `POKER-001`, `POKER-002`.
- Fake-token and private-balance language: `TOKEN-001`, `TOKEN-004`.
- Locale and layout: `I18N-001`, `I18N-002`, `UX-001`, `UX-002`, `UX-003`, `UX-004`, `UX-006`.
- Isolation, restart, and catalog evidence: `TEST-012`, `TEST-039`, `TEST-042`.

The `THPT-*` entries remain `PLANNED`. They cannot move to `PASS`, and pull request #120 cannot be ready, merged, closed, or counted, until separately owned issue #191 certification is accepted for the current catalog and extended to this game.

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
