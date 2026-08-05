# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-08-05T02:44:00Z.

## Current branch / active Codex work

- Protected main is exact complete-bug merge `59d7db2c5ca0ed1ef15a577df1f6dbccf134ddce`, with ordered parents terminal v0.9.5.54 main `3d96093ae524db56807f5a8fe89ead13f39a2672` then accepted #605 content head `44eb786d92ffae22964a0abcd566f2617e99d64f` and tree `0865dbfa00cd1979e43fcedf110afe04bd8714e2`.
- Local-only `codex/release-v0.9.5.55` prepares the repository-standard release packet from exact protected main.
- PR #605 is the sole current-main content integration for this release; no issue or contributor content is imported a second time.

## Accepted scope and requirements

- Sole content PR #605 resolves issues #421, #557, and #575 through #579 across wallet ordering, localized API errors, Bingo autoplay/reset, PWA activation, Russian token terminology, accessibility, and Roulette precision geometry.
- Requirements total exactly 900 unique rows after permanent additions `TOKEN-007`, `I18N-011`, `AUTO-015`, `BINGO-027`, `PWA-003`, `UX-025`, `TOOL-012`, and `TEST-153`; this release allocates no requirement or Browser identifier.
- The canonical package inventory is exactly 732 regular files; tests and the pull-request validator remain intentionally excluded from deployable archives.

## Version and contract allocation

- Release versions advance only to package `0.9.5.55`, application `9.56.13`, contracts `1.54.8`, tests `1.67.10`, and docs `1.65.10`; tooling remains `1.25.1`.
- Core, Admin, all game modules, and every other manifest entry remain exact protected-main values.
- The compatibility record retains exact terminal-green v0.9.5.54 source `3d96093ae524db56807f5a8fe89ead13f39a2672`, archive SHA-256 `609de8cc1f9d321ab59846f2db510ef8d4d6db1132e46c4f2e8c0fabbe102271`, and manifest SHA-256 `298d64e8d689126d3f8453fce7da8c796e651149f1719eda0a9720d783014e72` as the rollback predecessor.

## Rollback, validation, and handback

- Rollback remains application-only at exact schema 2; database rollback is prohibited outside `TOOL-003`. The migration catalog remains minimum 2 / expected 3 / apply held; no migration changes.
- The mutable packet is restricted to the standard twenty-six release-owned paths with new `contracts/compatibility/app-0.9.5.55.json`; the canonical package inventory is exactly 732 regular files.
- Local validation is browser-free: release and predecessor fixtures, requirements, versions, generated docs, contracts, boundaries, catalog, rules, terminology, density, bootstrap, storage/recovery, and diff hygiene.
- Issues #421, #557, and #575 through #579 were resolved by sole content PR #605. No commit, push, PR, workflow action, tag, publication, deployment, or production action is claimed by this mutable preparation.
