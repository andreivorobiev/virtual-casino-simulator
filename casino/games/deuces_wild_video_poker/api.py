# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Session-bound, ledger-only Deuces Wild API adapter for issue #92.

Existing requirements: SESSION-005, LEDGER-005, LEDGER-006, LEDGER-007,
LEDGER-009, and LEDGER-023. Permanent DWVP IDs remain owned by #77.
"""

# Import deep-copy support so rejected pre-ledger actions restore prior state exactly.
import copy
# Import regular-expression validation for bounded client action identifiers.
import re
# Import a process-local lock for exactly-once simulator settlement paths.
import threading

# Import the read-only player service without exposing a game-owned mutation boundary.
from casino.core import players
# Import the shared clock for persisted round lifecycle timestamps.
from casino.core.clock import utc_now
# Import the one canonical game-money boundary.
from casino.core.settlement import GameSettlementGateway
# Import the shared authenticated-player resolver used before every game dispatch.
from casino.core.request_player import resolve_authenticated_player
# Import provider-current player-scoped persistence for isolated atomic publication.
from casino.core.state_store import load_player_game_state, update_player_game_state
# Import public conflict, lookup, and validation errors for route boundaries.
from casino.errors import ConflictError, NotFoundError, ValidationError
# Import only this game's engine through the allowed isolated package boundary.
from casino.games.deuces_wild_video_poker import engine

# Use one stable game id for state documents, contracts, and ledger events.
GAME_ID = engine.GAME_ID
# Accept UUID-like and namespaced retry identifiers without arbitrary log text.
ACTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
# Serialize state preparation, ledger recovery, and marker persistence in this local process.
_ACTION_LOCK = threading.RLock()
# Keep one operation's optimistic comparison snapshot outside persistent state.
_ATOMIC_BASELINE_KEY = "_deuces_wild_atomic_baseline"
# Name the complete set of document fields owned by this game's engine and API adapter.
_GAME_STATE_KEYS = ("active_round", "recent_rounds", "actions")
# Name the game-owned ledger detail carrying stable internal idempotency keys.
IDEMPOTENCY_DETAIL = "idempotency_key"


# Normalize one required client action id before state or ledger access.
def require_action_id(value) -> str:
    # Preserve strings while rejecting implicit object representations.
    action_id = value.strip() if isinstance(value, str) else ""
    # Require a conservative URL- and log-safe identifier length and alphabet.
    if not ACTION_ID_PATTERN.fullmatch(action_id):
        # Describe the stable public boundary without echoing untrusted input.
        raise ValidationError("action_id must be 8-128 URL-safe characters")
    # Return the unchanged validated identity for replay matching.
    return action_id


# Resolve the player selected by the authenticated request context.
def request_player_id(body: dict, query: dict, context: dict | None = None) -> str:
    # Delegate precedence to the shared resolver so bound sessions override caller IDs.
    return resolve_authenticated_player(context or {}, body, query)


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


# Coordinate reload-safe game state with exactly-once ledger-only settlement.
class DeucesWildVideoPokerService:
    # Store production dependencies while allowing isolated tests to inject in-memory ports.
    def __init__(self, *, repository=None, debit=None, credit=None, read_ledger=None, get_player=players.get_player, clock=utc_now, seed_factory=None):
        # Use shared provider persistence unless a focused test supplies an in-memory repository.
        self._repository = repository or StateRepository()
        # Bind production and injected test seams behind the canonical settlement adapter.
        settlement = GameSettlementGateway(GAME_ID, IDEMPOTENCY_DETAIL, debit=debit, credit=credit, read_recent=read_ledger)
        # Preserve the historical callback shape while routing through the shared adapter.
        self._debit = settlement.debit
        # Preserve the historical credit shape while routing through the shared adapter.
        self._credit = settlement.credit
        # Preserve indexed proof lookup through the adapter-owned ledger seam.
        self._find_action = settlement.find
        # Store read-only player lookup for response payloads.
        self._get_player = get_player
        # Store the clock seam for deterministic focused tests.
        self._clock = clock
        # Store an optional deterministic seed factory that production leaves disabled.
        self._seed_factory = seed_factory

    # Load one authenticated player's isolated state document.
    def _load(self, player_id: str) -> dict:
        # Delegate schema migration and active provider selection to the shared store.
        state = self._repository.load(player_id)
        # Retain the exact game-owned values the next publication may replace.
        state[_ATOMIC_BASELINE_KEY] = self._game_snapshot(state)
        # Return tracked state without persisting the private comparison field.
        return state

    # Capture only fields owned by Deuces Wild while normalizing older documents.
    @staticmethod
    def _game_snapshot(state: dict) -> dict:
        # Start from the engine's canonical empty state for absent legacy fields.
        defaults = engine.default_state()
        # Detach each game-owned value so later caller mutation cannot change the baseline.
        return {key: copy.deepcopy(state.get(key, defaults[key])) for key in _GAME_STATE_KEYS}

    # Publish one authenticated player's compare-and-replace recovery transition. (DWVP-006)
    def _save(self, player_id: str, state: dict) -> None:
        # Require every publication to originate from a provider read or prior result.
        expected = copy.deepcopy(state.get(_ATOMIC_BASELINE_KEY))
        # Refuse an untracked whole-document write before entering provider storage.
        if not isinstance(expected, dict):
            # Keep accidental stale saves outside persistent player state.
            raise ConflictError("Deuces Wild state transition is missing its atomic baseline")
        # Capture the exact game-owned result before entering provider code.
        desired = self._game_snapshot(state)

        # Compare and replace only Deuces Wild fields against provider-current state.
        def publish(current: dict) -> dict:
            # Capture provider-current game fields without metadata or sibling values.
            observed = self._game_snapshot(current)
            # Accept exact same-result completion without rewriting provider values.
            if observed == desired:
                # Preserve current metadata and unrelated siblings unchanged.
                return current
            # Reject a stale transition before it can replace another action's state.
            if observed != expected:
                # Require a fresh load and authoritative recovery from the winner.
                raise ConflictError("Deuces Wild state changed during this action; reload and retry")
            # Publish every game-owned field as a detached provider value.
            for key in _GAME_STATE_KEYS:
                # Replace one owned field without copying operation metadata or siblings.
                current[key] = copy.deepcopy(desired[key])
            # Return the complete provider document with every unrelated sibling preserved.
            return current

        # Commit through the provider's cross-process read-modify-write boundary.
        authoritative = self._repository.update(player_id, publish)
        # Advance the private baseline to the exact committed game-owned result.
        state[_ATOMIC_BASELINE_KEY] = self._game_snapshot(authoritative)

    # Read the replay registry while tolerating pre-module or malformed documents.
    def _actions(self, state: dict) -> dict:
        # Create the private action registry only when it is absent.
        actions = state.setdefault("actions", {})
        # Reject corrupted non-object replay state rather than losing idempotency history.
        if not isinstance(actions, dict):
            # Surface persisted corruption as an explicit conflict.
            raise ConflictError("Deuces Wild action history is unavailable")
        # Return the mutable private registry for this loaded document.
        return actions

    # Require one replay record to describe the same logical command and payload.
    def _validate_replay(self, record: dict, *, command: str, round_id: str, fingerprint) -> None:
        # Fail closed when one client id is reused for another command, round, or input.
        if record.get("command") != command or record.get("round_id") != round_id or record.get("fingerprint") != fingerprint:
            # Protect exactly-once semantics from same-id semantic conflicts.
            raise ConflictError("action_id was already used for another Deuces Wild action")

    # Store one private replay record before returning a successful mutation.
    def _remember_action(self, state: dict, action_id: str, *, command: str, round_id: str, fingerprint) -> None:
        # Map the client identity to the exact normalized action semantics.
        self._actions(state)[action_id] = {"command": command, "round_id": round_id, "fingerprint": fingerprint}

    # Find a previously committed ledger movement by its stable internal action key.
    def _find_ledger_action(self, player_id: str, action_key: str):
        # Resolve the exact game-scoped storage identity without scanning ledger history.
        return self._find_action(player_id, action_key)

    # Verify that recovered ledger proof matches the complete expected movement.
    def _validate_ledger_event(self, event: dict, *, round_state: dict, transaction_type: str, signed_amount: float, action_key: str, fingerprint) -> None:
        # Read structured details without assuming unrelated historical rows provide them.
        details = event.get("details") or {}
        # Compare game, round, type, signed amount, key, and semantic fingerprint together.
        matches = event.get("game") == GAME_ID and event.get("round_id") == round_state["round_id"] and event.get("transaction_type") == transaction_type and round(float(event.get("amount", 0)), 2) == round(float(signed_amount), 2) and details.get(IDEMPOTENCY_DETAIL) == action_key and details.get("legacy_request_fingerprint", details.get("request_fingerprint")) == fingerprint
        # Reject lookalike or conflicting rows instead of accepting weak ledger proof.
        if not matches:
            # Preserve action identity across every material settlement field.
            raise ConflictError("Deuces Wild ledger action identity conflicts with an existing event")

    # Ensure the prepared wager debit exists exactly once.
    def _ensure_wager(self, player_id: str, state: dict, round_state: dict):
        # Derive a stable ledger action key from the deterministic round identity.
        action_key = f"{round_state['round_id']}:wager"
        # Bind both the amount and private prepared deal plan to the committed debit.
        fingerprint = {"wager": f"{round_state['wager']:.2f}", "deal_plan": engine.deal_plan_fingerprint(round_state)}
        # Recover committed proof before issuing any new balance movement.
        event = self._find_ledger_action(player_id, action_key)
        # Commit the aggregate wager only when no matching ledger row exists.
        if event is None:
            # Include player-independent audit semantics and both action identities.
            details = {IDEMPOTENCY_DETAIL: action_key, "client_action_id": round_state["deal_action_id"], "request_fingerprint": fingerprint, "wager": round_state["wager"]}
            # Route the positive wager amount through the shared debit service.
            event = self._debit(player_id, round_state["wager"], "DWVP_WAGER_DEBIT", GAME_ID, round_state["round_id"], details)
        # Validate newly created and recovered events through the same strict boundary.
        self._validate_ledger_event(event, round_state=round_state, transaction_type="DWVP_WAGER_DEBIT", signed_amount=-round_state["wager"], action_key=action_key, fingerprint=fingerprint)
        # Mark completion only after valid append-only proof exists.
        round_state["wager_status"] = "complete"
        # Store the immutable ledger id for diagnostics and focused evidence.
        round_state["wager_ledger_id"] = event.get("ledger_id")
        # Persist the completion marker so ordinary retries avoid ambiguity.
        self._save(player_id, state)
        # Return the committed or recovered ledger event.
        return event

    # Ensure the prepared returned-credit payout exists at most once.
    def _ensure_payout(self, player_id: str, state: dict, round_state: dict):
        # Skip zero ledger rows for a losing result.
        if not round_state.get("payout"):
            # Mark the no-credit terminal settlement complete.
            round_state["payout_status"] = "complete"
            # Persist the terminal marker for reload-safe state reads.
            self._save(player_id, state)
            # Return no event because no play-token movement occurred.
            return None
        # Derive one stable payout action key independent of repeated HTTP attempts.
        action_key = f"{round_state['round_id']}:payout"
        # Fingerprint the deterministic result and returned credits.
        fingerprint = {"result": round_state["result"], "multiplier": round_state["multiplier"], "payout": f"{round_state['payout']:.2f}"}
        # Recover a prior credit before issuing a potentially repeated movement.
        event = self._find_ledger_action(player_id, action_key)
        # Commit returned credits only when no matching ledger row exists.
        if event is None:
            # Include all stable audit dimensions without exposing private replacement cards.
            details = {IDEMPOTENCY_DETAIL: action_key, "client_action_id": round_state["draw_action_id"], "request_fingerprint": fingerprint, "result": round_state["result"], "multiplier": round_state["multiplier"], "wager": round_state["wager"]}
            # Route the positive returned credits through the shared credit service.
            event = self._credit(player_id, round_state["payout"], "DWVP_PAYOUT_CREDIT", GAME_ID, round_state["round_id"], details)
        # Validate newly created and recovered events identically.
        self._validate_ledger_event(event, round_state=round_state, transaction_type="DWVP_PAYOUT_CREDIT", signed_amount=round_state["payout"], action_key=action_key, fingerprint=fingerprint)
        # Mark settlement complete only after valid append-only proof exists.
        round_state["payout_status"] = "complete"
        # Store the immutable credit identifier for diagnostics and evidence.
        round_state["payout_ledger_id"] = event.get("ledger_id")
        # Persist the marker so reload never requires duplicate token movement.
        self._save(player_id, state)
        # Return the committed or recovered payout event.
        return event

    # Recover only already-prepared movements after reload or interruption.
    def _recover(self, player_id: str, state: dict) -> None:
        # Read the only active wagered round defensively.
        active_round = state.get("active_round")
        # Finish a wager that was prepared before a process interruption.
        if active_round and active_round.get("wager_status") != "complete":
            # Reconcile the debit through its stable round action key.
            self._ensure_wager(player_id, state, active_round)
        # Visit bounded settled history for any persisted pre-credit result.
        for round_state in state.get("recent_rounds", []):
            # Reconcile only completed cards whose payout marker remains pending.
            if round_state.get("phase") == "settled" and round_state.get("payout_status") != "complete":
                # Finish or recover the returned-credit action exactly once.
                self._ensure_payout(player_id, state, round_state)

    # Build the public state, paytable, and current-player payload.
    def _payload(self, player_id: str, state: dict, round_state=None, **extra) -> dict:
        # Return only sanitized game state plus read-only current-player information.
        return {"game": GAME_ID, "state": engine.public_state(state), "round": engine.public_round(round_state) if round_state is not None else None, "player": self._get_player(player_id), "paytable": dict(engine.PAYTABLE), **extra}

    # Read one player's reload-safe state and finish only prior prepared movements.
    def state(self, player_id: str) -> dict:
        # Serialize recovery against duplicate action requests in this process.
        with _ACTION_LOCK:
            # Load current player-owned state inside the settlement lock.
            state = self._load(player_id)
            # Recover wager or payout markers created by prior requests.
            self._recover(player_id, state)
            # Return the sanitized state with the immutable paytable.
            return self._payload(player_id, state)

    # Start or replay one held-card round under a stable deal action id.
    def start_round(self, player_id: str, body: dict) -> dict:
        # Validate action identity before state, entropy, or ledger access.
        action_id = require_action_id(body.get("action_id"))
        # Normalize the exact wager used by the request fingerprint.
        wager = engine.require_wager(body.get("wager"))
        # Derive the same opaque round identifier for every retry.
        round_id = engine.round_id_for(player_id, action_id)
        # Build the semantic fingerprint stored in replay state.
        fingerprint = {"wager": f"{wager:.2f}"}
        # Serialize preparation and reconciliation for duplicate local requests.
        with _ACTION_LOCK:
            # Load the latest player-owned state inside the action lock.
            state = self._load(player_id)
            # Recover every prepared wager and owed payout before admitting another round.
            self._recover(player_id, state)
            # Resolve any existing replay mapping before active-round checks.
            previous = self._actions(state).get(action_id)
            # Replay an earlier deal without drawing or debiting again.
            if previous is not None:
                # Require the exact same command, round, and normalized wager.
                self._validate_replay(previous, command="deal", round_id=round_id, fingerprint=fingerprint)
                # Resolve the originally prepared or settled round.
                round_state = engine.round_by_id(state, round_id)
                # Fail closed when replay metadata outlives required round state.
                if round_state is None:
                    # Prevent a stale action id from creating a replacement outcome.
                    raise ConflictError("Deuces Wild replay state is no longer available")
                # Recover a debit interrupted before its marker was saved.
                wager_event = self._ensure_wager(player_id, state, round_state)
                # Return the same round and current wallet state explicitly as a replay.
                return self._payload(player_id, state, round_state, wager=wager_event, replayed=True)
            # Reject an action whose ledger proof exists without matching reload state.
            if self._find_ledger_action(player_id, f"{round_id}:wager") is not None:
                # Avoid attaching an old debit to newly generated cards.
                raise ConflictError("Deuces Wild wager exists but its reload state is unavailable")
            # Prevent overlapping initial hands for one authenticated player.
            if state.get("active_round") is not None:
                # Require the current round to be drawn before another wager starts.
                raise ConflictError("Finish the active Deuces Wild round before dealing again")
            # Preserve clean state so an ordinary rejected debit leaves no phantom round.
            prior_state = copy.deepcopy(state)
            # Derive deterministic entropy only through an injected non-production seam.
            seed = self._seed_factory(action_id) if self._seed_factory else None
            # Prepare cards and private replacements before any token movement.
            round_state = engine.create_round(player_id, wager, action_id, seed=seed, round_id=round_id, created_at=self._clock())
            # Store the pending round so a post-debit crash can recover by stable key.
            state["active_round"] = round_state
            # Record the exact action semantics before the first ledger call.
            self._remember_action(state, action_id, command="deal", round_id=round_id, fingerprint=fingerprint)
            # Persist cards, private draw plan, and replay mapping before debit.
            self._save(player_id, state)
            # Start protected debit handling for insufficient-funds cleanup.
            try:
                # Ensure the prepared aggregate wager exactly once.
                wager_event = self._ensure_wager(player_id, state, round_state)
            # Restore prior state only when no new append-only movement committed.
            except Exception:
                # Look for committed proof in case marker persistence failed after debit.
                committed = self._find_ledger_action(player_id, f"{round_id}:wager")
                # Roll back prepared state only when the shared ledger has no event.
                if committed is None:
                    # Restore only game-owned values while retaining the prepared-state baseline.
                    for key in _GAME_STATE_KEYS:
                        # Copy the pre-request field without replacing provider siblings.
                        state[key] = copy.deepcopy(prior_state[key])
                    # Publish cleanup only if this request still owns the prepared result.
                    self._save(player_id, state)
                # Re-raise the original ledger, storage, or conflict error.
                raise
            # Return the new initial hand and committed wager evidence.
            return self._payload(player_id, state, round_state, wager=wager_event, replayed=False)

    # Set or replay the complete held-position list under one action id.
    def set_holds(self, player_id: str, round_id: str, body: dict) -> dict:
        # Validate action identity before state access.
        action_id = require_action_id(body.get("action_id"))
        # Normalize the complete desired hold set so the operation is idempotent.
        holds = engine.require_holds(body.get("holds"))
        # Use the canonical list directly as the replay fingerprint.
        fingerprint = {"holds": holds}
        # Serialize hold state against concurrent draw actions.
        with _ACTION_LOCK:
            # Load the latest player-owned document.
            state = self._load(player_id)
            # Resolve an earlier identical hold action first.
            previous = self._actions(state).get(action_id)
            # Replay the earlier state replacement without another mutation.
            if previous is not None:
                # Require the same target round and desired position list.
                self._validate_replay(previous, command="holds", round_id=round_id, fingerprint=fingerprint)
                # Resolve active or recently settled state for a lost response.
                round_state = engine.round_by_id(state, round_id)
                # Reject replay metadata whose round is no longer retained.
                if round_state is None:
                    # Keep stale action ids from targeting a newer round.
                    raise ConflictError("Deuces Wild replay state is no longer available")
                # Reconcile and validate the wager before returning any hold action replay.
                self._ensure_wager(player_id, state, round_state)
                # Return the current representation of the same logical round.
                return self._payload(player_id, state, round_state, replayed=True)
            # Resolve the authenticated player's only matching round.
            round_state = engine.round_by_id(state, round_id)
            # Reject missing and cross-player identifiers indistinguishably.
            if round_state is None:
                # Do not expose whether another player owns the supplied round id.
                raise NotFoundError("Active Deuces Wild round was not found")
            # Require immutable debit proof before accepting a hold on prepared cards.
            self._ensure_wager(player_id, state, round_state)
            # Apply the complete desired set through the pure engine boundary.
            engine.set_holds(round_state, holds)
            # Record action semantics before returning success.
            self._remember_action(state, action_id, command="holds", round_id=round_id, fingerprint=fingerprint)
            # Persist the selection for reload-safe continuation.
            self._save(player_id, state)
            # Return the updated initial hand and state.
            return self._payload(player_id, state, round_state, replayed=False)

    # Draw, settle, or replay one round under a stable draw action id.
    def draw(self, player_id: str, round_id: str, body: dict) -> dict:
        # Validate action identity before loading round state.
        action_id = require_action_id(body.get("action_id"))
        # Use the target round as the entire normalized draw fingerprint.
        fingerprint = {"round_id": round_id}
        # Serialize deterministic draw and payout recovery in this process.
        with _ACTION_LOCK:
            # Load current player-owned state inside the action lock.
            state = self._load(player_id)
            # Resolve an existing client action mapping before state transitions.
            previous = self._actions(state).get(action_id)
            # Replay an earlier draw without consuming replacements or crediting again.
            if previous is not None:
                # Require the same draw command and target round.
                self._validate_replay(previous, command="draw", round_id=round_id, fingerprint=fingerprint)
                # Resolve the already drawn or prepared round.
                round_state = engine.round_by_id(state, round_id)
                # Reject replay metadata whose result is no longer retained.
                if round_state is None:
                    # Prevent an old draw identity from targeting unrelated state.
                    raise ConflictError("Deuces Wild replay state is no longer available")
                # Reconcile and validate the wager before any draw replay can recover payout.
                self._ensure_wager(player_id, state, round_state)
                # Require deterministic cards to be complete before payout recovery.
                if round_state.get("phase") != "settled":
                    # Surface persisted replay corruption instead of drawing unexpectedly.
                    raise ConflictError("Deuces Wild draw replay is incomplete")
                # Recover any credit interrupted before its completion marker.
                payout_event = self._ensure_payout(player_id, state, round_state)
                # Return the same result explicitly as a replay.
                return self._payload(player_id, state, round_state, payout=payout_event, replayed=True)
            # Resolve only this authenticated player's active or retained round.
            round_state = engine.round_by_id(state, round_id)
            # Reject unknown and cross-session round identifiers uniformly.
            if round_state is None:
                # Keep another player's state existence private.
                raise NotFoundError("Deuces Wild round was not found")
            # Require one valid wager debit before computing cards or issuing returned credits.
            self._ensure_wager(player_id, state, round_state)
            # Recover a missing replay map when the settled round retains this action id.
            if round_state.get("phase") == "settled" and round_state.get("draw_action_id") == action_id:
                # Restore the exact replay semantics into private state.
                self._remember_action(state, action_id, command="draw", round_id=round_id, fingerprint=fingerprint)
                # Recover or confirm the payout action.
                payout_event = self._ensure_payout(player_id, state, round_state)
                # Return the same deterministic settlement as a replay.
                return self._payload(player_id, state, round_state, payout=payout_event, replayed=True)
            # Reject a different action id once a round is terminal.
            if round_state.get("phase") == "settled":
                # Preserve one client action identity for the payout transition.
                raise ConflictError("Round was already settled by another action_id")
            # Reject a payout event that exists without its deterministic result state.
            if self._find_ledger_action(player_id, f"{round_id}:payout") is not None:
                # Avoid attaching a committed credit to newly computed cards.
                raise ConflictError("Deuces Wild payout exists but its reload state is unavailable")
            # Complete the final hand solely from persisted replacement cards.
            engine.draw(round_state, action_id, completed_at=self._clock())
            # Record draw replay semantics before any payout credit.
            self._remember_action(state, action_id, command="draw", round_id=round_id, fingerprint=fingerprint)
            # Archive final cards before issuing returned credits.
            engine.archive_round(state, round_state)
            # Persist deterministic result and pending payout first.
            self._save(player_id, state)
            # Ensure the optional returned-credit action exactly once.
            payout_event = self._ensure_payout(player_id, state, round_state)
            # Return the terminal result and optional credit evidence.
            return self._payload(player_id, state, round_state, payout=payout_event, replayed=False)


# Register isolated additive-v1 routes for catalog discovery and focused tests.
def register(router, service=None, *, test_seed=None):
    # Create the production service unless a focused test injects controlled ports.
    game_service = service or DeucesWildVideoPokerService(seed_factory=(lambda action_id: f"{test_seed}:{action_id}") if test_seed is not None else None)

    # Register the authenticated player's reload-safe state endpoint.
    @router.get(r"/api/v1/games/deuces-wild-video-poker/state")
    # Read only the identity resolved by the shared session boundary.
    def state(body, query, context=None):
        # Resolve session ownership before state or ledger access.
        return game_service.state(request_player_id(body, query, context))

    # Register one replay-safe wagered initial deal.
    @router.post(r"/api/v1/games/deuces-wild-video-poker/rounds")
    # Start or replay a round for the resolved session player.
    def rounds(body, query, context=None):
        # Resolve session ownership before interpreting action data.
        return game_service.start_round(request_player_id(body, query, context), body)

    # Register reload-safe held-position replacement.
    @router.post(r"/api/v1/games/deuces-wild-video-poker/rounds/(?P<round_id>[A-Za-z0-9_-]+)/holds")
    # Set or replay holds for the resolved session player's round.
    def holds(body, query, round_id, context=None):
        # Resolve session ownership before locating the round.
        return game_service.set_holds(request_player_id(body, query, context), round_id, body)

    # Register deterministic draw and ledger payout settlement.
    @router.post(r"/api/v1/games/deuces-wild-video-poker/rounds/(?P<round_id>[A-Za-z0-9_-]+)/draw")
    # Complete or replay the resolved session player's round.
    def draw(body, query, round_id, context=None):
        # Resolve session ownership before locating or settling the round.
        return game_service.draw(request_player_id(body, query, context), round_id, body)

    # Return the service so focused tests can inspect injected adapters.
    return game_service
