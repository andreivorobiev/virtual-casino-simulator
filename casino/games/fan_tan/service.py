# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""SimpleWagerGame-backed, retry-safe Fan-Tan orchestration."""

# Import deep-copy support for detached provider and lifecycle projections.
import copy
# Import cryptographic pile selection for production entropy.
import secrets

# Import the read-only player facade required by the shared coordinator.
from casino.core import players
# Import the shared clock for persisted round lifecycle timestamps.
from casino.core.clock import utc_now
# Import the shared one-shot wager and settlement coordinator.
from casino.core.simple_game import SimpleWagerGame
# Import player-scoped reads and provider-atomic state mutation.
from casino.core.state_store import load_player_game_state, update_player_game_state
# Import public conflict and validation errors for route envelopes.
from casino.errors import ConflictError, ValidationError
# Import pure validation, settlement, and state helpers from this game only.
from casino.games.fan_tan import engine
# Import the stable game identity for state and ledger evidence.
from casino.games.fan_tan.rules import GAME_ID

# Bound caller-supplied idempotency identities before persistence.
MAX_ACTION_ID_LENGTH = 128


# Coordinate Fan-Tan prepared-state compatibility with shared settlement.
class FanTanService:
    # Capture injectable dependencies so focused tests avoid filesystem and ambient entropy.
    def __init__(self, *, ledger_gateway=None, state_loader=None, state_updater=None, randbelow=None, clock=None, get_player=None):
        # Use player-scoped storage compatible with the shared authenticated resolver.
        self._state_loader = state_loader or (lambda player_id: load_player_game_state(GAME_ID, player_id, engine.default_state))
        # Retain an optional focused-test updater without hiding the production provider call from audits.
        self._state_updater = state_updater
        # Use cryptographic pile selection unless a focused test injects a deterministic offset.
        self._randbelow = randbelow or secrets.randbelow
        # Use the shared UTC clock unless a focused test pins lifecycle time.
        self._clock = clock or utc_now
        # Use the read-only player facade only for the helper's internal terminal projection.
        self._get_player = get_player or players.get_player
        # Build one shared coordinator with adapters for the frozen request, proof, response, and state shapes.
        self._game = SimpleWagerGame(game_id=GAME_ID, wager_transaction_type="FAN_TAN_WAGER_DEBIT", settlement_transaction_type="FAN_TAN_SETTLEMENT_CREDIT", entropy=self._entropy, resolve=self._resolve, validate_bet=self._validate_bet, public_bet_catalog=lambda: engine.metadata()["outcomes"], ledger_gateway=ledger_gateway, state_loader=self._load_core_state, state_updater=self._update_core_state, entropy_source=self._randbelow, clock=self._clock, get_player=self._get_player, request_id_resolver=self._request_id, round_id_factory=self._round_id, action_key_builder=self._action_key, wager_details_builder=self._wager_details, wager_proof_reader=self._wager_proof, settlement_details_builder=self._settlement_details, public_round_builder=self._public_round, recent_round_limit=100, legacy_action_detail_key="fan_tan_action_id", lifecycle=self)

    # Validate the stable client identity required for safe action retries.
    @staticmethod
    def _action_id(value) -> str:
        # Normalize only string ids and reject empty, oversized, or control-character values.
        request_id = value.strip() if isinstance(value, str) else ""
        # Branch when the identity is unsafe to persist.
        if not request_id or len(request_id) > MAX_ACTION_ID_LENGTH or any(ord(character) < 32 for character in request_id):
            # Require one stable identity per atomic play.
            raise ValidationError("action_id must be a non-empty string of at most 128 characters")
        # Return the exact bounded normalized identity.
        return request_id

    # Read the established identity from the frozen v1 request field.
    def _request_id(self, request: dict) -> str:
        # Delegate exact compatibility validation to the game-owned rule.
        return self._action_id(request.get("action_id"))

    # Normalize one frozen Fan-Tan request for the shared coordinator.
    @staticmethod
    def _validate_bet(request: dict) -> tuple:
        # Normalize all covered residues and amounts in immutable table order.
        wagers = engine.normalize_wagers(request.get("wagers"))
        # Calculate the aggregate debit at shared two-decimal precision.
        total_wager = round(sum(wagers.values()), 2)
        # Bind conflicting retries to the exact normalized wager map.
        fingerprint = engine.wager_fingerprint(wagers)
        # Return the canonical wager, movement, and semantic identity expected by the helper.
        return wagers, total_wager, fingerprint

    # Preserve the established authenticated-player-plus-request round identity.
    @staticmethod
    def _round_id(_game_id: str, player_id: str, request_id: str) -> str:
        # Delegate to the published game-owned hash and ft_ prefix contract.
        return engine.round_id_for(player_id, request_id)

    # Preserve the historical wager and settlement action suffixes explicitly.
    @staticmethod
    def _action_key(round_id: str, action: str) -> str:
        # Join bounded server identities without exposing caller-controlled text.
        return f"{round_id}:{action}"

    # Validate one provider- or ledger-owned pile-count entropy value.
    @staticmethod
    def _require_pile_count(pile_count) -> int:
        # Reject booleans and non-integers before consulting pure game validation.
        candidate = pile_count if isinstance(pile_count, int) and not isinstance(pile_count, bool) else None
        # Reuse the pure engine's exact approved pile-count boundary.
        try:
            # Validate the count without retaining the derived residue.
            engine.residue_for_count(candidate)
        # Convert corrupted persisted proof into a retry conflict rather than redrawing.
        except (ValidationError, TypeError) as error:
            # Keep committed proof corruption outside response fabrication.
            raise ConflictError("Fan-Tan committed pile-count proof is invalid") from error
        # Return the exact validated integer for lifecycle and ledger details.
        return int(candidate)

    # Select one validated server-authoritative pile count for the helper seam.
    @staticmethod
    def _entropy(randbelow) -> int:
        # Delegate bounded uniform selection and validation to the pure engine.
        return engine.select_pile_count(randbelow)

    # Resolve one residue settlement from committed wagers and committed pile count.
    @staticmethod
    def _resolve(wagers: dict, pile_count: int) -> dict:
        # Reuse the pure engine so payout and residue semantics remain unchanged.
        return engine.settle(wagers, int(pile_count))

    # Build canonical and historical debit proof fields during the compatibility window.
    @staticmethod
    def _wager_details(*, request_id, fingerprint, wager, entropy, settled_at, **_context) -> dict:
        # Preserve historical readers beside canonical shared-helper recovery dimensions.
        return {"request_id": request_id, "action_id": request_id, "request_fingerprint": fingerprint, "wager": copy.deepcopy(wager), "wagers": copy.deepcopy(wager), "entropy": int(entropy), "pile_count": int(entropy), "settled_at": settled_at}

    # Decode either canonical shared proof or a pre-migration debit event.
    @staticmethod
    def _wager_proof(*, details, event, lifecycle_context, **_context) -> dict:
        # Prefer the canonical wager and fall back to historical plural naming.
        wager = details.get("wager", details.get("wagers"))
        # Prefer canonical entropy and recover historical committed pile count when necessary.
        entropy = details.get("entropy") if details.get("entropy") is not None else details.get("pile_count")
        # Reuse persisted preparation time before falling back to immutable event timing.
        settled_at = details.get("settled_at") or event.get("ts") or (lifecycle_context or {}).get("settled_at")
        # Return only deterministic inputs consumed by the shared coordinator.
        return {"wager": copy.deepcopy(wager), "entropy": FanTanService._require_pile_count(entropy), "settled_at": settled_at}

    # Build canonical and historical settlement evidence without changing meaning.
    @staticmethod
    def _settlement_details(*, request_id, fingerprint, entropy, total_return, settlement, **_context) -> dict:
        # Preserve old Fan-Tan audit fields beside shared proof dimensions.
        return {"request_id": request_id, "action_id": request_id, "request_fingerprint": fingerprint, "entropy": int(entropy), "pile_count": int(entropy), "total_return": total_return, "residue": settlement["residue"], "settlements": copy.deepcopy(settlement["settlements"])}

    # Preserve the frozen terminal round shape over the shared result.
    @staticmethod
    def _public_round(*, lifecycle_context, **_context) -> dict:
        # Require one provider-owned terminal recovery record before response publication.
        round_state = (lifecycle_context or {}).get("round_state")
        # Reject an incomplete lifecycle rather than fabricating a settled response.
        if not isinstance(round_state, dict) or round_state.get("phase") != "settled":
            # Surface a programmer-facing integration error outside the public contract.
            raise TypeError("Fan-Tan lifecycle did not produce a terminal round")
        # Return only the established sanitized public round fields.
        return {"round_id": round_state["round_id"], "action_id": round_state["action_id"], "request_fingerprint": round_state["request_fingerprint"], "player_id": round_state["player_id"], "status": "settled", "wagers": copy.deepcopy(round_state["wagers"]), "settled_at": round_state["settled_at"], "pile_count": round_state["pile_count"], "residue": round_state["residue"], "net_odds": round_state["net_odds"], "counting_steps": copy.deepcopy(round_state["counting_steps"]), "total_wager": round_state["total_wager"], "total_return": round_state["total_return"], "net": round_state["net"], "settlements": copy.deepcopy(round_state["settlements"])}

    # Load one detached provider document and normalize malformed legacy state safely.
    def _load_raw_state(self, player_id: str) -> dict:
        # Read one authenticated player's selected-provider document.
        state = self._state_loader(player_id)
        # Preserve a structured document or replace malformed bytes with a safe default.
        return copy.deepcopy(state) if isinstance(state, dict) else engine.default_state()

    # Execute one provider-current raw-state mutation through production or a focused seam.
    def _update_raw_state(self, player_id: str, mutator) -> dict:
        # Keep the production atomic function syntactically visible to governance discovery.
        return update_player_game_state(GAME_ID, player_id, mutator, engine.default_state) if self._state_updater is None else self._state_updater(GAME_ID, player_id, mutator, engine.default_state)

    # Locate one request in private active state or public settled history.
    @staticmethod
    def _round_for_request(state: dict, request_id: str):
        # Prefer an exact active recovery owner before terminal history.
        active = state.get("active_round")
        # Return the private active record when it owns this request.
        if isinstance(active, dict) and active.get("action_id") == request_id:
            # Preserve provider identity for callback-scoped mutation checks.
            return active
        # Scan settled history newest first for an exact retry.
        return next((row for row in reversed(state.get("recent_rounds", [])) if isinstance(row, dict) and row.get("action_id") == request_id), None)

    # Convert established state into the helper's private newest-first wrappers.
    @staticmethod
    def _to_core_state(raw_state: dict) -> dict:
        # Preserve unrelated provider-owned fields while excluding the private active slot.
        core_state = copy.deepcopy(raw_state)
        # Keep active preparation lifecycle outside settled-round replay discovery.
        core_state.pop("active_round", None)
        # Wrap terminal history newest-first because the shared helper prepends publications.
        core_state["recent_rounds"] = [{"request_id": row.get("action_id"), "request_fingerprint": row.get("request_fingerprint"), "round_id": row.get("round_id"), "total_return": row.get("total_return", 0), "public": copy.deepcopy(row)} for row in reversed(raw_state.get("recent_rounds", []))]
        # Preserve or restore the game marker expected by the helper.
        core_state.setdefault("game", GAME_ID)
        # Return detached compatibility state so mutations remain callback-scoped.
        return core_state

    # Convert helper wrappers back to direct oldest-first public history.
    @staticmethod
    def _to_raw_state(core_state: dict, active_round) -> dict:
        # Preserve every unrelated provider-owned sibling from the helper projection.
        raw_state = copy.deepcopy(core_state)
        # Restore direct terminal round rows in the established oldest-first order.
        raw_state["recent_rounds"] = [copy.deepcopy(row["public"]) for row in reversed(core_state.get("recent_rounds", []))]
        # Restore an exact provider-owned active recovery record only while one exists.
        if active_round is None:
            # Keep completed documents compatible with the historical no-active-field shape.
            raw_state.pop("active_round", None)
        else:
            # Preserve the exact active owner for crash recovery.
            raw_state["active_round"] = copy.deepcopy(active_round)
        # Return one provider-ready document without helper wrapper metadata.
        return raw_state

    # Load provider state in the representation expected by settled-round helper logic.
    def _load_core_state(self, player_id: str) -> dict:
        # Adapt one detached authenticated-player document without persisting a rewrite.
        return self._to_core_state(self._load_raw_state(player_id))

    # Publish one helper terminal round against exact provider-current game state.
    def _update_core_state(self, player_id: str, mutator) -> dict:
        # Adapt current provider state, invoke the shared merge, and archive only the owned request.
        def publish(raw_state: dict) -> dict:
            # Convert exact current terminal history into helper wrappers.
            current_core = self._to_core_state(raw_state)
            # Merge the committed terminal round while retaining concurrent distinct history.
            updated_core = mutator(current_core)
            # Read the current private recovery owner before clearing any state.
            active = raw_state.get("active_round")
            # Locate the terminal wrapper for the exact active request instead of assuming it stayed newest.
            owned_terminal = next((row for row in updated_core.get("recent_rounds", []) if isinstance(row, dict) and isinstance(active, dict) and row.get("request_id") == active.get("action_id")), None)
            # Clear only the active request whose exact terminal row is being archived.
            if active is not None and isinstance(owned_terminal, dict):
                # Reject divergent state and ledger-derived identities before archival.
                if active.get("round_id") != owned_terminal.get("round_id") or active.get("request_fingerprint") != owned_terminal.get("request_fingerprint"):
                    # Preserve active recovery rather than concealing corruption.
                    raise ConflictError("Fan-Tan committed round conflicts with active recovery state")
                # Require terminal lifecycle proof before releasing the recovery slot.
                if active.get("phase") != "settled":
                    # Keep an incomplete action visible for exact retry recovery.
                    raise ConflictError("Fan-Tan active round is not ready for archival")
                # Release only this exact completed request.
                active = None
            # Reject a publication that would bypass another request's active recovery slot.
            elif active is not None and updated_core.get("recent_rounds") != current_core.get("recent_rounds"):
                # Keep the distinct active request authoritative until it is recovered.
                raise ConflictError("Resume the active Fan-Tan round before archiving another")
            # Restore direct public rows and the verified active slot for provider persistence.
            return self._to_raw_state(updated_core, active)

        # Commit through the provider's cross-process atomic callback boundary.
        authoritative = self._update_raw_state(player_id, publish)
        # Return exact committed authority in the helper's private representation.
        return self._to_core_state(authoritative)

    # Locate and update one exact active request without replacing sibling provider fields.
    def _transition_active(self, player_id: str, request_id: str, round_id: str, fingerprint: str, transition) -> dict:
        # Apply one request-owned lifecycle transition against provider-current state.
        def publish(current: dict) -> dict:
            # Locate this request in the active slot or terminal history.
            existing = self._round_for_request(current, request_id)
            # Reject missing recovery state rather than reconstructing private fields.
            if existing is None:
                # Fail closed because committed movement must remain tied to durable request state.
                raise ConflictError("Fan-Tan active recovery state is missing")
            # Reject semantic or round identity divergence before mutation.
            if existing.get("request_fingerprint") != fingerprint or existing.get("round_id") != round_id:
                # Prevent one request identity from adopting another request's proof.
                raise ConflictError("Fan-Tan active recovery state conflicts with committed proof")
            # Preserve an already archived terminal winner without rewriting it.
            if current.get("active_round") is not existing:
                # Return the complete provider document unchanged.
                return current
            # Apply the bounded transition only to the exact active object.
            transition(existing)
            # Return the complete provider document with siblings intact.
            return current

        # Commit the transition and retain provider-returned authority.
        authoritative = self._update_raw_state(player_id, publish)
        # Re-read the exact request from active or terminal authority.
        round_state = self._round_for_request(authoritative, request_id)
        # Reject an updater that returned no matching lifecycle record.
        if round_state is None:
            # Fail closed before later settlement or publication stages.
            raise ConflictError("Fan-Tan lifecycle transition is missing")
        # Return a detached authoritative record for later adapters.
        return copy.deepcopy(round_state)

    # Persist or recover private pile count before any aggregate wager movement.
    def prepare(self, *, player_id, request_id, round_id, fingerprint, wager, **_context) -> dict:
        # Track whether provider state already owned this exact active request.
        replayed = False

        # Publish one new preparation or reuse exact provider-current recovery state.
        def publish(current: dict) -> dict:
            # Share replay classification with the returned lifecycle context.
            nonlocal replayed
            # Locate any active or terminal state for this request identity.
            existing = self._round_for_request(current, request_id)
            # Reuse only exact semantic and round identity.
            if existing is not None:
                # Reject changed wagers or a divergent round before ledger access.
                if existing.get("request_fingerprint") != fingerprint or existing.get("round_id") != round_id:
                    # Preserve the provider winner and fail this caller closed.
                    raise ConflictError("Fan-Tan action_id was already used with different wagers")
                # Mark preparation as recovered rather than newly generated.
                replayed = True
                # Preserve exact provider bytes for active or terminal replay.
                return current
            # Prevent a new request from bypassing another interrupted settlement.
            if current.get("active_round") is not None:
                # Require recovery of the committed active request first.
                raise ConflictError("Resume the active Fan-Tan round before starting another")
            # Draw one tentative roll only after provider authority proves this request is new.
            pile_count = self._require_pile_count(engine.select_pile_count(self._randbelow))
            # Capture one stable lifecycle start time beside newly prepared private pile count.
            created_at = self._clock()
            # Persist the complete private preparation before ledger movement.
            current["active_round"] = {"round_id": round_id, "action_id": request_id, "player_id": player_id, "request_fingerprint": fingerprint, "wagers": copy.deepcopy(wager), "pile_count": pile_count, "phase": "prepared", "wager_status": "pending", "settlement_status": "not_ready", "created_at": created_at}
            # Preserve unrelated provider-owned fields in the same document.
            return current

        # Commit or recover one provider-current preparation.
        authoritative = self._update_raw_state(player_id, publish)
        # Read the exact active or terminal request returned by provider authority.
        round_state = self._round_for_request(authoritative, request_id)
        # Reject an updater that lost the prepared request before token movement.
        if round_state is None:
            # Fail closed instead of drawing replacement pile count.
            raise ConflictError("Fan-Tan prepared state is missing")
        # Return private entropy and timing only to the shared coordinator.
        return {"entropy": self._require_pile_count(round_state.get("pile_count")), "settled_at": round_state.get("created_at") or round_state.get("settled_at"), "replayed": replayed, "round_state": copy.deepcopy(round_state)}

    # Clear only a genuinely uncommitted preparation after wager failure.
    def wager_failed(self, *, player_id, request_id, fingerprint, lifecycle_context, committed_event, error, **_context) -> None:
        # Detect a newly prepared semantic conflict with an older durable ledger request.
        new_request_conflict = not bool((lifecycle_context or {}).get("replayed")) and isinstance(error, ConflictError)
        # Retain prepared state when immutable proof may require response recovery.
        if committed_event is not None and not new_request_conflict:
            # Leave the exact request available for retry.
            return

        # Clear only this request's unchanged pre-wager preparation.
        def publish(current: dict) -> dict:
            # Read the current provider-owned recovery slot.
            active = current.get("active_round")
            # Preserve another request or a lifecycle phase already advanced by a winner.
            if not isinstance(active, dict) or active.get("action_id") != request_id or active.get("request_fingerprint") != fingerprint or active.get("phase") != "prepared" or active.get("wager_status") != "pending":
                # Return provider authority unchanged.
                return current
            # Release only the safe-to-edit uncommitted proposal.
            current.pop("active_round", None)
            # Preserve every unrelated sibling and terminal history row.
            return current

        # Persist request-owned cleanup before surfacing the original wager failure.
        self._update_raw_state(player_id, publish)

    # Publish committed wager proof before deterministic settlement intent.
    def wager_committed(self, *, player_id, request_id, round_id, fingerprint, entropy, settled_at, wager_event, lifecycle_context, **_context) -> None:
        # Define the exact committed-wager marker transition.
        def transition(active: dict) -> None:
            # Replace tentative pile count with immutable ledger proof.
            active["pile_count"] = self._require_pile_count(entropy)
            # Replace tentative timing with the immutable debit proof timestamp.
            active["settled_at"] = settled_at
            # Mark the aggregate wager complete only after ledger proof exists.
            active["wager_status"] = "complete"
            # Store the immutable debit event id for API evidence.
            active["wager_ledger_id"] = wager_event.get("ledger_id")
            # Mark result calculation as the next recovery phase.
            active["phase"] = "settling"

        # Commit the provider-current transition and update shared lifecycle context.
        lifecycle_context["round_state"] = self._transition_active(player_id, request_id, round_id, fingerprint, transition)

    # Publish deterministic result intent before any returned-credit movement.
    def settlement_resolved(self, *, player_id, request_id, round_id, fingerprint, settlement, lifecycle_context, **_context) -> None:
        # Define the exact known-result transition.
        def transition(active: dict) -> None:
            # Merge only deterministic engine result fields into the active record.
            active.update(copy.deepcopy(settlement))
            # Mark positive credits pending and zero returns complete.
            active["settlement_status"] = "pending" if settlement["total_return"] > 0 else "complete"

        # Commit result intent and carry provider authority into later stages.
        lifecycle_context["round_state"] = self._transition_active(player_id, request_id, round_id, fingerprint, transition)

    # Publish immutable returned-credit proof after a positive movement.
    def settlement_committed(self, *, player_id, request_id, round_id, fingerprint, settlement_event, lifecycle_context, **_context) -> None:
        # Define the exact committed-settlement marker transition.
        def transition(active: dict) -> None:
            # Mark returned-credit settlement complete only after proof exists.
            active["settlement_status"] = "complete"
            # Store the immutable credit event id for API evidence.
            active["settlement_ledger_id"] = settlement_event.get("ledger_id")

        # Commit credit proof and carry provider authority into terminal publication.
        lifecycle_context["round_state"] = self._transition_active(player_id, request_id, round_id, fingerprint, transition)

    # Freeze one provider-stable terminal marker before shared history publication.
    def finalize(self, *, player_id, request_id, round_id, fingerprint, lifecycle_context, **_context) -> dict:
        # Define an idempotent terminal lifecycle transition.
        def transition(active: dict) -> None:
            # Mark the public lifecycle complete after every required movement.
            active["phase"] = "settled"
            # Preserve the historical settled marker in the final public round.
            active["status"] = "settled"
            # Preserve the first provider-owned request timestamp across retries.
            active.setdefault("settled_at", active.get("created_at"))

        # Commit terminal fields before constructing one identical public round.
        lifecycle_context["round_state"] = self._transition_active(player_id, request_id, round_id, fingerprint, transition)
        # Return the mutated bounded context for the helper's public-round builder.
        return lifecycle_context

    # Return current isolated state and immutable rules metadata.
    def state(self, player_id: str) -> dict:
        # Load the exact current selected-provider document for this authenticated player.
        current = self._load_raw_state(player_id)
        # Preserve the frozen game, nested state, rules, outcomes, and direct history shape.
        return {"game": GAME_ID, "state": {"recent_rounds": copy.deepcopy(current.get("recent_rounds", []))}, **engine.metadata()}

    # Execute or replay one complete counted-pile round through the shared helper.
    def play(self, player_id: str, request: dict) -> dict:
        # Require an object payload before the shared resolver reads request fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before state, entropy, or ledger access.
            raise ValidationError("Fan-Tan play body must be an object")
        # Execute preparation, movements, deterministic settlement, and archival centrally.
        result = self._game.play(player_id, request)
        # Preserve the exact historical action response without helper-owned state or player fields.
        return {"round": result["round"], "replayed": result["replayed"], "ledger": {"wager": result["ledger"]["wager"], "settlement": result["ledger"]["settlement"]}}
