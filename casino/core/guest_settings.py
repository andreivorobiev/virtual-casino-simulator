# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Provider-backed guest-trial admission policy for GUEST-001 and ADMIN-032."""

# Import the deployed guest defaults so a missing document preserves current operator intent.
from casino import config
# Import the shared schema marker so JSON and MySQL documents use the same owned shape.
from casino.config import SCHEMA_VERSION
# Import the active provider accessor so the switch persists across application restarts.
from casino.core.storage import get_storage_provider

# Reserve one provider document for guest-trial admission independently from enrollment methods.
GUEST_SETTINGS_DOCUMENT_KEY = "settings/guest_trials"


# Build the safe first-read policy from deployment configuration.
def default_guest_settings() -> dict:
    # Return a new mapping so provider callers cannot mutate module constants.
    return {
        # Stamp the current provider schema.
        "schema_version": SCHEMA_VERSION,
        # Preserve the existing environment gate as the initial no-document behavior.
        "enabled": bool(config.GUEST_TRIALS_ENABLED),
    }


# Normalize stored state without accepting truthy strings or unknown fields as admission.
def _validated_settings(state) -> dict:
    # Resolve the configuration-backed default once for malformed or partial state.
    defaults = default_guest_settings()
    # Ignore non-mapping provider state rather than letting it break public login.
    source = state if isinstance(state, dict) else {}
    # Accept only an exact boolean; every other value preserves the reviewed default.
    enabled = source.get("enabled") if type(source.get("enabled")) is bool else defaults["enabled"]
    # Return only the canonical owned fields.
    return {"schema_version": SCHEMA_VERSION, "enabled": enabled}


# Read the current durable admission policy for public disclosure and backend enforcement.
def guest_settings() -> dict:
    # Resolve the active provider at call time so test and startup provider selection remains authoritative.
    provider = get_storage_provider()
    # Read the shared document without persisting on a read-only default path.
    stored = provider.read_document(GUEST_SETTINGS_DOCUMENT_KEY, default_guest_settings)
    # Return the canonical setting plus the fixed current grant for truthful Admin display.
    return {**_validated_settings(stored), "starting_balance": float(config.GUEST_STARTING_BALANCE)}


# Report only the boolean admission decision used by anonymous guest creation.
def trials_enabled() -> bool:
    # Read the latest provider state on every admission attempt so Admin changes need no restart.
    return guest_settings()["enabled"] is True


# Persist one strict owner-authored admission switch.
def save_guest_settings(updates: dict) -> dict:
    # Require one exact boolean so strings and integers cannot accidentally widen anonymous access.
    if not isinstance(updates, dict) or type(updates.get("enabled")) is not bool or set(updates) != {"enabled"}:
        # Use the shared validation taxonomy without echoing caller-controlled values.
        from casino.errors import ValidationError
        # Reject unsupported or ambiguous settings before provider mutation.
        raise ValidationError("guest trial settings require exactly one boolean enabled field")
    # Build the complete owned document for an atomic provider write.
    committed = {"schema_version": SCHEMA_VERSION, "enabled": updates["enabled"]}
    # Persist through the provider contract shared by JSON and MySQL deployments.
    get_storage_provider().write_document(GUEST_SETTINGS_DOCUMENT_KEY, committed)
    # Return the committed switch plus the fixed current token grant.
    return {**committed, "starting_balance": float(config.GUEST_STARTING_BALANCE)}
