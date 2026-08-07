# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-08-07T06:35:00Z.

## Current branch / active Codex work

- Protected main is exact play-policy merge `cdbb08fb1c37fb92640f2a7661ededa68e1cb029`, with ordered parents terminal v0.9.5.57 source `80b58cbf5e7c562e01a942e856052228fa8fadbe` then accepted #615 head `e22a1ada121e0f0a1773c882573b98daad0aea84` and tree `538f8aad42e24e4eb00881f16162219689515686`.
- Local-only `codex/release-v0.9.5.58` prepares the repository-standard release packet from exact protected main.
- Normal PR #615 is the sole content integration for issues #614, #616, #617, #618, and #619; no issue content is imported a second time.

## Accepted scope and requirements

- PR #615 resolves owner-configurable request policy, same-route scroll/focus stability, fixed 10,000-token guest trials with owner-controlled admission, and silent fresh/fallback audio with explicit owner override.
- Requirements total exactly 908 unique rows after accepted additions `AUDIO-010`, `SEC-015`, `ADMIN-032`, and `TEST-156`; this release allocates no requirement or Browser identifier.
- The canonical package inventory is exactly 737 regular files; tests and the pull-request validator remain intentionally excluded from deployable archives.

## Version and contract allocation

- Release versions advance only to package `0.9.5.58`, application `9.58.1`, contracts `1.55.1`, tests `1.69.2`, and docs `1.67.2`; tooling remains `1.25.1`.
- Content-owned Core `9.37.0`, Admin `1.16.0`, Audio `9.1.2`, and every other manifest entry remain exact protected-main values.
- The compatibility record retains exact terminal-green v0.9.5.57 source `80b58cbf5e7c562e01a942e856052228fa8fadbe`, archive SHA-256 `eda0bf1432691761da7deba58973af5db1b4c765fb0cb9c9e115d1f3b4479642`, and manifest SHA-256 `862907f5a6b8cd3b8d6bcd096a81ff7e24eaa3660572b6b2d38012c514fd6e95` as the rollback predecessor.

## Rollback, validation, and handback

- Rollback remains application-only at exact schema 2; database rollback is prohibited outside `TOOL-003`. The migration catalog remains minimum 2 / expected 3 / apply held; no migration changes.
- The mutable packet is restricted to the standard twenty-six release-owned paths with new `contracts/compatibility/app-0.9.5.58.json`; the canonical package inventory is exactly 737 regular files.
- Local validation is browser-free: release and predecessor fixtures, requirements, versions, generated docs, contracts, boundaries, catalog, rules, terminology, density, bootstrap, storage/recovery, and diff hygiene.
- Issues #614, #616, #617, #618, and #619 were resolved by normal content PR #615. No commit, push, PR, workflow action, tag, publication, deployment, or production action is claimed by this mutable preparation.
