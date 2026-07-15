# Issue #132 Shared Integration Evidence

Integration owner: #77

Game: Caribbean Stud

## Integrated Slice

- Distinct/countable game proof for Caribbean Stud.
- Game-local backend package with pure engine, service, and route registration adapter.
- Session-bound state and exactly-once ledger movements for ante, call, and settlement.
- Fold decision that forfeits ante without revealing dealer hole cards.
- Game-local frontend module, EN/RU resources, and focused static UI checks.
- Frozen additive OpenAPI v1 contract with compatibility digest and matrix ownership.
- Canonical `modules/caribbean_stud.json` descriptor at sort order 270.
- Permanent requirements `CS-001` through `CS-005`, generated documentation, visual matrix row, central API/browser/restart coverage, and catalog-discovered Long Suite driver.

## Shared Integration Boundary

Issue #77 promotes only the Caribbean Stud catalog, manifest, requirements, compatibility, visual, test-discovery, version, and documentation surfaces required for acceptance. Deployment, auth, OCI, other games, and the held Texas Hold'em draft remain untouched.

## Evidence Classification

Acceptance evidence is `after_pass` only when produced by the exact integrated head through the real authenticated backend at the four governed viewports in both English and Russian.
