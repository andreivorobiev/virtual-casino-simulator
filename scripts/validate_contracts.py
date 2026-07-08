# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import pathlib
# Import required dependency so this module can use its public functions or constants.
import sys

# Set ROOT to the value needed for the next operation.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Set CONTRACT_DIR to the value needed for the next operation.
CONTRACT_DIR = ROOT / "contracts" / "openapi"
# Set REQUIRED to the value needed for the next operation.
REQUIRED = [
    # Execute this statement as part of the module's documented control flow.
    "casino", "players", "ledger", "bots", "autoplay", "admin",
    # Execute this statement as part of the module's documented control flow.
    "roulette", "slots", "blackjack", "baccarat", "keno", "bingo",
]

# Define the main function used by this module.
def main():
    # Set errors to the value needed for the next operation.
    errors = []
    # Iterate through the collection to process each item.
    for name in REQUIRED:
        # Set path to the value needed for the next operation.
        path = CONTRACT_DIR / f"{name}.v1.yaml"
        # Branch when the following condition is true.
        if not path.exists():
            # Execute this statement as part of the module's documented control flow.
            errors.append(f"missing contract: {path}")
            # Execute this statement as part of the module's documented control flow.
            continue
        # Set text to the value needed for the next operation.
        text = path.read_text(encoding="utf-8")
        # Branch when the following condition is true.
        if "openapi: 3.0.3" not in text:
            # Execute this statement as part of the module's documented control flow.
            errors.append(f"{path} does not declare OpenAPI 3.0.3")
        # Branch when the following condition is true.
        if "paths:" not in text:
            # Execute this statement as part of the module's documented control flow.
            errors.append(f"{path} has no paths section")
        # Branch when the following condition is true.
        if "/api/v1/" not in text:
            # Execute this statement as part of the module's documented control flow.
            errors.append(f"{path} does not contain /api/v1 paths")
    # Set schema_dir to the value needed for the next operation.
    schema_dir = ROOT / "contracts" / "schemas"
    # Iterate through the collection to process each item.
    for required in ["api-response.schema.json", "ledger-event.schema.json", "module-manifest.schema.json"]:
        # Branch when the following condition is true.
        if not (schema_dir / required).exists():
            # Execute this statement as part of the module's documented control flow.
            errors.append(f"missing schema: {required}")
    # Branch when the following condition is true.
    if errors:
        # Write diagnostic output so the current operation can be inspected.
        print("Contract validation failed:")
        # Iterate through the collection to process each item.
        for err in errors:
            # Write diagnostic output so the current operation can be inspected.
            print(f" - {err}")
        # Return the computed value to the caller.
        return 1
    # Write diagnostic output so the current operation can be inspected.
    print(f"Contract validation passed for {len(REQUIRED)} OpenAPI files.")
    # Return the computed value to the caller.
    return 0

# Branch when the following condition is true.
if __name__ == "__main__":
    # Raise an error so invalid input or state is reported explicitly.
    raise SystemExit(main())
