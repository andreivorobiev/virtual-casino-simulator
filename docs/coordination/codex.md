# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-08-04T18:55:55Z.

## Current branch / active Codex work

- Protected main is exact wallet-timing and API-documentation merge `9ac160b38a6550e67e9030d01f5c933f3dee9164`, with ordered parents terminal v0.9.5.52 main `cfc7b807aa0697c819b9d1a10d17b3a2e81a7bbc` then accepted #602 content head `2c8cc015607ee4240e24fa4a226b55801946db3c` and tree `66e81589cf73a97b14c12e58667957395498d268`.
- Local-only `codex/release-v0.9.5.53` prepares the repository-standard release packet from exact protected main.
- PR #602 is the sole current-main content integration for this release; no issue or contributor content is imported a second time.

## Accepted scope and requirements

- Sole content PR #602 makes the committed wager debit visible immediately across all eighteen delayed-result browser games and refreshes the authoritative settled balance after each reveal without changing game economics or ledger settlement.
- The same content PR adds a read-only same-origin `/api-docs` explorer for all 62 published OpenAPI contracts using the pinned official Swagger UI 5.32.6 distribution.
- Requirements total exactly 892 unique rows after permanent additions `LEDGER-031`, `TEST-151`, `API-003`, and `TEST-152`; this release allocates no requirement or Browser identifier.

## Version and contract allocation

- Release versions advance only to package `0.9.5.53`, application `9.56.10`, contracts `1.54.6`, tests `1.67.7`, and docs `1.65.7`; tooling remains `1.25.0`.
- Core, Admin, all game modules, and every other manifest entry remain exact protected-main values.
- The new compatibility record binds exact v0.9.5.52 source `cfc7b807aa0697c819b9d1a10d17b3a2e81a7bbc`, archive SHA-256 `896886acc6416830a48d45a464eff1a297b8d98216e8b1aedd014dada4391026`, and manifest SHA-256 `2ffa20d8c30a7be1fe8002c95a1127a14944ad3cb00a0d4b7c9d969eb964942c`.

## Rollback, validation, and handback

- Rollback remains application-only at exact schema 2; database rollback is prohibited outside `TOOL-003`. The migration catalog remains minimum 2 / expected 3 / apply held; no migration changes.
- The mutable packet is restricted to the standard twenty-six release-owned paths with new `contracts/compatibility/app-0.9.5.53.json`; the canonical package inventory is expected to contain 732 regular files.
- Local validation is browser-free: release and predecessor fixtures, requirements, versions, generated docs, contracts, boundaries, catalog, rules, terminology, density, bootstrap, storage/recovery, and diff hygiene.
- Issues #583 through #601 were resolved by sole content PR #602. No commit, push, PR, workflow action, tag, publication, deployment, or production action is claimed by this mutable preparation.
