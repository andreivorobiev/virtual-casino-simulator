# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import json
# Import required dependency so this module can use its public functions or constants.
import pathlib
# Import required dependency so this module can use its public functions or constants.
import re

# Set ROOT to the value needed for the next operation.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Set MANIFEST to the value needed for the next operation.
MANIFEST = ROOT / "modules" / "module-manifest.json"
# Set VERSION_RE to the value needed for the next operation.
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")

# Define the main function used by this module.
def main():
    # Set data to the value needed for the next operation.
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    # Set errors to the value needed for the next operation.
    errors = []
    # Branch when the following condition is true.
    if not VERSION_RE.match(data.get("application", "")):
        # Execute this statement as part of the module's documented control flow.
        errors.append("application version is not semantic x.y.z")
    # Iterate through the collection to process each item.
    for module, version in data.get("modules", {}).items():
        # Branch when the following condition is true.
        if not VERSION_RE.match(version):
            # Execute this statement as part of the module's documented control flow.
            errors.append(f"module {module} version {version} is not semantic x.y.z")
        # Set module_file to the value needed for the next operation.
        module_file = ROOT / "modules" / f"{module}.json"
        # Branch when the following condition is true.
        if not module_file.exists():
            # Execute this statement as part of the module's documented control flow.
            errors.append(f"missing module manifest for {module}")
            # Execute this statement as part of the module's documented control flow.
            continue
        # Set body to the value needed for the next operation.
        body = json.loads(module_file.read_text(encoding="utf-8"))
        # Branch when the following condition is true.
        if body.get("version") != version:
            # Execute this statement as part of the module's documented control flow.
            errors.append(f"module {module} version mismatch between manifest and module file")
    # Branch when the following condition is true.
    if errors:
        # Write diagnostic output so the current operation can be inspected.
        print("Version validation failed:")
        # Iterate through the collection to process each item.
        for err in errors:
            # Write diagnostic output so the current operation can be inspected.
            print(f" - {err}")
        # Return the computed value to the caller.
        return 1
    # Write diagnostic output so the current operation can be inspected.
    print(f"Version validation passed for {len(data.get('modules', {}))} modules.")
    # Return the computed value to the caller.
    return 0

# Branch when the following condition is true.
if __name__ == "__main__":
    # Raise an error so invalid input or state is reported explicitly.
    raise SystemExit(main())
