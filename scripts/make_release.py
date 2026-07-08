# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import argparse
# Import required dependency so this module can use its public functions or constants.
import hashlib
# Import required dependency so this module can use its public functions or constants.
import pathlib
# Import required dependency so this module can use its public functions or constants.
import shutil
# Import required dependency so this module can use its public functions or constants.
import subprocess
# Import required dependency so this module can use its public functions or constants.
import sys

# Set ROOT to the value needed for the next operation.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Set DIST to the value needed for the next operation.
DIST = ROOT / "dist"

# Define the run function used by this module.
def run(cmd):
    # Write diagnostic output so the current operation can be inspected.
    print("+", " ".join(cmd))
    # Set subprocess.check_call(cmd, cwd to the value needed for the next operation.
    subprocess.check_call(cmd, cwd=ROOT)

# Define the main function used by this module.
def main():
    # Set parser to the value needed for the next operation.
    parser = argparse.ArgumentParser()
    # Set parser.add_argument("--app-version", required to the value needed for the next operation.
    parser.add_argument("--app-version", required=True)
    # Set args to the value needed for the next operation.
    args = parser.parse_args()
    # Execute this statement as part of the module's documented control flow.
    run([sys.executable, "verify_rules.py"])
    # Execute this statement as part of the module's documented control flow.
    run([sys.executable, "tests/run_tests.py", "--api"])
    # Execute this statement as part of the module's documented control flow.
    run([sys.executable, "scripts/validate_contracts.py"])
    # Execute this statement as part of the module's documented control flow.
    run([sys.executable, "scripts/validate_module_boundaries.py"])
    # Execute this statement as part of the module's documented control flow.
    run([sys.executable, "scripts/validate_requirements.py"])
    # Execute this statement as part of the module's documented control flow.
    run([sys.executable, "scripts/validate_versions.py"])
    # Execute this statement as part of the module's documented control flow.
    run([sys.executable, "scripts/generate_docs.py"])
    # Execute this statement as part of the module's documented control flow.
    run([sys.executable, "scripts/package_app.py"])
    # Set DIST.mkdir(exist_ok to the value needed for the next operation.
    DIST.mkdir(exist_ok=True)
    # Set checks to the value needed for the next operation.
    checks = []
    # Iterate through the collection to process each item.
    for file in sorted(DIST.glob("*")):
        # Branch when the following condition is true.
        if file.is_file():
            # Execute this statement as part of the module's documented control flow.
            checks.append(f"{hashlib.sha256(file.read_bytes()).hexdigest()}  {file.name}")
    # Set (DIST / "checksums.txt").write_text("\n".join(checks) + "\n" to the value needed for the next operation.
    (DIST / "checksums.txt").write_text("\n".join(checks) + "\n", encoding="utf-8")
    # Write diagnostic output so the current operation can be inspected.
    print(f"Release {args.app_version} artifacts are in {DIST}")
    # Return the computed value to the caller.
    return 0

# Branch when the following condition is true.
if __name__ == "__main__":
    # Raise an error so invalid input or state is reported explicitly.
    raise SystemExit(main())
