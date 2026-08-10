# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import json
# Import required dependency so this module can use its public functions or constants.
import pathlib
# Import required dependency so this module can use its public functions or constants.
import re
# Import sys so direct script execution resolves the current checkout before helper imports.
import sys

# Set ROOT to the value needed for the next operation.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Prefer the current checkout over unrelated installed packages during direct execution.
sys.path.insert(0, str(ROOT))
# Import the checked-source assembler so every ordinary requirement validation rejects aggregate drift.
from scripts.assemble_requirements import synchronize as synchronize_requirement_sources
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
    # Require byte-exact agreement between independently owned sources and the compatibility aggregate.
    try:
        # Check without writing so ordinary validation remains side-effect free.
        if not synchronize_requirement_sources(ROOT, write=False):
            # Provide the exact repair command for a stale generated aggregate.
            errors.append("requirements.json is stale; run python scripts/assemble_requirements.py --write")
    # Convert absent, malformed, or misowned source shards into one fail-closed diagnostic.
    except Exception as exc:
        # Preserve the exception class and bounded message for a focused source repair.
        errors.append(f"requirement source assembly failed: {type(exc).__name__}: {exc}")
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
