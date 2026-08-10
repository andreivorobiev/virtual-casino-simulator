# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-08-10T06:26:07Z.

## Current branch / active Codex work

- Protected main is exact account/Admin merge `97d6646081fcb5d6bfd7c93892841322da0d31a9`, with ordered parents terminal v0.9.5.59 source `339de540f632c5b2897213b0223e4aa415171c9b` then accepted #638 head `c8f78c73388c80b059a0be9208225d53a2b4d867`.
- Local-only `codex/release-v0.9.5.60` prepares the repository-standard release packet from exact protected main.
- Normal PR #638 is the sole content integration for issues #334, #351, #352, #378, and #388; no issue content is imported a second time.

## Accepted scope and requirements

- PR #638 completes recovery challenges, owner-role safeguards, personal settings, guest conversion readiness, and owner-controlled session policy while preserving restricted-preview enrollment and provider latches.
- Requirements total exactly 924 unique rows after thirteen accepted additions; this release allocates no requirement or Browser identifier.
- The canonical package inventory is exactly 740 regular files; repository documentation, tests, and the pull-request validator remain intentionally excluded from deployable archives.

## Version and contract allocation

- Release versions advance only to package `0.9.5.60`, application `9.59.1`, contracts `1.56.1`, tests `1.70.1`, and docs `1.68.1`; tooling remains `1.25.3`.
- Content-owned Core `9.38.0`, Admin `1.17.0`, Audio `9.1.3`, Ledger `9.1.1`, and every other manifest entry remain exact protected-main values.
- The compatibility record retains exact terminal-green v0.9.5.59 source `339de540f632c5b2897213b0223e4aa415171c9b`, archive SHA-256 `23b30f5ea72d92e4125be4545bb1e2b9a868c14fc71b67a90cb7662255b2e673`, and manifest SHA-256 `e35b0e70e4ae173e03fa74408843e8cd5cf1cd96ec96c3c8008a7fdceb1b7ff3` as the rollback predecessor.

## Rollback, validation, and handback

- Rollback remains application-only at exact schema 2; database rollback is prohibited outside `TOOL-003`. The migration catalog remains minimum 2 / expected 3 / apply held; no migration changes.
- The mutable packet is restricted to the standard twenty-six release-owned paths with new `contracts/compatibility/app-0.9.5.60.json`; the canonical package inventory is exactly 740 regular files.
- Local validation is browser-free: release and predecessor fixtures, requirements, versions, generated docs, contracts, boundaries, catalog, rules, terminology, density, bootstrap, storage/recovery, and diff hygiene.
- Issues #334, #351, #352, #378, and #388 were resolved by normal content PR #638. No commit, push, PR, workflow action, tag, publication, deployment, or production action is claimed by this mutable preparation.
