# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Validate permanent requirement identities, mappings, and generated-source integrity.
import json
import pathlib
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
    for req in requirements:
        # Set rid to the value needed for the next operation.
        rid = req.get("id", "")
        if not ID_RE.match(rid):
            errors.append(f"invalid requirement id: {rid}")
        if rid in seen:
            errors.append(f"duplicate requirement id: {rid}")
        seen.add(rid)
        if not req.get("module"):
            errors.append(f"{rid} missing module")
        if not req.get("description"):
            errors.append(f"{rid} missing description")
        if not req.get("status"):
            errors.append(f"{rid} missing status")
    if errors:
        # Write diagnostic output so the current operation can be inspected.
        print("Requirement validation failed:")
        for err in errors[:100]:
            # Write diagnostic output so the current operation can be inspected.
            print(f" - {err}")
        return 1
    # Write diagnostic output so the current operation can be inspected.
    print(f"Requirement validation passed for {len(requirements)} requirements.")
    return 0

if __name__ == "__main__":
    # Raise an error so invalid input or state is reported explicitly.
    raise SystemExit(main())
