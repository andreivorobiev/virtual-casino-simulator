# Let It Ride Integration Record For #77

Issue #134 is promoted through the single-owner #77 lane into the canonical catalog, compatibility, requirements, visual, central-test, and long-suite surfaces.

## Canonical Module Descriptor

The canonical descriptor lives at `modules/let_it_ride.json`.

Key integrated values:

- Module id: `let_it_ride`
- Version: `1.0.0`
- Sort order: `280`
- Route: `/games/let_it_ride`
- Backend registration: `casino.games.let_it_ride.api:register`
- Frontend export: `LetItRideGame`
- Ready selector: `[data-testid='let-it-ride']`
- Contract: `contracts/openapi/let_it_ride.v1.yaml`

## Permanent Requirements

Issue #77 allocates and validates:

- `LIR-001`: Let It Ride deals three player cards plus two community cards and supports two ride-or-pull decision beats before final poker evaluation.
- `LIR-002`: Additive v1 routes resolve only the authenticated player and keep active or recent rounds reload-safe.
- `LIR-003`: Opening wager, pull refunds, and final returned credits are ledger-only and exactly-once under stable action IDs.
- `LIR-004`: Complete EN/RU visible and accessible copy remains responsive and timer-clean at every required viewport.
- `LIR-005`: Catalog, contract, browser, long-suite, requirement, module, version, and visual evidence are traceable after shared integration.

## Visual Matrix Row

The `let_it_ride` surface at route `/games/let_it_ride` uses selector `[data-testid='let-it-ride']` and states:

- `ready`
- `first_decision`
- `second_decision`
- `settled`
- `route_restored`

Required locales are `en-US` and `ru-RU`. Required viewports are `desktop_primary`, `desktop_compact`, `tablet`, and `mobile`. Apply `VIS-COPY-001`, `VIS-TOKEN-002`, `VIS-LAYOUT-001`, `VIS-LAYOUT-002`, `VIS-LAYOUT-003`, `VIS-SCROLL-001`, `VIS-SCROLL-002`, `VIS-HIERARCHY-001`, `VIS-RESPONSIVE-001`, `VIS-EVIDENCE-001`, and `VIS-CATALOG-001`.

Real-backend `after-pass` evidence covers ready, first decision, second decision, settled, reduced-motion, and route-restored states in both locales across the allocated viewports.

## Shared-Ledger Follow-Up

Prepared player state, ledger action scanning, and a process lock protect the supported local one-process server. A future multi-process deployment still needs a storage-provider idempotency key enforced in the same transaction as balance and ledger insertion. The adapter supplies `details.let_it_ride_action_id` so shared storage can promote that value without changing the game contract.
