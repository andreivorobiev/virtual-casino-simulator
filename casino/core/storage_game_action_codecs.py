# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Provider-neutral durable game-action identity and canonical JSON codecs."""

# Import JSON so shared lifecycle codecs preserve their exact durable encoding.
import json
# Import value typing for bounded durable object validation.
from typing import Any

# Import the immutable identity and canonical value encoder shared by both providers.
from casino.core.game_action import GameActionIdentity, canonical_json_bytes
# Import fixed recovery boundaries used by corrupt durable identity handling.
from casino.errors import ConflictError, ValidationError


# Own the provider-neutral lifecycle codecs needed by JSON and MySQL storage.
class GameActionCodecMixin:
    # Convert one immutable canonical value to ordinary JSON containers.
    def _plain_canonical(self, value) -> Any:
        # Reuse the contract's unique bounded encoding before decoding plain containers.
        return json.loads(canonical_json_bytes(value).decode("utf-8"))

    # Reject duplicate object keys while decoding provider-owned durable JSON.
    def _unique_json_object(self, pairs: list[tuple[str, Any]]) -> dict:
        # Build one ordinary object after checking every physical key.
        result = {}
        # Inspect pairs in the decoder's source order.
        for key, value in pairs:
            # Reject a repeated key instead of accepting last-value-wins corruption.
            if key in result:
                # Normalize duplicate keys into the private recovery boundary.
                raise ValueError("duplicate key")
            # Retain the unique decoded key and value.
            result[key] = value
        # Return the strictly decoded object.
        return result

    # Return the canonical durable scope key for one action identity.
    def _game_action_scope_key(self, identity: GameActionIdentity) -> str:
        # Encode the three bounded identity fragments without delimiter ambiguity.
        return json.dumps(list(identity.scope_key), separators=(",", ":"), ensure_ascii=False)

    # Serialize one exact action identity for journal or receipt storage.
    def _serialize_game_action_identity(self, identity: GameActionIdentity) -> dict:
        # Return only the four immutable identity fields.
        return {
            # Preserve the caller-stable action key.
            "action_key": identity.action_key,
            # Preserve the game namespace.
            "game_id": identity.game_id,
            # Preserve the authenticated owner.
            "player_id": identity.player_id,
            # Preserve the canonical request/resource fingerprint.
            "request_fingerprint": identity.request_fingerprint,
        }

    # Reconstruct one exact action identity from private durable JSON.
    def _deserialize_game_action_identity(self, value: Any) -> GameActionIdentity:
        # Require the exact durable identity field set.
        if type(value) is not dict or set(value) != {"action_key", "game_id", "player_id", "request_fingerprint"}:
            # Reject malformed durable identity state.
            raise ConflictError("Game action storage requires operator recovery")
        try:
            # Reconstruct through the contract's exact direct-validation boundary.
            return GameActionIdentity(
                # Restore the game namespace.
                game_id=value["game_id"],
                # Restore the authenticated owner.
                player_id=value["player_id"],
                # Restore the caller-stable action key.
                action_key=value["action_key"],
                # Restore the canonical semantic fingerprint.
                request_fingerprint=value["request_fingerprint"],
            )
        # Normalize contract validation without exposing corrupt values.
        except ValidationError:
            # Preserve the original durable bytes for operator repair.
            raise ConflictError("Game action storage requires operator recovery") from None
