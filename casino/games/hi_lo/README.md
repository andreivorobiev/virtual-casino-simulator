# Hi-Lo game module

Issue: [#85](https://github.com/andreivorobiev/virtual-casino-simulator/issues/85)

Parents: #66 and #73. Shared integration owner: #77.

This package implements the game-owned Hi-Lo slice without editing the shared catalog, router, shell, aggregate version manifest, central requirements, compatibility inventory, test runners, or visual matrix.

## Rules profile

One wagered round has two steps:

1. Deal one visible opening card and debit the wager.
2. Choose whether the next card will be `higher` or `lower`.

Cards come from one standard 52-card deck without replacement through the merged #96 card primitive. Rank comparison ignores suits and treats ace as high. A correct prediction uses the server-owned visible-rank paytable, from `0.96x` on a 2 or ace to `1.93x` on an 8. An equal rank returns the original wager as a tie refund, and an incorrect prediction returns nothing. The deprecated frozen-v1 scalar remains `2`, while `rules.correct_paytable` is the authoritative settlement source for current clients.

The private reveal card is persisted before the wager debit, excluded from API responses, and never written to wager ledger details. The browser therefore cannot inspect the result before choosing.

## Public actions

- `GET /api/v1/games/hi-lo/state`
- `POST /api/v1/games/hi-lo/rounds`
- `POST /api/v1/games/hi-lo/rounds/{round_id}/guesses`

Deal and guess commands each require a bounded `action_id`. Reusing an action with the same semantic payload returns the original state and ledger proof. Reusing it with a changed wager, round, or direction fails closed.

## Session, state, and ledger invariants

- Route handlers prefer `context.resolved_player_id` and `context.bound_player_id`; normal shared-router dispatch replaces hostile body and query player IDs before game access.
- State is stored per authenticated player with one reload-safe active decision, 20 settled rounds, and private compact action receipts that prevent reused IDs after public history pruning.
- Every wager uses `HI_LO_WAGER_DEBIT` through `casino/core/ledger.py`.
- Correct guesses use `HI_LO_PAYOUT_CREDIT`; equal ranks use `HI_LO_REFUND_CREDIT`; incorrect guesses create no zero-value ledger row.
- Ledger events include player, game, round, transaction type, amount, stage, action identity, request fingerprint, and revealed result context where applicable.
- A bounded player-scoped reentrant stripe, durable player-state action receipts, and provider-enforced ledger action identity prevent duplicate movements while allowing unrelated MySQL wallets to settle concurrently.
- Game code never mutates player balances or storage-provider balance fields directly.

A future multi-process deployment must add an atomic unique idempotency key to the shared ledger provider before claiming the same guarantee across processes. That shared-core follow-up is outside issue #85.

## Requirement mapping

Permanent Hi-Lo requirements are `HILO-001` through `HILO-005`. Shared requirements used by the module include `CARD-001`, `CARD-002`, `CORE-009`, `CORE-011`, `CORE-012`, `CORE-018`, `CORE-021`, `CORE-022`, `LEDGER-005`, `LEDGER-006`, `LEDGER-007`, `LEDGER-009`, `LEDGER-023`, `SESSION-005`, `I18N-001`, `I18N-002`, `TOKEN-001`, and `TEST-042`.

Issue #77 owns the permanent five-dimension block for rules, session/reload behavior, ledger/retry safety, EN/RU responsive UI, and discovered acceptance evidence.

## Focused validation

```powershell
python -m unittest tests.games.hi_lo.test_engine tests.games.hi_lo.test_api
node tests/games/hi_lo/test_frontend.mjs
python scripts/validate_contracts.py
python scripts/validate_module_boundaries.py
python scripts/validate_requirements.py
python scripts/check_comment_density.py
```

The #77 shared lane registers the descriptor, aggregate revision, compatibility metadata, visual row, and central API/browser/restart coverage. Long Suite 100 discovers this module through `tests.game_drivers.hi_lo:play`.
