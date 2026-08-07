# Casino War isolated slice

This package implements GitHub issue #82 without modifying shared catalog, router, shell, test-runner, requirement-registry, version-manifest, or visual-matrix files owned by #81/#110 and #77.

## Rules

- Six standard decks use the merged `CARD-001` card and deterministic shuffle primitives.
- Player and dealer each receive one card; ace is high and suits do not break ties.
- An initial player win returns twice the ante. An initial dealer win returns zero.
- An initial tie offers surrender, which returns half the ante, or war, which adds a matching wager.
- War burns three cards, then deals player and dealer cards. A player win or second tie credits three times the original ante: the original stake and even-money win plus the pushed war wager. A dealer win returns zero.

The pure engine only produces ordered ledger intents. It never imports player storage and never mutates balances.

## API and state

The additive v1 surface is documented in `contracts/openapi/casino_war.v1.yaml`:

- `GET /api/v1/games/casino-war/state`
- `POST /api/v1/games/casino-war/rounds`
- `POST /api/v1/games/casino-war/rounds/{round_id}/surrender`
- `POST /api/v1/games/casino-war/rounds/{round_id}/war`

Every command requires an `action_id`. The controller persists the complete prepared transition before wallet movement, calls only `casino.core.settlement.GameSettlementGateway`, stores each committed marker immediately, and recovers immutable proof by stable action id. Provider-owned action identity supplies cross-process exactly-once behavior; process-local locking is no longer the money-integrity boundary.

The route adapter prefers #110's `context.resolved_player_id`, then the existing `context.bound_player_id`, before any compatibility body/query value. Normal authenticated users therefore remain session-bound when the shared resolver lands.

## Browser behavior

`web/games/casino_war.js` exports `CasinoWarGame` for catalog discovery. It imports the merged `CARD-002` renderer and installs its shared stylesheet idempotently. All Casino War-owned visible and accessible copy comes from the EN/RU domain files. The layout keeps the card table wider than both support rails on desktop and stacks controls, stage, and history on compact viewports.

The game owns no animation or autoplay timers. Reduced-motion CSS disables decorative transitions, and `unmount()` releases the locale subscription and state references.

## Requirement mapping

- Shared module/API behavior: `CORE-008`, `CORE-009`, `CORE-011`, `CORE-012`.
- Ledger-only settlement: `LEDGER-005`, `LEDGER-006`, `LEDGER-007`, `LEDGER-023`.
- Session isolation: `SESSION-003`, `SESSION-004`, plus planned `SESSION-005` from #81/#110.
- Cards and accessibility: `CARD-001`, `CARD-002`.
- Locale behavior: `I18N-001`, `I18N-002`.
- Permanent Casino War requirements `CW-001` through `CW-005` are registered in `docs/requirements/requirements.json` and cover rules, session/reload state, ledger settlement, EN/RU responsive behavior, and discovered acceptance evidence.

## Focused validation

From the repository root with Python and Node available:

```powershell
python -m unittest discover -s casino/games/casino_war/tests -p "test_*.py"
node casino/games/casino_war/tests/frontend_module_tests.mjs
node --check web/games/casino_war.js
python scripts/validate_module_boundaries.py
python scripts/validate_contracts.py
python scripts/check_comment_density.py
```
