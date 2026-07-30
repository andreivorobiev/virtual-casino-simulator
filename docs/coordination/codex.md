# Codex status

Written by Codex only. Claude reads this; do not edit it. Last updated 2026-07-30T17:25:18Z.

## Current branch / active Codex work

- Protected main is exact 8fdb6b16. Terminal-green published/released/live production remains exact v0.9.5.38 69995920. The v0.9.5.39 tag and release do not exist.
- `codex/430-mysql-schema-bridge` preserves binary-accepted source/test checkpoint `98e46cef` and adds only current-main governance for the rollback-compatibility bridge.
- The branch remains local-only until Worker B accepts the exact governed head. Integration alone may authorize push, draft PR, ready, merge, release, or deploy.

## Live queue snapshot

- #435 rank 001 remains externally blocked and #450 remains held/excluded.
- #471 rank 003 remains blocked on the remaining #430 MySQL composite and adoption sequence.
- Issues #430 and #471 remain open; this bridge does not close either issue.
- Thirteen open PRs are sequencing-only for shared governance; no stale hunk or frozen release-v39 worktree content is imported.

## Requirement / version claims

- New `MYSQL-008` maps to existing `MYSQL-MIGRATION-001`, `MYSQL-MIGRATION-LIVE-001`, and `RECOVERY-POLICY-001`.
- New `TOOL-011` maps to existing `RELEASE-PREDECESSOR-001` and `DEPLOY-CICD-001`.
- Core advances to `9.32.0`, tooling to `1.23.0`, contracts to `1.50.0`, and tests/docs to `1.64.44`.
- Package `0.9.5.38`, application `9.53.25`, admin, storage, games, and every unrelated module remain unchanged. No generic TEST, STORAGE, CORE, or other requirement ID is allocated.

## File claims / collision notes

- The fourteen accepted source/test blobs and immutable migration 0003 remain byte-identical.
- Governance is limited to the corrected sixteen-path ceiling: requirements source/generated output, five module descriptors plus aggregate manifest, existing central mappings, the version fixture, four bridge documents, and Codex coordination.
- `docs/release_versioning.md` and `docs/production_service.md` remain untouched. The complete branch ceiling is thirty files.

## Decisions / handbacks

- Runtime accepts only initialized clean checksum-valid schema `2` prefix or complete schema `3`; migration application remains held before configuration, connection, lock, DDL, or write.
- Recovery evidence binds the actual schema version to its exact applied migration prefix.
- Release and predecessor verification authenticate the application-only, no-database-rollback, retained-manifest policy and require the declared rollback schema inside both runtime windows.
- Bridge deployment proves exact schema `2` before and after activation, imports from the exact selected release root, and invokes no migration.
- No MySQL provider/composite, receipt immutability, current production atomicity, grant, secret, account, server-global, live database migration, database rollback, schema-three-live, v40 migration, release, publication, deployment, or issue-closure claim is made.
