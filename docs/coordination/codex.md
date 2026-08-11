# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-08-11T13:06:25Z.

## Current branch / active Codex work

- Protected main is exact secure mobile core merge `9a1dbec69995f6292b882ff75c9cfbd6aeb891db`, following terminal-green v0.9.5.73 source `bb3664fdc410115480d980c2470a1091173a9ce1`.
- Isolated branch `codex/release-v0.9.5.74` prepares the repository-standard release packet from exact protected main.
- Normal PR #680 closed repository-controlled issue #681 and progresses umbrella issue #183; the remaining queue continues after terminal v0.9.5.74 deployment.

## Accepted scope and requirements

- PR #680 adds a default-off native OS transport with vault-bound bearer and CSRF, exact session lifecycle, governed deep-link, and deterministic cross-host mobile build boundaries while preserving browser/PWA behavior.
- Native OAuth handoff, signed-device, verified-link, store, and physical-device evidence remain explicitly pending under issues #183, #184, #185, and #195.
- Requirements total exactly 952 after permanent `CORE-032`, `AUTH-019`, `SEC-016`, `SESSION-013`, and `TEST-172`; no release requirement identifier is allocated.

## Version and contract allocation

- Release versions advance only to package `0.9.5.74`, application `9.64.1`, contracts `1.61.1`, tests `1.79.1`, and docs `1.76.1`; tooling remains content-owned `1.30.0`.
- Core remains content-owned `9.42.0`, Mobile remains `1.0.0` with package `0.2.0`, Players remains `9.1.2`, Ledger remains `9.1.2`, and every game revision remains exact protected-main values.
- The compatibility record retains exact terminal-green v0.9.5.73 source `bb3664fdc410115480d980c2470a1091173a9ce1`, archive SHA-256 `951d871df8eb6b5896714b62d7841f9b0a79416a080b08f86f6aa7e156627cc8`, and manifest SHA-256 `84467f62e4178f586567e16207ef295df05f6cb81c265491d0dff89c0b4b62c4`.

## Rollback, validation, and handback

- Rollback remains application-only at exact schema 2; database rollback is prohibited outside `TOOL-003`. The migration catalog remains minimum 2 / expected 3 / apply held.
- The canonical deployable inventory is exactly 759 regular files: terminal v0.9.5.73 inventory 756 plus the packaged mobile client security contract, mobile module descriptor, and this compatibility record.
- Local validation is browser-free; fresh hosted all-nine evidence remains mandatory before normal merge and immutable publication.
- No live mail, OAuth, or provider traffic, provider-console change, public-signup activation, public-policy activation, public launch, database migration, runtime topology change, game behavior, settlement semantics, paytable, or wagering-economics change is claimed.
