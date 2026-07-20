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
    "auth", "admin-users", "feedback", "transactional-mail",
]
# Point to the mixed-surface Operations contract that cannot use the legacy v1-only skeleton rule.
OPERATIONS_CONTRACT = CONTRACT_DIR / "operations.v1.yaml"
# Point to the checked restricted-preview request and access policy.
PREVIEW_SECURITY_CONTRACT = ROOT / "contracts" / "compatibility" / "restricted-preview-security.json"
# Point to the inert one-time-token compatibility policy.
TOKEN_COMPATIBILITY_CONTRACT = ROOT / "contracts" / "compatibility" / "one-time-tokens-infrastructure.json"
# Point to the component-only v2 token contract that deliberately publishes no routes.
TOKEN_COMPONENT_CONTRACT = CONTRACT_DIR / "one-time-tokens.v2.yaml"
# Point to the disabled transactional-mail compatibility policy.
MAIL_COMPATIBILITY_CONTRACT = ROOT / "contracts" / "compatibility" / "transactional-mail.json"

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
        # Require exactly the two deliberately anonymous application routes.
        # Preserve only login, explicitly approved disposable guest entry, and liveness as anonymous routes.
        if preview_security.get("anonymous_routes") != ["/api/v2/auth/login", "/api/v2/auth/guest", "/healthz"]:
            # Fail closed when anonymous route scope expands or changes order.
            errors.append(f"{PREVIEW_SECURITY_CONTRACT} does not preserve the anonymous route allowlist")
        # Require public enrollment and live provider flows to stay disabled.
        access_policy = preview_security.get("access_policy", {})
        # Check each non-public stage switch explicitly.
        if access_policy.get("public_signup") is not False or access_policy.get("live_oauth") is not False or access_policy.get("admin_requires_admin_session") is not True:
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
    # Require the inert token compatibility policy to remain parseable and exact.
    try:
        # Parse the checked token policy without reading runtime secrets or state.
        token_policy = json.loads(TOKEN_COMPATIBILITY_CONTRACT.read_text(encoding="utf-8"))
        # Require the permanent artifact identity and inert stage.
        if token_policy.get("artifact") != "one-time-tokens-infrastructure" or token_policy.get("stage") != "inert-foundation":
            # Reject renamed or repurposed token policy records.
            errors.append(f"{TOKEN_COMPATIBILITY_CONTRACT} does not identify the inert token foundation")
        # Require the exact fixed purpose vocabulary.
        if token_policy.get("purposes") != ["invitation", "email_verification", "password_reset", "magic_link"]:
            # Reject purpose expansion without a separately reviewed contract change.
            errors.append(f"{TOKEN_COMPATIBILITY_CONTRACT} does not preserve the token purpose allowlist")
        # Require separate fixed policy records for every supported purpose.
        purpose_policies = token_policy.get("purpose_policies", {})
        # Check exact purpose membership and bounded default lifetimes together.
        if set(purpose_policies) != {"invitation", "email_verification", "password_reset", "magic_link"} or {purpose: details.get("default_ttl_seconds") for purpose, details in purpose_policies.items()} != {"invitation": 604800, "email_verification": 86400, "password_reset": 3600, "magic_link": 900}:
            # Reject collapsed, missing, expanded, or unbounded purpose policies.
            errors.append(f"{TOKEN_COMPATIBILITY_CONTRACT} does not preserve separate purpose policies")
        # Require every consumer and live-use authority to remain absent.
        authorization = token_policy.get("authorization", {})
        # Check repository approval separately from every denied live capability.
        if authorization.get("repository_merge_requires_separate_owner_approval") is not True or any(authorization.get(key) is not False for key in ("consumer_routes_authorized", "signup_authorized", "recovery_authorized", "mail_authorized", "oauth_authorized", "deployment_authorized", "public_exposure_authorized")):
            # Reject a compatibility artifact that widens authority.
            errors.append(f"{TOKEN_COMPATIBILITY_CONTRACT} does not preserve the inert authorization boundary")
        # Require the generic public error contract and frozen v1 boundary.
        if token_policy.get("public_errors") != {"consume_reason": "invalid_token", "request_reason": "invalid_request", "state_specific_reason_exposed": False} or token_policy.get("compatibility", {}).get("api_v1_frozen") is not True:
            # Reject enumeration or compatibility drift.
            errors.append(f"{TOKEN_COMPATIBILITY_CONTRACT} does not preserve generic errors and frozen v1")
    # Convert absent or malformed policy into one stable contract error.
    except (OSError, json.JSONDecodeError) as exc:
        # Report only the artifact path and exception class.
        errors.append(f"token compatibility policy could not be validated: {TOKEN_COMPATIBILITY_CONTRACT} ({type(exc).__name__})")
    # Require the component-only OpenAPI artifact to publish schemas and no routes.
    try:
        # Read the inert component contract as text for exact boundary checks.
        token_component_text = TOKEN_COMPONENT_CONTRACT.read_text(encoding="utf-8")
        # Require OpenAPI 3.0.3, an explicitly empty path map, and the fixed purpose vocabulary.
        if "openapi: 3.0.3" not in token_component_text or "paths: {}" not in token_component_text or not all(purpose in token_component_text for purpose in ("invitation", "email_verification", "password_reset", "magic_link")):
            # Reject malformed or incomplete component publication.
            errors.append(f"{TOKEN_COMPONENT_CONTRACT} does not preserve the inert v2 component contract")
        # Reject any concrete API route from the infrastructure-only artifact.
        if "/api/" in token_component_text:
            # Prevent the component contract from silently becoming a live surface.
            errors.append(f"{TOKEN_COMPONENT_CONTRACT} must not publish routes")
    # Convert an absent component artifact into one stable contract error.
    except OSError as exc:
        # Report only the artifact path and exception class.
        errors.append(f"token component contract could not be validated: {TOKEN_COMPONENT_CONTRACT} ({type(exc).__name__})")
    # Require the transactional-mail compatibility boundary to remain parseable and exact.
    try:
        # Parse the disabled infrastructure policy without reading any runtime mail configuration.
        mail_policy = json.loads(MAIL_COMPATIBILITY_CONTRACT.read_text(encoding="utf-8"))
        # Require the permanent identity, stage, purpose allowlist, and frozen v1 boundary.
        if mail_policy.get("artifact") != "transactional-mail" or mail_policy.get("stage") != "disabled-foundation" or mail_policy.get("purposes") != ["invitation", "email_verification", "password_reset", "magic_link"] or mail_policy.get("compatibility", {}).get("api_v1_frozen") is not True:
            # Reject renamed, widened, or compatibility-breaking policy records.
            errors.append(f"{MAIL_COMPATIBILITY_CONTRACT} does not preserve the disabled mail foundation")
        # Require the exact approved repository-only authority boundary.
        mail_authorization = mail_policy.get("authorization", {})
        # Check authorized inert surfaces separately from every denied live capability.
        if mail_authorization.get("repository_merge_approved_in_workroom_issue") != 23 or mail_authorization.get("disabled_infrastructure_authorized") is not True or mail_authorization.get("admin_readiness_authorized") is not True or any(mail_authorization.get(key) is not False for key in ("consumer_routes_authorized", "live_provider_delivery_authorized", "provider_account_changes_authorized", "credentials_authorized", "dns_or_email_auth_changes_authorized", "deployment_authorized", "public_signup_or_exposure_authorized")):
            # Reject any contract that widens the exact Workroom #23 approval.
            errors.append(f"{MAIL_COMPATIBILITY_CONTRACT} does not preserve the Workroom #23 authority boundary")
        # Require dual gates, at-most-once ambiguous handling, and raw-value exclusion.
        release_gates = mail_policy.get("release_gates", {})
        # Validate the two independent false defaults and their combined provider requirement.
        if release_gates.get("repository_feature_default") is not False or release_gates.get("network_release_default") is not False or release_gates.get("both_required_for_provider_access") is not True:
            # Reject a policy that could make provider access reachable under one switch.
            errors.append(f"{MAIL_COMPATIBILITY_CONTRACT} does not preserve independent release gates")
        # Read the lifecycle and persistence declarations for exact safety anchors.
        lifecycle = mail_policy.get("delivery_lifecycle", {})
        persistence = mail_policy.get("persistence", {})
        # Require caller idempotency, ambiguous-result freezing, and no raw bearer/provider persistence.
        if lifecycle.get("caller_idempotency_required") is not True or lifecycle.get("one_atomic_transport_claim_per_attempt") is not True or lifecycle.get("ambiguous_result") != "uncertain and never automatically retried" or persistence.get("tokened_url") != "never persisted" or persistence.get("provider_response") != "never persisted or logged":
            # Reject weakening of delivery duplication or data-minimization policy.
            errors.append(f"{MAIL_COMPATIBILITY_CONTRACT} does not preserve mail lifecycle safety")
    # Convert an absent or malformed policy into one stable contract diagnostic.
    except (OSError, json.JSONDecodeError) as exc:
        # Report only the checked artifact path and exception class.
        errors.append(f"mail compatibility policy could not be validated: {MAIL_COMPATIBILITY_CONTRACT} ({type(exc).__name__})")
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
    print(f"Contract validation passed for {len(REQUIRED) + len(REQUIRED_V2) + 4} shared policies and {len(GAMES)} catalog games.")
    # Return the computed value to the caller.
    return 0

# Branch when the following condition is true.
if __name__ == "__main__":
    # Raise an error so invalid input or state is reported explicitly.
    raise SystemExit(main())
