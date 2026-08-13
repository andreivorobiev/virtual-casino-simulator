# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Import required dependency so this module can use schema version metadata.
from casino.config import SCHEMA_VERSION
from casino.core.clock import utc_now
# Import required dependency so this module can use the configured storage provider.
from casino.core.storage import get_storage_provider
from casino.core.ids import new_id
from casino.errors import NotFoundError, ValidationError

# Define the default_players function used by this module.
def default_players() -> dict:
    # Set now to the value needed for the next operation.
    now = utc_now()
    return {"schema_version": SCHEMA_VERSION, "players": [
        {"player_id": "human", "display_name": "You", "type": "human", "balance": 5000.0, "created_at": now, "updated_at": now, "status": "active"},
        {"player_id": "bot_1", "display_name": "Ava", "type": "bot", "balance": 5000.0, "created_at": now, "updated_at": now, "status": "active"},
        {"player_id": "bot_2", "display_name": "Mia", "type": "bot", "balance": 5000.0, "created_at": now, "updated_at": now, "status": "active"},
        {"player_id": "bot_3", "display_name": "Zoe", "type": "bot", "balance": 5000.0, "created_at": now, "updated_at": now, "status": "active"},
    ]}

# Define the load_players function used by this module.
def load_players() -> dict:
    # Return only the configured provider's validated player document.
    return get_storage_provider().load_players(default_players)

# Define the list_players function used by this module.
def list_players() -> list[dict]:
    return load_players()["players"]

# Define the get_player function used by this module.
def get_player(player_id: str) -> dict:
    for p in list_players():
        if p["player_id"] == player_id:
            return p
    # Raise an error so invalid input or state is reported explicitly.
    raise NotFoundError(f"Player {player_id} was not found")

# Define the update_player function used by this module.
def update_player(player_id: str, updater) -> dict:
    # Return the provider-managed update so JSON and MySQL share player semantics.
    return get_storage_provider().update_player(player_id, updater)

# Define the create_player function used by this module.
def create_player(display_name: str, kind: str = "human", balance: float = 5000.0) -> dict:
    if not display_name or not display_name.strip():
        # Raise an error so invalid input or state is reported explicitly.
        raise ValidationError("display_name is required")
    # Set now to the value needed for the next operation.
    now = utc_now()
    # Set player to the value needed for the next operation.
    player = {"player_id": new_id("player"), "display_name": display_name.strip(), "type": kind, "balance": round(float(balance),2), "created_at": now, "updated_at": now, "status": "active"}
    # Append this one player through the provider's row-scoped path instead of rewriting the whole
    # player document. A load/append/full-rewrite cycle here would drop out of the cross-process wallet
    # lock between the read and the write, so a bet settling concurrently could be silently reverted,
    # and on MySQL it would replace every player row from a stale snapshot (issue #402).
    # insert_player holds the wallet lock across the JSON read-modify-write and uses a row-scoped
    # INSERT IGNORE plus SELECT ... FOR UPDATE on MySQL, so it is safe on both providers.
    return get_storage_provider().insert_player(player)

# Define the ensure_player_for_user function used by this module.
def ensure_player_for_user(user_id: str, display_name: str, player_id: str | None = None) -> dict:
    # Branch when the caller supplied an existing player binding.
    if player_id:
        # Start protected logic so missing legacy players can be repaired.
        try:
            return get_player(player_id)
        # Handle the expected failure path for the protected logic.
        except NotFoundError:
            # Continue so a replacement player can be created for the user.
            pass
    # Set label to the value needed for the next operation.
    label = display_name.strip() if display_name and display_name.strip() else user_id
    return create_player(label, "human", 5000.0)

# Provision one deterministic invited-account player idempotently across JSON and MySQL. (INVITE-003)
def ensure_invited_player(player_id: str, display_name: str) -> dict:
    # Require the saga-owned opaque identifier before touching wallet state.
    if not str(player_id or "").startswith("player_invite_"):
        # Reject caller-selected or malformed identifiers outside the invitation namespace.
        raise ValidationError("invited player identifier is invalid")
    # Normalize the recipient-selected display name without accepting an empty wallet label.
    label = str(display_name or "").strip()
    # Reject an empty label before constructing a persistent player row.
    if not label:
        # Keep provisioning state unchanged on invalid presentation input.
        raise ValidationError("display_name is required")
    # Capture one creation timestamp used only when this is the first successful provision.
    now = utc_now()
    # Build the deterministic zero-side-effect row before the provider transaction.
    player = {"player_id": player_id, "display_name": label, "type": "human", "balance": 5000.0, "created_at": now, "updated_at": now, "status": "active"}
    # Delegate insert-or-read semantics to the configured JSON or MySQL provider.
    return get_storage_provider().ensure_player(player)


# Provision one deterministic zero-balance wallet for verified-email activation. (AUTH-018, USER-010)
def ensure_email_enrollment_player(player_id: str, display_name: str) -> dict:
    # Require the server-owned email-enrollment identifier namespace before wallet storage access.
    if not str(player_id or "").startswith("player_email_"):
        # Reject caller-selected wallet identifiers outside the verified-email saga.
        raise ValidationError("email enrollment player identifier is invalid")
    # Normalize the pending account label without accepting an empty player record.
    label = str(display_name or "").strip()[:80]
    # Fail before storage mutation when the verified signup omitted a usable display name.
    if not label:
        # Preserve all existing player rows on invalid input.
        raise ValidationError("display_name is required")
    # Capture one creation instant used only for the first successful provisioning attempt.
    now = utc_now()
    # Create the recoverable inactive wallet at zero so only the ledger can fund it.
    player = {"player_id": player_id, "display_name": label, "type": "human", "balance": 0.0, "created_at": now, "updated_at": now, "status": "provisioning"}
    # Delegate insert-or-read semantics to the configured JSON or MySQL provider.
    existing = get_storage_provider().ensure_player(player)
    # Reject a conflicting replay that could inherit pre-existing funds or active status.
    if existing.get("display_name") != label or existing.get("status") not in {"provisioning", "active"}:
        # Preserve the conflicting wallet for operator investigation.
        raise ValidationError("email enrollment player replay conflicts with existing state")
    # Return the exact durable wallet selected by the provider.
    return existing


# Activate one verified-email wallet only after its starting-balance ledger credit is durable. (USER-010)
def activate_email_enrollment_player(player_id: str) -> dict:
    # Apply the final status transition under the provider's row-scoped wallet lock.
    def activate(player: dict) -> None:
        # Accept only the recoverable provisioning state or an idempotent active replay.
        if player.get("status") not in {"provisioning", "active"}:
            # Refuse to revive suspended or otherwise operator-controlled accounts.
            raise ValidationError("email enrollment player cannot be activated")
        # Mark the fully funded wallet available to authenticated gameplay.
        player["status"] = "active"
        # Refresh the lifecycle timestamp after the successful activation boundary.
        player["updated_at"] = utc_now()
    # Return the provider-owned updated row.
    return update_player(player_id, activate)


# Provision one deterministic social-enrollment player idempotently across JSON and MySQL. (OAUTH-013)
def ensure_social_player(player_id: str, display_name: str) -> dict:
    # Require only the server-owned social-enrollment identifier namespace.
    if not str(player_id or "").startswith("player_social_"):
        # Reject caller-selected or malformed wallet identifiers.
        raise ValidationError("social player identifier is invalid")
    # Normalize the provider display label without accepting an empty wallet label.
    label = str(display_name or "").strip()[:80]
    # Reject unusable provider display metadata before storage access.
    if not label:
        # Keep all provisioning state unchanged.
        raise ValidationError("display_name is required")
    # Capture one creation timestamp used only by the first successful provision.
    now = utc_now()
    # Build the deterministic full-account wallet row with the established starting balance.
    player = {"player_id": player_id, "display_name": label, "type": "human", "balance": 5000.0, "created_at": now, "updated_at": now, "status": "active"}
    # Delegate insert-or-read semantics to the configured JSON or MySQL provider.
    return get_storage_provider().ensure_player(player)
