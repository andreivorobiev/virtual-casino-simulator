# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import json
# Import required dependency so this module can use its public functions or constants.
import pathlib
# Import required dependency so this module can use its public functions or constants.
import re

# Set ROOT to the value needed for the next operation.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Set REQ to the value needed for the next operation.
REQ = ROOT / "docs" / "requirements" / "requirements.json"
# Set ID_RE to the value needed for the next operation.
ID_RE = re.compile(r"^[A-Z][A-Z0-9-]*-\d{3}$")

# Define the main function used by this module.
def main():
    # Set data to the value needed for the next operation.
    data = json.loads(REQ.read_text(encoding="utf-8"))
    # Set requirements to the value needed for the next operation.
    requirements = data.get("requirements", [])
    # Set seen to the value needed for the next operation.
    seen = set()
    # Set errors to the value needed for the next operation.
    errors = []
    # Iterate through the collection to process each item.
    for req in requirements:
        # Set rid to the value needed for the next operation.
        rid = req.get("id", "")
        # Branch when the following condition is true.
        if not ID_RE.match(rid):
            # Execute this statement as part of the module's documented control flow.
            errors.append(f"invalid requirement id: {rid}")
        # Branch when the following condition is true.
        if rid in seen:
            # Execute this statement as part of the module's documented control flow.
            errors.append(f"duplicate requirement id: {rid}")
        # Execute this statement as part of the module's documented control flow.
        seen.add(rid)
        # Branch when the following condition is true.
        if not req.get("module"):
            # Execute this statement as part of the module's documented control flow.
            errors.append(f"{rid} missing module")
        # Branch when the following condition is true.
        if not req.get("description"):
            # Execute this statement as part of the module's documented control flow.
            errors.append(f"{rid} missing description")
        # Branch when the following condition is true.
        if not req.get("status"):
            # Execute this statement as part of the module's documented control flow.
            errors.append(f"{rid} missing status")
    # Branch when the following condition is true.
    if errors:
        # Write diagnostic output so the current operation can be inspected.
        print("Requirement validation failed:")
        # Iterate through the collection to process each item.
        for err in errors[:100]:
            # Write diagnostic output so the current operation can be inspected.
            print(f" - {err}")
        # Return the computed value to the caller.
        return 1
    # Write diagnostic output so the current operation can be inspected.
    print(f"Requirement validation passed for {len(requirements)} requirements.")
    # Return the computed value to the caller.
    return 0

# Branch when the following condition is true.
if __name__ == "__main__":
    # Raise an error so invalid input or state is reported explicitly.
    raise SystemExit(main())
