# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""SimpleWagerGame-backed orchestration for retry-safe Big Six Wheel spins."""

# Import deep-copy support for detached compatibility projections.
import copy
# Import cryptographic index selection for production wheel outcomes.
import secrets
# Import the shared UTC clock for settled response timestamps.
from casino.core.clock import utc_now
# Import the shared one-shot wager and settlement coordinator.
from casino.core.simple_game import SimpleWagerGame
# Import player-scoped reads and provider-atomic state mutation.
from casino.core.state_store import load_player_game_state, update_player_game_state
# Import standard validation errors for request identity enforcement.
from casino.errors import ValidationError
# Import pure Big Six calculations and state helpers.
from casino.games.big_six_wheel import engine
# Import the stable game identity for every ledger event.
from casino.games.big_six_wheel.rules import GAME_ID, outcome_catalog

# Bound caller-supplied idempotency identifiers before persistence.
MAX_CLIENT_REQUEST_ID_LENGTH = 128
# Retain the established Big Six history capacity across the shared-helper migration.
RECENT_ROUND_LIMIT = 100


# Coordinate legacy-compatible state projection with shared exactly-once settlement.
class BigSixWheelService:
    # Capture injectable seams so deterministic tests avoid filesystem and ambient entropy.
    def __init__(self, *, ledger_gateway=None, state_loader=None, state_updater=None, randbelow=None, clock=None):
        # Use player-scoped storage compatible with the authenticated-player resolver.
        self.state_loader = state_loader or (lambda player_id: load_player_game_state(GAME_ID, player_id, engine.default_state))
        # Publish state through the provider-current callback boundary by default.
        self.state_updater = state_updater
        # Use cryptographic uniform selection unless a focused test supplies a deterministic index.
        self.randbelow = randbelow or secrets.randbelow
        # Use the shared UTC clock unless a focused test pins response time.
        self.clock = clock or utc_now
        # Build one shared coordinator with adapters for the frozen Big Six public and ledger shapes.
        self._game = SimpleWagerGame(game_id=GAME_ID, wager_transaction_type="BIG_SIX_WAGER_DEBIT", settlement_transaction_type="BIG_SIX_SETTLEMENT_CREDIT", entropy=self._entropy, resolve=self._resolve, validate_bet=self._validate_bet, ledger_gateway=ledger_gateway, state_loader=self._load_core_state, state_updater=self._update_core_state, entropy_source=self.randbelow, clock=self.clock, get_player=lambda player_id: {"player_id": player_id}, request_id_resolver=self._request_id, round_id_factory=self._round_id, wager_details_builder=self._wager_details, wager_proof_reader=self._wager_proof, settlement_details_builder=self._settlement_details, public_round_builder=self._public_round, recent_round_limit=RECENT_ROUND_LIMIT)

    # Validate a required client action identity used for safe network retries.
    @staticmethod
    def _client_request_id(value) -> str:
        # Normalize only string ids and reject empty, oversized, or control-character values.
        request_id = value.strip() if isinstance(value, str) else ""
        # Branch when the public idempotency identity is not safe to persist.
        if not request_id or len(request_id) > MAX_CLIENT_REQUEST_ID_LENGTH or any(ord(character) < 32 for character in request_id):
            # Require clients to send one stable identity per spin attempt.
            raise ValidationError("client_request_id must be a non-empty string of at most 128 characters")
        # Return the bounded identity without changing caller-visible casing.
        return request_id

    # Read the established retry identity from the frozen v1 request field.
    def _request_id(self, request: dict) -> str:
        # Delegate exact trimming and control-character validation to the game-owned rule.
        return self._client_request_id(request.get("client_request_id"))

    # Preserve Big Six's established player-plus-client-request round identity.
    @staticmethod
    def _round_id(_game_id: str, player_id: str, request_id: str) -> str:
        # Delegate to the published game-owned hash and prefix contract.
        return engine.round_id_for(player_id, request_id)

    # Normalize a frozen v1 wager request for the shared settlement coordinator.
    @staticmethod
    def _validate_bet(request: dict) -> tuple:
        # Normalize every public outcome amount through the game-owned decimal rules.
        wagers = engine.normalize_wagers(request.get("wagers"))
        # Calculate the established aggregate debit at ledger precision.
        total_wager = round(sum(wagers.values()), 2)
        # Bind conflicting retries to the exact normalized wager map.
        fingerprint = engine.wager_fingerprint(wagers)
        # Return the wager, aggregate movement, and semantic identity expected by the core.
        return wagers, total_wager, fingerprint

    # Draw one validated wheel position through the injected entropy source.
    @staticmethod
    def _entropy(randbelow) -> dict:
        # Wrap the game-owned index in a JSON-compatible proof object.
        return {"result_index": engine.select_index(randbelow)}

    # Resolve one Big Six settlement from committed wagers and committed entropy.
    @staticmethod
    def _resolve(wagers: dict, entropy: dict) -> dict:
        # Reuse the pure game engine so payout semantics remain unchanged.
        return engine.settle(wagers, int(entropy["result_index"]))

    # Build canonical and historical debit proof fields during the compatibility window.
    @staticmethod
    def _wager_details(*, request_id, fingerprint, wager, entropy, settled_at, **_context) -> dict:
        # Preserve old proof readers while adding the shared helper's canonical recovery fields.
        return {"request_id": request_id, "client_request_id": request_id, "request_fingerprint": fingerprint, "wager": wager, "wagers": wager, "entropy": entropy, "result_index": entropy["result_index"], "settled_at": settled_at}

    # Decode either canonical shared proof or a pre-migration Big Six debit event.
    def _wager_proof(self, *, details, event, **_context) -> dict:
        # Prefer the canonical wager and fall back to historical plural naming.
        wager = details.get("wager", details.get("wagers"))
        # Prefer canonical entropy and rebuild it from the historical wheel index when absent.
        entropy = details.get("entropy") if details.get("entropy") is not None else ({"result_index": details.get("result_index")} if details.get("result_index") is not None else None)
        # Prefer the canonical proof timestamp and preserve historical event timing during recovery.
        settled_at = details.get("settled_at") or event.get("ts") or self.clock()
        # Return only the committed deterministic inputs consumed by the core.
        return {"wager": wager, "entropy": entropy, "settled_at": settled_at}

    # Build canonical and historical credit evidence without changing settlement meaning.
    @staticmethod
    def _settlement_details(*, request_id, fingerprint, entropy, total_return, settlement, **_context) -> dict:
        # Preserve old Big Six audit fields alongside the shared proof dimensions.
        return {"request_id": request_id, "client_request_id": request_id, "request_fingerprint": fingerprint, "entropy": entropy, "total_return": total_return, "outcome": settlement["outcome"], "result_index": entropy["result_index"], "settlements": settlement["settlements"]}

    # Preserve the frozen Big Six public round shape over the shared settlement result.
    @staticmethod
    def _public_round(*, request_id, player_id, round_id, fingerprint, wager, settlement, settled_at, **_context) -> dict:
        # Return the established direct round row without shared-helper wrapper fields.
        return {"round_id": round_id, "client_request_id": request_id, "request_fingerprint": fingerprint, "player_id": player_id, "status": "settled", "wagers": wager, "settled_at": settled_at, **settlement}

    # Convert one established direct-row state document into shared-helper storage wrappers.
    @staticmethod
    def _to_core_state(raw_state: dict) -> dict:
        # Preserve unrelated provider-owned fields while adapting only recent-round representation.
        core_state = copy.deepcopy(raw_state)
        # Wrap newest rounds first because the shared helper prepends committed history.
        core_state["recent_rounds"] = [{"request_id": row.get("client_request_id"), "request_fingerprint": row.get("request_fingerprint"), "round_id": row.get("round_id"), "total_return": row.get("total_return", 0), "public": copy.deepcopy(row)} for row in reversed(raw_state.get("recent_rounds", []))]
        # Preserve or restore the game marker expected by the shared helper.
        core_state.setdefault("game", GAME_ID)
        # Return detached compatibility state so mutations remain callback-scoped.
        return core_state

    # Convert shared wrappers back to the frozen direct-row state representation.
    @staticmethod
    def _to_raw_state(core_state: dict) -> dict:
        # Preserve unrelated provider-owned fields before unwrapping recent rounds.
        raw_state = copy.deepcopy(core_state)
        # Restore oldest-to-newest public rows exactly as the Big Six state endpoint established.
        raw_state["recent_rounds"] = [copy.deepcopy(row["public"]) for row in reversed(core_state.get("recent_rounds", []))]
        # Return a detached provider-ready document without shared wrapper metadata.
        return raw_state

    # Load provider state and expose it in the shared helper's private representation.
    def _load_core_state(self, player_id: str) -> dict:
        # Adapt one detached authenticated-player document without persisting a rewrite.
        return self._to_core_state(self.state_loader(player_id))

    # Publish one shared-helper mutation against exact provider-current Big Six state.
    def _update_core_state(self, player_id: str, mutator) -> dict:
        # Adapt current provider state, invoke the shared merge, and restore frozen storage shape.
        def publish(raw_state: dict) -> dict:
            # Run the shared mutation only against a detached compatibility projection.
            updated_core = mutator(self._to_core_state(raw_state))
            # Persist direct public rows and every unrelated sibling field.
            return self._to_raw_state(updated_core)

        # Commit through the provider's cross-process atomic callback boundary.
        authoritative = update_player_game_state(GAME_ID, player_id, publish, engine.default_state) if self.state_updater is None else self.state_updater(GAME_ID, player_id, publish, engine.default_state)
        # Return exact committed authority in the private representation expected by the core.
        return self._to_core_state(authoritative)

    # Return the current isolated game state and immutable outcome metadata.
    def state(self, player_id: str) -> dict:
        # Read only the session-bound player's established direct-row document.
        state = self.state_loader(player_id)
        # Return the exact frozen state response without shared-helper private wrappers.
        return {"game": GAME_ID, "outcomes": outcome_catalog(), "recent_rounds": list(state.get("recent_rounds", []))}

    # Execute or replay one ledger-backed spin request through the shared helper.
    def spin(self, player_id: str, request: dict) -> dict:
        # Require an object payload before the shared resolver reads request fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before state, entropy, or ledger access.
            raise ValidationError("Big Six spin body must be an object")
        # Execute the complete exactly-once action through SimpleWagerGame.
        result = self._game.play(player_id, request)
        # Preserve the established game-owned action envelope without shared player/state metadata.
        return {"round": result["round"], "replayed": result["replayed"], "ledger": result["ledger"]}
