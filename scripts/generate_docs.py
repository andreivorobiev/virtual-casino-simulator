# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import argparse
# Import required dependency so this module can use its public functions or constants.
import json
# Import required dependency so this module can use its public functions or constants.
import pathlib

# Set ROOT to the value needed for the next operation.
ROOT = pathlib.Path(__file__).resolve().parents[1]

# Define the render_markdown function used by this module.
def render_markdown():
    # Set req to the value needed for the next operation.
    req = json.loads((ROOT / "docs" / "requirements" / "requirements.json").read_text(encoding="utf-8"))
    # Set modules to the value needed for the next operation.
    modules = json.loads((ROOT / "modules" / "module-manifest.json").read_text(encoding="utf-8"))
    # Set lines to the value needed for the next operation.
    lines = ["# Virtual Casino Requirements and Validation", "", f"Application: {modules['application']}", "", "## Modules", ""]
    # Iterate through the collection to process each item.
    for name, version in modules.get("modules", {}).items():
        # Execute this statement as part of the module's documented control flow.
        lines.append(f"- {name}: {version}")
    # Set lines + to the value needed for the next operation.
    lines += ["", "## Requirements", ""]
    # Iterate through the collection to process each item.
    for r in req.get("requirements", []):
        # Execute this statement as part of the module's documented control flow.
        lines.append(f"- **{r['id']}** ({r.get('module','')}) - {r.get('status','')}: {r.get('description','')}")
    # Return the computed value to the caller.
    return "\n".join(lines) + "\n"

# Define the main function used by this module.
def main():
    # Set parser to the value needed for the next operation.
    parser = argparse.ArgumentParser()
    # Set parser.add_argument("--check", action to the value needed for the next operation.
    parser.add_argument("--check", action="store_true")
    # Set args to the value needed for the next operation.
    args = parser.parse_args()
    # Set out to the value needed for the next operation.
    out = ROOT / "docs" / "requirements" / "requirements_generated.md"
    # Set text to the value needed for the next operation.
    text = render_markdown()
    # Branch when the following condition is true.
    if args.check and out.exists() and out.read_text(encoding="utf-8") != text:
        # Write diagnostic output so the current operation can be inspected.
        print("Generated docs are out of date; run python scripts/generate_docs.py")
        # Return the computed value to the caller.
        return 1
    # Set out.write_text(text, encoding to the value needed for the next operation.
    out.write_text(text, encoding="utf-8")
    # Write diagnostic output so the current operation can be inspected.
    print(f"Wrote {out}")
    # Return the computed value to the caller.
    return 0

# Branch when the following condition is true.
if __name__ == "__main__":
    # Raise an error so invalid input or state is reported explicitly.
    raise SystemExit(main())
