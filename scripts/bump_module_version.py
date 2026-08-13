# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Apply validated semantic-version bumps to module descriptors.
import argparse
import json
import pathlib
# Import subprocess execution for canonical generated-document alignment.
import subprocess
# Import the active interpreter so generation uses the same supported runtime.
import sys

# Resolve the repository root independently of the caller's working directory.
ROOT = pathlib.Path(__file__).resolve().parents[1]

# Compute one semantic-version successor for the requested compatibility level.
def bump(version, level):
    # Parse the three governed numeric components before selecting the successor.
    major, minor, patch = [int(x) for x in version.split(".")]
    # Reset minor and patch components for an incompatible major transition.
    if level == "major":
        return f"{major+1}.0.0"
    # Reset the patch component for a compatible feature transition.
    if level == "minor":
        return f"{major}.{minor+1}.0"
    # Advance only the patch component for a compatible correction.
    return f"{major}.{minor}.{patch+1}"

# Apply one validated bump beneath an explicit repository root for CLI and test parity.
def bump_module(root, module_name, level):
    # Resolve the canonical aggregate beneath the caller-owned root.
    manifest_path = root / "modules" / "module-manifest.json"
    # Load the current aggregate before selecting one independent module.
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # Read the exact current revision and compute its one-step successor.
    current = manifest["modules"][module_name]
    new = bump(current, level)
    # Update only the selected aggregate entry.
    manifest["modules"][module_name] = new
    # Persist deterministic human-readable JSON with the repository's trailing-newline convention.
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    # Resolve and load only the matching module descriptor.
    module_path = root / "modules" / f"{module_name}.json"
    module = json.loads(module_path.read_text(encoding="utf-8"))
    # Keep the descriptor revision exactly aligned with the aggregate.
    module["version"] = new
    # Persist the one independently owned descriptor without touching any shared test pin file.
    module_path.write_text(json.dumps(module, indent=2) + "\n", encoding="utf-8")
    # Return both revisions for stable CLI diagnostics and focused tests.
    return current, new

# Parse one sanctioned module bump and leave all derived version docs aligned.
def main():
    # Define the exact module and compatibility-level CLI contract.
    parser = argparse.ArgumentParser()
    # Select a descriptor already governed by the aggregate manifest.
    parser.add_argument("module")
    # Restrict transitions to the three semantic-version compatibility levels.
    parser.add_argument("level", choices=["patch", "minor", "major"])
    # Reject malformed or incomplete invocations before any file is written.
    args = parser.parse_args()
    # Apply the exact module-local transition through the reusable helper.
    current, new = bump_module(ROOT, args.module, args.level)
    # Regenerate derived version documentation so the sanctioned CLI leaves validation-ready tracked bytes.
    subprocess.check_call([sys.executable, "scripts/generate_docs.py"], cwd=ROOT)
    # Write diagnostic output so the current operation can be inspected.
    print(f"Bumped {args.module}: {current} -> {new}")
    return 0

if __name__ == "__main__":
    # Raise an error so invalid input or state is reported explicitly.
    raise SystemExit(main())
