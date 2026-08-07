# Sic Bo

Issue: [#88](https://github.com/andreivorobiev/virtual-casino-simulator/issues/88)

This isolated game implements a complete 50-position Sic Bo table: small, big, totals 4-17, six single-number positions, six specific doubles, six specific triples, any triple, and all fifteen two-number combinations. The payout profile follows the Massachusetts Gaming Commission Sic Bo rules linked below.

## Public actions

- `GET /api/v1/games/sic-bo/state`
- `POST /api/v1/games/sic-bo/rounds`

Each round accepts a required bounded `action_id` plus a canonical map of position IDs to play-token wagers. The server rolls exactly three dice, performs one aggregate wager debit, calculates every position, and creates at most one aggregate returned-credit event.

## Session, ledger, and reload invariants

- The handler prefers `resolved_player_id` and `bound_player_id` from authenticated request context. Caller body or query IDs remain compatibility-only fallbacks and cannot override a session binding.
- Every token movement calls `casino.core.settlement.GameSettlementGateway`; game code never imports the ledger implementation or mutates balances or storage-provider balance fields.
- Wager and payout events use deterministic `sic_bo_action_id` values derived from a server-bounded round ID.
- Reusing `action_id` with the same normalized wagers returns the same dice and settlement. Reusing it with different wagers fails closed.
- Private dice and prepared state persist before debit. Dice remain hidden from the public state shape until ledger proof of the wager exists.
- A retry recovers committed dice from ledger details, recovers any committed payout, archives the settled round, and cannot duplicate either movement in the supported single-process local server.
- The browser keeps the same action ID and wager snapshot across an ambiguous response, restores active recovery state after reload, and uses only public API actions.

## Deterministic and motion seams

Production dice use server-side `secrets.randbelow`. Focused tests inject a bounded integer source; the API exposes no seed or forced result. The merged #97 `web/core/dice.js` helper is intentionally not used to choose authoritative outcomes because it runs in the browser. The frontend does reuse #97's `createMotionTimerScope` for reduced-motion-aware reveal timing and route/reload cleanup.

## Rules source

- [Massachusetts Gaming Commission Sic Bo rules](https://massgaming.com/wp-content/uploads/RULES-Sic-Bo-2-1-18.pdf)
- [Massachusetts table-game rules index](https://massgaming.com/regulations/table-games-rules/)

These links document three dice, the eight wager families used by the 50 positions, triple exclusions for small/big, and the implemented net payout odds. The simulator remains play-token only and does not model real-money play.

## Requirement traceability

Existing impacted IDs: `CORE-008` through `CORE-012`, `CORE-022`, `LEDGER-005`, `LEDGER-006`, `LEDGER-007`, `LEDGER-009`, `LEDGER-023`, `SESSION-005`, `I18N-001`, `I18N-002`, `DICE-001`, `MOTION-001` through `MOTION-003`, `UX-001`, `UX-002`, `UX-003`, `UX-004`, `UX-006`, and `UX-009`.

Permanent Sic Bo requirements `SIC-BO-001` through `SIC-BO-005` are registered in `docs/requirements/requirements.json` and cover rules, session/reload safety, ledger retry safety, EN/RU responsive UI, and discovered acceptance evidence.
