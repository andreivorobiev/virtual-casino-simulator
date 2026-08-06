# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-08-06T01:35:00Z.

## Current branch / active Codex work

- Protected main is exact Autoplay merge `b1c143b9821a13c8825d89a11b3511c907303180`, with ordered parents accepted viewport merge `a8f3351bba1401bf039d9bdbba2326bdefb5a88e` then accepted #608 head `86fc1c34503dd1d349d26221e731b73d53015a4f` and tree `c8cd0acc3e20092b0bf9132d0805012b4a1b6e19`.
- Local-only `codex/release-v0.9.5.56` prepares the repository-standard release packet from exact protected main.
- Normal PR #609 is the viewport/action-stability integration and normal PR #608 is the subsequent Autoplay recovery integration; neither issue content is imported a second time.

## Accepted scope and requirements

- PR #609 resolves issue #607 across viewport containment, layout telemetry, same-route scroll/focus stability, and permanent Browser coverage; PR #608 resolves issue #555 through phase-safe temporary-rate-limit recovery without replaying completed game actions.
- Requirements total exactly 904 unique rows after permanent additions `UX-026`, `UX-027`, `TEST-154`, and `TEST-155` plus amendments to `AUTO-015` and `TEST-153`; this release allocates no requirement or Browser identifier.
- The canonical package inventory is exactly 733 regular files; tests and the pull-request validator remain intentionally excluded from deployable archives.

## Version and contract allocation

- Release versions advance only to package `0.9.5.56`, application `9.57.1`, contracts `1.54.9`, tests `1.68.1`, and docs `1.66.1`; tooling remains `1.25.1`.
- Content-owned Autoplay and game-module versions, Core, Admin, and every other manifest entry remain exact protected-main values.
- The compatibility record retains exact terminal-green v0.9.5.55 source `21efda5b6c8dbce52ad846c1ea4a202ec6551fb2`, archive SHA-256 `c483d1f16160044c21a2bd750cc53eb465a730af9ec8d884c23681acdf3244b8`, and manifest SHA-256 `595e52b01a9c690a7fb1711a603b8a2fd33b0c2a50d6f9da1760fc2de3cecdea` as the rollback predecessor.

## Rollback, validation, and handback

- Rollback remains application-only at exact schema 2; database rollback is prohibited outside `TOOL-003`. The migration catalog remains minimum 2 / expected 3 / apply held; no migration changes.
- The mutable packet is restricted to the standard twenty-six release-owned paths with new `contracts/compatibility/app-0.9.5.56.json`; the canonical package inventory is exactly 733 regular files.
- Local validation is browser-free: release and predecessor fixtures, requirements, versions, generated docs, contracts, boundaries, catalog, rules, terminology, density, bootstrap, storage/recovery, and diff hygiene.
- Issues #607 and #555 were resolved by normal content PRs #609 and #608. No commit, push, PR, workflow action, tag, publication, deployment, or production action is claimed by this mutable preparation.
