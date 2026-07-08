# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import argparse
# Import required dependency so this module can use its public functions or constants.
import json
# Import required dependency so this module can use its public functions or constants.
import pathlib

# Set ROOT to the value needed for the next operation.
ROOT = pathlib.Path(__file__).resolve().parents[1]

# Define the bump function used by this module.
def bump(version, level):
    # Set major, minor, patch to the value needed for the next operation.
    major, minor, patch = [int(x) for x in version.split(".")]
    # Branch when the following condition is true.
    if level == "major":
        # Return the computed value to the caller.
        return f"{major+1}.0.0"
    # Branch when the following condition is true.
    if level == "minor":
        # Return the computed value to the caller.
        return f"{major}.{minor+1}.0"
    # Return the computed value to the caller.
    return f"{major}.{minor}.{patch+1}"

# Define the main function used by this module.
def main():
    # Set parser to the value needed for the next operation.
    parser = argparse.ArgumentParser()
    # Execute this statement as part of the module's documented control flow.
    parser.add_argument("module")
    # Set parser.add_argument("level", choices to the value needed for the next operation.
    parser.add_argument("level", choices=["patch", "minor", "major"])
    # Set args to the value needed for the next operation.
    args = parser.parse_args()
    # Set manifest_path to the value needed for the next operation.
    manifest_path = ROOT / "modules" / "module-manifest.json"
    # Set manifest to the value needed for the next operation.
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # Set current to the value needed for the next operation.
    current = manifest["modules"][args.module]
    # Set new to the value needed for the next operation.
    new = bump(current, args.level)
    # Set manifest["modules"][args.module] to the value needed for the next operation.
    manifest["modules"][args.module] = new
    # Set manifest_path.write_text(json.dumps(manifest, indent to the value needed for the next operation.
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    # Set module_path to the value needed for the next operation.
    module_path = ROOT / "modules" / f"{args.module}.json"
    # Set module to the value needed for the next operation.
    module = json.loads(module_path.read_text(encoding="utf-8"))
    # Set module["version"] to the value needed for the next operation.
    module["version"] = new
    # Set module_path.write_text(json.dumps(module, indent to the value needed for the next operation.
    module_path.write_text(json.dumps(module, indent=2), encoding="utf-8")
    # Write diagnostic output so the current operation can be inspected.
    print(f"Bumped {args.module}: {current} -> {new}")
    # Return the computed value to the caller.
    return 0

# Branch when the following condition is true.
if __name__ == "__main__":
    # Raise an error so invalid input or state is reported explicitly.
    raise SystemExit(main())
