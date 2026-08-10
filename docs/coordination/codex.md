# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-08-10T12:05:00Z.

## Current branch / active Codex work

- Protected main is exact storage-integrity merge `21c1ba2b8e0925102b25bc0a3e73a900392d494d`, following terminal v0.9.5.61 source `8d3c253ed9073f5c1ff0e22001ee103de2de9cb5`.
- Local-only `codex/release-v0.9.5.62` prepares the repository-standard release packet from exact protected main.
- Normal PR #646 is the sole post-v0.9.5.61 content integration for issue #431; no issue content is imported a second time.

## Accepted scope and requirements

- PR #646 removes runtime whole-player-map writes in favor of explicit inserts and lock-correct, insert-missing-only bootstrap behavior for JSON and MySQL providers.
- Requirements total exactly 930 unique rows after accepted additions `STORAGE-012` and `TEST-162`; this release allocates no requirement or Browser identifier.
- The canonical package inventory is exactly 742 regular files; repository documentation, tests, and engineering audit scripts remain intentionally excluded from deployable archives.

## Version and contract allocation

- Release versions advance only to package `0.9.5.62`, application `9.59.3`, contracts `1.56.3`, tests `1.71.3`, and docs `1.69.3`; tooling remains content-owned `1.26.0`.
- Content-owned Core `9.38.1`, Players `9.1.1`, Admin `1.17.0`, Ledger `9.1.1`, and every runtime/game manifest entry remain exact protected-main values.
- The compatibility record retains exact terminal-green v0.9.5.61 source `8d3c253ed9073f5c1ff0e22001ee103de2de9cb5`, archive SHA-256 `59eb83cffd9f1a98b2edec04db25c8d14ec7e6f94b25f3037448679953e83572`, and manifest SHA-256 `2174de35bab21f4f6e5a599b3e222e1d365717f3cf9b2887926d182f1a5bc1a0` as the rollback predecessor.

## Rollback, validation, and handback

- Rollback remains application-only at exact schema 2; database rollback is prohibited outside `TOOL-003`. The migration catalog remains minimum 2 / expected 3 / apply held; no migration changes.
- The mutable packet is restricted to the standard twenty-six release-owned paths with new `contracts/compatibility/app-0.9.5.62.json`; the canonical package inventory is exactly 742 regular files.
- Local validation is browser-free: release and predecessor fixtures, requirements, versions, generated docs, contracts, boundaries, catalog, rules, terminology, density, bootstrap, storage/recovery, and diff hygiene.
- Issue #431 was resolved by normal content PR #646. Broader portfolio tickets remain open unless their complete acceptance or external evidence is separately proven. No commit, push, PR, workflow action, tag, publication, deployment, or production action is claimed by this mutable preparation.
