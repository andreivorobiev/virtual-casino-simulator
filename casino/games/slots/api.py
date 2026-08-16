# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Slots API actions, spin persistence, and exactly-once settlement orchestration.
# Import deep-copy support for detached optimistic game-state snapshots.
import copy
# Import player-scoped reads and provider-atomic state mutation.
from casino.core.state_store import load_player_game_state, update_player_game_state
from casino.core.validation import require_player_id
from casino.core import players
# Import the one canonical game-money boundary.
from casino.core.settlement import GameSettlementGateway
from casino.core.history import append_history
# Import the shared opaque-id helper so debit, spin, credit, and history share one round.
from casino.core.ids import new_id
from casino.games.slots import engine
# Import the public conflict boundary used for stale state publications.
from casino.errors import ConflictError
# Set GAME_ID to the value needed for the next operation.
GAME_ID = "slots"
# Bind every Slots movement to the shared storage-atomic settlement adapter.
SETTLEMENT = GameSettlementGateway(GAME_ID)
# Keep one operation's optimistic comparison snapshot outside persistent state.
_ATOMIC_BASELINE_KEY = "_slots_atomic_baseline"
# Name every always-present state field owned by Slots transitions.
_GAME_STATE_KEYS = tuple(engine.default_state())
# Name optional owned fields that compatible historical and bonus states may omit.
_OPTIONAL_GAME_STATE_KEYS = ("free_spin_basis", "progressive_meters")

# Capture detached values for every Slots-owned state field.
def _game_snapshot(state: dict) -> dict:
    # Build one fresh compatibility baseline for absent predecessor fields.
    defaults = engine.default_state()
    # Normalize every always-present field to the current default shape.
    snapshot = {key: copy.deepcopy(state.get(key, defaults[key])) for key in _GAME_STATE_KEYS}
    # Preserve optional field presence so deletion is compared and published exactly.
    for key in _OPTIONAL_GAME_STATE_KEYS:
        # Copy only optional fields that exist in this exact document.
        if key in state:
            # Detach nested bonus or legacy-meter values from caller mutation.
            snapshot[key] = copy.deepcopy(state[key])
    # Return only state governed by this game module.
    return snapshot

# Load one player document and bind its exact game-owned baseline.
def _load_state(player_id: str) -> dict:
    # Read the provider-owned player document through the shared state boundary.
    state = load_player_game_state(GAME_ID, player_id, engine.default_state)
    # Retain only the game-owned values expected by the next publication.
    state[_ATOMIC_BASELINE_KEY] = _game_snapshot(state)
    # Return tracked state without persisting private operation metadata.
    return state

# Publish one provider-current compare-and-replace transition. (SLOT-038)
def _save_state(player_id: str, state: dict) -> None:
    # Require every publication to originate from a tracked provider read.
    expected = copy.deepcopy(state.get(_ATOMIC_BASELINE_KEY))
    # Reject fabricated or stale detached documents before storage access.
    if not isinstance(expected, dict):
        # Keep untracked state outside provider bytes.
        raise ConflictError("Slots state transition is missing its atomic baseline")
    # Capture the exact game-owned result before entering provider code.
    desired = _game_snapshot(state)

    # Compare and replace only Slots-owned fields on current state.
    def publish(current: dict) -> dict:
        # Detach provider-current game fields from unrelated siblings.
        observed = _game_snapshot(current)
        # Accept an identical publication without rewriting siblings.
        if observed == desired:
            # Preserve the complete authoritative provider document.
            return current
        # Reject an operation whose game-owned baseline lost a race.
        if observed != expected:
            # Require recovery from the authoritative winning action.
            raise ConflictError("Slots state changed during this action; reload and retry")
        # Replace every always-present game-owned field with detached desired bytes.
        for key in _GAME_STATE_KEYS:
            # Publish copies so later caller mutation cannot leak into storage.
            current[key] = copy.deepcopy(desired[key])
        # Synchronize optional fields, including authoritative deletion.
        for key in _OPTIONAL_GAME_STATE_KEYS:
            # Publish optional values that remain part of the desired state.
            if key in desired:
                # Detach the optional value from the operation's local document.
                current[key] = copy.deepcopy(desired[key])
            else:
                # Remove optional game state that this transition consumed or migrated.
                current.pop(key, None)
        # Return the complete document with every unrelated sibling preserved.
        return current

    # Commit through the provider's cross-process mutation boundary.
    authoritative = update_player_game_state(GAME_ID, player_id, publish, engine.default_state)
    # Advance the in-memory baseline to the exact committed game-owned result.
    state[_ATOMIC_BASELINE_KEY] = _game_snapshot(authoritative)

# Return a detached public state without private optimistic metadata.
def _public_state(state: dict) -> dict:
    # Copy the response state so sanitization cannot mutate the tracked operation.
    public = copy.deepcopy(state)
    # Keep the private compare-and-replace baseline out of the frozen v1 payload.
    public.pop(_ATOMIC_BASELINE_KEY, None)
    # Return every historical public game and sibling field unchanged.
    return public

# Define the request_player_id function used by this module.
def request_player_id(body, query) -> str:
    # Return the explicit player id while preserving the legacy human default.
    return require_player_id({"player_id": body.get("player_id") or query.get("player_id") or "human"})

# Define the payload function used by this module.
def payload(player_id: str, state=None):
    # Set state to the value needed for the next operation.
    state = state or _load_state(player_id)
    # Return detached runtime rules so the browser never relies on stale embedded economics.
    return {"game": GAME_ID, "state": _public_state(state), "player": players.get_player(player_id), "config": {"symbols": list(engine.SYMBOLS), "paylines": list(engine.PAYLINES.keys()), "paytable": {symbol: dict(table) for symbol, table in engine.PAYTABLE.items()}, "economics": engine.economics_config()}}

# Define the register function used by this module.
def register(router):
    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/games/slots/state")
    # Define the state function used by this module.
    def state(body, query): return payload(request_player_id(body, query))

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/games/slots/config")
    # Define the config function used by this module.
    def config(body, query): return payload(request_player_id(body, query))["config"]

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/slots/spin")
    # Define the spin function used by this module.
    def spin(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Normalize the submitted line count through the exact engine-owned closed vocabulary.
        active_lines = engine.normalize_active_lines(body.get("active_lines", 5))
        # Preserve the frozen v1 cent-normalized amount range at the game-owned boundary.
        line_bet = engine.normalize_line_bet(body.get("line_bet", 1))
        # Set state to the value needed for the next operation.
        state = _load_state(player_id)
        # Preview the exact current-route cost while a banked feature remains zero-cost.
        configuration = engine.effective_configuration(state, active_lines, line_bet)
        # Use the engine-owned cost equation before the current ledger debit.
        cost = configuration["cost"]
        # Allocate one round identity before money movement so every debit and settlement row reconciles.
        round_id = new_id("slot")
        # Set debit to the value needed for the next operation.
        debit = None
        if cost > 0:
            # Set debit to the value needed for the next operation.
            debit, _debit_replayed = SETTLEMENT.apply_once(player_id=player_id, signed_amount=-cost, transaction_type="SLOTS_SPIN_DEBIT", round_id=round_id, action_key=f"{round_id}:wager", request_fingerprint=f"{round_id}:{configuration['active_lines']}:{configuration['line_bet']}:{cost}", details={"active_lines": configuration["active_lines"], "line_bet": configuration["line_bet"], "cost": cost})
        # Set result to the value needed for the next operation.
        result = engine.spin(state, active_lines, line_bet, round_id=round_id)
        # Set credit to the value needed for the next operation.
        credit = None
        if result["payout"] > 0:
            # Set credit to the value needed for the next operation.
            credit, _credit_replayed = SETTLEMENT.apply_once(player_id=player_id, signed_amount=result["payout"], transaction_type="SLOTS_PAYOUT_CREDIT", round_id=result["round_id"], action_key=f"{result['round_id']}:settlement", request_fingerprint=f"{result['round_id']}:{result['payout']}", details={"wins": result["wins"], "line_payout": result["line_payout"], "scatter_payout": result["scatter_payout"], "progressive_hit": result["progressive_hit"]})
        # Set bal to the value needed for the next operation.
        bal = players.get_player(player_id)["balance"]
        append_history(GAME_ID, result["round_id"], player_id, "spin", f"{result['active_lines']} lines @ {result['line_bet']}", result["cost"], "win" if result["payout"] else "loss", result["payout"], bal, result)
        _save_state(player_id, state)
        return {"spin": result, "debit": debit, "credit": credit, **payload(player_id, state)}
