# Changelog

**Per-release notes live in [`RELEASE_NOTES.md`](RELEASE_NOTES.md), which is the maintained
release record.** It carries every packaged release with its scope, gating, and rollback statement.

Canonical version sources:

- `modules/module-manifest.json` — `application` is the packaged application release; entries under
  `modules` are independent per-module source revisions.
- `pyproject.toml` — package metadata version, kept in step by `scripts/validate_versions.py`.

This file is retained only for the historical bootstrap entry below. It is **not** a current
statement of repository state: the repository has advanced many releases past 9.1.1.

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
