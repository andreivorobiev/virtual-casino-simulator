# Red Dog

This package implements GitHub issue #84. Issue #77 owns its catalog descriptor, canonical long driver, requirement registry, aggregate version manifest, compatibility metadata, visual matrix, and real-backend acceptance coverage.

## Rules

The implementation follows the regulated Red Dog sequence documented by the [New Jersey rule](https://www.law.cornell.edu/regulations/new-jersey/N-J-A-C-13-69F-6-5) and the [British Columbia Lottery Corporation rules of play](https://www.casinosbc.com/content/dam/casinosbc/about-games/how-to-play/craps/Rules-For-Play-Craps.pdf):

- Six standard decks use the merged `CARD-001` construction and deterministic shuffle primitives.
- The first two cards establish a rank spread; suits have no significance and ace is high.
- Consecutive cards push immediately without a third card.
- A pair draws a third card automatically. Three of a kind pays 11 to 1 profit; any other third card pushes.
- Any other opening offers call or a matching raise before the third card is drawn.
- A third card strictly between the opening ranks wins. Spread 1 pays 5 to 1, spread 2 pays 4 to 1, spread 3 pays 2 to 1, and spreads 4 through 11 pay 1 to 1.
- Winning credits return every committed stake in addition to the listed profit.

The pure engine produces ordered ledger intents and never imports player storage or mutates balances.

## API and state

The additive v1 surface is documented in `contracts/openapi/red_dog.v1.yaml`:

- `GET /api/v1/games/red-dog/state`
- `POST /api/v1/games/red-dog/rounds`
- `POST /api/v1/games/red-dog/rounds/{round_id}/call`
- `POST /api/v1/games/red-dog/rounds/{round_id}/raise`

Every command requires an `action_id`. Exact retries replay one prepared transition; reuse with a different command, round, or wager fails closed. The controller persists the prepared transition before wallet movement, calls only `casino.core.settlement.GameSettlementGateway`, stores each committed marker immediately, and recovers immutable provider proof by stable action id.

The route adapter consumes the player identity resolved by the authenticated router context. Caller body or query identifiers never replace that bound identity.

## Browser behavior

`web/games/red_dog.js` exports `RedDogGame` for catalog discovery. It imports the merged `CARD-002` renderer, installs the shared card stylesheet idempotently, and replaces its default labels with Red Dog-owned EN/RU accessible names. Every visible and ARIA string comes from the paired game dictionaries.

The layout keeps the three-card table wider than both support rails on desktop and stacks controls, stage, and data below the shared breakpoint. The module owns no animation or autoplay timer. Reduced-motion CSS disables decorative transitions, and `unmount()` releases the locale subscription, retry keys, stylesheet ownership, and state references.

## Requirement mapping

- Module/API behavior: `CORE-008`, `CORE-009`, `CORE-011`, `CORE-012`.
- Ledger-only settlement: `LEDGER-005`, `LEDGER-006`, `LEDGER-007`, `LEDGER-023`.
- Authenticated player isolation: `SESSION-003`, `SESSION-004`, `SESSION-005`.
- Shared cards and accessibility: `CARD-001`, `CARD-002`.
- Locale behavior: `I18N-001`, `I18N-002`.
- Stable visual behavior: `UX-001`, `UX-002`, `UX-003`, `UX-006`.

Issue #77 allocates permanent Red Dog requirements `RD-001` through `RD-005` for rules, session binding, ledger safety, EN/RU responsive behavior, and discovered acceptance evidence.

## Focused validation

From the repository root with Python and Node available:

```powershell
python -m unittest discover -s casino/games/red_dog/tests -p "test_*.py"
node casino/games/red_dog/tests/frontend_module_tests.mjs
node --check web/games/red_dog.js
python scripts/validate_module_boundaries.py
python scripts/validate_contracts.py
python scripts/check_comment_density.py
```
