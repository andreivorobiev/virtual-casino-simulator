"""Run canonical validation before producing a TOOL-003 release candidate."""

# Import argument parsing for canonical version, tag, and rollback inputs.
import argparse
# Import hashing support for the human-readable companion checksum file.
import hashlib
# Import JSON support for canonical packaged application metadata.
import json
# Import portable paths for repository and ignored distribution locations.
import pathlib
# Import filesystem cleanup for stale ignored candidate outputs.
import shutil
# Import subprocess execution for fail-fast repository validators.
import subprocess
# Import the active interpreter path for every Python validation command.
import sys
# Import temporary directories for API validation away from repository runtime fixtures.
import tempfile
# Import ZIP extraction for an exact tracked HEAD validation copy.
import zipfile

# Resolve the repository root independently of the caller's working directory.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Keep generated candidates under the repository's ignored distribution directory.
DIST = ROOT / "dist"
# Define the API validation command separately so it can run in an isolated exact-HEAD copy.
API_VALIDATION = [sys.executable, "tests/run_tests.py", "--api"]
# Define the exact deterministic validation sequence recorded in release provenance.
VALIDATIONS = [
    # Validate repository governance and static rule invariants.
    [sys.executable, "verify_rules.py"],
    # Validate the complete API behavior required for a release candidate.
    API_VALIDATION,
    # Validate frozen and additive API contract surfaces.
    [sys.executable, "scripts/validate_contracts.py"],
    # Validate module import and ownership boundaries.
    [sys.executable, "scripts/validate_module_boundaries.py"],
    # Validate canonical game catalog discovery and descriptors.
    [sys.executable, "scripts/validate_game_catalog.py"],
    # Validate permanent requirement mappings and implementation files.
    [sys.executable, "scripts/validate_requirements.py"],
    # Validate packaged and independent module version alignment.
    [sys.executable, "scripts/validate_versions.py"],
    # Validate generated documentation without mutating the checkout.
    [sys.executable, "scripts/generate_docs.py", "--check"],
    # Validate deterministic artifact, exclusion, smoke, and rollback behavior.
    [sys.executable, "-m", "unittest", "tests.release_artifact_tests"],
    # Validate listener-free WSGI parity, fail-closed configuration, and service hardening.
    [sys.executable, "-m", "unittest", "tests.production_service_tests"],
]
# Define the post-package copied-release lifecycle gate separately because it consumes the built archive.
COPIED_SERVICE_SMOKE = [sys.executable, "tests/production_service_smoke.py", "--archive", "dist/virtual_casino_simulator_package.zip"]


# Render a command without host-specific interpreter paths for deterministic provenance.
def command_label(command):
    # Replace the current interpreter with the portable Python command name.
    rendered = ["python" if item == sys.executable else item for item in command]
    # Join arguments in their already validated fixed order.
    return " ".join(rendered)


# Execute one repository validator and fail immediately on any nonzero result.
def run(command):
    # Print the portable command label for local and CI diagnostics.
    print("+", command_label(command))
    # Run from the repository root so every validator resolves canonical files.
    subprocess.check_call(command, cwd=ROOT)


# Run API tests from an exact tracked archive so resets cannot touch repository runtime fixtures.
def run_api_isolated(command):
    # Print the same portable command label recorded in release provenance.
    print("+", command_label(command), "[isolated exact HEAD copy]")
    # Allocate a disposable directory outside the repository and user runtime data.
    with tempfile.TemporaryDirectory(prefix="casino-release-api-") as temporary:
        # Resolve the temporary tracked-source archive path.
        archive_path = pathlib.Path(temporary) / "source.zip"
        # Resolve the clean extraction target used by the API suite.
        source_root = pathlib.Path(temporary) / "source"
        # Export only Git-tracked bytes from the exact current commit.
        subprocess.check_call(
            ["git", "archive", "--format=zip", f"--output={archive_path}", "HEAD"],
            cwd=ROOT,
        )
        # Open the trusted Git-produced archive for structural path validation.
        with zipfile.ZipFile(archive_path, "r") as archive:
            # Reject absolute or traversal members before disposable extraction.
            if any(pathlib.PurePosixPath(name).is_absolute() or ".." in pathlib.PurePosixPath(name).parts for name in archive.namelist()):
                # Stop if repository metadata ever yields an unsafe validation archive.
                raise ValueError("exact-HEAD API validation archive contains an unsafe path")
            # Extract the already validated tracked source into the disposable target.
            archive.extractall(source_root)
        # Execute the full API suite where resets and generated runtime files are disposable.
        subprocess.check_call(command, cwd=source_root)


# Parse canonical version, optional tag, and retained rollback manifest inputs.
def parse_args():
    # Describe the validation-first release candidate driver.
    parser = argparse.ArgumentParser(description="Validate and build a reproducible Casino Simulator release candidate.")
    # Accept a manual version only so it can be checked against canonical metadata.
    parser.add_argument("--app-version")
    # Bind release-event candidates to the canonical version tag.
    parser.add_argument("--release-tag")
    # Supply the immediately previous release manifest for rollback eligibility.
    parser.add_argument("--previous-manifest", type=pathlib.Path)
    # Return the validated command-line namespace.
    return parser.parse_args()


# Validate the checkout and produce deterministic ignored release assets.
def main():
    # Parse caller inputs before running expensive repository validators.
    args = parse_args()
    # Load the canonical packaged application release from the aggregate manifest.
    canonical_version = json.loads((ROOT / "modules" / "module-manifest.json").read_text(encoding="utf-8"))["application"]
    # Reject any manual workflow input that diverges from canonical repository metadata.
    if args.app_version is not None and args.app_version != canonical_version:
        # Stop before tests, cleanup, or packaging can alter ignored outputs.
        raise SystemExit(f"--app-version must match canonical packaged application release {canonical_version}")
    # Reject a release tag that is not the canonical immutable version tag.
    if args.release_tag is not None and args.release_tag != f"v{canonical_version}":
        # Stop before tests when release-event identity diverges from the source tree.
        raise SystemExit(f"--release-tag must be v{canonical_version}")
    # Reject tracked or staged changes before any validator can claim exact-HEAD evidence.
    tracked_status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    ).strip()
    # Stop when candidate source bytes are not identical to the current commit.
    if tracked_status:
        # Report the invariant without echoing potentially private repository paths.
        raise SystemExit("tracked checkout must be clean before release validation")
    # Run every fixed validator before deleting or writing ignored candidate outputs.
    for command in VALIDATIONS:
        # Isolate the state-mutating API suite from repository runtime fixtures.
        if command is API_VALIDATION:
            # Run the exact command against a Git-archived clean source copy.
            run_api_isolated(command)
        # Run read-only validators directly against the exact clean checkout.
        else:
            # Fail fast so the provenance manifest can truthfully record every row as passed.
            run(command)
    # Remove stale ignored candidates only after all source validation succeeds.
    if DIST.exists():
        # Delete the known ignored distribution directory without touching source or data.
        shutil.rmtree(DIST)
    # Start the deterministic packager command with portable validation evidence.
    package_command = [sys.executable, "scripts/package_app.py"]
    # Add each completed validation command to the checksum-bound manifest.
    for command in VALIDATIONS:
        # Preserve fixed validation order for byte-reproducible JSON output.
        package_command.extend(["--validation", command_label(command)])
    # Record the copied-release process gate that must pass before candidate checksums are finalized.
    package_command.extend(["--validation", command_label(COPIED_SERVICE_SMOKE)])
    # Bind the candidate to a canonical release tag only on a release event.
    if args.release_tag is not None:
        # Forward the already validated tag to the deterministic packager.
        package_command.extend(["--release-tag", args.release_tag])
    # Bind the candidate to the retained immediately previous artifact when supplied.
    if args.previous_manifest is not None:
        # Forward the manifest path without copying its host path into provenance.
        package_command.extend(["--previous-manifest", str(args.previous_manifest)])
    # Build and listener-free smoke-test the deterministic application artifact.
    run(package_command)
    # Start the packaged production process on an ephemeral loopback port and prove lifecycle safety.
    run(COPIED_SERVICE_SMOKE)
    # Collect checksums only for the two canonical release assets.
    asset_names = ["release-manifest.json", "virtual_casino_simulator_package.zip"]
    # Render stable SHA-256 rows in lexical asset-name order.
    checksum_rows = [
        f"{hashlib.sha256((DIST / name).read_bytes()).hexdigest()}  {name}"
        for name in sorted(asset_names)
    ]
    # Write the companion checksum file with normalized newlines.
    (DIST / "checksums.txt").write_text("\n".join(checksum_rows) + "\n", encoding="utf-8", newline="\n")
    # Report sanitized release identity and stable ignored output names.
    print(f"Release {canonical_version} candidate assets are in dist/")
    # Return success only after validation, packaging, smoke, and checksums complete.
    return 0


# Run the release driver only when the module is executed directly.
if __name__ == "__main__":
    # Exit with the explicit result so CI receives fail-closed status.
    raise SystemExit(main())
