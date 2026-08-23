# Changelog

**Per-release notes live in [`RELEASE_NOTES.md`](RELEASE_NOTES.md), which is the maintained
release record.** It carries every packaged release with its scope, gating, and rollback statement.

Canonical version sources:

- `modules/module-manifest.json` — `application` is the packaged application release; entries under
  `modules` are independent per-module source revisions.
- `pyproject.toml` — package metadata version, kept in step by `scripts/validate_versions.py`.

This file retains the historical bootstrap entry and concise unreleased source-delivery notes.
Packaged release history, deployment evidence, and rollback statements remain exclusively in
`RELEASE_NOTES.md`.

## PostgreSQL storage-provider source delivery (unreleased documentation)

- Documented the explicit optional PostgreSQL provider, bounded per-process pool, checksum-bound
  schema-five catalog, disposable-only migration runner, and provider-neutral storage behavior
  delivered by issues #1055 through #1060.
- Documented the unchanged A–J conformance contract, exact relational authorization boundaries,
  and distinct MySQL service versus PostgreSQL private-cluster cleanup ownership.
- Added local PostgreSQL 16, connection-pool, migration, authorization-marker, cleanup, and rollback
  guidance without changing application, API, gameplay, schema, provider, or deployment behavior.
- Kept JSON as the absent-selector default and MySQL behavior unchanged; PostgreSQL requires
  explicit selection and the optional `postgres` dependency group.
- This documentation does not create or authorize a production PostgreSQL target, apply migrations
  to existing data, publish a release, or change packaged application release `0.9.5.85`.

## 9.1.1 - Repository Bootstrap + Codex Migration Payload (historical)

- Added GitHub-ready governance files.
- Added Codex root and module instructions.
- Added OpenAPI v1 contract skeletons.
- Added JSON schemas and compatibility manifests.
- Added module manifests for independent module revisioning.
- Added validation scripts for contracts, boundaries, requirements, versions, and comment density.
- Added GitHub Actions workflow scaffolding.
- Added PR and issue templates.
- Added mandatory commenting policy.
- Added dense code comments to active Python and JavaScript source files.
- No intentional gameplay behavior changes from v9.1.0.
