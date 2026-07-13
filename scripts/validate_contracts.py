# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import pathlib
# Import required dependency so this module can use its public functions or constants.
import sys

# Set ROOT to the value needed for the next operation.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Add the repository root before importing the runtime catalog facade.
sys.path.insert(0, str(ROOT))
# Import canonical game descriptors so contract discovery scales with the catalog.
from casino.config import GAMES
# Set CONTRACT_DIR to the value needed for the next operation.
CONTRACT_DIR = ROOT / "contracts" / "openapi"
# Set REQUIRED to the value needed for the next operation.
REQUIRED = ["casino", "players", "ledger", "bots", "autoplay", "admin"]
# Set REQUIRED_V2 to the value needed for the next operation.
REQUIRED_V2 = [
    # Execute this statement as part of the module's documented control flow.
    "auth", "admin-users",
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
    # Validate every game-owned contract discovered from the canonical catalog.
    for game in GAMES:
        # Require each playable game to declare at least one public contract.
        if not game.get("contracts"):
            # Report the catalog id so the owning game slice can repair its descriptor.
            errors.append(f"catalog game {game['id']} has no contracts")
        # Validate every contract path owned by this catalog entry.
        for relative_path in game.get("contracts", []):
            # Resolve the declared contract beneath the repository root.
            path = ROOT / relative_path
            # Reject missing contract files before inspecting their contents.
            if not path.exists():
                # Report the exact missing declaration.
                errors.append(f"missing catalog contract: {relative_path}")
                # Continue to the next contract without reading an absent file.
                continue
            # Read the contract as text for the established skeleton checks.
            text = path.read_text(encoding="utf-8")
            # Require current game contracts to remain on the frozen v1 compatibility surface.
            if "openapi: 3.0.3" not in text or "/api/v1/" not in text:
                # Report malformed or wrongly versioned catalog contracts together.
                errors.append(f"catalog contract {relative_path} is not an OpenAPI 3.0.3 v1 contract")
    # Iterate through the collection to process each item.
    for name in REQUIRED_V2:
        # Set path to the value needed for the next operation.
        path = CONTRACT_DIR / f"{name}.v2.yaml"
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
        if "/api/v2" not in text:
            # Execute this statement as part of the module's documented control flow.
            errors.append(f"{path} does not contain /api/v2 paths")
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
    print(f"Contract validation passed for {len(REQUIRED) + len(REQUIRED_V2)} shared APIs and {len(GAMES)} catalog games.")
    # Return the computed value to the caller.
    return 0

# Branch when the following condition is true.
if __name__ == "__main__":
    # Raise an error so invalid input or state is reported explicitly.
    raise SystemExit(main())
