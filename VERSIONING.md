# Versioning

This page states the repository's version scheme in one place so release
archaeology never requires tribal knowledge. `modules/module-manifest.json` is
the canonical source for the current packaged release, historical baseline,
and module revisions. `scripts/validate_versions.py` asserts that the two
current top-level numbers stated here match that manifest, so this document
cannot silently rot.

## Current numbers

- Packaged application release: `0.9.5.83`
- Historical source baseline: `9.1.0`

## What each number means

- **Packaged application release** (for example `0.9.5.83`). The single
  user-facing release number, held at the top-level `application` key of
  `modules/module-manifest.json`. Runtime, API, browser, and Admin surfaces all
  display this number, and it changes only through a formal release-artifact
  packet. GitHub release tags for the current lineage are `v<packaged>` (for
  example `v0.9.5.83`).
- **Historical source baseline** (`9.1.0`). Provenance only. It records the
  source revision the current repository was reorganized from and is never a
  current release number. It is held at the top-level `source_baseline` key of
  the manifest.
- **Module revisions** (for example `application`, `core`, `admin`,
  `contracts`, `tests`, `docs`, `tooling`, and each game). Independent
  per-module source revisions under the `modules` object of the manifest. A
  module revision is bumped whenever its owned source changes and may advance
  many times between packaged releases. `modules.application` is the application
  *module* revision and is deliberately distinct from the packaged application
  release at the top level.

## Why the numbering lineage changed

Earlier releases were tagged in a `9.x` lineage (for example `v9.2.0` through
`v9.5.6`); those tags remain in GitHub for historical continuity. The project
then adopted the four-part packaged-release lineage `0.9.x.y` (for example
`0.9.5.5` and onward through `0.9.5.83`) to express pre-1.0 packaged releases
independently of the historical source baseline. Both tag lineages are visible
on the GitHub Releases and Tags pages; the current lineage is `v0.9.5.*` and the
`v9.*` tags are historical.

## Which surface shows which number

| Surface | Number shown |
| --- | --- |
| Runtime, API, browser shell, Admin | Packaged application release (`0.9.5.83`) |
| `README.md`, `CODEX_START_HERE.md`, this file | Packaged application release and historical source baseline |
| `modules/module-manifest.json` | Canonical packaged release, source baseline, and every module revision |
| GitHub Releases / Tags — current lineage | `v0.9.5.*` |
| GitHub Releases / Tags — historical lineage | `v9.*` (superseded) |

## How this stays correct

`scripts/validate_versions.py` reconciles the aggregate manifest, the module
manifests, runtime values, package metadata, `README.md`, `CODEX_START_HERE.md`,
and this document. Any drift between the numbers stated here and the manifest
fails CI, so `VERSIONING.md` cannot fall out of date without the version
validator rejecting the change.
