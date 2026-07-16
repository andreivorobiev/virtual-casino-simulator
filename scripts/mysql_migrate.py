"""Deployment-only MySQL migration runner for MYSQL-005 and STORAGE-007."""

# Import argument parsing for explicit non-mutating and apply commands.
import argparse
# Import JSON for sanitized machine-readable command output.
import json
# Import portable external proof paths.
from pathlib import Path

# Import the checksum-bound migration state machine and isolated configuration.
from casino.core.mysql_migrations import MigrationConfig, MigrationError, apply_migrations, dry_run, inspect_schema, load_catalog, schema_contract, verify_runtime_compatibility


# Import the optional driver only when this deployment tool is invoked.
def _connect(config: MigrationConfig):
    # Start protected optional-driver import for a fixed dependency diagnostic.
    try:
        # Import the supported MySQL connector without changing runtime package requirements.
        import mysql.connector
    # Convert a missing optional dependency into a value-free migration error.
    except ImportError as exc:
        # Name only the documented optional dependency group.
        raise MigrationError("MySQL migration tooling requires the optional mysql dependency") from exc
    # Open one deployment-only connection without logging connector arguments.
    return mysql.connector.connect(**config.kwargs())


# Render only migration state and catalog identities that contain no target details.
def _state_payload(state) -> dict:
    # Load the public expected/minimum/catalog contract from immutable release files.
    contract = schema_contract()
    # Return a fresh sanitized machine record.
    return {
        # State whether the migration metadata boundary exists.
        "initialized": state.initialized,
        # Publish only the numeric schema version.
        "current_version": state.current_version,
        # Publish only the finite clean/applying/dirty/uninitialized status.
        "status": state.status,
        # Publish an in-flight numeric version without target or statement details.
        "applying_version": state.applying_version,
        # Publish the exact version required by this immutable release.
        "expected_version": contract["expected_version"],
        # Publish the minimum runtime-compatible version independently.
        "minimum_version": contract["minimum_version"],
        # Publish the packaged catalog checksum for provenance matching.
        "catalog_sha256": contract["catalog_sha256"],
    }


# Parse one explicit deployment operation without providing a repair bypass.
def parse_args():
    # Describe the DDL-free inspection and proof-gated apply boundary.
    parser = argparse.ArgumentParser(description="Inspect or apply the checksum-bound Casino MySQL migration catalog.")
    # Require an explicit operation so an invocation never defaults to mutation.
    parser.add_argument("command", choices=("status", "check", "dry-run", "apply"))
    # Accept only an external machine-verifiable proof path.
    parser.add_argument("--backup-proof", type=Path)
    # Accept a bounded advisory-lock wait only for apply.
    parser.add_argument("--lock-timeout", type=int, default=30)
    # Return the parsed command line.
    return parser.parse_args()


# Execute the selected command and emit only sanitized JSON.
def main() -> int:
    # Parse the non-secret command selection first.
    args = parse_args()
    # Start protected configuration, connection, and migration handling.
    try:
        # Load only deployment-prefixed MySQL variables.
        config = MigrationConfig.from_env()
        # Open one deployment-only connection for the command duration.
        connection = _connect(config)
        # Always close the connection after status, failure, or apply.
        try:
            # Load and verify immutable files before inspecting state.
            migrations = load_catalog()[0]
            # Return read-only status without creating metadata or taking a lock.
            if args.command == "status":
                # Inspect table and migration metadata using SELECT statements only.
                state = inspect_schema(connection, migrations)
                # Emit only the sanitized state record.
                print(json.dumps(_state_payload(state), sort_keys=True))
                # Return success after the non-mutating inspection.
                return 0
            # Return exact runtime compatibility without changing metadata.
            if args.command == "check":
                # Reuse the same SELECT-only verifier used by application startup.
                state = verify_runtime_compatibility(connection)
                # Emit only the sanitized compatible state.
                print(json.dumps(_state_payload(state), sort_keys=True))
                # Return success after exact compatibility.
                return 0
            # Validate plan and proof without lock, metadata, or application writes.
            if args.command == "dry-run":
                # Read the proof and compute pending versions through SELECT-only database access.
                pending = dry_run(connection, config, args.backup_proof)
                # Inspect the same unchanged state for sanitized output.
                state = inspect_schema(connection, migrations)
                # Add only pending numeric versions and stable names to the public record.
                payload = {**_state_payload(state), "pending": [{"version": item.version, "name": item.name} for item in pending]}
                # Emit the proof-validated plan without connection details.
                print(json.dumps(payload, sort_keys=True))
                # Return success without database mutation.
                return 0
            # Reject nonsensical lock timeouts before acquiring a database lock.
            if not 0 <= args.lock_timeout <= 300:
                # Preserve a value-free CLI diagnostic.
                raise MigrationError("MySQL migration lock timeout is invalid")
            # Apply the proof-bound plan under the target advisory lock.
            state = apply_migrations(connection, config, args.backup_proof, args.lock_timeout)
            # Emit only the final sanitized exact-compatible state.
            print(json.dumps(_state_payload(state), sort_keys=True))
            # Return success after migration and lock release are confirmed.
            return 0
        # Close the deployment-only connection after every command.
        finally:
            # Remove migration credentials from process-owned connector state.
            connection.close()
    # Report only the fixed migration-policy error text.
    except MigrationError as exc:
        # Emit no target, credential, SQL, path, or driver detail.
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        # Return a stable nonzero automation status.
        return 2
    # Convert unexpected connector and filesystem failures to one secret-safe outcome.
    except Exception:
        # Emit no exception representation because drivers may include connection details.
        print(json.dumps({"ok": False, "error": "MySQL migration command failed safely"}, sort_keys=True))
        # Return a distinct unexpected-failure status.
        return 3


# Run the explicit command only when invoked as a deployment tool.
if __name__ == "__main__":
    # Exit with the stable automation status from main.
    raise SystemExit(main())
