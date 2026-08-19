# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Bootstrap deterministic repository data and run safe baseline validators.
import pathlib
import shutil
import subprocess
import sys

# Anchor every validation command to the repository independently of the caller's directory.
ROOT = pathlib.Path(__file__).resolve().parents[1]

# Run one validator from the repository root while allowing explicitly optional tool checks.
def run(cmd, optional=False):
    # Write diagnostic output so the current operation can be inspected.
    print("+", " ".join(cmd))
    # Start protected logic so failures can be handled safely.
    try:
        # Preserve the child command's failure status so required gates stop the bootstrap.
        subprocess.check_call(cmd, cwd=ROOT)
    # Handle the expected failure path for the protected logic.
    except Exception as exc:
        if optional:
            # Write diagnostic output so the current operation can be inspected.
            print(f"optional command failed: {exc}")
        # Handle the fallback branch when prior conditions did not match.
        else:
            raise

# Prepare runtime directories and execute the repository's deterministic validation sequence.
def main():
    for folder in ["data", "logs", "dist"]:
        # Ensure expected runtime directories exist without disturbing their current contents.
        (ROOT / folder).mkdir(exist_ok=True)
    run([sys.executable, "-m", "py_compile", "run.py", "verify_rules.py", "tests/run_tests.py", "tests/runner.py"])
    run([sys.executable, "verify_rules.py"])
    # Enforce the monotonic escape-by-default innerHTML migration before broader API suites run. (SEC-017)
    run([sys.executable, "scripts/validate_inner_html_templates.py"])
    # Reject unreviewed large first-party sources and stale or overgrown audit-register entries. (TOOL-020)
    run([sys.executable, "scripts/validate_file_length.py"])
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
            # Syntax-check each application entry point when Node is locally available.
            run(["node", "--check", path], optional=True)
        for path in sorted((ROOT / "web" / "core").glob("*.js")) + sorted((ROOT / "web" / "games").glob("*.js")):
            # Syntax-check shared and game frontend modules without making Node a bootstrap prerequisite.
            run(["node", "--check", str(path.relative_to(ROOT))], optional=True)
    # Write diagnostic output so the current operation can be inspected.
    print("Repository bootstrap validation completed.")
    return 0

if __name__ == "__main__":
    # Raise an error so invalid input or state is reported explicitly.
    raise SystemExit(main())
