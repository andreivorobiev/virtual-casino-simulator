# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-08-10T18:05:00Z.

## Current branch / active Codex work

- Protected main is exact compact-projection merge `e6206a697deba2e3163c011287d2cf99d2395553`, following terminal-green v0.9.5.65 source `dd0c884625afa96bde621ae4e9f78759d1639ee9`.
- Isolated branch `codex/release-v0.9.5.66` prepares the repository-standard release packet from exact protected main.
- Normal PR #659 is the sole post-v0.9.5.65 content integration; it closed bounded issue #660 while parent #323 remains open for production latency acceptance.

## Accepted scope and requirements

- PR #659 adds opt-in compact shell and Roulette play projections, preserves complete legacy responses by default, and reuses one immutable Roulette catalog per wheel mode.
- Requirements total exactly 935 unique rows after allocating only `TEST-166`; no release identifier is allocated.
- The canonical package inventory is exactly 746 regular files; repository documentation, tests, requirement sources, and engineering audit scripts remain intentionally excluded from deployable archives.

## Version and contract allocation

- Release versions advance only to package `0.9.5.66`, application `9.59.8`, contracts `1.57.5`, tests `1.72.7`, and docs `1.70.7`; tooling remains content-owned `1.27.1`.
- Core remains content-owned `9.39.2` and Roulette remains content-owned `9.6.4`; every other runtime and game revision remains exact protected-main values.
- The compatibility record retains exact terminal-green v0.9.5.65 source `dd0c884625afa96bde621ae4e9f78759d1639ee9`, archive SHA-256 `bdaf08ad767e014a0a4b03a4f5db36daf8e88513f38268a26f5618b1c53ec169`, and manifest SHA-256 `fa0a4e7c44faca7c5fefb11d30b9f94077630c0853bf8b587b5e74d2aec2251b` as the rollback predecessor.

## Rollback, validation, and handback

- Rollback remains application-only at exact schema 2; database rollback is prohibited outside `TOOL-003`. The migration catalog remains minimum 2 / expected 3 / apply held; no migration changes.
- The mutable packet is restricted to release-owned paths and new `contracts/compatibility/app-0.9.5.66.json`; the canonical package inventory is exactly 746 regular files.
- Local validation is browser-free: release and predecessor fixtures, requirements, versions, generated docs, contracts, boundaries, catalog, rules, density, bootstrap, and diff hygiene.
- Bounded issue #660 was resolved by normal content PR #659. Parent #323 and broader portfolio tickets remain open unless their complete acceptance or external evidence is separately proven. No tag, publication, deployment, or production action is claimed by this mutable preparation.
