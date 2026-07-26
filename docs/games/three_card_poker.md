# Three Card Poker isolated game slice

Issue: [#93](https://github.com/andreivorobiev/virtual-casino-simulator/issues/93)

Parents: #66 and #73. Shared integration lane: #77. Catalog foundation: #81.

## Selected rules profile

This fake-money simulator follows the Maryland State Lottery and Gaming Control Agency [Standard Rules - Three Card Poker, Version 1.4](https://www.mdgaming.com/wp-content/uploads/2026/04/Three-Card-Poker-Standard-Rules-Version-1.4-accessible.pdf). It uses one standard 52-card deck for each round and implements only the core Ante/Play game plus the optional Pair Plus wager. Progressive, envy, Six Card Bonus, and five-card progressive wagers are outside issue #93.

The Three Card Poker ranking order is straight flush, three of a kind, straight, flush, pair, then high card. A straight therefore outranks a flush. Ace-king-queen is the highest straight and ace-2-3 is the lowest. Suits have equal rank.

The dealer qualifies with queen high or better. After seeing three player cards, the player either:

- makes a Play wager equal to the Ante; or
- folds, forfeiting the Ante and any Pair Plus wager placed with it.

When the player plays and the dealer does not qualify, the Ante wins at 1 to 1 and the Play wager is returned. When the dealer qualifies, the higher hand wins both Ante and Play at 1 to 1, equal hands push, and a lower player hand loses both wagers.

This module explicitly selects Maryland Ante Bonus Paytable A and Pair Plus Paytable C:

| Wager | Hand | Net odds |
| --- | --- | ---: |
| Ante Bonus A | Straight flush | 5 to 1 |
| Ante Bonus A | Three of a kind | 4 to 1 |
| Ante Bonus A | Straight | 1 to 1 |
| Pair Plus C | Straight flush | 40 to 1 |
| Pair Plus C | Three of a kind | 30 to 1 |
| Pair Plus C | Straight | 6 to 1 |
| Pair Plus C | Flush | 3 to 1 |
| Pair Plus C | Pair | 1 to 1 |

The Ante Bonus applies after a Play wager regardless of whether the dealer qualifies or whether the player hand outranks the dealer. Pair Plus is evaluated from the player hand independently of the dealer after the player chooses Play.

## Deterministic and private state model

- Production deals use the shared `casino.core.cards` deck and shuffle primitives; deterministic cards are injectable only through focused test dependencies and never through the public API.
- Three-card ranking is game-owned because the shared poker evaluator intentionally handles five through seven cards, while shared card normalization and deck construction remain authoritative.
- State is stored by authenticated player. A caller-supplied compatibility `player_id` cannot override the router's session-bound identity.
- A dealt round persists the player hand, hidden dealer hand, opening wagers, request fingerprint, and settlement markers before returning the decision state.
- State responses and deal responses keep dealer card identities hidden until the round is settled. Reload restores the same actionable or settled round.

## Ledger and retry design

Every token movement goes through `casino/core/ledger.py`; the game never writes a player balance directly.

1. `POST /rounds` requires a bounded `request_id`, normalizes the Ante and optional Pair Plus amounts, creates a stable round identity, persists prepared state, and applies exactly one combined opening-wager debit.
2. Reusing the same `request_id` and wager fingerprint returns the existing round. Reusing it with different wagers fails closed.
3. `POST /rounds/{round_id}/decisions` requires a bounded `action_id` and either `play` or `fold`.
4. Play applies exactly one matching-ante debit and at most one combined settlement credit. Fold performs no further movement because the opening wagers were already debited.
5. Decision retries recover committed ledger actions and return the original result. Reusing an `action_id` for a different decision fails closed.

The adapter targets the supported single-process local simulator and serializes state/ledger recovery with a process-local lock. A future multi-process deployment would require a unique idempotency key enforced atomically by shared storage before making the same guarantee.

## Permanent requirements

The permanent block registered in `docs/requirements/requirements.json` is:

- `TCP-001`: one-deck Three Card Poker implements the documented rankings, dealer qualification, Ante/Play decisions, Ante Bonus A, and Pair Plus C.
- `TCP-002`: additive v1 endpoints bind the authenticated player and preserve private reload-safe round state with hidden dealer cards before settlement.
- `TCP-003`: opening wagers, Play wagers, refunds, and payouts are ledger-only and retry-safe under stable request and action identities.
- `TCP-004`: the game surface provides complete EN/RU visible and accessible copy across required responsive viewports with reduced-motion-safe lifecycle behavior.
- `TCP-005`: catalog, contract, browser, long-suite, requirement, module, version, and visual evidence remain traceable through module-owned metadata.

Existing cross-cutting requirements include `API-001`, `CARD-001`, `CARD-002`, `CORE-008`, `CORE-009`, `CORE-010`, `CORE-021`, `I18N-001`, `I18N-002`, `LEDGER-005`, `LEDGER-006`, `LEDGER-007`, `LEDGER-009`, `LEDGER-023`, `POKER-001`, `SESSION-005`, `STORAGE-001`, `STORAGE-002`, and `TEST-042`.

## #77 integration

The canonical descriptor at `modules/three_card_poker.json` owns the module version, catalog sort order `190`, and route `/games/three_card_poker`. Packaged application release impact was None.

#77 completed integration:

- descriptor promotion to `modules/three_card_poker.json`, the `three_card_poker` revision in `modules/module-manifest.json`, and recalculated shared module revisions;
- permanent requirements `TCP-001` through `TCP-005`, central and generated requirements, and mapped API/browser test IDs;
- the OpenAPI contract in the compatibility matrix and contract digest;
- the `three_card_poker` visual-matrix row and game-specific real-backend API/browser coverage;
- catalog discovery, the module-owned long driver, full API/browser suites, and Long Suite 100;
- EN/RU `after_pass` evidence for every assigned state and viewport.

The shared manifest, requirement registry, compatibility inventory, visual matrix, and catalog-driven test discovery all carry Three Card Poker on current main.
