# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import pathlib
# Import required dependency so this module can use its public functions or constants.
import shutil
# Import required dependency so this module can use its public functions or constants.
import zipfile

# Set ROOT to the value needed for the next operation.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Set DIST to the value needed for the next operation.
DIST = ROOT / "dist"

# Define the main function used by this module.
def main():
    # Set DIST.mkdir(exist_ok to the value needed for the next operation.
    DIST.mkdir(exist_ok=True)
    # Set package to the value needed for the next operation.
    package = DIST / "virtual_casino_simulator_package.zip"
    # Branch when the following condition is true.
    if package.exists():
        # Execute this statement as part of the module's documented control flow.
        package.unlink()
    # Manage this resource with automatic setup and cleanup.
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as zf:
        # Iterate through the collection to process each item.
        for path in ROOT.rglob("*"):
            # Branch when the following condition is true.
            if path.is_dir():
                # Execute this statement as part of the module's documented control flow.
                continue
            # Branch when the following condition is true.
            if any(part in {".git", "dist", "data", "logs", "__pycache__"} for part in path.parts):
                # Execute this statement as part of the module's documented control flow.
                continue
            # Execute this statement as part of the module's documented control flow.
            zf.write(path, path.relative_to(ROOT.parent))
    # Write diagnostic output so the current operation can be inspected.
    print(f"Wrote {package}")
    # Return the computed value to the caller.
    return 0

# Branch when the following condition is true.
if __name__ == "__main__":
    # Raise an error so invalid input or state is reported explicitly.
    raise SystemExit(main())
