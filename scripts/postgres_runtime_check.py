# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Verify a production PostgreSQL runtime target through its DDL-free identity."""

# Import JSON for one bounded machine-readable result.
import json
# Import environment access for the explicit provider selector.
import os

# Import the checksum-bound SELECT-only runtime verifier.
from casino.core.postgres_migrations import MigrationError, verify_runtime_compatibility
# Import the bounded connect timeout owned by the PostgreSQL pool policy.
from casino.core.postgres_pool import PostgresPoolConfig
# Import the runtime-only target configuration without migration authority.
from casino.core.storage.base import PostgresConfig
# Import the shared value-free configuration error category.
from casino.errors import ValidationError


# Connect with only the ordinary runtime identity after every local policy check passes.
def _connect(config: PostgresConfig, timeout_seconds: int):
    # Import the optional driver only after explicit PostgreSQL selection and configuration.
    try:
        # Load psycopg 3 for the one bounded readiness connection.
        import psycopg
        # Load dict rows because the migration verifier accepts this production provider shape.
        from psycopg.rows import dict_row
    # Convert a missing optional dependency to one fixed operator result.
    except ImportError as exc:
        # Name no interpreter, installation path, or import traceback.
        raise MigrationError("PostgreSQL runtime check requires the optional postgres dependency") from exc
    # Open one ordinary DDL-free runtime connection without logging its options.
    return psycopg.connect(**config.kwargs(), autocommit=False, connect_timeout=timeout_seconds, row_factory=dict_row)


# Execute one SELECT-only schema proof and publish no target or credential detail.
def main() -> int:
    # Protect every configuration, connector, query, and cleanup failure behind fixed output.
    try:
        # Require the application and deployment check to select the same provider explicitly.
        if os.getenv("CASINO_STORAGE_PROVIDER", "").strip().lower() != "postgres":
            # Refuse accidental execution against the MySQL or JSON production lane.
            raise MigrationError("PostgreSQL runtime check requires explicit provider selection")
        # Load the dedicated runtime target configuration only.
        config = PostgresConfig.from_env()
        # Keep the production database on literal IPv4 loopback.
        if config.host != "127.0.0.1":
            # Prevent a deployment poll from reaching a remote database endpoint.
            raise MigrationError("PostgreSQL runtime check requires a loopback target")
        # Reuse the reviewed bounded physical-connect deadline.
        pool_policy = PostgresPoolConfig.from_env()
        # Open one runtime-identity connection after local checks pass.
        connection = _connect(config, pool_policy.connect_timeout_seconds)
        # Always release connector state after the read-only proof.
        try:
            # Verify exact clean schema five and immutable checksum history with SELECT only.
            state = verify_runtime_compatibility(connection)
            # End the verifier's read transaction explicitly.
            connection.rollback()
        # Close the physical session on success or failure.
        finally:
            # Release runtime credentials retained by the connector object.
            connection.close()
        # Emit only finite schema and provider facts needed by deployment automation.
        print(json.dumps({"ok": True, "data": {"current_version": state.current_version, "status": state.status, "storage_provider": "postgres"}}, sort_keys=True))
        # Return success only after exact compatible state and cleanup.
        return 0
    # Convert every expected policy or configuration failure to one fixed result.
    except (MigrationError, ValidationError):
        # Publish no target, role, database, password, or observed schema detail.
        print(json.dumps({"ok": False, "error": "PostgreSQL runtime schema is not ready"}, sort_keys=True))
        # Return the stable policy failure status.
        return 2
    # Collapse native connector and unexpected failures without exception text.
    except Exception:
        # Avoid leaking libpq diagnostics that can contain connection values.
        print(json.dumps({"ok": False, "error": "PostgreSQL runtime check failed safely"}, sort_keys=True))
        # Return a distinct unexpected-failure status.
        return 3


# Execute the fixed no-argument check only for direct deployment invocation.
if __name__ == "__main__":
    # Propagate the stable automation status to the caller.
    raise SystemExit(main())
