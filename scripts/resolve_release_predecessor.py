"""Resolve and verify the compatibility-declared predecessor for one packaged release.

Protected publication must not infer rollback from GitHub's release ordering. The repository
compatibility record owns that decision, so this tool emits the exact immutable predecessor tag and
can verify that a downloaded manifest represents the same version and tag before packaging proceeds.
"""

# Import command-line parsing for the publication workflow entrypoint.
import argparse
# Import JSON decoding for compatibility and release manifest records.
import json
# Import SHA-256 hashing for exact retained manifest verification.
import hashlib
# Import paths so every record stays rooted in the checked-out repository.
import pathlib
# Import regular expressions for strict packaged-version and commit validation.
import re
# Import bounded process reporting for fail-closed workflow use.
import sys

# Resolve the repository root from this tracked script rather than the caller's working directory.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Accept the repository's three- or four-part numeric packaged release identities.
VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)?$")
# Require exact lowercase protected-main commit provenance in a downloaded manifest.
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


# Read one JSON object while keeping parsing errors path-free at the command boundary.
def read_object(path: pathlib.Path) -> dict:
    # Decode the tracked or downloaded JSON bytes using the repository encoding.
    value = json.loads(path.read_text(encoding="utf-8"))
    # Reject arrays and scalars because every supported record is a JSON object.
    if not isinstance(value, dict):
        # Fail closed without reflecting any untrusted content.
        raise ValueError("record is not an object")
    # Return the validated object shape.
    return value


# Resolve the exact predecessor tag declared by the current release compatibility record.
def predecessor_tag(app_version: str, root: pathlib.Path = ROOT) -> str:
    # Reject symbolic, partial, or shell-shaped version identities.
    if not VERSION_RE.fullmatch(app_version):
        # Keep the reason stable for sanitized workflow logs.
        raise ValueError("invalid application version")
    # Locate only the canonical compatibility record for the requested packaged release.
    record_path = root / "contracts" / "compatibility" / f"app-{app_version}.json"
    # Parse the current release compatibility record.
    record = read_object(record_path)
    # Require the filename and record identity to agree exactly.
    if record.get("app_version") != app_version:
        # Reject copied or stale records before selecting rollback provenance.
        raise ValueError("compatibility identity mismatch")
    # Read the repository-authoritative predecessor declaration.
    predecessor = record.get("predecessor")
    # Require the predecessor declaration to retain its governed object shape.
    if not isinstance(predecessor, dict):
        # Refuse publication without an explicit rollback declaration.
        raise ValueError("predecessor declaration missing")
    # Read the exact retained packaged version.
    previous_version = predecessor.get("app_version")
    # Require a canonical numeric predecessor identity.
    if not isinstance(previous_version, str) or not VERSION_RE.fullmatch(previous_version):
        # Reject malformed or symbolic predecessor values.
        raise ValueError("predecessor version invalid")
    # Derive the only allowed compatibility-record path for that predecessor.
    expected_record = f"contracts/compatibility/app-{previous_version}.json"
    # Require the declaration to point at that exact repository-owned record.
    if predecessor.get("compatibility_record") != expected_record:
        # Prevent redirected or mismatched rollback-policy inputs.
        raise ValueError("predecessor record path invalid")
    # Require release-manifest provenance rather than an ungoverned rollback artifact.
    if predecessor.get("required_artifact") != "release-manifest.json":
        # Reject rollback declarations that cannot be checksum verified by release tooling.
        raise ValueError("predecessor artifact invalid")
    # Require exact retained source, archive, and manifest identities in current release policy.
    for identity_name in ("source_commit_sha", "artifact_sha256", "manifest_sha256"):
        # Read one pinned lowercase SHA-256 or Git commit identity.
        identity = predecessor.get(identity_name)
        # Apply the full Git-commit width only to source provenance.
        identity_pattern = COMMIT_RE if identity_name == "source_commit_sha" else re.compile(r"^[0-9a-f]{64}$")
        # Reject missing, uppercase, shortened, or non-hexadecimal identity pins.
        if not isinstance(identity, str) or not identity_pattern.fullmatch(identity):
            # Refuse rollback selection without exact retained bytes and source.
            raise ValueError("predecessor identity pin invalid")
    # Parse the declared predecessor record to prove it remains tracked and self-consistent.
    previous_record = read_object(root / pathlib.PurePosixPath(expected_record))
    # Require the predecessor record to identify the same retained application version.
    if previous_record.get("app_version") != previous_version:
        # Reject stale copies before the workflow contacts GitHub Releases.
        raise ValueError("predecessor compatibility identity mismatch")
    # Return the immutable release tag derived from repository policy.
    return f"v{previous_version}"


# Verify a downloaded predecessor manifest against the compatibility-declared version and tag.
def verify_manifest(app_version: str, manifest_path: pathlib.Path, root: pathlib.Path = ROOT) -> str:
    # Resolve the repository-declared predecessor tag first.
    expected_tag = predecessor_tag(app_version, root)
    # Parse the checksum-bound manifest downloaded from that immutable GitHub Release.
    manifest_bytes = manifest_path.read_bytes()
    # Decode the exact bytes only after capturing their immutable checksum.
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    # Require the downloaded record to remain a JSON object.
    if not isinstance(manifest, dict):
        # Reject arrays or scalars before provenance inspection.
        raise ValueError("predecessor manifest is not an object")
    # Reload the candidate policy so exact retained identities can be compared.
    compatibility = read_object(root / "contracts" / "compatibility" / f"app-{app_version}.json")
    # Read the already shape-validated predecessor declaration.
    predecessor = compatibility["predecessor"]
    # Require the downloaded manifest bytes to match the pinned retained manifest.
    if hashlib.sha256(manifest_bytes).hexdigest() != predecessor["manifest_sha256"]:
        # Reject any rebuilt, reformatted, or substituted manifest.
        raise ValueError("predecessor manifest checksum mismatch")
    # Require the manifest version to match the selected predecessor tag.
    if manifest.get("app_version") != expected_tag.removeprefix("v"):
        # Reject mislabeled or stale release assets.
        raise ValueError("predecessor manifest version mismatch")
    # Read the source provenance block recorded by package_app.py.
    source = manifest.get("source")
    # Require source provenance to retain its governed object shape.
    if not isinstance(source, dict):
        # Refuse a predecessor that cannot identify its immutable source.
        raise ValueError("predecessor manifest source missing")
    # Require the manifest to name the same immutable tag that was downloaded.
    if source.get("release_tag") != expected_tag:
        # Reject cross-tag asset substitution.
        raise ValueError("predecessor manifest tag mismatch")
    # Require a full protected-main commit identity for rollback auditability.
    if not isinstance(source.get("commit_sha"), str) or not COMMIT_RE.fullmatch(source["commit_sha"]):
        # Reject manifests with ambiguous or malformed source commits.
        raise ValueError("predecessor manifest commit invalid")
    # Require the full source commit to match the compatibility-pinned retained release.
    if source["commit_sha"] != predecessor["source_commit_sha"]:
        # Reject a manifest from another commit under a misleading tag.
        raise ValueError("predecessor manifest commit mismatch")
    # Read the checksum-bound artifact identity.
    artifact = manifest.get("artifact")
    # Require the predecessor archive block to retain its governed shape.
    if not isinstance(artifact, dict):
        # Reject a manifest that cannot bind its rollback archive.
        raise ValueError("predecessor artifact missing")
    # Require the canonical archive name and exact compatibility-pinned digest.
    if artifact.get("name") != "virtual_casino_simulator_package.zip" or artifact.get("sha256") != predecessor["artifact_sha256"]:
        # Reject renamed, rebuilt, or substituted predecessor archives.
        raise ValueError("predecessor artifact identity mismatch")
    # Return the verified predecessor tag for bounded workflow evidence.
    return expected_tag


# Run the resolver or manifest verifier for the production publication workflow.
def main(argv=None) -> int:
    # Describe the compatibility-owned predecessor gate.
    parser = argparse.ArgumentParser(description="Resolve or verify a release predecessor from repository compatibility policy.")
    # Require the candidate packaged application version.
    parser.add_argument("--app-version", required=True, help="Candidate packaged application version")
    # Optionally verify an already downloaded predecessor manifest.
    parser.add_argument("--verify-manifest", type=pathlib.Path, help="Downloaded predecessor release-manifest.json")
    # Parse caller-supplied arguments.
    args = parser.parse_args(argv)
    # Convert all policy, file, and JSON failures into one bounded workflow result.
    try:
        # Verify the downloaded manifest when the caller supplied it.
        tag = verify_manifest(args.app_version, args.verify_manifest) if args.verify_manifest else predecessor_tag(args.app_version)
    # Handle malformed records and unreadable files without printing host paths or record contents.
    except (OSError, ValueError, json.JSONDecodeError):
        # Emit only the stable gate name so logs cannot reflect untrusted provenance.
        print("release predecessor unavailable: compatibility or manifest validation failed", file=sys.stderr)
        # Fail publication before candidate packaging.
        return 1
    # Emit only the non-secret immutable predecessor tag for workflow composition.
    print(tag)
    # Report successful resolution or verification.
    return 0


# Execute the command-line entrypoint when the script is invoked directly.
if __name__ == "__main__":
    # Propagate the fail-closed result to GitHub Actions.
    raise SystemExit(main())
