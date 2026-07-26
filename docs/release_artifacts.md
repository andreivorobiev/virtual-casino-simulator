# Reproducible release artifacts

Requirement `TOOL-003` defines the repository-only release-artifact and rollback-provenance gate. Producing a candidate is evidence; it is not approval to deploy or expose the application.

## Candidate assets

`python scripts/make_release.py` validates the exact clean Git checkout and writes three ignored files under `dist/`:

- `virtual_casino_simulator_package.zip` contains only explicitly allowlisted, Git-tracked application files.
- `release-manifest.json` binds the archive to the full commit SHA, canonical packaged version, optional canonical tag, supported Python range, module revisions, distinct MySQL expected/minimum migration versions plus catalog/chain checksums, declared dependency/SBOM inputs, every packaged file hash, the archive checksum, completed validation commands, and rollback provenance.
- `checksums.txt` provides convenience SHA-256 rows for the archive and manifest. The JSON manifest remains the canonical machine-readable provenance record.

The ZIP writer sorts members, fixes their timestamps and modes, and writes exact source bytes with fixed compression settings. The manifest uses the Git commit time as its deterministic provenance timestamp. Equivalent builds from the same clean commit therefore produce identical archive and manifest bytes.

## Fail-closed packaging boundary

The packager obtains its source inventory from `git ls-files`; it never recursively walks the working directory. Only the runtime Python package, browser assets, module and contract metadata, selected public documentation, package metadata, launch entry point, deployment-only migration runner, and checksum-pinned canonical migration catalog/files are eligible. No parallel checked-in SQL schema snapshot exists to drift from the catalog.

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

## Protected v9.2.0 predecessor recovery

The one-time `bootstrap-v9.2.0-predecessor` workflow-dispatch action exists only to recover the missing predecessor required by v9.3.0. It is eligible only when dispatched by the repository owner from protected `main` after the reviewed v9.3.0 change is merged. The caller must confirm exact pre-bump commit `832c067596e44375217514c1cf28f9e5352abd4b`, while the workflow binds the successor to the exact protected-main dispatch SHA.

The workflow refuses any existing v9.2.0 tag or draft, prerelease, or published Release. It checks out the predecessor by full commit, rebuilds the tagged candidate twice, compares every original asset byte-for-byte, independently verifies the archive and manifest, and creates a checksum-bound recovery receipt naming the exact successor. Only then may it create and verify a draft and publish it as a non-latest retained Release. No upload-after-create, overwrite, clobber, deletion, direct tag push, or non-protected-branch recovery path exists.

The recovered v9.2.0 manifest is intentionally not rollback-eligible itself because no earlier retained artifact exists. It preserves exact MySQL schema-v2 compatibility and explicitly excludes database rollback. Its retained manifest supplied the application-only predecessor for v9.3.0; each later ordinary protected release consumes the retained manifest for its immediate predecessor.

## Application-only rollback

Each publication-eligible manifest records the immediately previous retained release version, commit, archive checksum, and manifest checksum. Before rollback, verify the retained manifest and archive, install the prior archive into a new immutable release directory, run the same clean-copy verification, then atomically repoint the application release selector according to the separately approved deployment procedure.

The compatibility record, not GitHub release-list ordering, selects the retained predecessor. A published release with incorrect rollback provenance remains immutable and is superseded by a new patch identity; its assets and tag are never replaced in place. v0.9.5.7 therefore retains checksum-verified v0.9.5.5 as its declared application-only predecessor and intentionally does not use the defective v0.9.5.6 rollback pointer.

This gate covers application artifact rollback only. A predecessor may be selected only when its manifest accepts the already-applied MySQL migration version. Database or schema rollback is intentionally outside `TOOL-003` and must follow the separately accepted migration and recovery gates. A candidate without a valid prior manifest remains useful for branch validation but is not eligible for immutable publication.

## Local commands

Build an unpublished candidate from a clean committed checkout:

```powershell
python scripts/make_release.py
```

Verify existing assets without rebuilding:

```powershell
python scripts/package_app.py --verify-only --archive dist/virtual_casino_simulator_package.zip --manifest dist/release-manifest.json
```

Build a canonical tagged v0.9.5.7 candidate with the retained v0.9.5.5 rollback manifest selected by compatibility policy:

```powershell
python scripts/make_release.py --release-tag v0.9.5.7 --previous-manifest previous/release-manifest.json
```

For v0.9.5.7, `previous/release-manifest.json` must be the checksum-verified retained v0.9.5.5 release manifest declared by `contracts/compatibility/app-0.9.5.7.json`. `scripts/resolve_release_predecessor.py` derives that exact tag and verifies the downloaded manifest before packaging. The immutable v0.9.5.6 assets are not replaced or used as rollback provenance because their recorded predecessor is inconsistent with repository policy. The resulting v0.9.5.7 pointer authorizes application-artifact rollback only; it neither rolls back MySQL schema version 2 nor permits provider, DNS, billing, signup, OAuth, mail, edge, or public-exposure changes.
