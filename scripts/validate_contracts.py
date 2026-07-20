# AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
# Import required dependency so this module can use its public functions or constants.
import pathlib
# Import JSON parsing for the restricted-preview compatibility artifact.
import json
# Import required dependency so this module can use its public functions or constants.
import sys

# Set ROOT to the value needed for the next operation.
ROOT = pathlib.Path(__file__).resolve().parents[1]
# Add the repository root before importing the runtime catalog facade.
sys.path.insert(0, str(ROOT))
# Import canonical game descriptors so contract discovery scales with the catalog.
from casino.config import GAMES
# Import the deterministic security inventory builder and checked artifact path.
from scripts.generate_server_authority_matrix import MATRIX_PATH, build_matrix
# Set CONTRACT_DIR to the value needed for the next operation.
CONTRACT_DIR = ROOT / "contracts" / "openapi"
# Set REQUIRED to the value needed for the next operation.
REQUIRED = ["casino", "players", "ledger", "bots", "autoplay", "admin"]
# Set REQUIRED_V2 to the value needed for the next operation.
REQUIRED_V2 = [
    # Execute this statement as part of the module's documented control flow.
    "auth", "admin-users",
]
# Point to the mixed-surface Operations contract that cannot use the legacy v1-only skeleton rule.
OPERATIONS_CONTRACT = CONTRACT_DIR / "operations.v1.yaml"
# Point to the checked restricted-preview request and access policy.
PREVIEW_SECURITY_CONTRACT = ROOT / "contracts" / "compatibility" / "restricted-preview-security.json"

# Define the main function used by this module.
def main():
    # Set errors to the value needed for the next operation.
    errors = []
    # Load and compare the hostile-client inventory before validating individual contracts.
    try:
        # Parse the checked artifact so malformed JSON is reported through the normal validator.
        authority_matrix = __import__("json").loads(MATRIX_PATH.read_text(encoding="utf-8"))
        # Require exact catalog and action alignment with current canonical sources.
        if authority_matrix != build_matrix():
            # Provide the generator command instead of masking the stale inventory.
            errors.append("server-authority matrix is stale; run python scripts/generate_server_authority_matrix.py")
    # Convert missing or malformed matrix failures into one contract diagnostic.
    except Exception as exc:
        # Report the exception class and message for a focused repair.
        errors.append(f"server-authority matrix could not be validated: {type(exc).__name__}: {exc}")
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
    # Validate the promoted Operations contract through its explicit least-privilege route policy.
    if not OPERATIONS_CONTRACT.exists():
        # Report the exact missing shared contract.
        errors.append(f"missing contract: {OPERATIONS_CONTRACT}")
    # Inspect all policy anchors only when the contract exists.
    else:
        # Read the mixed anonymous, authenticated, and Admin contract once.
        operations_text = OPERATIONS_CONTRACT.read_text(encoding="utf-8")
        # Require the exact approved routes and one anonymous security declaration.
        if not all(path in operations_text for path in ("/healthz:", "/readyz:", "/api/v2/admin/operations:")) or operations_text.count("security: []") != 1:
            # Fail closed when route or anonymous-policy drift occurs.
            errors.append(f"{OPERATIONS_CONTRACT} does not preserve the approved Operations route policy")
        # Require readiness and Admin telemetry to use the authenticated cookie scheme.
        if operations_text.count("- cookieSession: []") != 2:
            # Report authentication drift without exposing any runtime configuration.
            errors.append(f"{OPERATIONS_CONTRACT} does not protect readiness and Admin telemetry")
    # Require the restricted-preview policy artifact to remain parseable and exact.
    try:
        # Parse the checked policy without evaluating any runtime configuration.
        preview_security = json.loads(PREVIEW_SECURITY_CONTRACT.read_text(encoding="utf-8"))
        # Require the permanent artifact identity and stage.
        if preview_security.get("artifact") != "restricted-preview-security" or preview_security.get("stage") != "restricted-preview":
            # Reject renamed or repurposed policy records.
            errors.append(f"{PREVIEW_SECURITY_CONTRACT} does not identify the restricted-preview policy")
        # Require exactly the reviewed login, disabled-by-default OAuth, and liveness routes.
        expected_anonymous = ["/api/v2/auth/login", "/api/v2/auth/oauth/providers", "/api/v2/auth/oauth/{google|facebook}/start", "/api/v2/auth/oauth/{google|facebook}/callback", "/healthz"]
        # Compare the complete ordered allowlist so generalized provider routes fail validation.
        if preview_security.get("anonymous_routes") != expected_anonymous:
            # Fail closed when anonymous route scope expands or changes order.
            errors.append(f"{PREVIEW_SECURITY_CONTRACT} does not preserve the anonymous route allowlist")
        # Require public enrollment disabled and provider auth bounded to disabled-default invite users.
        access_policy = preview_security.get("access_policy", {})
        # Check each non-public stage switch explicitly.
        if access_policy.get("public_signup") is not False or access_policy.get("oauth_disabled_by_default") is not True or access_policy.get("oauth_existing_invite_users_only") is not True or access_policy.get("admin_requires_admin_session") is not True:
            # Report access-policy drift without runtime details.
            errors.append(f"{PREVIEW_SECURITY_CONTRACT} does not preserve restricted-preview access")
        # Require exact request integrity rather than advisory browser behavior.
        integrity = preview_security.get("request_integrity", {})
        # Check canonical Host, Origin, and distinct CSRF proof together.
        if integrity.get("origin") != "exact" or integrity.get("csrf") != "per-session-distinct" or integrity.get("host") != "exact-canonical-authority":
            # Reject weakened request-integrity descriptions.
            errors.append(f"{PREVIEW_SECURITY_CONTRACT} does not preserve exact request integrity")
    # Convert absent or malformed preview policy into one stable contract error.
    except (OSError, json.JSONDecodeError) as exc:
        # Report only the artifact path and exception class.
        errors.append(f"restricted-preview policy could not be validated: {PREVIEW_SECURITY_CONTRACT} ({type(exc).__name__})")
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
    print(f"Contract validation passed for {len(REQUIRED) + len(REQUIRED_V2) + 2} shared policies and {len(GAMES)} catalog games.")
    # Return the computed value to the caller.
    return 0

# Branch when the following condition is true.
if __name__ == "__main__":
    # Raise an error so invalid input or state is reported explicitly.
    raise SystemExit(main())
