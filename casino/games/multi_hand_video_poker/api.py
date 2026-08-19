# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Session-compatible, ledger-only API adapter for issue #94."""

# Import regular-expression validation for bounded client retry identifiers.
import re
# Import bounded player-scoped serialization so unrelated wallets can proceed concurrently.
from casino.core.player_locks import player_action_lock

# Import shared ledger, player, and clock services without mutating balances directly.
from casino.core import players
# Route every player-wallet movement through the shared exactly-once settlement boundary.
from casino.core.settlement import GameSettlementGateway
# Import the shared clock for persisted round lifecycle timestamps.
from casino.core.clock import utc_now
# Import the shared id generator for ledger-correlated round identifiers.
from casino.core.ids import new_id
# Import player-scoped state helpers so reads and publications share the provider boundary.
from casino.core.state_store import load_player_game_state, update_player_game_state
# Import the canonical player-id validator used by current and future router paths.
from casino.core.validation import require_player_id
# Import public conflict, lookup, and validation errors for route boundaries.
from casino.errors import ConflictError, NotFoundError, ValidationError
# Import only this game's deterministic engine through the allowed module boundary.
from casino.games.multi_hand_video_poker import engine

# Use one game id consistently for state documents and ledger events.
GAME_ID = engine.GAME_ID
# Bound client retry keys to conservative URL-safe identifier characters.
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


# Persist and load one player's state through explicit provider-owned boundaries.
class StateRepository:
    # Load one player-scoped document for read-only payload construction.
    def load(self, player_id: str) -> dict:
        # Delegate schema normalization and provider selection to the shared store.
        return load_player_game_state(GAME_ID, player_id, engine.default_state)

    # Apply one complete transition while the provider owns its cross-process lock.
    def update(self, player_id: str, mutator) -> dict:
        # Delegate current-state loading, rollback, and publication to the atomic helper.
        return update_player_game_state(GAME_ID, player_id, mutator, engine.default_state)


# Resolve the player identity already bound by current main or the #81 shared resolver.
def request_player_id(body: dict, query: dict) -> str:
    # Prefer query because current main replaces it from bound_player_id before dispatch.
    player_id = query.get("player_id") or body.get("player_id") or "human"
    # Validate the resolved value without accepting an empty identity.
    return require_player_id({"player_id": player_id})


# Validate the required idempotency key used for wager retry recovery.
def require_request_id(value) -> str:
    # Require a bounded string whose characters remain safe in logs and JSON state.
    if not isinstance(value, str) or not REQUEST_ID_PATTERN.fullmatch(value):
        # Explain the accepted retry-key boundary without echoing caller input.
        raise ValidationError("request_id must be 1-128 URL-safe characters")
    # Return the validated key unchanged for exact replay matching.
    return value


# Coordinate game state with ledger-only settlement through injectable dependencies.
class MultiHandVideoPokerService:
    # Store production dependencies while allowing isolated tests to use in-memory adapters.
    def __init__(self, *, repository=None, debit=None, credit=None, read_ledger=None, get_player=players.get_player, clock=utc_now, id_factory=new_id, seed_factory=None):
        # Use shared provider persistence unless a focused test supplies an in-memory repository.
        self._repository = repository or StateRepository()
        # Store the only allowed wager debit operation.
        settlement = GameSettlementGateway(GAME_ID, debit=debit, credit=credit, read_recent=read_ledger)
        self._debit = settlement.debit
        # Store the only allowed payout credit operation.
        self._credit = settlement.credit
        # Store ledger history lookup for crash-safe replay detection.
        self._read_ledger = settlement.read_recent
        # Store player reads for response payloads without balance mutation.
        self._get_player = get_player
        # Store the clock hook for deterministic focused tests.
        self._clock = clock
        # Store the round-id hook for deterministic focused tests.
        self._id_factory = id_factory
        # Store an optional seed factory that production catalog registration leaves disabled.
        self._seed_factory = seed_factory

    # Load one authenticated player's isolated game state.
    def _load(self, player_id: str) -> dict:
        # Delegate through the standard player-game state storage abstraction.
        return self._repository.load(player_id)

    # Apply one transition against the provider-owned latest player document. (MHVP-007)
    def _update(self, player_id: str, mutator) -> dict:
        # Delegate locking, rollback, and publication to the shared atomic boundary.
        return self._repository.update(player_id, mutator)

    # Replace one caller snapshot with the complete authoritative provider result. (MHVP-007)
    @staticmethod
    def _refresh_state(state: dict, authoritative: dict) -> None:
        # Remove stale top-level fields that another process may have replaced.
        state.clear()
        # Preserve caller object identity while adopting every provider-owned field.
        state.update(authoritative)

    # Resolve one exact round and reject a missing or reused identity before marker publication.
    @staticmethod
    def _matching_round(state: dict, expected: dict) -> dict:
        # Locate active or archived state through the engine's established lookup boundary.
        round_state = engine.round_by_id(state, expected["round_id"])
        # Bind markers to immutable request, player, wager, and hand-count dimensions.
        fields = ("round_id", "request_id", "player_id", "hand_count", "wager_per_hand", "total_wager")
        # Reject disappearance or identity drift rather than marking an unrelated round complete.
        if round_state is None or any(round_state.get(field) != expected.get(field) for field in fields):
            # Keep the internal recovery conflict fixed and non-reflecting.
            raise ConflictError("Video poker round state changed during settlement")
        # Return the exact current round so sibling fields remain provider-authoritative.
        return round_state

    # Find a prior ledger event that proves an exactly-once movement already occurred.
    def _ledger_event(self, player_id: str, round_id: str, transaction_type: str):
        # Read a bounded recent window sufficient for the game's bounded round history.
        events = self._read_ledger(player_id, 500)
        # Match all three ownership fields so another game or player cannot satisfy replay.
        return next((event for event in events if event.get("game") == GAME_ID and event.get("round_id") == round_id and event.get("transaction_type") == transaction_type), None)

    # Ensure the round's aggregate wager has exactly one ledger debit.
    def _ensure_wager(self, player_id: str, state: dict, round_state: dict):
        # Look for a committed debit before issuing a potentially repeated movement.
        event = self._ledger_event(player_id, round_state["round_id"], "MHVP_WAGER_DEBIT")
        # Create the aggregate debit only when no committed ledger proof exists.
        if event is None:
            # Debit once for all selected hands and include complete audit dimensions.
            event = self._debit(player_id, round_state["total_wager"], "MHVP_WAGER_DEBIT", GAME_ID, round_state["round_id"], {"request_id": round_state["request_id"], "hand_count": round_state["hand_count"], "wager_per_hand": round_state["wager_per_hand"]})
        # Publish the completion marker against the latest round without replacing siblings.
        def complete(current: dict) -> dict:
            # Resolve only the round whose immutable wager dimensions produced this event.
            current_round = self._matching_round(current, round_state)
            # Mark state only after a ledger event exists or has been recovered.
            current_round["wager_status"] = "complete"
            # Store the immutable ledger id for diagnostics and API evidence.
            current_round["wager_ledger_id"] = event.get("ledger_id")
            # Return the complete current document for atomic publication.
            return current

        # Adopt the authoritative document after the marker commits.
        self._refresh_state(state, self._update(player_id, complete))
        # Return the committed event and the provider-current round body.
        return event, self._matching_round(state, round_state)

    # Ensure the round's aggregate returned credits have at most one ledger credit.
    def _ensure_payout(self, player_id: str, state: dict, round_state: dict):
        # Skip ledger writes for zero payouts because shared ledger rows cannot be zero.
        if not round_state.get("total_payout"):
            # Use no ledger id because zero-credit settlements create no ledger row.
            event = None
        # Look for a committed credit before issuing a potentially repeated movement.
        else:
            # Look for a committed credit before issuing a potentially repeated movement.
            event = self._ledger_event(player_id, round_state["round_id"], "MHVP_PAYOUT_CREDIT")
            # Create the aggregate payout credit only when no committed ledger proof exists.
            if event is None:
                # Credit all qualifying hands in one auditable ledger event.
                event = self._credit(player_id, round_state["total_payout"], "MHVP_PAYOUT_CREDIT", GAME_ID, round_state["round_id"], {"hand_count": round_state["hand_count"], "wager_per_hand": round_state["wager_per_hand"], "outcome": round_state["outcome"], "results": [{"hand_index": result["hand_index"], "outcome": result["outcome"], "payout": result["payout"]} for result in round_state["results"]]})

        # Publish the terminal settlement marker against the provider-owned latest document.
        def complete(current: dict) -> dict:
            # Resolve the same immutable round even when another request archived it first.
            current_round = self._matching_round(current, round_state)
            # Mark state only after a ledger event exists or zero payout is proven.
            current_round["payout_status"] = "complete"
            # Store a ledger id only for a positive committed payout.
            if event is not None:
                # Preserve immutable payout proof for response and restart diagnostics.
                current_round["payout_ledger_id"] = event.get("ledger_id")
            # Return the complete latest document for atomic publication.
            return current

        # Adopt the authoritative document after the terminal marker commits.
        self._refresh_state(state, self._update(player_id, complete))
        # Return the optional event and exact provider-current round body.
        return event, self._matching_round(state, round_state)

    # Build the public state/player payload shared by every game route.
    def payload(self, player_id: str, state=None) -> dict:
        # Load state only when the caller has not already mutated an in-memory copy.
        current = state if state is not None else self._load(player_id)
        # Return sanitized game state and a read-only current-player snapshot.
        return {"game": GAME_ID, "state": engine.public_state(current), "player": self._get_player(player_id), "hand_counts": list(engine.HAND_COUNTS), "paytable": dict(engine.PAYTABLE)}

    # Start or replay one idempotent wagered round.
    def start_round(self, player_id: str, body: dict) -> dict:
        # Validate the client retry key before touching state or the ledger.
        request_id = require_request_id(body.get("request_id"))
        # Normalize the hand count once so replay comparison and creation cannot diverge.
        hand_count = engine.require_hand_count(body.get("hand_count"))
        # Normalize the per-hand wager once before any durable state transition.
        wager_per_hand = engine.require_wager_per_hand(body.get("wager_per_hand"))
        # Serialize local settlement calls while provider callbacks protect cross-process state.
        with player_action_lock(player_id):
            # Retain creation ownership and round identity outside the provider callback.
            selected = {}

            # Prepare or replay one round against the provider-owned latest document.
            def prepare(current: dict) -> dict:
                # Clear callback evidence defensively if a provider ever retries the mutator.
                selected.clear()
                # Recover an earlier request before enforcing the one-active-round rule.
                existing = engine.round_for_request(current, request_id)
                # Reuse a compatible prepared or settled request without creating another round.
                if existing is not None:
                    # Reject reuse of one idempotency key for different money movement.
                    if existing["hand_count"] != hand_count or existing["wager_per_hand"] != wager_per_hand:
                        # Keep one request identity bound to one immutable wager.
                        raise ConflictError("request_id was already used with different round settings")
                    # Return detached selection evidence after the provider transition commits.
                    selected.update({"round_id": existing["round_id"], "created": False})
                    # Leave the complete provider-owned document unchanged on replay.
                    return current
                # Prevent a second wager while the current common hand awaits a draw.
                if current.get("active_round") is not None:
                    # Require the player to finish the current round first.
                    raise ConflictError("Finish the active round before dealing again")
                # Derive a deterministic test seed only through an injected non-production hook.
                seed = self._seed_factory(request_id) if self._seed_factory else None
                # Create the reload-safe round before issuing its aggregate ledger debit.
                round_state = engine.create_round(player_id, hand_count, wager_per_hand, request_id, seed=seed, round_id=self._id_factory("mhvp"), created_at=self._clock())
                # Store the pending round so a crash after debit can recover by round id.
                current["active_round"] = round_state
                # Bind rollback and response reconstruction to the exact new round.
                selected.update({"round_id": round_state["round_id"], "created": True})
                # Publish the complete provider-current document atomically.
                return current

            # Commit preparation without allowing a stale whole-document overwrite.
            state = self._update(player_id, prepare)
            # Resolve the exact selected round from the authoritative document.
            round_state = engine.round_by_id(state, selected["round_id"])
            # Start protected debit handling so rejected wagers do not trap an empty round.
            try:
                # Ensure the aggregate wager through the exactly-once ledger guard.
                wager_event, round_state = self._ensure_wager(player_id, state, round_state)
            # Remove a non-debited pending round when the ledger rejects the wager.
            except Exception:
                # Clear the active slot only when no committed debit can be found.
                if selected["created"] and self._ledger_event(player_id, selected["round_id"], "MHVP_WAGER_DEBIT") is None:
                    # Remove only this action's exact still-pending prepared round.
                    def rollback(current: dict) -> dict:
                        # Read the current active slot without assuming the stale caller snapshot won.
                        active_round = current.get("active_round")
                        # Clear only the exact request and round while it still lacks ledger proof.
                        if active_round and active_round.get("round_id") == selected["round_id"] and active_round.get("request_id") == request_id and active_round.get("wager_status") == "pending":
                            # Leave every unrelated concurrent field untouched.
                            current["active_round"] = None
                        # Publish either the bounded rollback or the unchanged latest document.
                        return current

                    # Adopt the provider-current result after bounded rollback.
                    self._refresh_state(state, self._update(player_id, rollback))
                # Re-raise the original ledger or storage error.
                raise
            # Return the authoritative common hand and committed wager evidence.
            return {"round": engine.public_round(round_state), "wager": wager_event, "replayed": not selected["created"], **self.payload(player_id, state)}

    # Persist hold positions for reload-safe continuation.
    def set_holds(self, player_id: str, round_id: str, holds) -> dict:
        # Serialize hold changes against concurrent draws.
        with player_action_lock(player_id):
            # Apply the hold selection inside the same lock that reads actionable state.
            def apply_holds(current: dict) -> dict:
                # Read the only actionable round from the provider-current active slot.
                round_state = current.get("active_round")
                # Reject missing or stale round identifiers.
                if not round_state or round_state.get("round_id") != round_id:
                    # Keep cross-player and unknown-round behavior indistinguishable.
                    raise NotFoundError("Active video poker round was not found")
                # Prevent another process from drawing before wager publication finishes.
                if round_state.get("wager_status") != "complete":
                    # Fail closed until the prepared round has immutable debit proof.
                    raise ConflictError("Round wager is not complete")
                # Validate and persist the shared hold positions through the engine.
                engine.set_holds(round_state, holds)
                # Publish the complete latest document without replacing siblings.
                return current

            # Commit the selection against the provider-owned latest state.
            state = self._update(player_id, apply_holds)
            # Resolve the exact active round after atomic publication.
            round_state = state["active_round"]
            # Return the updated public common hand.
            return {"round": engine.public_round(round_state), **self.payload(player_id, state)}

    # Draw every hand and settle one aggregate payout exactly once.
    def draw(self, player_id: str, round_id: str) -> dict:
        # Serialize deterministic draw, pre-credit state, ledger check, and completion marker.
        with player_action_lock(player_id):
            # Retain replay classification outside the atomic draw callback.
            selected = {}

            # Complete or replay the draw against the provider-owned latest document.
            def settle(current: dict) -> dict:
                # Clear callback evidence defensively if a provider ever retries the mutator.
                selected.clear()
                # Find active or recent state so a repeated draw can recover settlement.
                round_state = engine.round_by_id(current, round_id)
                # Reject unknown identifiers without exposing another player's state.
                if round_state is None:
                    # Return a stable lookup error for cross-session safety.
                    raise NotFoundError("Video poker round was not found")
                # Record whether cards were already complete before this request began.
                selected["replayed"] = round_state.get("phase") == "settled"
                # Complete cards only when this is the active hold-phase round.
                if round_state.get("phase") == "hold":
                    # Reject draw while a prepared wager still lacks immutable ledger proof.
                    if round_state.get("wager_status") != "complete":
                        # Keep state and money ordering fail closed across processes.
                        raise ConflictError("Round wager is not complete")
                    # Read the active slot defensively before checking its identifier.
                    active_round = current.get("active_round")
                    # Reject drawing a historical hold-shaped record after state corruption.
                    if not active_round or active_round.get("round_id") != round_id:
                        # Prevent an archived record from becoming actionable again.
                        raise ConflictError("Only the active round can be drawn")
                    # Compute all final hands exactly once from persisted replacement pools.
                    engine.draw(round_state, completed_at=self._clock())
                    # Archive the completed result before issuing any payout credit.
                    engine.archive_round(current, round_state)
                # Reject unknown states rather than guessing a settlement action.
                elif round_state.get("phase") != "settled":
                    # Explain the stale action as a state conflict.
                    raise ConflictError("This round cannot be settled in its current phase")
                # Publish deterministic results or the unchanged replay atomically.
                return current

            # Commit draw/archive against the complete latest state document.
            state = self._update(player_id, settle)
            # Resolve the exact settled round from authoritative active or recent state.
            round_state = engine.round_by_id(state, round_id)
            # Ensure the aggregate payout through the ledger recovery guard.
            payout_event, round_state = self._ensure_payout(player_id, state, round_state)
            # Return the completed hands and optional committed payout event.
            return {"round": engine.public_round(round_state), "payout": payout_event, "replayed": selected["replayed"], **self.payload(player_id, state)}


# Register the isolated routes for catalog discovery or direct focused tests.
def register(router, service=None, *, test_seed=None):
    # Create the production service unless an isolated test supplies its own dependencies.
    game_service = service or MultiHandVideoPokerService(seed_factory=(lambda request_id: f"{test_seed}:{request_id}") if test_seed is not None else None)

    # Register the player-scoped reload-safe state endpoint.
    @router.get(r"/api/v1/games/multi-hand-video-poker/state")
    # Return state for the identity already bound by the shared router.
    def state(body, query):
        # Resolve the router-bound player and return only that player's state.
        return game_service.payload(request_player_id(body, query))

    # Register the idempotent aggregate-wager deal endpoint.
    @router.post(r"/api/v1/games/multi-hand-video-poker/rounds")
    # Create or replay a round for the bound player.
    def rounds(body, query):
        # Resolve the router-bound player before any state or ledger access.
        return game_service.start_round(request_player_id(body, query), body)

    # Register reload-safe common hold selection.
    @router.post(r"/api/v1/games/multi-hand-video-poker/rounds/(?P<round_id>[A-Za-z0-9_-]+)/holds")
    # Save shared hold positions for the bound player's active round.
    def holds(body, query, round_id):
        # Resolve the router-bound player before locating the round.
        return game_service.set_holds(request_player_id(body, query), round_id, body.get("holds"))

    # Register deterministic multi-hand draw and aggregate settlement.
    @router.post(r"/api/v1/games/multi-hand-video-poker/rounds/(?P<round_id>[A-Za-z0-9_-]+)/draw")
    # Complete and settle the bound player's round.
    def draw(body, query, round_id):
        # Resolve the router-bound player before locating or settling the round.
        return game_service.draw(request_player_id(body, query), round_id)

    # Return the service so focused tests can inspect injected adapters.
    return game_service
