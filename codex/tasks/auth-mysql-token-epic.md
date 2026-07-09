# Auth, Multi-User, MySQL, Licensing, and Token Model Epic

## Task

- Issue: https://github.com/andreivorobiev/virtual-casino-simulator/issues/34
- Branch: codex/auth-mysql-token-coordination
- Coordinator chat: Casino Simulator - Coordinator

## Goal

- Goal: Coordinate the approved foundation work for authenticated multi-user play, MySQL-capable storage, private user sessions, toy-simulator licensing, and product-wide play-token terminology.
- Non-goals: Do not implement gameplay rule changes, real-money behavior, external identity providers, or public self-signup in this epic.
- User-visible behavior expected: The final merged work requires login, uses play tokens marked with `◈`, clearly states this is a toy simulator and not a gambling site, and keeps each user's state isolated.

## Workstream Issues

- #35: Requirements, contracts, and coordination packets.
- #36: Apache-2.0 licensing and private beta toy-simulator terms.
- #37: Token terminology and validator.
- #38: JSON provider abstraction and MySQL schema.
- #39: Auth backend, sessions, bootstrap admin, and current-user APIs.
- #40: Frontend login gate, terms acceptance, and current-user shell.
- #41: Admin user management, terms status, and locale controls.
- #42: Private per-user game state and game API adaptation.
- #43: Integration validation and copied-deployment long suite.

## Coordination Rules

- Start each worker from this coordination branch unless the coordinator supplies a newer stacked base.
- Each worker creates its own `codex/...` branch and PR.
- If two workers need the same file, stop and report the conflict before editing.
- Keep `/api/v1` compatible unless a task explicitly scopes a compatibility shim or `/api/v2` route.
- Preserve ledger balance mutation through `casino/core/ledger.py`.
- Runtime test runs must happen from copied deployment environments, not directly from the source tree.

## Acceptance

- All child PRs reference #34 and their child issue.
- Requirement IDs, contracts, module versions, tests, and docs are aligned.
- Mandatory long suite 100 passes from a copied deployment environment.
- Coordinator asks before optional suite 300 or 500.

## Durable Requirement/Contract References

- Requirements foundation: AUTH-001 through AUTH-005, SESSION-001 through SESSION-004, USER-001 through USER-005, STORAGE-001 through STORAGE-004, MYSQL-001 through MYSQL-004, TERMS-001 through TERMS-004, LIC-001 through LIC-003, TOKEN-001 through TOKEN-004, API-001 through API-002, and TEST-037 through TEST-040.
- v2 contract foundation: `contracts/openapi/auth.v2.yaml` and `contracts/openapi/admin-users.v2.yaml`.
- Compatibility metadata: `contracts/compatibility/auth-mysql-token-foundation.json`, `contracts/compatibility/module-api-matrix.json`, and `contracts/compatibility/contract-digests.json`.
