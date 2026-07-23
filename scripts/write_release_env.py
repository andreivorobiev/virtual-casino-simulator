"""Write the deploy-time build-provenance environment fragment from a verified release manifest. (#287)

The runtime never invokes Git and never inspects checkout paths, so the only supported way to pin a
running deployment to a source commit is to supply `CASINO_BUILD_SHA` as ordinary configuration. This
tool derives that value from the checksum-bound release manifest produced by `scripts/package_app.py`
and writes exactly one non-secret assignment. It refuses every manifest whose recorded commit is not a
full lowercase 40-character Git SHA, so an unpinnable deployment fails at install time rather than
silently publishing `null` provenance from `/readyz` and the Admin Operations surface.
"""

# Import argument parsing for the deployment-invoked command line.
import argparse
# Import JSON parsing for the release manifest input.
import json
# Import filesystem paths for manifest and destination handling.
import pathlib
# Import regular expressions for exact commit validation.
import re
# Import process exit handling for fail-closed operator feedback.
import sys

# Accept only a full lowercase Git commit so short or symbolic references can never be deployed.
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
# Name the single Operations-owned provenance variable this tool is permitted to write.
BUILD_SHA_ENV = "CASINO_BUILD_SHA"


# Read the recorded source commit from a release manifest without echoing any other manifest content.
def manifest_commit(manifest_path: pathlib.Path) -> str:
    # Parse the manifest produced by the release pipeline.
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # Reject a manifest that is not the expected object shape.
    if not isinstance(manifest, dict):
        # Fail closed without including the parsed value in the message.
        raise ValueError("release manifest is not a JSON object")
    # Read the source block that carries release provenance.
    source = manifest.get("source")
    # Reject a manifest whose source block is missing or malformed.
    if not isinstance(source, dict):
        # Fail closed without including the parsed value in the message.
        raise ValueError("release manifest has no source block")
    # Read the recorded commit identity.
    commit = source.get("commit_sha")
    # Require an exact full lowercase commit so provenance is unambiguous.
    if not isinstance(commit, str) or not COMMIT_RE.fullmatch(commit):
        # Fail closed without including the rejected value in the message.
        raise ValueError("release manifest commit must be a full lowercase 40-character Git SHA")
    # Return the validated commit.
    return commit


# Render the complete environment fragment for one validated commit.
def render_fragment(commit: str) -> str:
    # Emit a purpose comment and exactly one assignment so the file can never carry a secret.
    return f"# Deployment build provenance for #287; regenerated per release and never hand-edited.\n{BUILD_SHA_ENV}={commit}\n"


# Write the fragment atomically so a partially written file can never be sourced by the service.
def write_fragment(destination: pathlib.Path, fragment: str) -> None:
    # Stage the bytes beside the destination so the replace stays on one filesystem.
    staging = destination.with_name(destination.name + ".tmp")
    # Write the staged fragment with fixed newlines for byte-stable deployment evidence.
    staging.write_text(fragment, encoding="utf-8", newline="\n")
    # Replace the destination atomically so readers see either the old or the new fragment.
    staging.replace(destination)


# Derive and write the provenance fragment for one deployment.
def main(argv=None) -> int:
    # Describe the deployment-only tool.
    parser = argparse.ArgumentParser(description="Write the CASINO_BUILD_SHA deployment fragment from a release manifest.")
    # Accept the verified release manifest that binds the artifact to its commit.
    parser.add_argument("--manifest", type=pathlib.Path, required=True, help="Path to the verified release-manifest.json")
    # Accept the destination environment fragment consumed by the service unit.
    parser.add_argument("--destination", type=pathlib.Path, required=True, help="Path to the generated release environment fragment")
    # Parse the deployment-supplied arguments.
    args = parser.parse_args(argv)
    # Start protected derivation so every failure prints one bounded operator message.
    try:
        # Resolve the validated commit from the manifest.
        commit = manifest_commit(args.manifest)
    # Convert malformed manifests and unreadable files into a fail-closed exit.
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        # Print only the bounded reason so manifest contents never enter deployment logs.
        print(f"release provenance unavailable: {exc}", file=sys.stderr)
        # Fail the deployment step rather than installing an unpinnable release.
        return 1
    # Persist the single validated assignment.
    write_fragment(args.destination, render_fragment(commit))
    # Report the pinned commit so the operator can compare it against the release directory.
    print(f"wrote {BUILD_SHA_ENV} for commit {commit}")
    # Report deployment-step success.
    return 0


# Run the tool when invoked directly by a deployment step.
if __name__ == "__main__":
    # Propagate the fail-closed exit status to the calling deployment shell.
    raise SystemExit(main())
