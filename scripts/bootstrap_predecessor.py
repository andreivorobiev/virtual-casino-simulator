"""Create fail-closed TOOL-003 provenance for the one-time v9.2.0 predecessor recovery."""

# Import argument parsing for the workflow-owned recovery inputs.
import argparse
# Import hashing for immutable artifact, manifest, and receipt binding.
import hashlib
# Import JSON support for canonical release and successor metadata.
import json
# Import portable paths for isolated Actions workspace assets.
import pathlib
# Import regular expressions for exact full Git commit validation.
import re

# Bind the only predecessor version authorized by the protected recovery packet.
PREDECESSOR_VERSION = "9.2.0"
# Bind the predecessor to the last protected-main commit before the packaged version bump.
PREDECESSOR_COMMIT = "832c067596e44375217514c1cf28f9e5352abd4b"
# Bind the recovery receipt to the private-invite successor release.
SUCCESSOR_VERSION = "9.3.0"
# Require full lowercase Git object identities instead of branches or abbreviated SHAs.
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
# Name the one additional immutable recovery receipt asset.
RECEIPT_NAME = "predecessor-recovery.json"


# Return the lowercase SHA-256 digest for exact supplied bytes.
def sha256_bytes(payload):
    # Hash bytes once so every receipt and checksum comparison uses the same representation.
    return hashlib.sha256(payload).hexdigest()


# Load one canonical UTF-8 JSON object with a focused malformed-input boundary.
def load_object(path, description):
    # Parse the complete file without copying any host path into durable provenance.
    value = json.loads(path.read_text(encoding="utf-8"))
    # Reject arrays and scalars before field-level provenance checks.
    if not isinstance(value, dict):
        # Report only the public asset class rather than a local path.
        raise ValueError(f"{description} must be a JSON object")
    # Return the validated mapping for exact comparisons.
    return value


# Validate the rebuilt predecessor and protected-main successor, then return a canonical receipt.
def build_receipt(predecessor_manifest_path, successor_manifest_path, successor_commit):
    # Require the workflow-supplied successor identity to be an exact full commit.
    if not COMMIT_RE.fullmatch(successor_commit):
        # Refuse symbolic, uppercase, shortened, or malformed target identities.
        raise ValueError("successor commit must be a full lowercase Git SHA")
    # Prevent a recovery receipt from pointing the successor back at its predecessor.
    if successor_commit == PREDECESSOR_COMMIT:
        # Require the accepted v9.3.0 protected-main merge as a distinct target.
        raise ValueError("successor commit must differ from the predecessor commit")
    # Read exact predecessor manifest bytes for checksum-bound receipt provenance.
    predecessor_bytes = predecessor_manifest_path.read_bytes()
    # Parse the rebuilt release manifest only after retaining its immutable digest input.
    predecessor = json.loads(predecessor_bytes.decode("utf-8"))
    # Require the exact authorized packaged predecessor identity.
    if predecessor.get("app_version") != PREDECESSOR_VERSION:
        # Stop a different application version from occupying the bootstrap release.
        raise ValueError("predecessor manifest application version is not v9.2.0")
    # Read source provenance defensively before exact commit and tag comparison.
    source = predecessor.get("source")
    # Require the exact protected-main source commit and canonical tag.
    if not isinstance(source, dict) or source.get("commit_sha") != PREDECESSOR_COMMIT or source.get("release_tag") != f"v{PREDECESSOR_VERSION}":
        # Refuse any rebuilt artifact not bound to the authorized source and tag.
        raise ValueError("predecessor manifest source identity is not exact")
    # Read the application-only rollback boundary from the predecessor candidate.
    rollback = predecessor.get("rollback")
    # Require the bootstrap predecessor to remain explicitly non-rollback-eligible itself.
    if not isinstance(rollback, dict) or rollback.get("application_only") is not True or rollback.get("eligible") is not False or rollback.get("previous") is not None:
        # Prevent circular, invented, or database-coupled bootstrap provenance.
        raise ValueError("predecessor rollback eligibility boundary is invalid")
    # Preserve the repository's explicit database exclusion for the bootstrap predecessor.
    if rollback.get("database_rollback") != "outside-TOOL-003":
        # Refuse any receipt that could imply a MySQL rollback authorization.
        raise ValueError("predecessor manifest does not prohibit database rollback")
    # Read exact MySQL compatibility metadata from the rebuilt predecessor.
    mysql_schema = predecessor.get("mysql_schema")
    # Require the already-accepted exact schema-v2 runtime window.
    if not isinstance(mysql_schema, dict) or (mysql_schema.get("minimum_version"), mysql_schema.get("expected_version")) != (2, 2):
        # Stop a predecessor that cannot run against the canonical migrated schema.
        raise ValueError("predecessor MySQL compatibility is not exact schema v2")
    # Read the predecessor artifact identity after manifest structure is trusted.
    artifact = predecessor.get("artifact")
    # Require a named SHA-256-bound archive before inspecting sibling bytes.
    if not isinstance(artifact, dict) or not isinstance(artifact.get("name"), str) or not re.fullmatch(r"[0-9a-f]{64}", str(artifact.get("sha256", ""))):
        # Refuse incomplete or malformed release artifact provenance.
        raise ValueError("predecessor artifact identity is invalid")
    # Resolve the archive only beside the supplied manifest inside the isolated candidate directory.
    archive_path = predecessor_manifest_path.parent / artifact["name"]
    # Read exact rebuilt archive bytes for independent checksum confirmation.
    archive_bytes = archive_path.read_bytes()
    # Require the archive bytes to match the checksum-bound predecessor manifest.
    if sha256_bytes(archive_bytes) != artifact["sha256"]:
        # Stop before receipt creation when the rebuilt archive does not authenticate.
        raise ValueError("predecessor artifact checksum does not match its manifest")
    # Load the accepted successor's canonical packaged-version manifest.
    successor = load_object(successor_manifest_path, "successor module manifest")
    # Require the workflow dispatch target to be the released v9.3.0 source tree.
    if successor.get("application") != SUCCESSOR_VERSION:
        # Prevent an arbitrary protected-main commit from being named as the successor.
        raise ValueError("successor packaged application version is not v9.3.0")
    # Return stable public provenance without host paths, credentials, or provider data.
    return {
        # Version the recovery receipt format independently from application releases.
        "schema_version": 1,
        # Map the receipt to the permanent deterministic release requirement.
        "requirement": "TOOL-003",
        # Bind the exact predecessor source and rebuilt immutable assets.
        "predecessor": {
            # Record the only authorized predecessor application version.
            "app_version": PREDECESSOR_VERSION,
            # Record the exact pre-bump protected-main commit.
            "commit_sha": PREDECESSOR_COMMIT,
            # Record the canonical version tag created only by the workflow.
            "release_tag": f"v{PREDECESSOR_VERSION}",
            # Bind the complete rebuilt predecessor manifest bytes.
            "manifest_sha256": sha256_bytes(predecessor_bytes),
            # Name the authenticated application archive without a host path.
            "artifact_name": artifact["name"],
            # Bind the exact rebuilt application archive bytes.
            "artifact_sha256": artifact["sha256"],
        },
        # Bind the target to the exact protected-main merge selected at dispatch time.
        "successor": {
            # Record the reviewed private-invite packaged release.
            "app_version": SUCCESSOR_VERSION,
            # Record the exact accepted protected-main merge at dispatch.
            "commit_sha": successor_commit,
        },
        # State the only rollback semantics this recovered predecessor may support.
        "rollback": {
            # Limit recovery use to immutable application artifacts.
            "scope": "application-only",
            # Prohibit any inference of database or schema rollback authority.
            "database_rollback": "prohibited",
            # Preserve compatibility with the already accepted schema-v2 runtime.
            "mysql_expected_schema_version": 2,
        },
    }


# Write one new receipt and extend the existing candidate checksum inventory without replacement.
def write_recovery_assets(predecessor_manifest_path, successor_manifest_path, successor_commit, receipt_path, checksums_path):
    # Refuse to replace or append to any previously created recovery receipt.
    if receipt_path.exists():
        # Preserve one-shot recovery semantics even in a reused workspace.
        raise FileExistsError("predecessor recovery receipt already exists")
    # Build the fully validated canonical receipt before any output mutation.
    receipt = build_receipt(predecessor_manifest_path, successor_manifest_path, successor_commit)
    # Resolve the authenticated archive beside the predecessor manifest.
    archive_path = predecessor_manifest_path.parent / receipt["predecessor"]["artifact_name"]
    # Define the exact two rows emitted by the predecessor's original release driver.
    expected_rows = {
        # Authenticate the complete release manifest bytes.
        f"{sha256_bytes(predecessor_manifest_path.read_bytes())}  {predecessor_manifest_path.name}",
        # Authenticate the rebuilt application archive bytes.
        f"{sha256_bytes(archive_path.read_bytes())}  {archive_path.name}",
    }
    # Read and normalize only non-empty candidate checksum rows.
    existing_rows = {row for row in checksums_path.read_text(encoding="utf-8").splitlines() if row}
    # Refuse stale, missing, duplicate-collapsed, or unexpected checksum inventory.
    if existing_rows != expected_rows or len(checksums_path.read_text(encoding="utf-8").splitlines()) != 2:
        # Stop before creating a receipt when candidate assets are not exact.
        raise ValueError("predecessor checksum inventory is not the expected clean candidate set")
    # Serialize the receipt deterministically with sorted keys and one trailing newline.
    receipt_text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    # Create the receipt exclusively so no prior bytes can be overwritten.
    with receipt_path.open("x", encoding="utf-8", newline="\n") as handle:
        # Write the validated public provenance once.
        handle.write(receipt_text)
    # Build the checksum row for the newly created immutable receipt.
    receipt_row = f"{sha256_bytes(receipt_text.encode('utf-8'))}  {receipt_path.name}\n"
    # Append exactly one recovery row after the original release driver rows.
    with checksums_path.open("a", encoding="utf-8", newline="\n") as handle:
        # Extend the candidate inventory without replacing either original row.
        handle.write(receipt_row)
    # Return the receipt so tests and workflow diagnostics can verify its public identities.
    return receipt


# Parse only the isolated candidate and successor inputs supplied by the protected workflow.
def parse_args():
    # Describe the one-time protected predecessor recovery helper.
    parser = argparse.ArgumentParser(description="Bind the exact v9.2.0 predecessor to an accepted v9.3.0 protected-main successor.")
    # Accept the rebuilt predecessor manifest path.
    parser.add_argument("--predecessor-manifest", type=pathlib.Path, required=True)
    # Accept the successor aggregate manifest path from the merged protected-main checkout.
    parser.add_argument("--successor-manifest", type=pathlib.Path, required=True)
    # Accept the exact protected-main successor commit selected by workflow dispatch.
    parser.add_argument("--successor-commit", required=True)
    # Accept the one-shot receipt output path inside the predecessor candidate directory.
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    # Accept the original two-row candidate checksum inventory for authenticated extension.
    parser.add_argument("--checksums", type=pathlib.Path, required=True)
    # Return the parsed, still-untrusted workflow arguments.
    return parser.parse_args()


# Validate inputs and create one checksum-bound recovery receipt.
def main():
    # Parse the protected workflow inputs before reading any candidate bytes.
    args = parse_args()
    # Create exactly one receipt and extend its sibling checksum inventory.
    receipt = write_recovery_assets(args.predecessor_manifest, args.successor_manifest, args.successor_commit, args.receipt, args.checksums)
    # Report only public release identities and the receipt filename.
    print(f"Bound v{receipt['predecessor']['app_version']} to v{receipt['successor']['app_version']} in {args.receipt.name}")
    # Return success only after all exact provenance and write-once gates pass.
    return 0


# Run the helper only when the workflow or a developer invokes it directly.
if __name__ == "__main__":
    # Exit through the explicit result so Actions fails closed on any exception.
    raise SystemExit(main())
