# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Deployment-only PostgreSQL migration runner for guarded PostgreSQL 16 targets."""

# Import argument parsing for explicit inspection and apply commands.
import argparse
# Import JSON for sanitized machine-readable output.
import json
# Import constant-time equality for release-provenance binding.
import hmac
# Import strict patterns for immutable release commit identities.
import re
# Import the interpreter path list for exact extracted-release binding.
import sys
# Import portable paths for the selected immutable release root.
from pathlib import Path

# Resolve the release root from this immutable script rather than ambient cwd.
SCRIPT_ROOT = Path(__file__).resolve().parents[1]
# Bind absolute-script execution to the selected release source.
if str(SCRIPT_ROOT) not in sys.path:
    # Prepend only the canonical release root before importing candidate modules.
    sys.path.insert(0, str(SCRIPT_ROOT))

# Import the checksum-bound PostgreSQL migration state machine and isolated configuration.
from casino.core.postgres_migrations import MigrationConfig, MigrationError, apply_migrations, dry_run, inspect_schema, load_catalog, require_authorized_target, schema_contract, verify_migration_compatibility

# Accept only the exact immutable commit shape recorded by release packaging.
RELEASE_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


# Import psycopg lazily only after configuration and disposable-target validation.
def _connect(config: MigrationConfig):
    # Start one fixed optional-driver import boundary.
    try:
        # Import the supported psycopg 3 connector only for this deployment tool.
        import psycopg
    # Convert a missing optional dependency into a value-free migration result.
    except ImportError as exc:
        # Name only the documented optional dependency group.
        raise MigrationError("PostgreSQL migration tooling requires the optional postgres dependency") from exc
    # Open one bounded deployment-only connection without logging its arguments.
    return psycopg.connect(**config.kwargs(), autocommit=False, connect_timeout=5)


# Render only migration state and catalog identities with no target details.
def _state_payload(state) -> dict:
    # Load the public expected/minimum/catalog contract from immutable files.
    contract = schema_contract()
    # Return one fresh sanitized machine record.
    return {
        # State whether the target has a complete metadata boundary.
        "initialized": state.initialized,
        # Publish only the numeric current version.
        "current_version": state.current_version,
        # Publish only the finite state label.
        "status": state.status,
        # Publish an in-flight version without target identity.
        "applying_version": state.applying_version,
        # Publish the exact version required by this release.
        "expected_version": contract["expected_version"],
        # Publish the exact compatible minimum independently.
        "minimum_version": contract["minimum_version"],
        # Publish the packaged catalog checksum for provenance matching.
        "catalog_sha256": contract["catalog_sha256"],
        # Publish only the closed guarded empty-target application policy.
        "apply_policy": contract["apply_policy"],
    }


# Read one exact release commit without exposing other manifest content.
def _manifest_commit(manifest_path: Path | None) -> str:
    # Require an explicit manifest path for production authorization.
    if manifest_path is None:
        # Stop before any target or connector access.
        raise MigrationError("PostgreSQL production migration release manifest is required")
    # Protect filesystem and parser details behind one fixed provenance result.
    try:
        # Parse the checksum-verified deployment manifest selected by the operator.
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # Collapse missing, unreadable, malformed, or non-UTF-8 input.
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        # Avoid reporting the path or parser content.
        raise MigrationError("PostgreSQL production migration release manifest is invalid") from exc
    # Read the source mapping only from the reviewed manifest shape.
    source = manifest.get("source") if type(manifest) is dict else None
    # Read the exact source commit without coercion.
    commit = source.get("commit_sha") if type(source) is dict else None
    # Require one immutable lowercase full SHA.
    if type(commit) is not str or not RELEASE_SHA_RE.fullmatch(commit):
        # Refuse symbolic, short, uppercase, or absent provenance.
        raise MigrationError("PostgreSQL production migration release manifest is invalid")
    # Return only the validated non-secret commit identity.
    return commit


# Parse one explicit deployment operation without repair bypasses.
def parse_args(argv=None):
    # Describe the read-only inspection and guarded empty-target apply boundary.
    parser = argparse.ArgumentParser(description="Inspect or apply the checksum-bound Casino PostgreSQL migration catalog on an authorized guarded target.")
    # Require one explicit command so invocation never defaults to mutation.
    parser.add_argument("command", choices=("status", "check", "dry-run", "apply"))
    # Accept the already verified release manifest required only by production authorization.
    parser.add_argument("--release-manifest", type=Path, help="Verified release-manifest.json for production bootstrap")
    # Parse either the process arguments or a caller-owned test list.
    return parser.parse_args(argv)


# Execute the selected command and emit only sanitized JSON.
def main(argv=None) -> int:
    # Parse the non-secret command selection first.
    args = parse_args(argv)
    # Start protected configuration, connection, and migration handling.
    try:
        # Validate every packaged descriptor before reading environment or importing psycopg.
        migrations = load_catalog()[0]
        # Load only deployment-prefixed PostgreSQL variables.
        config = MigrationConfig.from_env()
        # Resolve one exact authorization mode before connector import or access.
        authorization_mode = require_authorized_target(config)
        # Bind production authority to the exact packaged commit before opening a connection.
        if authorization_mode == "production":
            # Read only the manifest's validated source commit.
            release_commit = _manifest_commit(args.release_manifest)
            # Require exact equality with the separately supplied production authorization.
            if not hmac.compare_digest(release_commit, config.release_sha):
                # Stop without reporting either commit value.
                raise MigrationError("PostgreSQL production migration release identity does not match")
        # Refuse an irrelevant manifest in disposable mode so command meaning remains explicit.
        elif args.release_manifest is not None:
            # Keep the original disposable lane isolated from production provenance.
            raise MigrationError("PostgreSQL disposable migration does not accept a release manifest")
        # Open one deployment-only connection for the command duration.
        connection = _connect(config)
        # Always close the connection after success or failure.
        try:
            # Return read-only target-bound status without creating metadata or taking a lock.
            if args.command == "status":
                # Inspect table and migration metadata using SELECT statements only.
                state = inspect_schema(connection, config, migrations)
                # Roll back the read-only transaction explicitly.
                connection.rollback()
                # Emit only the sanitized state record.
                print(json.dumps(_state_payload(state), sort_keys=True))
                # Return success after non-mutating inspection.
                return 0
            # Return exact runtime compatibility without changing metadata.
            if args.command == "check":
                # Reuse the SELECT-only compatibility verifier.
                state = verify_migration_compatibility(connection, config)
                # Roll back the read-only transaction explicitly.
                connection.rollback()
                # Emit only compatible sanitized state.
                print(json.dumps(_state_payload(state), sort_keys=True))
                # Return success after exact compatibility.
                return 0
            # Return the immutable pending suffix without schema mutation.
            if args.command == "dry-run":
                # Inspect and authorize the plan through SELECT statements only.
                pending = dry_run(connection, config)
                # Reinspect the unchanged state for output.
                state = inspect_schema(connection, config, migrations)
                # Roll back the read-only transaction explicitly.
                connection.rollback()
                # Add only stable numeric and name identities.
                payload = {**_state_payload(state), "pending": [{"version": item.version, "name": item.name} for item in pending]}
                # Emit the unchanged plan evidence.
                print(json.dumps(payload, sort_keys=True))
                # Return success without mutation.
                return 0
            # Apply only through the guarded public state machine.
            if args.command == "apply":
                # Execute all pending transactional migrations under the target lock.
                state = apply_migrations(connection, config)
                # Emit only exact final migration evidence.
                print(json.dumps(_state_payload(state), sort_keys=True))
                # Return success after exact version and unlock confirmation.
                return 0
            # Reject unreachable choices rather than growing a fallback.
            raise MigrationError("PostgreSQL migration command is unsupported")
        # Close deployment-owned connector state on every outcome.
        finally:
            # Release connection memory containing migration credentials.
            connection.close()
    # Report only fixed migration-policy diagnostics.
    except MigrationError as exc:
        # Emit no target, credential, SQL, path, or driver detail.
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True))
        # Return a stable policy failure status.
        return 2
    # Collapse unexpected failures into one secret-safe result.
    except Exception:
        # Emit no exception representation because connectors may include target data.
        print(json.dumps({"ok": False, "error": "PostgreSQL migration command failed safely"}, sort_keys=True))
        # Return a distinct unexpected-failure status.
        return 3


# Run the explicit command only when invoked as a deployment tool.
if __name__ == "__main__":
    # Exit with the stable automation result from main.
    raise SystemExit(main())
