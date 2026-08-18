# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Bootstrap deterministic repository data and run safe baseline validators.
import pathlib
import shutil
import subprocess
import sys

# Set ROOT to the value needed for the next operation.
ROOT = pathlib.Path(__file__).resolve().parents[1]

# Define the run function used by this module.
def run(cmd, optional=False):
    # Write diagnostic output so the current operation can be inspected.
    print("+", " ".join(cmd))
    # Start protected logic so failures can be handled safely.
    try:
        # Set subprocess.check_call(cmd, cwd to the value needed for the next operation.
        subprocess.check_call(cmd, cwd=ROOT)
    # Handle the expected failure path for the protected logic.
    except Exception as exc:
        if optional:
            # Write diagnostic output so the current operation can be inspected.
            print(f"optional command failed: {exc}")
        # Handle the fallback branch when prior conditions did not match.
        else:
            raise

# Define the main function used by this module.
def main():
    for folder in ["data", "logs", "dist"]:
        # Set (ROOT / folder).mkdir(exist_ok to the value needed for the next operation.
        (ROOT / folder).mkdir(exist_ok=True)
    run([sys.executable, "-m", "py_compile", "run.py", "verify_rules.py", "tests/run_tests.py", "tests/runner.py"])
    run([sys.executable, "verify_rules.py"])
    # Enforce the monotonic escape-by-default innerHTML migration before broader API suites run. (SEC-017)
    run([sys.executable, "scripts/validate_inner_html_templates.py"])
    run([sys.executable, "tests/run_tests.py", "--api"])
    run([sys.executable, "scripts/validate_contracts.py"])
    run([sys.executable, "scripts/validate_module_boundaries.py"])
    # Validate catalog-owned backend, frontend, contract, route, and test-driver discovery hooks.
    run([sys.executable, "scripts/validate_game_catalog.py"])
    run([sys.executable, "scripts/validate_requirements.py"])
    run([sys.executable, "scripts/validate_versions.py"])
    run([sys.executable, "scripts/check_file_headers.py", "--check"])
    if shutil.which("node"):
        for path in ["web/app.js", "web/admin.js"]:
            # Set run(["node", "--check", path], optional to the value needed for the next operation.
            run(["node", "--check", path], optional=True)
        for path in sorted((ROOT / "web" / "core").glob("*.js")) + sorted((ROOT / "web" / "games").glob("*.js")):
            # Set run(["node", "--check", str(path.relative_to(ROOT))], option to the value needed for the next operation.
            run(["node", "--check", str(path.relative_to(ROOT))], optional=True)
    # Write diagnostic output so the current operation can be inspected.
    print("Repository bootstrap validation completed.")
    return 0

if __name__ == "__main__":
    # Raise an error so invalid input or state is reported explicitly.
    raise SystemExit(main())
