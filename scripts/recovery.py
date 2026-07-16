"""Run fail-closed encrypted recovery workflows for MYSQL-006 and TOOL-004."""

# Import argument parsing for explicit backup, restore, and evidence-check modes.
import argparse
# Import base64 for external binary key material.
import base64
# Import dynamic loading for one operator-owned destination adapter factory.
import importlib
# Import JSON for sanitized external evidence records.
import json
# Import environment access for paths, adapter selection, and secret material.
import os
# Import stderr output for fixed operator-facing failures.
import sys
# Import portable paths for operator-owned external evidence files.
from pathlib import Path

# Import only the reviewed repository-side recovery contract.
from casino.core import recovery

# Map every independent key role to its external environment variable.
KEY_ENVIRONMENT = {
    # Load only the AES-256 encryption role.
    "encryption_key": "CASINO_RECOVERY_ENCRYPTION_KEY_B64",
    # Load only the source manifest signing role.
    "evidence_hmac_key": "CASINO_RECOVERY_MANIFEST_HMAC_KEY_B64",
    # Load only the destination acknowledgement verification role.
    "destination_ack_hmac_key": "CASINO_RECOVERY_DESTINATION_ACK_HMAC_KEY_B64",
    # Load only the provider read-only evidence verification role.
    "provider_evidence_hmac_key": "CASINO_RECOVERY_PROVIDER_EVIDENCE_HMAC_KEY_B64",
    # Load only the clean-target authorization and result role.
    "restore_evidence_hmac_key": "CASINO_RECOVERY_RESTORE_EVIDENCE_HMAC_KEY_B64",
}


# Read one required external text value without echoing it.
def required_environment(name):
    # Read and trim the selected operator-owned value.
    value = str(os.environ.get(name, "")).strip()
    # Reject missing values with a key-name-only diagnostic.
    if not value:
        # Identify only the configuration field, never its value.
        raise recovery.RecoveryError(f"Required recovery configuration is missing: {name}")
    # Return the external value for in-process use only.
    return value


# Load independent binary key roles from strict canonical base64.
def load_keys():
    # Collect decoded roles under protected fixed diagnostics.
    decoded = {}
    # Decode each named role independently.
    for field, environment_name in KEY_ENVIRONMENT.items():
        # Read the external base64 value.
        encoded = required_environment(environment_name)
        # Decode without ignoring malformed characters.
        try:
            # Store only decoded binary material in memory.
            decoded[field] = base64.b64decode(encoded, validate=True)
        # Replace decoding details and values with a key-name-only error.
        except (ValueError, TypeError) as exc:
            # Preserve no supplied secret in the diagnostic.
            raise recovery.RecoveryError(f"Recovery key configuration is invalid: {environment_name}") from exc
    # Validate strength and pairwise role independence.
    return recovery.RecoveryKeys(**decoded)


# Load one JSON object from an operator-owned external file.
def load_external_json(environment_name):
    # Resolve the external path without printing or persisting it.
    path = Path(required_environment(environment_name))
    # Read and parse under fixed secret-safe diagnostics.
    try:
        # Decode one UTF-8 JSON object.
        value = json.loads(path.read_text(encoding="utf-8"))
    # Replace path, parser, and content details with one key-name-only error.
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        # Preserve only the configuration field name.
        raise recovery.RecoveryError(f"Recovery evidence could not be read: {environment_name}") from exc
    # Require an object for every signed evidence contract.
    if not isinstance(value, dict):
        # Reject ambiguous top-level arrays or scalars.
        raise recovery.RecoveryError(f"Recovery evidence is invalid: {environment_name}")
    # Return the in-memory object only.
    return value


# Load one operator-owned adapter factory without provider assumptions.
def load_adapter():
    # Read a module and factory name from external configuration.
    specification = required_environment("CASINO_RECOVERY_ADAPTER")
    # Require exactly one module-to-factory separator.
    if specification.count(":") != 1:
        # Reject ambiguous dynamic loading syntax without echoing it.
        raise recovery.RecoveryError("Recovery adapter configuration is invalid")
    # Separate importable module and factory attribute.
    module_name, factory_name = specification.split(":", 1)
    # Require ordinary dotted identifiers only.
    if not module_name or not factory_name or any(not part.isidentifier() for part in module_name.split(".")) or not factory_name.isidentifier():
        # Reject paths, arguments, and arbitrary expressions.
        raise recovery.RecoveryError("Recovery adapter configuration is invalid")
    # Import and instantiate under fixed diagnostics.
    try:
        # Import the operator-installed adapter module.
        module = importlib.import_module(module_name)
        # Resolve the zero-argument factory.
        factory = getattr(module, factory_name)
        # Create the preconfigured destination and verifier adapter.
        return factory()
    # Replace import, configuration, and provider details.
    except Exception as exc:
        # Preserve no module path or adapter exception.
        raise recovery.RecoveryError("Recovery adapter could not be initialized") from exc


# Build one redacted argv-free process configuration from external paths.
def load_process_config():
    # Resolve the no-argument dump wrapper path.
    dump_program = Path(required_environment("CASINO_RECOVERY_DUMP_PROGRAM"))
    # Resolve the no-argument restore wrapper path.
    restore_program = Path(required_environment("CASINO_RECOVERY_RESTORE_PROGRAM"))
    # Resolve the encrypted-staging-only directory.
    staging_directory = Path(required_environment("CASINO_RECOVERY_STAGING_DIRECTORY"))
    # Parse one bounded timeout without echoing input.
    try:
        # Convert the external timeout to an integer.
        timeout_seconds = int(str(os.environ.get("CASINO_RECOVERY_TIMEOUT_SECONDS", "900")).strip())
    # Replace malformed input with a fixed diagnostic.
    except ValueError as exc:
        # Preserve no supplied value.
        raise recovery.RecoveryError("Recovery process timeout is invalid") from exc
    # Load the explicit least-privilege child environment from an external JSON file.
    process_environment = load_external_json("CASINO_RECOVERY_PROCESS_ENV_PATH")
    # Return one intrinsically redacted validated process record.
    return recovery.RecoveryProcessConfig(dump_program, restore_program, staging_directory, process_environment, timeout_seconds)


# Run one complete encrypted off-instance logical backup.
def run_backup():
    # Load independent key roles.
    keys = load_keys()
    # Load strict public release/schema/source context.
    context = load_external_json("CASINO_RECOVERY_CONTEXT_PATH")
    # Load one preconfigured destination adapter.
    destination = load_adapter()
    # Complete encryption, upload, exact acknowledgements, and staging cleanup.
    manifest = recovery.complete_off_instance_backup(load_process_config(), keys, context, destination)
    # Emit only the signed sanitized manifest for operator evidence storage.
    print(json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True))


# Run one complete clean-target restore drill.
def run_restore():
    # Load independent key roles.
    keys = load_keys()
    # Load the exact signed recovery manifest.
    manifest = load_external_json("CASINO_RECOVERY_MANIFEST_PATH")
    # Load its exact destination-owned acknowledgement.
    acknowledgement = load_external_json("CASINO_RECOVERY_DESTINATION_ACK_PATH")
    # Load independent empty-target authorization.
    authorization = load_external_json("CASINO_RECOVERY_TARGET_AUTHORIZATION_PATH")
    # Load strict public release/schema/source context.
    context = load_external_json("CASINO_RECOVERY_CONTEXT_PATH")
    # Read only the opaque expected target HMAC.
    target_hmac = required_environment("CASINO_RECOVERY_TARGET_HMAC_SHA256")
    # Load one preconfigured destination and clean-target verifier adapter.
    adapter = load_adapter()
    # Complete preverification, argv-free restore, quarantine policy, and post-restore proof.
    result = recovery.restore_clean_target(load_process_config(), keys, manifest, acknowledgement, authorization, target_hmac, adapter, context, adapter.verify_restored_target)
    # Emit only sanitized computed timing and evidence identities.
    print(json.dumps({"status": "verified", "observed_rpo_seconds": result.observed_rpo_seconds, "observed_rto_seconds": result.observed_rto_seconds, "evidence_sha256": result.evidence_sha256}, sort_keys=True, separators=(",", ":")))


# Validate current provider, off-instance, retention, and age evidence without mutation.
def run_check():
    # Load independent key roles.
    keys = load_keys()
    # Load provider-signed sanitized read-only evidence.
    provider = load_external_json("CASINO_RECOVERY_PROVIDER_EVIDENCE_PATH")
    # Validate current completion and approved-cost inclusion.
    provider_result = recovery.validate_provider_evidence(provider, keys.provider_evidence_hmac_key)
    # Load exact signed logical recovery manifest.
    manifest_record = load_external_json("CASINO_RECOVERY_MANIFEST_PATH")
    # Load exact destination-owned acknowledgement.
    acknowledgement = load_external_json("CASINO_RECOVERY_DESTINATION_ACK_PATH")
    # Validate paired manifest and destination evidence.
    manifest = recovery.validate_recovery_manifest(manifest_record, keys.evidence_hmac_key, acknowledgement, keys.destination_ack_hmac_key)
    # Enforce recovery-point age and active retention alerts.
    health = recovery.validate_recovery_age(manifest)
    # Emit only sanitized boolean and age observations.
    print(json.dumps({"status": "current", "provider_completed": provider_result.completed, "cost_included": provider_result.cost_included, **health}, sort_keys=True, separators=(",", ":")))


# Parse one explicit repository-owned recovery command.
def main():
    # Create the dependency-free command parser.
    parser = argparse.ArgumentParser(description="Encrypted recovery gate tooling")
    # Require one explicit mode and never infer backup or restore.
    parser.add_argument("command", choices=("backup", "restore", "check"))
    # Parse the selected mode.
    args = parser.parse_args()
    # Run under fixed secret-safe diagnostics.
    try:
        # Execute encrypted backup only when explicitly selected.
        if args.command == "backup":
            # Run the backup workflow.
            run_backup()
        # Execute clean-target restore only when explicitly selected.
        elif args.command == "restore":
            # Run the restore workflow.
            run_restore()
        # Execute evidence-only validation otherwise.
        else:
            # Run current provider/recovery evidence checks.
            run_check()
    # Convert every expected recovery refusal into one value-free CLI error.
    except recovery.RecoveryError as exc:
        # Print only fixed repository-owned diagnostics.
        print(str(exc), file=sys.stderr)
        # Return a stable failure status.
        return 1
    # Return success only after the selected workflow completes.
    return 0


# Run the explicit CLI when executed as a script.
if __name__ == "__main__":
    # Exit with the stable command status.
    raise SystemExit(main())
