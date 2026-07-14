# Let It Ride Integration Record For #77

Issue #134 parks this descriptor outside `modules/` until #77 owns shared integration. The isolated worker does not edit shared catalog, router, shell, aggregate manifest, permanent requirements, compatibility matrices, visual matrix, central test discovery, or long-suite registry.

## Proposed Module Descriptor

The proposal lives at `codex/tasks/artifacts/issue-134-let-it-ride/let_it_ride.module.proposal.json`.

Key proposed values:

- Module id: `let_it_ride`
- Version: `0.1.0-proposal`
- Route: `/games/let_it_ride`
- Backend registration: `casino.games.let_it_ride.api:register`
- Frontend export: `LetItRideGame`
- Ready selector: `[data-testid='let-it-ride']`
- Contract: `contracts/openapi/let_it_ride.v1.yaml`

## Proposed Requirements

Permanent requirement IDs are intentionally not allocated in this isolated slice. Proposed allocation for #77 or the central requirements owner:

- `LIR-001`: Let It Ride deals three player cards plus two community cards and supports two ride-or-pull decision beats before final poker evaluation.
- `LIR-002`: Additive v1 routes resolve only the authenticated player and keep active or recent rounds reload-safe.
- `LIR-003`: Opening wager, pull refunds, and final returned credits are ledger-only and exactly-once under stable action IDs.
- `LIR-004`: Complete EN/RU visible and accessible copy remains responsive and timer-clean at every required viewport.
- `LIR-005`: Catalog, contract, browser, long-suite, requirement, module, version, and visual evidence are traceable after shared integration.

## Proposed Visual Matrix Row

Add a `let_it_ride` surface at route `/games/let_it_ride` with selector `[data-testid='let-it-ride']` and states:

- `ready`
- `first_decision`
- `second_decision`
- `settled`
- `route_restored`

Required locales are `en-US` and `ru-RU`. Required viewports are `desktop_primary`, `desktop_compact`, `tablet`, and `mobile`. Apply `VIS-COPY-001`, `VIS-TOKEN-002`, `VIS-LAYOUT-001`, `VIS-LAYOUT-002`, `VIS-LAYOUT-003`, `VIS-SCROLL-001`, `VIS-SCROLL-002`, `VIS-HIERARCHY-001`, `VIS-RESPONSIVE-001`, `VIS-EVIDENCE-001`, and `VIS-CATALOG-001`.

After shared registration, capture real-backend `after_pass` evidence for ready, first decision, second decision, settled, and route-restored states in both locales across the allocated viewports. This isolated worker evidence record deliberately makes no count-acceptance or visual-matrix acceptance claim before #77 integrates the route.

## Shared-Ledger Follow-Up

Prepared player state, ledger action scanning, and a process lock protect the supported local one-process server. A future multi-process deployment still needs a storage-provider idempotency key enforced in the same transaction as balance and ledger insertion. The adapter supplies `details.let_it_ride_action_id` so shared storage can promote that value without changing the game contract.
