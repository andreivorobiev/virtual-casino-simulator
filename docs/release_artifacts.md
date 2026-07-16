# Reproducible release artifacts

Requirement `TOOL-003` defines the repository-only release-artifact and rollback-provenance gate. Producing a candidate is evidence; it is not approval to deploy or expose the application.

## Candidate assets

`python scripts/make_release.py` validates the exact clean Git checkout and writes three ignored files under `dist/`:

- `virtual_casino_simulator_package.zip` contains only explicitly allowlisted, Git-tracked application files.
- `release-manifest.json` binds the archive to the full commit SHA, canonical packaged version, optional canonical tag, supported Python range, module revisions, declared dependency/SBOM inputs, every packaged file hash, the archive checksum, completed validation commands, and rollback provenance.
- `checksums.txt` provides convenience SHA-256 rows for the archive and manifest. The JSON manifest remains the canonical machine-readable provenance record.

The ZIP writer sorts members, fixes their timestamps and modes, and writes exact source bytes with fixed compression settings. The manifest uses the Git commit time as its deterministic provenance timestamp. Equivalent builds from the same clean commit therefore produce identical archive and manifest bytes.

## Fail-closed packaging boundary

The packager obtains its source inventory from `git ls-files`; it never recursively walks the working directory. Only the runtime Python package, browser assets, module and contract metadata, selected public documentation, package metadata, launch entry point, and checked-in SQL schema are eligible.

Runtime data, logs, tests, local evidence, caches, environment files, key-like files, local worktrees, and all untracked content are excluded. A credential-like tracked path beneath an otherwise allowed application root causes the build to fail instead of being silently omitted. Symlinks and unsafe archive paths are also rejected.

## Validation and clean-copy smoke

The release driver completes repository rules, API tests, contract and boundary validators, catalog and requirement validators, version validation, generated-document drift checking, and focused release-artifact tests before packaging. The resulting manifest records the fixed command set as passed.

The verifier then authenticates the archive checksum and complete member inventory before extracting to a temporary clean directory. It validates canonical module metadata, imports the application and configuration, and checks required static assets. It does not start the HTTP server or open a listener, and it directs any defensive data lookup to the temporary directory.

## Branch and publication behavior

Pull requests and manual workflow runs may build a seven-day unpublished Actions artifact. A manual `app_version` must exactly match `modules/module-manifest.json`.

Immutable GitHub Release publication is a separate job and remains fail closed unless all of these conditions hold:

1. The trigger is a published GitHub Release event for the canonical `v<version>` tag.
2. GitHub reports the release ref as protected.
3. Repository variable `ENABLE_IMMUTABLE_RELEASE_PUBLISH` is explicitly set to `true`.
4. The `immutable-release` environment permits the job.
5. A prior non-draft, non-prerelease asset supplies a valid `release-manifest.json` rollback pointer.
6. Independent checksum, exact commit/tag, file inventory, rollback, and clean-copy smoke verification passes.

Release assets are uploaded without replacement semantics. An asset-name collision fails rather than mutating an existing immutable artifact.

## Application-only rollback

Each publication-eligible manifest records the immediately previous retained release version, commit, archive checksum, and manifest checksum. Before rollback, verify the retained manifest and archive, install the prior archive into a new immutable release directory, run the same clean-copy verification, then atomically repoint the application release selector according to the separately approved deployment procedure.

This gate covers application artifact rollback only. Database or schema rollback is intentionally outside `TOOL-003` and must follow the separately accepted migration and recovery gates. A candidate without a valid prior manifest remains useful for branch validation but is not eligible for immutable publication.

## Local commands

Build an unpublished candidate from a clean committed checkout:

```powershell
python scripts/make_release.py
```

Verify existing assets without rebuilding:

```powershell
python scripts/package_app.py --verify-only --archive dist/virtual_casino_simulator_package.zip --manifest dist/release-manifest.json
```

Build a canonical tagged candidate with retained rollback provenance:

```powershell
python scripts/make_release.py --release-tag v9.2.0 --previous-manifest previous/release-manifest.json
```
