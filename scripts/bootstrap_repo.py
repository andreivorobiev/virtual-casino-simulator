# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
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
        # Branch when the following condition is true.
        if optional:
            # Write diagnostic output so the current operation can be inspected.
            print(f"optional command failed: {exc}")
        # Handle the fallback branch when prior conditions did not match.
        else:
            # Execute this statement as part of the module's documented control flow.
            raise

# Define the main function used by this module.
def main():
    # Iterate through the collection to process each item.
    for folder in ["data", "logs", "dist"]:
        # Set (ROOT / folder).mkdir(exist_ok to the value needed for the next operation.
        (ROOT / folder).mkdir(exist_ok=True)
    # Execute this statement as part of the module's documented control flow.
    run([sys.executable, "-m", "py_compile", "run.py", "verify_rules.py", "tests/run_tests.py"])
    # Execute this statement as part of the module's documented control flow.
    run([sys.executable, "verify_rules.py"])
    # Execute this statement as part of the module's documented control flow.
    run([sys.executable, "tests/run_tests.py", "--api"])
    # Execute this statement as part of the module's documented control flow.
    run([sys.executable, "scripts/validate_contracts.py"])
    # Execute this statement as part of the module's documented control flow.
    run([sys.executable, "scripts/validate_module_boundaries.py"])
    # Validate catalog-owned backend, frontend, contract, route, and test-driver discovery hooks.
    run([sys.executable, "scripts/validate_game_catalog.py"])
    # Execute this statement as part of the module's documented control flow.
    run([sys.executable, "scripts/validate_requirements.py"])
    # Execute this statement as part of the module's documented control flow.
    run([sys.executable, "scripts/validate_versions.py"])
    # Execute this statement as part of the module's documented control flow.
    run([sys.executable, "scripts/check_comment_density.py"])
    # Branch when the following condition is true.
    if shutil.which("node"):
        # Iterate through the collection to process each item.
        for path in ["web/app.js", "web/admin.js"]:
            # Set run(["node", "--check", path], optional to the value needed for the next operation.
            run(["node", "--check", path], optional=True)
        # Iterate through the collection to process each item.
        for path in sorted((ROOT / "web" / "core").glob("*.js")) + sorted((ROOT / "web" / "games").glob("*.js")):
            # Set run(["node", "--check", str(path.relative_to(ROOT))], option to the value needed for the next operation.
            run(["node", "--check", str(path.relative_to(ROOT))], optional=True)
    # Write diagnostic output so the current operation can be inspected.
    print("Repository bootstrap validation completed.")
    # Return the computed value to the caller.
    return 0

# Branch when the following condition is true.
if __name__ == "__main__":
    # Raise an error so invalid input or state is reported explicitly.
    raise SystemExit(main())
