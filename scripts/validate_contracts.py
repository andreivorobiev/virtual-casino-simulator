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
    "auth", "admin-users", "transactional-mail", "invitations", "feedback", "user-settings", "self-service-batch",
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
# Point to the disabled restricted-preview invitation compatibility policy.
INVITATION_COMPATIBILITY_CONTRACT = ROOT / "contracts" / "compatibility" / "invitation-enrollment.json"
# Point to the owner-approved disabled invite-only OAuth compatibility policy.
OAUTH_COMPATIBILITY_CONTRACT = ROOT / "contracts" / "compatibility" / "oauth-invite-only-runtime.json"
# Point to the manual-only Workroom-approved feedback compatibility policy.
FEEDBACK_COMPATIBILITY_CONTRACT = ROOT / "contracts" / "compatibility" / "manual-feedback-reporting.json"
# Point to the module-to-contract compatibility matrix that must mirror every module descriptor's declared contracts. (issue #415)
MODULE_API_MATRIX_PATH = ROOT / "contracts" / "compatibility" / "module-api-matrix.json"
# Point to the frozen-contract digest map that must cover and match every declared contract file. (issue #415)
CONTRACT_DIGESTS_PATH = ROOT / "contracts" / "compatibility" / "contract-digests.json"


# Rebuild the module-to-contract map from the authoritative per-module descriptors. (issue #415)
def build_module_contract_map():
    # Collect only modules that declare a contracts list so inert modules stay absent.
    mapping = {}
    # Iterate the descriptor directory deterministically so regeneration is stable.
    for module_path in sorted((ROOT / "modules").glob("*.json")):
        # Skip the aggregate manifest because it is not a module descriptor.
        if module_path.stem == "module-manifest":
            # Continue with the next descriptor.
            continue
        # Read the descriptor's declared contract list without trusting absent keys.
        declared = json.loads(module_path.read_text(encoding="utf-8")).get("contracts", [])
        # Record only modules that publish at least one contract surface.
        if declared:
            # Copy the list so later mutation cannot alias the descriptor content.
            mapping[module_path.stem] = list(declared)
    # Return the deterministic module-to-contract map.
    return mapping


# Recompute the digest map covering declared contracts plus every already-frozen extra entry. (issue #415)
def build_contract_digests(existing):
    # Import hashing locally so the validator's import surface stays unchanged for other callers.
    import hashlib
    # Start from every module-declared contract path.
    paths = {rel for declared in build_module_contract_map().values() for rel in declared}
    # Preserve non-module frozen entries so regeneration never silently drops an existing freeze.
    paths.update(existing.keys())
    # Compute one current digest per existing contract file.
    digests = {}
    # Iterate deterministically so the artifact diff stays reviewable.
    for rel in sorted(paths):
        # Resolve the tracked contract file beneath the repository root.
        target = ROOT / rel
        # Digest only files that exist; missing files stay absent so the checker reports them.
        if target.is_file():
            # Record the exact frozen-byte identity of the contract.
            digests[rel] = hashlib.sha256(target.read_bytes()).hexdigest()
    # Return the complete regenerated digest map.
    return digests


# Verify or regenerate both compatibility artifacts against the module descriptors. (issue #415)
def check_compatibility_artifacts(errors, write=False):
    # Import hashing locally for the per-file drift comparison.
    import hashlib
    # Start protected artifact handling so malformed JSON reports through the normal validator envelope.
    try:
        # Parse the tracked matrix artifact.
        matrix = json.loads(MODULE_API_MATRIX_PATH.read_text(encoding="utf-8"))
        # Parse the tracked digest artifact.
        digests = json.loads(CONTRACT_DIGESTS_PATH.read_text(encoding="utf-8"))
    # Convert absent or malformed artifacts into one stable diagnostic per file.
    except (OSError, json.JSONDecodeError) as exc:
        # Report only the artifact family and exception class.
        errors.append(f"compatibility matrix artifacts could not be parsed ({type(exc).__name__})")
        # Stop artifact checking because neither comparison is possible.
        return
    # Rebuild the authoritative module map once for both modes.
    expected_matrix = build_module_contract_map()
    # Regenerate both artifacts in place when the caller asked for repair.
    if write:
        # Merge descriptor-declared rows over the tracked matrix so curated non-declaring rows are never dropped.
        merged_matrix = {**matrix, **expected_matrix}
        # Write the regenerated matrix with stable formatting for reviewable diffs.
        MODULE_API_MATRIX_PATH.write_text(json.dumps(merged_matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        # Write the regenerated digest map preserving already-frozen extra entries.
        CONTRACT_DIGESTS_PATH.write_text(json.dumps(build_contract_digests(digests), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        # Report the repair without failing the run.
        print("Regenerated module-api-matrix.json and contract-digests.json from module descriptors.")
        # Skip checking because the artifacts were just rewritten from source.
        return
    # Require every declaring module to appear in the matrix with its exact contract list.
    for module, declared in expected_matrix.items():
        # Compare the tracked row against the descriptor's declaration.
        if matrix.get(module) != declared:
            # Name the stale module and the regeneration command.
            errors.append(f"module-api-matrix.json is stale for {module}; run python scripts/validate_contracts.py --write-compatibility")
    # Require every curated non-declaring row to reference only files that still exist.
    for module, listed in matrix.items():
        # Check only rows the descriptors do not own so declaring modules are not double-reported.
        if module not in expected_matrix:
            # Iterate the curated row's contract paths.
            for rel in listed:
                # Report references to contract files that no longer exist.
                if not (ROOT / rel).is_file():
                    # Name the curated row and its dangling reference.
                    errors.append(f"module-api-matrix.json row {module} references missing contract file {rel}")
    # Require a present, current digest for every declared contract path.
    for module, declared in expected_matrix.items():
        # Iterate each declared contract surface.
        for rel in declared:
            # Resolve the tracked contract file.
            target = ROOT / rel
            # Report a declared contract whose file is absent.
            if not target.is_file():
                # Name the missing file through the module that declares it.
                errors.append(f"{module} declares missing contract file {rel}")
                # Continue with the next declared path.
                continue
            # Compare the frozen digest against current bytes.
            if digests.get(rel) != hashlib.sha256(target.read_bytes()).hexdigest():
                # Name the drifted or missing digest entry and the regeneration command.
                errors.append(f"contract-digests.json is stale or missing for {rel}; run python scripts/validate_contracts.py --write-compatibility")
    # Require every already-frozen extra entry to stay current so silent contract drift is impossible.
    for rel in digests:
        # Resolve the frozen file for drift comparison.
        target = ROOT / rel
        # Report frozen entries whose file disappeared or whose bytes drifted.
        if not target.is_file() or digests[rel] != hashlib.sha256(target.read_bytes()).hexdigest():
            # Name the drifted freeze without duplicating the declared-path diagnostics.
            if not any(rel in declared for declared in expected_matrix.values()):
                # Report the standalone frozen entry drift.
                errors.append(f"contract-digests.json is stale for standalone entry {rel}")

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
        # Require readiness and Admin telemetry to expose the bounded deployment monitor scheme.
        if operations_text.count("- monitorBearer: []") != 2 or "accepted only for /readyz and /api/v2/admin/operations" not in operations_text:
            # Report monitor-auth drift without exposing any runtime configuration.
            errors.append(f"{OPERATIONS_CONTRACT} does not preserve the deployment monitor boundary")
    # Require the restricted-preview policy artifact to remain parseable and exact.
    try:
        # Parse the checked policy without evaluating any runtime configuration.
        preview_security = json.loads(PREVIEW_SECURITY_CONTRACT.read_text(encoding="utf-8"))
        # Require the permanent artifact identity and stage.
        if preview_security.get("artifact") != "restricted-preview-security" or preview_security.get("stage") != "restricted-preview":
            # Reject renamed or repurposed policy records.
            errors.append(f"{PREVIEW_SECURITY_CONTRACT} does not identify the restricted-preview policy")
        # Preserve login, approved guest/invitation entry, disabled enrollment policy/signup, disabled provider status/start/callback, CSRF recovery, and liveness as anonymous routes. (issue #224)
        if preview_security.get("anonymous_routes") != ["/api/v2/auth/login", "/api/v2/auth/guest", "/api/v2/auth/redeem-invitation", "/api/v2/auth/enrollment-policy", "/api/v2/auth/signup", "/api/v2/auth/oauth/providers", "/api/v2/auth/csrf", "/api/v2/auth/oauth/{google|facebook}/start", "/api/v2/auth/oauth/{google|facebook}/callback", "/healthz"]:
            # Fail closed when anonymous route scope expands or changes order.
            errors.append(f"{PREVIEW_SECURITY_CONTRACT} does not preserve the anonymous route allowlist")
        # Require public enrollment and live provider flows to stay disabled.
        access_policy = preview_security.get("access_policy", {})
        # Check each non-public stage switch explicitly.
        if access_policy.get("public_signup") is not False or access_policy.get("live_oauth") is not False or access_policy.get("admin_requires_admin_session") is not True or access_policy.get("monitor_bearer_limited_to_operations") is not True or access_policy.get("oauth_provider_flags_default_false") is not True or access_policy.get("oauth_provider_network_release_flags_default_false") is not True or access_policy.get("oauth_existing_private_invite_accounts_only") is not True:
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
    # Require the separately approved disabled invitation compatibility boundary to remain exact.
    try:
        # Parse the invitation policy without reading runtime configuration or private state.
        invitation_policy = json.loads(INVITATION_COMPATIBILITY_CONTRACT.read_text(encoding="utf-8"))
        # Require permanent artifact identity, stage, and frozen v1 compatibility.
        if invitation_policy.get("artifact") != "invitation-enrollment" or invitation_policy.get("stage") != "disabled-restricted-preview" or invitation_policy.get("compatibility", {}).get("api_v1_frozen") is not True:
            # Reject renamed, widened, or compatibility-breaking invitation policy.
            errors.append(f"{INVITATION_COMPATIBILITY_CONTRACT} does not identify the disabled invitation boundary")
        # Require the exact Workroom #24 repository-only authorization and every denied live capability.
        invitation_authorization = invitation_policy.get("authorization", {})
        # Check the two disabled code surfaces separately from live, provider, deployment, and public authority.
        if invitation_authorization.get("repository_merge_approved_in_workroom_issue") != 24 or invitation_authorization.get("disabled_admin_invitation_authorized") is not True or invitation_authorization.get("disabled_private_redemption_authorized") is not True or any(invitation_authorization.get(key) is not False for key in ("live_mail_authorized", "live_enrollment_authorized", "provider_or_network_authorized", "dns_authorized", "deployment_authorized", "public_signup_or_exposure_authorized")):
            # Reject any widening beyond the exact owner-approved disabled repository scope.
            errors.append(f"{INVITATION_COMPATIBILITY_CONTRACT} does not preserve the Workroom #24 authority boundary")
        # Require all independent false defaults and frozen generic public error semantics.
        invitation_gates = invitation_policy.get("release_gates", {})
        # Check invitation, redemption, mail feature, and mail network gates together.
        if any(invitation_gates.get(key) is not False for key in ("invitation_issuance_default", "redemption_default", "mail_feature_default", "mail_network_release_default")) or invitation_gates.get("all_required_for_live_delivery") is not True or invitation_policy.get("privacy", {}).get("public_error") != "one generic invitation_unavailable reason":
            # Reject a policy that makes enrollment reachable or enumerable under one switch.
            errors.append(f"{INVITATION_COMPATIBILITY_CONTRACT} does not preserve disabled gates and generic errors")
    # Convert absent or malformed policy into one stable contract diagnostic.
    except (OSError, json.JSONDecodeError) as exc:
        # Report only the checked artifact path and exception class.
        errors.append(f"invitation compatibility policy could not be validated: {INVITATION_COMPATIBILITY_CONTRACT} ({type(exc).__name__})")
    # Require the separately approved disabled invite-only OAuth compatibility boundary to remain exact.
    try:
        # Parse the OAuth policy without reading runtime credentials, proofs, or identity state.
        oauth_policy = json.loads(OAUTH_COMPATIBILITY_CONTRACT.read_text(encoding="utf-8"))
        # Require frozen v1 compatibility and the exact implemented-disabled repository status.
        if oauth_policy.get("status") != "implemented_disabled_by_default" or oauth_policy.get("v1_compatibility", {}).get("policy") != "unchanged":
            # Reject a renamed, widened, or compatibility-breaking policy.
            errors.append(f"{OAUTH_COMPATIBILITY_CONTRACT} does not preserve disabled OAuth compatibility")
        # Read the additive route declarations once for exact boundary checks.
        oauth_routes = oauth_policy.get("v2_endpoints", [])
        # Require the six exact routes and continued denial of signup, user creation, merge, and email linking.
        if oauth_routes != ["GET /api/v2/auth/oauth/providers", "POST /api/v2/auth/oauth/{google|facebook}/start", "GET /api/v2/auth/oauth/{google|facebook}/callback", "GET /api/v2/me/oauth/providers", "POST /api/v2/me/oauth/{google|facebook}/unlink", "GET /api/v2/admin/oauth/providers"] or oauth_policy.get("account_boundary", {}).get("public_signup") is not False or oauth_policy.get("account_boundary", {}).get("provider_user_creation") is not False or oauth_policy.get("account_boundary", {}).get("email_matching_or_linking") is not False:
            # Reject route expansion or any provider-selected account behavior.
            errors.append(f"{OAUTH_COMPATIBILITY_CONTRACT} does not preserve the invite-only account boundary")
        # Read both provider-specific false-default gate declarations.
        provider_flags = oauth_policy.get("provider_flags", {})
        # Require exact provider enable/release names and their conjunctive runtime policy.
        if provider_flags.get("google") != ["CASINO_OAUTH_ENABLED_GOOGLE defaults false", "CASINO_OAUTH_NETWORK_RELEASED_GOOGLE defaults false"] or provider_flags.get("facebook") != ["CASINO_OAUTH_ENABLED_FACEBOOK defaults false", "CASINO_OAUTH_NETWORK_RELEASED_FACEBOOK defaults false"] or provider_flags.get("runtime_available") != "provider configuration readiness AND its independent provider-network release latch":
            # Reject any single-switch or cross-provider release policy.
            errors.append(f"{OAUTH_COMPATIBILITY_CONTRACT} does not preserve independent OAuth release gates")
        # Read the durable flow policy once for recovery and separation checks.
        flow_security = oauth_policy.get("flow_security", {})
        # Require recoverable claims, terminal replay protection, and physically separate metadata/proofs.
        if flow_security.get("recoverable_atomic_one_time_flow") is not True or flow_security.get("replay_rejected") is not True or not flow_security.get("durable_separation", {}).get("metadata") or not flow_security.get("durable_separation", {}).get("exchange_proofs"):
            # Reject weakened replay, ambiguity, or proof-separation policy.
            errors.append(f"{OAUTH_COMPATIBILITY_CONTRACT} does not preserve OAuth flow safety")
        # Require exact Workroom approval traceability and continued denial of live release authority.
        if "Workroom #25 owner comment 5027642551" not in oauth_policy.get("repository_merge_approval", "") or "do not authorize live provider" not in oauth_policy.get("gate_policy", ""):
            # Reject missing repository authority or accidental live authority.
            errors.append(f"{OAUTH_COMPATIBILITY_CONTRACT} does not preserve the Workroom #25 authority boundary")
    # Convert absent or malformed policy into one stable contract diagnostic.
    except (OSError, json.JSONDecodeError) as exc:
        # Report only the checked artifact path and exception class.
        errors.append(f"OAuth compatibility policy could not be validated: {OAUTH_COMPATIBILITY_CONTRACT} ({type(exc).__name__})")
    # Require the narrowed manual-only feedback authority and compatibility boundary to remain exact.
    try:
        # Parse the checked policy without inspecting any retained user report data.
        feedback_policy = json.loads(FEEDBACK_COMPATIBILITY_CONTRACT.read_text(encoding="utf-8"))
        # Require the exact artifact, additive v2 contract, and frozen v1 surface.
        if feedback_policy.get("artifact") != "manual-feedback-reporting" or feedback_policy.get("compatibility", {}).get("api_v1_frozen") is not True or feedback_policy.get("compatibility", {}).get("contract") != "contracts/openapi/feedback.v2.yaml":
            # Reject renamed, missing, or compatibility-breaking manual feedback policy.
            errors.append(f"{FEEDBACK_COMPATIBILITY_CONTRACT} does not preserve additive feedback compatibility")
        # Read the exact Workroom decision boundary once.
        feedback_authorization = feedback_policy.get("authorization", {})
        # Require manual capture and triage while denying every external, guest, deployment, and public capability.
        if feedback_authorization.get("workroom_issue") != 28 or feedback_authorization.get("decision_comment") != 5049349447 or feedback_authorization.get("sanitized_manual_draft") is not True or feedback_authorization.get("manual_issue_link_recording") is not True or any(feedback_authorization.get(key) is not False for key in ("automatic_github_publication", "external_issue_mutation", "credentials_authorized", "guest_or_anonymous_reporting", "deployment_or_public_exposure")):
            # Reject scope widening beyond the owner-approved manual-only slice.
            errors.append(f"{FEEDBACK_COMPATIBILITY_CONTRACT} does not preserve the Workroom #28 authority boundary")
        # Require privacy-safe reporter, export, and malformed-state recovery declarations.
        if feedback_policy.get("compatibility", {}).get("publication_mode") != "manual_only" or feedback_policy.get("privacy", {}).get("reporter") != "HMAC-derived opaque reference only" or feedback_policy.get("privacy", {}).get("export") != "metadata and evidence digests only" or feedback_policy.get("storage", {}).get("malformed_state") != "preserved unchanged for operator recovery":
            # Reject privacy or recoverability weakening.
            errors.append(f"{FEEDBACK_COMPATIBILITY_CONTRACT} does not preserve feedback privacy and recovery")
    # Convert an absent or malformed policy into one stable contract diagnostic.
    except (OSError, json.JSONDecodeError) as exc:
        # Report only the checked artifact path and exception class.
        errors.append(f"feedback compatibility policy could not be validated: {FEEDBACK_COMPATIBILITY_CONTRACT} ({type(exc).__name__})")
    # Enforce module-to-contract matrix coverage and frozen digest currency. (issue #415)
    check_compatibility_artifacts(errors, write="--write-compatibility" in sys.argv)
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
    print(f"Contract validation passed for {len(REQUIRED) + len(REQUIRED_V2) + 6} shared policies and {len(GAMES)} catalog games.")
    # Return the computed value to the caller.
    return 0

# Branch when the following condition is true.
if __name__ == "__main__":
    # Raise an error so invalid input or state is reported explicitly.
    raise SystemExit(main())
