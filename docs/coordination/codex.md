# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-08-10T10:15:00Z.

## Current branch / active Codex work

- Protected main is exact portfolio-gate merge `81dc97733a64b1f044c65c56a2ce6c4171420169`, following persistent-memory merge `ae708003ff8894fbe181174a9c97f5bf8bebf33c` and terminal v0.9.5.60 source `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`.
- Local-only `codex/release-v0.9.5.61` prepares the repository-standard release packet from exact protected main.
- Normal PRs #640 and #642 are the sole post-v0.9.5.60 content integrations for bounded issues #641 and #643; no issue content is imported a second time.

## Accepted scope and requirements

- PR #640 adds governance-first persistent agent memory and a fail-closed provenance validator; PR #642 adds source-bound payload, multiprocess-safety, and game-suite-discovery gates.
- Requirements total exactly 928 unique rows after accepted additions `TOOL-013`, `TEST-159`, `TEST-160`, and `TEST-161`; this release allocates no requirement or Browser identifier.
- The canonical package inventory is exactly 741 regular files; repository agent memory, documentation, tests, and engineering audit scripts remain intentionally excluded from deployable archives.

## Version and contract allocation

- Release versions advance only to package `0.9.5.61`, application `9.59.2`, contracts `1.56.2`, tests `1.71.1`, and docs `1.69.1`; tooling remains content-owned `1.26.0`.
- Content-owned Core `9.38.0`, Admin `1.17.0`, Audio `9.1.3`, Ledger `9.1.1`, and every runtime/game manifest entry remain exact protected-main values.
- The compatibility record retains exact terminal-green v0.9.5.60 source `b6d31cdbf980765dcb24b7dbe21bffb8c5034ed0`, archive SHA-256 `b64d2e081f9a3d0ccd08eeb80aba19a919dce00376dd0758201ee181718db118`, and manifest SHA-256 `15c9e75165ffc05b7e94f1f1ba34fbf16f770e9783f3f8e32ae29ed9293e307b` as the rollback predecessor.

## Rollback, validation, and handback

- Rollback remains application-only at exact schema 2; database rollback is prohibited outside `TOOL-003`. The migration catalog remains minimum 2 / expected 3 / apply held; no migration changes.
- The mutable packet is restricted to the standard twenty-six release-owned paths with new `contracts/compatibility/app-0.9.5.61.json`; the canonical package inventory is exactly 741 regular files.
- Local validation is browser-free: release and predecessor fixtures, requirements, versions, generated docs, contracts, boundaries, catalog, rules, terminology, density, bootstrap, storage/recovery, and diff hygiene.
- Bounded issues #641 and #643 were resolved by normal content PRs #640 and #642. Broader selected portfolio tickets remain open unless their complete acceptance or external evidence is separately proven. No commit, push, PR, workflow action, tag, publication, deployment, or production action is claimed by this mutable preparation.
