# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-08-10T15:00:00Z.

## Current branch / active Codex work

- Protected main is exact provider-index bridge merge `06a12e5beb6bc2bfb2aeac28b040d6d544dff6d5`, following terminal-green v0.9.5.63 source `909b6ac1db8671a1087a8b466b23704fe2110878`.
- Isolated branch `codex/release-v0.9.5.64` prepares the repository-standard release packet from exact protected main.
- Normal PR #652 is the sole post-v0.9.5.63 content integration for bounded issue #653 and umbrella #432; no issue content is imported a second time.

## Accepted scope and requirements

- PR #652 exposes one provider-owned action lookup, routes settlement and Deuces Wild recovery through existing JSON and MySQL indexes, and removes million-row recovery scans without changing money semantics.
- Requirements total exactly 933 unique rows after allocating only `LEDGER-033` and `TEST-164`; no release identifier is allocated.
- The canonical package inventory is exactly 744 regular files; repository documentation, tests, and engineering audit scripts remain intentionally excluded from deployable archives.

## Version and contract allocation

- Release versions advance only to package `0.9.5.64`, application `9.59.5`, contracts `1.57.2`, tests `1.72.3`, and docs `1.70.3`; tooling remains content-owned `1.27.0`.
- Content-owned Core `9.39.1`, Ledger `9.1.2`, Deuces Wild `1.1.3`, and every other runtime/game revision remain exact protected-main values.
- The compatibility record retains exact terminal-green v0.9.5.63 source `909b6ac1db8671a1087a8b466b23704fe2110878`, archive SHA-256 `0ea2c50cdd4ba586ec5abcfbba6a4a8e824366642131a866388ae5cd8f40197e`, and manifest SHA-256 `306a3f583348421c47f62b5eadec2aab4f8c2badd17edd3c1992ffa6dd55617d` as the rollback predecessor.

## Rollback, validation, and handback

- Rollback remains application-only at exact schema 2; database rollback is prohibited outside `TOOL-003`. The migration catalog remains minimum 2 / expected 3 / apply held; no migration changes.
- The mutable packet is restricted to the standard twenty-six release-owned paths with new `contracts/compatibility/app-0.9.5.64.json`; the canonical package inventory is exactly 744 regular files.
- Local validation is browser-free: release and predecessor fixtures, requirements, versions, generated docs, contracts, boundaries, catalog, rules, density, bootstrap, storage/recovery, and diff hygiene.
- Bounded issue #653 was resolved by normal content PR #652. Umbrella #432 remains open for the later append-only JSON journal transition; broader portfolio tickets remain open unless their complete acceptance or external evidence is separately proven. No tag, publication, deployment, or production action is claimed by this mutable preparation.
