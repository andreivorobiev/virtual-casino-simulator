# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-08-10T23:31:14Z.

## Current branch / active Codex work

- Protected main is exact action-journal merge `5d39f47ab61aa8b28001120f9fbc0f3f773f8408`, following terminal-green v0.9.5.68 source `697de74129758c91b2f4748d596a2bec2b0f79e0`.
- Isolated branch `codex/release-v0.9.5.69` prepares the repository-standard release packet from exact protected main.
- Normal PR #669 closed repository-controlled issue #432; the remaining queue is being re-audited against the deployed v0.9.5.69 baseline.

## Accepted scope and requirements

- PR #669 replaces per-action whole-history JSON action snapshot rewrites with one append-only commit and one projection marker while retaining legacy snapshot readability.
- Cross-process tails, pending-only crash recovery, indexed projection lookup, fail-closed corruption handling, and bounded periodic compaction preserve exactly-once settlement behavior.
- Requirements total exactly 942 after permanent `LEDGER-034` and `TEST-169`; no release identifier is allocated.

## Version and contract allocation

- Release versions advance only to package `0.9.5.69`, application `9.61.2`, contracts `1.59.2`, tests `1.74.3`, and docs `1.72.3`; tooling remains content-owned `1.28.0`.
- Core remains content-owned `9.40.1` and Ledger remains content-owned `9.1.2`; every game revision remains exact protected-main values.
- The compatibility record retains exact terminal-green v0.9.5.68 source `697de74129758c91b2f4748d596a2bec2b0f79e0`, archive SHA-256 `94c66cd5a175e3781f351aa9de506239e741596e602d5d82dd8f7ad6dc6aa0ad`, and manifest SHA-256 `4b33e043d13080e644c454ae6d9689939d813fc158956a4849d39295a85ad0ed`.

## Rollback, validation, and handback

- Rollback remains application-only at exact schema 2; database rollback is prohibited outside `TOOL-003`. The migration catalog remains minimum 2 / expected 3 / apply held.
- The canonical deployable inventory is exactly 751 regular files: terminal v0.9.5.68 inventory 750 plus this compatibility record.
- Local validation is browser-free; fresh hosted all-nine evidence remains mandatory before normal merge and immutable publication.
- No provider traffic, provider-console change, public-policy activation, public launch, database migration, game, settlement semantics, paytable, or wagering-economics change is claimed.
