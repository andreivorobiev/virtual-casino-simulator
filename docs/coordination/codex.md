# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-08-06T03:45:00Z.

## Current branch / active Codex work

- Protected main is exact P0 containment merge `a0772367e082d5017286e65884ab82d6d90a321c`, with ordered parents terminal v0.9.5.56 source `21ad8562c7d0f19fef6aae16b6a7fba751de0b25` then accepted #612 head `125c7098887b2ab3e24f24f37ca00ec4d30c0ef2` and tree `012b622445e6493e52be180b744f7517fa350dae`.
- Local-only `codex/release-v0.9.5.57` prepares the repository-standard release packet from exact protected main.
- Normal PR #612 is the sole content integration for issue #611; no issue content is imported a second time.

## Accepted scope and requirements

- PR #612 resolves P0 issue #611 by fitting complete Roulette and Bingo desktop boards above the fixed footer while retaining designed tablet/mobile scrolling.
- Requirements total exactly 904 unique rows; amended `UX-026` and `TEST-154` govern the accepted behavior and this release allocates no requirement or Browser identifier.
- The canonical package inventory is exactly 734 regular files; tests and the pull-request validator remain intentionally excluded from deployable archives.

## Version and contract allocation

- Release versions advance only to package `0.9.5.57`, application `9.57.2`, contracts `1.54.10`, tests `1.68.3`, and docs `1.66.3`; tooling remains `1.25.1`.
- Content-owned Roulette `9.6.1`, Bingo `9.3.5`, and every other manifest entry remain exact protected-main values.
- The compatibility record retains exact terminal-green v0.9.5.56 source `21ad8562c7d0f19fef6aae16b6a7fba751de0b25`, archive SHA-256 `702555aea3dc7031be9f92ab889b4eee6b0eb87cbd86a3547d887ffd65db1c36`, and manifest SHA-256 `a4af7c0f5bee1f7364d7b85f1b3eb51285309e30b8c48432fc7d1f28d38ff4e8` as the rollback predecessor.

## Rollback, validation, and handback

- Rollback remains application-only at exact schema 2; database rollback is prohibited outside `TOOL-003`. The migration catalog remains minimum 2 / expected 3 / apply held; no migration changes.
- The mutable packet is restricted to the standard twenty-six release-owned paths with new `contracts/compatibility/app-0.9.5.57.json`; the canonical package inventory is exactly 734 regular files.
- Local validation is browser-free: release and predecessor fixtures, requirements, versions, generated docs, contracts, boundaries, catalog, rules, terminology, density, bootstrap, storage/recovery, and diff hygiene.
- Issue #611 was resolved by normal content PR #612. No commit, push, PR, workflow action, tag, publication, deployment, or production action is claimed by this mutable preparation.
