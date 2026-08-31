# Reproducible release artifacts

Requirements `TOOL-003`, `TOOL-008`, and `TOOL-011` define the repository-only release-artifact, publication-intent and rollback-provenance gates. Producing a candidate is evidence; it is not approval to deploy or expose the application.

## Candidate assets

`python scripts/make_release.py` validates the exact clean Git checkout and writes three ignored files under `dist/`:

- `virtual_casino_simulator_package.zip` contains only explicitly allowlisted, Git-tracked application files.
- `release-manifest.json` binds the archive to the full commit SHA, canonical packaged version, optional canonical tag, supported Python range, module revisions, distinct MySQL expected/minimum migration versions, exact apply policy, catalog/chain checksums, declared dependency/SBOM inputs, every packaged file hash, the archive checksum, completed validation commands, and rollback provenance.
- `checksums.txt` provides convenience SHA-256 rows for the archive and manifest. The JSON manifest remains the canonical machine-readable provenance record.

The ZIP writer sorts members, fixes their timestamps and modes, and writes exact source bytes with fixed compression settings. The manifest uses the Git commit time as its deterministic provenance timestamp. Equivalent builds from the same clean commit therefore produce identical archive and manifest bytes.

## Fail-closed packaging boundary

The packager obtains its source inventory from `git ls-files`; it never recursively walks the working directory. Only the runtime Python package, browser assets, module and contract metadata, selected public documentation, package metadata, launch entry point, deployment-only migration runner, and checksum-pinned canonical migration catalog/files are eligible. No parallel checked-in SQL schema snapshot exists to drift from the catalog.

Runtime data, logs, tests, local evidence, caches, environment files, key-like files, local worktrees, and all untracked content are excluded. A credential-like tracked path beneath an otherwise allowed application root causes the build to fail instead of being silently omitted. Symlinks and unsafe archive paths are also rejected. The allowlist and required inventory include every Python command that the production workflow runs from the extracted release; a regression derives those host paths from `.github/workflows/deploy-production.yml` and fails if any referenced script is absent from the archive.

## Validation and clean-copy smoke

The release driver completes repository rules, API tests, contract and boundary validators, catalog and requirement validators, version validation, generated-document drift checking, and focused release-artifact tests before packaging. The resulting manifest records the fixed command set as passed.

The verifier then authenticates the archive checksum and complete member inventory before extracting to a temporary clean directory. It validates canonical module metadata, imports the application and configuration, and checks required static assets. It does not start the HTTP server or open a listener, and it directs any defensive data lookup to the temporary directory.

## Branch and publication behavior

Pull requests and manual workflow runs may build a seven-day unpublished Actions artifact. A manual `app_version` must exactly match `modules/module-manifest.json`.

Ordinary protected-main pushes with an unchanged packaged version are read-only publication no-ops. Every three-hour batch uses one independently reviewed release-only wrapper; the [production CI/CD runbook](production_cicd_runbook.md#three-hour-coordinator-procedure-1084) specifies the coordinator, semantic allowlist, failure holds and live acceptance evidence. Immutable publication requires all of these conditions:

1. The trigger is an exact protected-main push whose one merged release-only PR and semantic identity-only diff pass the read-only preflight. The merge and wrapper commits each have exactly one canonical commit-to-pull association.
2. The canonical PR has at least one current-head approval from a non-owner human reviewer, distinct from its author, who retains provider-observed `write` or `admin` permission. The latest effective state per reviewer applies; any latest current-head `CHANGES_REQUESTED` blocks, `DISMISSED` is nonqualifying, and extra bot, owner, author, or non-collaborator approvals are supplemental only.
3. The exact `Senior B` and `Worker10` operational receipts bind the wrapper head/tree and pre-merge metadata digest, are posted by the same repository-owner identity, remain unedited, and strictly predate the merge. Receipt text explicitly says it is supplemental only and is neither the provider-distinct GitHub review approval nor release authorization.
4. Inside the shared publication lock, current protected main still equals the reviewed wrapper result and the candidate is the next compatible packaged patch. The admission snapshot is re-fetched before mutation and after publication; a changed fingerprint fails closed.
5. The Release API authoritatively reports absence and the peeled tag is absent, or an already complete stable release binds exactly the same full source SHA and three assets. Unknown, conflicting, draft and partial states fail closed.
6. The compatibility-declared predecessor is exactly the packaged version being replaced; it binds that version's exact source, archive and manifest checksums and accepts schema-two application-only rollback.
7. A new candidate passes the unchanged release-driver validations. The direct post-writer verifier downloads both current and predecessor assets and requires canonical checksums, exact commit/tag, inventory, rollback and clean-copy verification plus a stable before/after hosted observation.

Only the conditional main-push job has normal publication write permission. It creates the three assets once; an attempt-one run that observes an already complete exact-head release downloads and verifies it without replacement. A failed publication rerun remains prohibited and requires incident classification. The legacy-named `Publish exact-main release` job is a post-merge `always()` aggregate, is absent from branch protection, and is not a required merge context. It accepts only successful intent plus `noop/skipped/skipped` or successful intent plus `publish/success/success` for decision/writer/verifier. The direct verifier supplies the required automated hosted evidence.

The `release: published` lane is supplemental **verify-only** evidence for an externally initiated published-release event. A repository `GITHUB_TOKEN` publication cannot trigger it, so it contributes nothing to the direct aggregate. It retains the protected-ref, `ENABLE_IMMUTABLE_RELEASE_PUBLISH=true` and `immutable-release` environment gates, but has only `contents: read`: it authenticates the peeled tag, full source, hosted three assets and exact predecessor, then runs checksum/archive/rollback/clean-copy verification. It does not rebuild, upload, replace, delete, or publish. The before/after provider observations prove bounded stability, not provider immutability. The historical one-time predecessor recovery below remains separate and unchanged apart from shared non-cancellable serialization.

Admission inventories deliberately fail closed at the first-page cap (`<100`) instead of claiming pagination completeness. `codex_review_placeholder` is status-only name compatibility, never review proof. Current publication remains HOLD until the non-owner reviewer and branch, tag, and environment settings listed in the [production CI/CD runbook](production_cicd_runbook.md#current-provider-prerequisites-and-hold-1095) are independently applied and accepted. No API, compatibility contract, storage provider, database, production host, deployment, or release behavior is broadened by this governance correction.

## Protected v9.2.0 predecessor recovery

The one-time `bootstrap-v9.2.0-predecessor` workflow-dispatch action exists only to recover the missing predecessor required by v9.3.0. It is eligible only when dispatched by the repository owner from protected `main` after the reviewed v9.3.0 change is merged. The caller must confirm exact pre-bump commit `832c067596e44375217514c1cf28f9e5352abd4b`, while the workflow binds the successor to the exact protected-main dispatch SHA.

The workflow refuses any existing v9.2.0 tag or draft, prerelease, or published Release. It checks out the predecessor by full commit, rebuilds the tagged candidate twice, compares every original asset byte-for-byte, independently verifies the archive and manifest, and creates a checksum-bound recovery receipt naming the exact successor. Only then may it create and verify a draft and publish it as a non-latest retained Release. No upload-after-create, overwrite, clobber, deletion, direct tag push, or non-protected-branch recovery path exists.

The recovered v9.2.0 manifest is intentionally not rollback-eligible itself because no earlier retained artifact exists. It preserves exact MySQL schema-v2 compatibility and explicitly excludes database rollback. Its retained manifest supplied the application-only predecessor for v9.3.0; each later ordinary protected release consumes the retained manifest for its immediate predecessor.

## Application-only rollback

Each publication-eligible manifest records the immediately previous retained release version, commit, archive checksum, manifest checksum, and declared rollback MySQL version. Before rollback, verify the retained manifest and archive, install the prior archive into a new immutable release directory, run the same clean-copy verification, then atomically repoint the application release selector according to the separately approved deployment procedure.

The authenticated compatibility record, not GitHub release-list ordering, selects the retained predecessor. Packaging and verification require its rollback policy to be exactly application-only, database rollback prohibited, and retained-predecessor manifest required. The rollback schema declaration must match the packaged compatibility record and fit both the candidate and predecessor runtime windows. A published release with incorrect rollback provenance, an incomplete host-command inventory, or a failed-closed activation remains immutable and is superseded by a new patch identity; its assets and tag are never replaced in place. v0.9.5.86 declares unchanged rollback schema 2 inside its schema-2-through-5 MySQL runtime window and retains exact immutable v0.9.5.85 as its application-only predecessor for the existing MySQL deployment. The first PostgreSQL preview deployment instead uses the separately documented stop-and-withdraw rollback and never applies an older artifact to its initialized PostgreSQL target.

This gate covers application artifact rollback only. An exact-schema-three, exact-schema-four, or exact-schema-five candidate cannot select the exact-schema-two-only v0.9.5.38 predecessor. A bridge release operating at schema `2` may select v0.9.5.38, and a future release operating at schema `3`, `4`, or `5` may select a bridge predecessor only when both runtime windows include that exact version. Database or schema rollback is intentionally outside `TOOL-003` and `TOOL-011` and must follow the separately accepted migration and recovery gates. A candidate without a valid prior manifest remains useful for branch validation but is not eligible for immutable publication.

## Local commands

Build an unpublished candidate from a clean committed checkout:

```powershell
python scripts/make_release.py
```

Verify existing assets without rebuilding:

```powershell
python scripts/package_app.py --verify-only --archive dist/virtual_casino_simulator_package.zip --manifest dist/release-manifest.json
```

Build a canonical tagged v0.9.5.86 candidate with the retained v0.9.5.85 rollback manifest selected by compatibility policy:

```powershell
python scripts/make_release.py --release-tag v0.9.5.86 --previous-manifest previous/release-manifest.json
```

For v0.9.5.86, `previous/release-manifest.json` must be the checksum-verified retained v0.9.5.85 release manifest declared by `contracts/compatibility/app-0.9.5.86.json`. `scripts/resolve_release_predecessor.py` derives that exact tag and verifies the downloaded manifest before packaging. The candidate and predecessor MySQL windows both accept the declared unchanged schema 2 rollback point. The resulting v0.9.5.86 pointer authorizes application-artifact rollback only for the existing MySQL deployment; it never rolls back MySQL or PostgreSQL. The new PostgreSQL preview follows `docs/oci_postgres_preview.md`, whose first-deployment rollback is service stop and public-origin withdrawal without a database down-migration.
