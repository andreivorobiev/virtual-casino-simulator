# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-08-10T14:45:00Z.

## Current branch / active Codex work

- Protected main is exact descriptor-enforcement merge `74124efada105763afd5cd1cf015627bdd8333e8`, following terminal-green v0.9.5.62 source `3967dab1419bcc8ebfd7c8584a4bb9baa4665b34`.
- Isolated branch `codex/release-v0.9.5.63` prepares the repository-standard release packet from exact protected main.
- Normal PR #649 is the sole post-v0.9.5.62 content integration for issue #433; no issue content is imported a second time.

## Accepted scope and requirements

- PR #649 mounts descriptor-owned settings coercion centrally, retires duplicated per-game rule domains, repairs poisoned persisted rules to engine defaults, and generates OpenAPI request schemas plus authority-matrix bounded fields from the same descriptors.
- Requirements total exactly 931 unique rows after allocating only `TEST-163`; existing `SEC-002`, `SEC-004`, and `SEC-014` are amended rather than duplicated.
- The canonical package inventory is exactly 743 regular files; repository documentation, tests, and engineering audit scripts remain intentionally excluded from deployable archives.

## Version and contract allocation

- Release versions advance only to package `0.9.5.63`, application `9.59.4`, contracts `1.57.1`, tests `1.72.1`, and docs `1.70.1`; tooling remains content-owned `1.27.0`.
- Content-owned Core `9.39.0`, Blackjack `9.1.10`, Baccarat `9.1.15`, Roulette `9.6.3`, and every other runtime/game revision remain exact protected-main values.
- The compatibility record retains exact terminal-green v0.9.5.62 source `3967dab1419bcc8ebfd7c8584a4bb9baa4665b34`, archive SHA-256 `0486a4da292c66615f4df37c6986c65bea36ccf75185c7de2223c0bb07ee2e98`, and manifest SHA-256 `47cfd70de9c25c8e0330971414c7559d64bb16d5e6998de8f8ecf209c4136f48` as the rollback predecessor.

## Rollback, validation, and handback

- Rollback remains application-only at exact schema 2; database rollback is prohibited outside `TOOL-003`. The migration catalog remains minimum 2 / expected 3 / apply held; no migration changes.
- The mutable packet is restricted to the standard twenty-six release-owned paths with new `contracts/compatibility/app-0.9.5.63.json`; the canonical package inventory is exactly 743 regular files.
- Local validation is browser-free: release and predecessor fixtures, requirements, versions, generated docs, contracts, boundaries, catalog, rules, density, bootstrap, storage/recovery, and diff hygiene.
- Issue #433 was resolved by normal content PR #649. Broader portfolio tickets remain open unless their complete acceptance or external evidence is separately proven. No tag, publication, deployment, or production action is claimed by this mutable preparation.
