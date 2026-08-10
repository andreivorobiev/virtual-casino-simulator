# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-08-10T16:30:00Z.

## Current branch / active Codex work

- Protected main is exact governance-shards merge `17907c9e07460c999e74262973f56df438936793`, following terminal-green v0.9.5.64 source `2ce7678cff80c21897ced419a54f3ff98305a261`.
- Isolated branch `codex/release-v0.9.5.65` prepares the repository-standard release packet from exact protected main.
- Normal PR #656 is the sole post-v0.9.5.64 content integration for issue #434; no issue content is imported a second time.

## Accepted scope and requirements

- PR #656 makes the governed requirement aggregate generated from one non-game spine plus 46 descriptor-owned game shards, adds a fail-closed assembler, and runs browser-free Python game suites through one shared mapped API case.
- Requirements total exactly 934 unique rows after allocating only `TEST-165` and expanding `TEST-161`; no release identifier is allocated.
- The canonical package inventory is exactly 745 regular files; repository documentation, tests, requirement sources, and engineering audit scripts remain intentionally excluded from deployable archives.

## Version and contract allocation

- Release versions advance only to package `0.9.5.65`, application `9.59.6`, contracts `1.57.3`, tests `1.72.5`, and docs `1.70.5`; tooling remains content-owned `1.27.1`.
- Every runtime and game revision remains exact protected-main values.
- The compatibility record retains exact terminal-green v0.9.5.64 source `2ce7678cff80c21897ced419a54f3ff98305a261`, archive SHA-256 `7b68afe58d0e76e7be99e429b025af4395c0919cbf69d40d3618a02d49929f0d`, and manifest SHA-256 `d80300664cd6c2cf05800d1f2ef861b6758baa76f736cabe30aa4da3192cb00c` as the rollback predecessor.

## Rollback, validation, and handback

- Rollback remains application-only at exact schema 2; database rollback is prohibited outside `TOOL-003`. The migration catalog remains minimum 2 / expected 3 / apply held; no migration changes.
- The mutable packet is restricted to the normal release-owned paths plus the new governed requirements spine source and new `contracts/compatibility/app-0.9.5.65.json`; the canonical package inventory is exactly 745 regular files.
- Local validation is browser-free: release and predecessor fixtures, requirement assembly, requirements, versions, generated docs, contracts, boundaries, catalog, rules, density, bootstrap, and diff hygiene.
- Issue #434 was resolved by normal content PR #656. Broader portfolio tickets remain open unless their complete acceptance or external evidence is separately proven. No tag, publication, deployment, or production action is claimed by this mutable preparation.
