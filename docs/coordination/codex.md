# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-08-13T22:00:00Z.

## Current branch / active Codex work

- PR #736 supplies the repository-side pull-poller delivery prerequisite for #732; its exact merge source is rebound before publication.
- Isolated branch `codex/release-v0.9.5.77` prepares the repository-standard release packet from the accepted poller source.
- Release ticket #735 owns immutable v0.9.5.77 publication; parent #732 remains open for the owner-run host install and evidence.

## Accepted scope and requirements

- PR #736 packages one production-host pull poller plus systemd service and timer templates, durable alarms, immutable release verification, and an owner-run install and rollback-drill runbook.
- GitHub Actions retain immutable publication but no longer attempt the unreachable inbound SSH upload and activation leg; required status-context names remain exact.
- Requirements total exactly 965 after permanent `OPS-007`, `TOOL-015`, and `TEST-180`; no release requirement identifier is allocated.

## Version and contract allocation

- Release versions advance only to package `0.9.5.77`, application `9.67.1`, contracts `1.61.4`, tests `1.87.1`, and docs `1.83.1`; tooling remains content-owned `1.34.0`.
- Core remains content-owned `9.43.1`, Mobile remains `1.0.0` with package `0.2.0`, Players remains `9.1.3`, Ledger remains `9.1.2`, and every game revision remains exact accepted values.
- The compatibility record retains exact immutable v0.9.5.76 source `f37c4f78627bcbc6407f33c61d5b01a6181a3314`, archive SHA-256 `51dfc3d97d2690431a350a3e44fde5250cd66ce5af5e9456d4cf4f2d01ca77cd`, and manifest SHA-256 `fb1cf1bf7f1c516abed4bb1a76379a0f88bcb46f61c4ec1ee65ca635a2b3b884`.

## Rollback, validation, and handback

- Rollback remains application-only at exact schema 2; database rollback is prohibited outside `TOOL-003`. The migration catalog remains minimum 2 / expected 4 / apply held, while production remains exact schema 2.
- The canonical deployable inventory is exactly 767 regular files: accepted source selection 766 plus this compatibility record; the poller and both systemd templates are packaged.
- Local validation is browser-free; fresh hosted all-nine evidence remains mandatory before normal merge and immutable publication.
- No host installation, live mail, OAuth, provider traffic, provider-console change, public-signup activation, public-policy activation, public launch, database migration, grant mutation, game behavior, settlement semantics, paytable, route or API adoption, or wagering-economics change is claimed by the release packet.
