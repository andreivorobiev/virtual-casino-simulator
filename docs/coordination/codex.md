# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-08-23T04:50:00Z.

## Current branch / active Codex work

- Protected main is frozen at exact `8b25bedd2261a0364ff0e6ea9044c334a61eca07`, containing the completed PostgreSQL program and governed OCI restricted-preview deployment path through #1079.
- Isolated branch `codex/release-v0.9.5.86` is the owner-authorized release-only wrapper for that exact protected-main base.
- Publication and deployment are authorized for v0.9.5.86: existing production remains MySQL schema 2, while #1078 owns a separate PostgreSQL 16 preview at `preview.tiltseven.com` with no paid-capacity fallback.

## Accepted scope and requirements

- `TOOL-003` binds v0.9.5.86 to the exact immutable v0.9.5.85 hosted archive and manifest as the application-only predecessor for existing MySQL production.
- `STORAGE-026`, `TOOL-021`, and `TEST-258` bind the PostgreSQL preview to release-authorized empty-target bootstrap, least-privilege roles, DDL-free runtime checks, exact edge policy, and fail-closed deployment evidence.
- The first PostgreSQL preview rollback is stop-and-withdraw only; no older artifact or schema reversal may be applied to the initialized target.
- Requirements remain exactly 1129 and the frozen `/api/v1` contract remains unchanged.

## Version and validation allocation

- Packaged release advances to `0.9.5.86`.
- Application, contracts, tests, and docs receive compatible release-wrapper patch revisions; Core, tooling, operations, Admin, and every content-owned game module remain at their exact protected-main revisions.
- The frozen `/api/v1` contract and all game, paytable, settlement, signup, OAuth, provider, billing, and public-launch behavior remain unchanged.

## Validation and handback

- Local validation rebuilds the canonical tagged candidate twice, compares all three artifact bytes, and verifies exact commit, tag, predecessor, schema window, inventory, and clean-copy smoke.
- The immutable release-only PR must pass every ordinary protected-branch context on its exact head before one normal non-bypass merge.
- The protected-main workflow must publish exact v0.9.5.86 assets. Existing MySQL production must converge through the unchanged default poller, while the new OCI preview must prove exact PostgreSQL identity, TLS, loopback-only database access, encrypted backup, isolated restore, cleanup, and alarm-free live readiness before #1078 closes.
