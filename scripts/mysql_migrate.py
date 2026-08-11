# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Deployment-only MySQL migration runner for MYSQL-005 and STORAGE-007."""

# Import argument parsing for explicit non-mutating and apply commands.
import argparse
# Import JSON for sanitized machine-readable command output.
import json
# Import portable external proof paths.
from pathlib import Path
# Import the interpreter path list for exact extracted-release module binding.
import sys

# Resolve the selected extracted release root from this immutable script.
SCRIPT_ROOT = Path(__file__).resolve().parents[1]
# Bind direct absolute-script execution to the selected release rather than ambient cwd/site state.
if str(SCRIPT_ROOT) not in sys.path:
    # Prepend only the canonical release root before importing candidate modules.
    sys.path.insert(0, str(SCRIPT_ROOT))

# Import the checksum-bound migration state machine and isolated configuration.
from casino.core.mysql_migrations import MigrationConfig, MigrationError, RedactedConnectionOptions, dry_run, inspect_schema, load_catalog, schema_contract, verify_runtime_compatibility
# Import the strict non-shell assignment reader used by root-managed service environments.
from scripts.validate_monitor_config import read_assignment

# Pin the only root-managed runtime environment inspected by the bridge deployment check.
RUNTIME_ENV_PATH = Path("/etc/casino/casino.env")
# Name the existing runtime DML tuple without accepting migration or administrator credentials.
RUNTIME_ENV = {
    # Read the runtime-selected host.
    "host": "CASINO_MYSQL_HOST",
    # Read the runtime-selected TCP port.
    "port": "CASINO_MYSQL_PORT",
    # Read the runtime DML account.
    "user": "CASINO_MYSQL_USER",
    # Read the runtime DML secret.
    "password": "CASINO_MYSQL_PASSWORD",
    # Read the runtime-selected database.
    "database": "CASINO_MYSQL_DATABASE",
}


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


# Load the existing runtime DML tuple without sourcing shell text or accepting migration credentials.
def _runtime_options(runtime_env_path: Path = RUNTIME_ENV_PATH) -> RedactedConnectionOptions:
    # Read each reviewed runtime assignment through the strict non-shell parser.
    values = {field: read_assignment(runtime_env_path, environment).strip() for field, environment in RUNTIME_ENV.items()}
    # Reject incomplete runtime configuration without identifying a field or value.
    if any(not value for value in values.values()):
        # Stop before a connector import or network access.
        raise MigrationError("MySQL runtime schema-check configuration is incomplete")
    # Parse the existing runtime port without accepting booleans, aliases, or fallback values.
    try:
        # Convert the exact decimal port assignment.
        port = int(values["port"])
    # Normalize malformed runtime configuration into one fixed failure.
    except (TypeError, ValueError) as exc:
        # Preserve no raw assignment text.
        raise MigrationError("MySQL runtime schema-check configuration is invalid") from exc
    # Require a valid TCP port and the established literal-loopback deployment boundary.
    if values["host"].lower() != "127.0.0.1" or port < 1 or port > 65535:
        # Refuse a redirected or malformed runtime target.
        raise MigrationError("MySQL runtime schema-check configuration is invalid")
    # Return one intrinsically redacted connector mapping.
    return RedactedConnectionOptions(host=values["host"], port=port, user=values["user"], password=values["password"], database=values["database"])


# Open one runtime DML connection only for the fixed bridge schema-two proof.
def _connect_runtime(runtime_env_path: Path = RUNTIME_ENV_PATH):
    # Start protected optional-driver import for a fixed dependency diagnostic.
    try:
        # Import the supported connector without installing or changing dependencies.
        import mysql.connector
    # Convert a missing optional dependency into one value-free policy error.
    except ImportError as exc:
        # Name only the documented optional dependency group.
        raise MigrationError("MySQL migration tooling requires the optional mysql dependency") from exc
    # Connect with only the existing runtime DML tuple.
    return mysql.connector.connect(**_runtime_options(runtime_env_path))


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
        # Publish the closed bridge apply policy.
        "apply_policy": contract["apply_policy"],
    }


# Parse one explicit deployment operation without providing a repair bypass.
def parse_args():
    # Describe the DDL-free inspection and proof-gated apply boundary.
    parser = argparse.ArgumentParser(description="Inspect or apply the checksum-bound Casino MySQL migration catalog.")
    # Require an explicit operation so an invocation never defaults to mutation.
    parser.add_argument("command", choices=("status", "check", "dry-run", "apply", "bridge-check-schema2"))
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
        # Refuse held application before configuration, driver import, connection, or lock acquisition.
        if args.command == "apply":
            # Validate the immutable held catalog before returning its fixed policy result.
            load_catalog()
            # Preserve the same defense-in-depth result as the public apply boundary.
            raise MigrationError("MySQL migration apply policy is held")
        # Run the fixed deployment bridge check with only the existing runtime DML identity.
        if args.command == "bridge-check-schema2":
            # Open one runtime connection after the fixed environment file is parsed.
            connection = _connect_runtime()
            # Always close the runtime connection after the read-only proof.
            try:
                # Reuse runtime startup validation for checksum-prefix and clean-state proof.
                state = verify_runtime_compatibility(connection)
                # Require exact schema two even though this bridge runtime also accepts schema three.
                if state.current_version != 2:
                    # Stop cutover without exposing the observed version.
                    raise MigrationError("MySQL bridge deployment requires exact schema two")
                # Emit only sanitized schema and catalog evidence.
                print(json.dumps(_state_payload(state), sort_keys=True))
                # Return success after the fixed exact-schema proof.
                return 0
            # Close the runtime DML connection on success or failure.
            finally:
                # Release connector-owned state containing credentials.
                connection.close()
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
            # Reject unreachable command choices rather than growing a mutation fallback.
            raise MigrationError("MySQL migration command is unsupported")
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
