# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""SimpleWagerGame-backed, reload-safe Sic Bo orchestration for issue #88."""

# Import deep-copy support for detached provider and lifecycle projections.
import copy
# Import conservative action-id validation for persisted retry identities.
import re
# Import cryptographic bounded integers for production dice entropy.
import secrets

# Import the read-only players facade without a game-owned ledger mutation boundary.
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
from casino.games.sic_bo import engine
# Import the stable game identity for every ledger event.
from casino.games.sic_bo.rules import GAME_ID

# Restrict client action identities to bounded log-safe characters.
ACTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


# Coordinate Sic Bo prepared-state compatibility with shared exactly-once settlement.
class SicBoService:
    # Capture injectable dependencies so focused tests avoid filesystem and ambient entropy.
    def __init__(self, *, ledger_gateway=None, state_loader=None, state_updater=None, get_player=None, randbelow=None, clock=None):
        # Use player-scoped storage compatible with the shared authenticated resolver.
        self._state_loader = state_loader or (lambda player_id: load_player_game_state(GAME_ID, player_id, engine.default_state))
        # Retain an optional focused-test updater without hiding the production provider call from audits.
        self._state_updater = state_updater
        # Use the read-only player facade for current wallet snapshots.
        self._get_player = get_player or players.get_player
        # Use cryptographic bounded integers unless a focused test injects deterministic dice.
        self._randbelow = randbelow or secrets.randbelow
        # Use the shared UTC clock unless a focused test pins lifecycle time.
        self._clock = clock or utc_now
        # Build one shared coordinator with adapters for Sic Bo's frozen action, proof, and state shapes.
        self._game = SimpleWagerGame(game_id=GAME_ID, wager_transaction_type="SIC_BO_WAGER_DEBIT", settlement_transaction_type="SIC_BO_PAYOUT_CREDIT", entropy=self._entropy, resolve=self._resolve, validate_bet=self._validate_bet, public_bet_catalog=engine.public_bets, ledger_gateway=ledger_gateway, state_loader=self._load_core_state, state_updater=self._update_core_state, entropy_source=self._randbelow, clock=self._clock, get_player=self._get_player, request_id_resolver=self._request_id, round_id_factory=self._round_id, action_key_builder=self._action_key, wager_details_builder=self._wager_details, wager_proof_reader=self._wager_proof, settlement_details_builder=self._settlement_details, public_round_builder=self._public_round, recent_round_limit=engine.RECENT_ROUND_LIMIT, legacy_action_detail_key="sic_bo_action_id", lifecycle=self)

    # Validate the stable identity required for safe action retries.
    @staticmethod
    def _action_id(value) -> str:
        # Require one bounded URL-safe string without coercing caller values.
        if not isinstance(value, str) or not ACTION_ID_PATTERN.fullmatch(value):
            # Reject malformed identities before state, entropy, or ledger access.
            raise ValidationError("action_id must be 1-128 URL-safe characters")
        # Return the original case-sensitive action identity.
        return value

    # Read the established action identity from the frozen v1 request field.
    def _request_id(self, request: dict) -> str:
        # Delegate exact pattern validation to the game-owned compatibility rule.
        return self._action_id(request.get("action_id"))

    # Normalize a frozen Sic Bo request for the shared settlement coordinator.
    @staticmethod
    def _validate_bet(request: dict) -> tuple:
        # Match the closed request schema while retaining the v1 compatibility player field.
        unexpected_fields = set(request) - {"action_id", "wagers", "player_id"}
        # Reject misspelled or speculative fields instead of silently discarding them.
        if unexpected_fields:
            # Keep the error deterministic without echoing arbitrary caller-controlled values.
            raise ValidationError("Sic Bo round body contains unsupported fields")
        # Normalize all positions and amounts into canonical board order.
        wagers = engine.normalize_wagers(request.get("wagers"))
        # Calculate the aggregate debit at the shared ledger's two-decimal precision.
        total_wager = round(sum(wagers.values()), 2)
        # Bind conflicting retries to the exact normalized wager map.
        fingerprint = engine.wager_fingerprint(wagers)
        # Return the canonical wager, movement, and semantic identity expected by the helper.
        return wagers, total_wager, fingerprint

    # Preserve Sic Bo's established authenticated-player-plus-action round identity.
    @staticmethod
    def _round_id(_game_id: str, player_id: str, request_id: str) -> str:
        # Delegate to the published game-owned hash and prefix contract.
        return engine.round_id_for(player_id, request_id)

    # Preserve Sic Bo's historical payout suffix beside the shared settlement vocabulary.
    @staticmethod
    def _action_key(round_id: str, action: str) -> str:
        # Translate only the helper's settlement role to the frozen payout action key.
        suffix = "payout" if action == "settlement" else action
        # Join bounded server identities without exposing caller-controlled action text.
        return f"{round_id}:{suffix}"

    # Roll exactly three validated server-authoritative dice for the default helper seam.
    @staticmethod
    def _entropy(randbelow) -> list[int]:
        # Delegate bounded entropy validation and one-based face conversion to the pure engine.
        return engine.roll_dice(randbelow)

    # Resolve one Sic Bo settlement from committed wagers and committed dice.
    @staticmethod
    def _resolve(wagers: dict, dice: list[int]) -> dict:
        # Reuse the pure 50-position engine so payout semantics remain unchanged.
        return engine.settle(wagers, dice)

    # Build canonical and historical debit proof fields during the compatibility window.
    @staticmethod
    def _wager_details(*, request_id, fingerprint, wager, entropy, settled_at, **_context) -> dict:
        # Preserve historical readers while adding canonical shared-helper recovery dimensions.
        return {"request_id": request_id, "action_id": request_id, "request_fingerprint": fingerprint, "wager": wager, "wagers": wager, "entropy": entropy, "dice": list(entropy), "settled_at": settled_at}

    # Decode either canonical shared proof or a pre-migration Sic Bo debit event.
    @staticmethod
    def _wager_proof(*, details, event, lifecycle_context, **_context) -> dict:
        # Prefer the canonical wager and fall back to historical plural naming.
        wager = details.get("wager", details.get("wagers"))
        # Prefer canonical entropy and recover historical committed dice when necessary.
        entropy = details.get("entropy") if details.get("entropy") is not None else details.get("dice")
        # Reuse persisted preparation time before falling back to immutable event timing.
        settled_at = details.get("settled_at") or (lifecycle_context or {}).get("settled_at") or event.get("ts")
        # Return only deterministic inputs consumed by the shared coordinator.
        return {"wager": wager, "entropy": engine.require_dice(entropy), "settled_at": settled_at}

    # Build canonical and historical payout evidence without changing settlement meaning.
    @staticmethod
    def _settlement_details(*, request_id, fingerprint, entropy, total_return, settlement, **_context) -> dict:
        # Preserve old Sic Bo audit fields beside the shared proof dimensions.
        return {"request_id": request_id, "action_id": request_id, "request_fingerprint": fingerprint, "entropy": list(entropy), "dice": list(entropy), "total_return": total_return, "outcome": settlement["outcome"], "settlements": settlement["settlements"]}

    # Preserve the frozen Sic Bo terminal round shape over the shared result.
    @staticmethod
    def _public_round(*, lifecycle_context, **_context) -> dict:
        # Require one provider-owned terminal recovery record before response publication.
        round_state = (lifecycle_context or {}).get("round_state")
        # Reject an incomplete lifecycle rather than fabricating a settled response.
        if not isinstance(round_state, dict) or round_state.get("phase") != "settled":
            # Surface a programmer-facing integration error outside the public contract.
            raise TypeError("Sic Bo lifecycle did not produce a terminal round")
        # Return the established sanitized round with no shared-helper wrapper fields.
        return engine.public_round(round_state)

    # Load one detached provider document and normalize malformed legacy state safely.
    def _load_raw_state(self, player_id: str) -> dict:
        # Read one authenticated player's selected-provider document.
        state = self._state_loader(player_id)
        # Preserve a structured document or replace malformed bytes with a safe default.
        return copy.deepcopy(state) if isinstance(state, dict) else engine.default_state()

    # Execute one provider-current raw-state mutation through production or a focused seam.
    def _update_raw_state(self, player_id: str, mutator) -> dict:
        # Keep the production atomic function syntactically visible to governance discovery.
        return update_player_game_state(GAME_ID, player_id, mutator, engine.default_state) if self._state_updater is None else self._state_updater(player_id, mutator)

    # Convert established Sic Bo state into the helper's private newest-first wrappers.
    @staticmethod
    def _to_core_state(raw_state: dict) -> dict:
        # Preserve unrelated provider-owned fields while excluding the private active slot.
        core_state = copy.deepcopy(raw_state)
        # Keep active preparation lifecycle outside settled-round replay discovery.
        core_state.pop("active_round", None)
        # Wrap terminal history newest-first because the shared helper prepends publications.
        core_state["recent_rounds"] = [{"request_id": row.get("action_id"), "request_fingerprint": row.get("request_fingerprint"), "round_id": row.get("round_id"), "total_return": row.get("total_return", 0), "public": engine.public_round(row)} for row in reversed(raw_state.get("recent_rounds", []))]
        # Preserve or restore the game marker expected by the helper.
        core_state.setdefault("game", GAME_ID)
        # Return detached compatibility state so mutations remain callback-scoped.
        return core_state

    # Convert helper wrappers back to direct oldest-first Sic Bo history.
    @staticmethod
    def _to_raw_state(core_state: dict, active_round) -> dict:
        # Preserve every unrelated provider-owned sibling from the helper projection.
        raw_state = copy.deepcopy(core_state)
        # Restore direct terminal round rows in the established oldest-first order.
        raw_state["recent_rounds"] = [copy.deepcopy(row["public"]) for row in reversed(core_state.get("recent_rounds", []))]
        # Restore the exact provider-owned active recovery record or null.
        raw_state["active_round"] = copy.deepcopy(active_round)
        # Return one provider-ready document without helper wrapper metadata.
        return raw_state

    # Load provider state in the representation expected by settled-round helper logic.
    def _load_core_state(self, player_id: str) -> dict:
        # Adapt one detached authenticated-player document without persisting a rewrite.
        return self._to_core_state(self._load_raw_state(player_id))

    # Publish one helper terminal round against exact provider-current Sic Bo state.
    def _update_core_state(self, player_id: str, mutator) -> dict:
        # Adapt current provider state, invoke the shared merge, and archive only the owned action.
        def publish(raw_state: dict) -> dict:
            # Convert exact current terminal history into helper wrappers.
            current_core = self._to_core_state(raw_state)
            # Merge the committed terminal round while retaining concurrent distinct history.
            updated_core = mutator(current_core)
            # Read the current private recovery owner before clearing any state.
            active = raw_state.get("active_round")
            # Locate the terminal wrapper for the exact active action instead of assuming it stayed newest.
            owned_terminal = next((row for row in updated_core.get("recent_rounds", []) if isinstance(row, dict) and isinstance(active, dict) and row.get("request_id") == active.get("action_id")), None)
            # Clear only the active action whose exact terminal row is being archived.
            if active is not None and isinstance(owned_terminal, dict):
                # Reject divergent state and ledger-derived identities before archival.
                if active.get("round_id") != owned_terminal.get("round_id") or active.get("request_fingerprint") != owned_terminal.get("request_fingerprint"):
                    # Preserve active recovery rather than concealing corruption.
                    raise ConflictError("Sic Bo committed round conflicts with active recovery state")
                # Require terminal lifecycle proof before releasing the recovery slot.
                if active.get("phase") != "settled":
                    # Keep an incomplete action visible for exact retry recovery.
                    raise ConflictError("Sic Bo active round is not ready for archival")
                # Release only this exact completed action.
                active = None
            # Reject a publication that would bypass another action's active recovery slot.
            elif active is not None and updated_core.get("recent_rounds") != current_core.get("recent_rounds"):
                # Keep the distinct active action authoritative until it is recovered.
                raise ConflictError("Resume the active Sic Bo round before archiving another")
            # Restore direct Sic Bo rows and the verified active slot for provider persistence.
            return self._to_raw_state(updated_core, active)

        # Commit through the provider's cross-process atomic callback boundary.
        authoritative = self._update_raw_state(player_id, publish)
        # Return exact committed authority in the helper's private representation.
        return self._to_core_state(authoritative)

    # Locate and update one exact active action without replacing sibling provider fields.
    def _transition_active(self, player_id: str, request_id: str, round_id: str, fingerprint: str, transition) -> dict:
        # Apply one action-owned lifecycle transition against provider-current state.
        def publish(current: dict) -> dict:
            # Locate this action in the active slot or terminal history.
            existing = engine.round_for_action(current, request_id)
            # Reject missing recovery state rather than reconstructing private fields from scratch.
            if existing is None:
                # Fail closed because committed movement must remain tied to a durable action record.
                raise ConflictError("Sic Bo active recovery state is missing")
            # Reject semantic or round identity divergence before mutating lifecycle markers.
            if existing.get("request_fingerprint") != fingerprint or existing.get("round_id") != round_id:
                # Prevent one action identity from adopting another action's proof.
                raise ConflictError("Sic Bo active recovery state conflicts with committed proof")
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
        # Re-read the exact action from active or terminal authority.
        round_state = engine.round_for_action(authoritative, request_id)
        # Reject an updater that returned no matching lifecycle record.
        if round_state is None:
            # Fail closed before later settlement or publication stages.
            raise ConflictError("Sic Bo lifecycle transition is missing")
        # Return a detached authoritative record for later adapters.
        return copy.deepcopy(round_state)

    # Persist or recover private dice before any aggregate wager movement.
    def prepare(self, *, player_id, request_id, round_id, fingerprint, wager, **_context) -> dict:
        # Track whether provider state already owned this exact active action.
        replayed = False
        # Hold newly generated private values only when provider state has no winner.
        proposed = {}

        # Publish one new preparation or reuse exact provider-current recovery state.
        def publish(current: dict) -> dict:
            # Share replay classification with the returned lifecycle context.
            nonlocal replayed
            # Locate any active or terminal state for this action identity.
            existing = engine.round_for_action(current, request_id)
            # Reuse only exact semantic and round identity.
            if existing is not None:
                # Reject changed wagers or a divergent round before any ledger access.
                if existing.get("request_fingerprint") != fingerprint or existing.get("round_id") != round_id:
                    # Preserve the provider winner and fail this caller closed.
                    raise ConflictError("Sic Bo action_id was already used with different wagers")
                # Mark preparation as recovered rather than newly generated.
                replayed = True
                # Preserve exact provider bytes for active or terminal replay.
                return current
            # Prevent a new action from bypassing another interrupted settlement.
            if current.get("active_round") is not None:
                # Require recovery of the committed active action first.
                raise ConflictError("Resume the active Sic Bo round before starting another")
            # Draw one tentative triple only after provider authority proves this action is new.
            proposed["dice"] = engine.roll_dice(self._randbelow)
            # Capture one stable lifecycle start time beside newly prepared private dice.
            proposed["created_at"] = self._clock()
            # Persist the complete private preparation before ledger movement.
            current["active_round"] = {"round_id": round_id, "action_id": request_id, "player_id": player_id, "request_fingerprint": fingerprint, "wagers": copy.deepcopy(wager), "dice": proposed["dice"], "phase": "prepared", "wager_status": "pending", "payout_status": "not_ready", "created_at": proposed["created_at"]}
            # Preserve unrelated provider-owned fields in the same document.
            return current

        # Commit or recover one provider-current preparation.
        authoritative = self._update_raw_state(player_id, publish)
        # Read the exact active or terminal action returned by provider authority.
        round_state = engine.round_for_action(authoritative, request_id)
        # Reject an updater that lost the prepared action before any token movement.
        if round_state is None:
            # Fail closed instead of drawing replacement dice.
            raise ConflictError("Sic Bo prepared state is missing")
        # Return private entropy and timing only to the shared coordinator.
        return {"entropy": engine.require_dice(round_state.get("dice")), "settled_at": round_state.get("created_at"), "replayed": replayed, "round_state": copy.deepcopy(round_state)}

    # Clear only a genuinely uncommitted preparation after wager failure.
    def wager_failed(self, *, player_id, request_id, fingerprint, lifecycle_context, committed_event, error, **_context) -> None:
        # Detect a newly prepared semantic conflict with an older durable ledger action.
        new_action_conflict = not bool((lifecycle_context or {}).get("replayed")) and isinstance(error, ConflictError)
        # Retain prepared state when immutable proof may require response recovery.
        if committed_event is not None and not new_action_conflict:
            # Leave the exact action available for retry.
            return

        # Clear only this action's unchanged pre-wager preparation.
        def publish(current: dict) -> dict:
            # Read the current provider-owned recovery slot.
            active = current.get("active_round")
            # Preserve another action or a lifecycle phase already advanced by a winner.
            if not isinstance(active, dict) or active.get("action_id") != request_id or active.get("request_fingerprint") != fingerprint or active.get("phase") != "prepared" or active.get("wager_status") != "pending":
                # Return provider authority unchanged.
                return current
            # Release only the safe-to-edit uncommitted proposal.
            current["active_round"] = None
            # Preserve every unrelated sibling and terminal history row.
            return current

        # Persist action-owned cleanup before surfacing the original wager failure.
        self._update_raw_state(player_id, publish)

    # Publish committed wager proof and reveal eligibility before settlement intent.
    def wager_committed(self, *, player_id, request_id, round_id, fingerprint, entropy, wager_event, lifecycle_context, **_context) -> None:
        # Define the exact committed-wager marker transition.
        def transition(active: dict) -> None:
            # Replace any tentative dice with immutable ledger proof.
            active["dice"] = engine.require_dice(entropy)
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
            active["payout_status"] = "pending" if settlement["total_return"] > 0 else "complete"

        # Commit result intent and carry provider authority into later stages.
        lifecycle_context["round_state"] = self._transition_active(player_id, request_id, round_id, fingerprint, transition)

    # Publish immutable payout proof after a positive returned-credit movement.
    def settlement_committed(self, *, player_id, request_id, round_id, fingerprint, settlement_event, lifecycle_context, **_context) -> None:
        # Define the exact committed-payout marker transition.
        def transition(active: dict) -> None:
            # Mark returned-credit settlement complete only after immutable proof exists.
            active["payout_status"] = "complete"
            # Store the immutable payout event id for API evidence.
            active["payout_ledger_id"] = settlement_event.get("ledger_id")

        # Commit payout proof and carry provider authority into terminal publication.
        lifecycle_context["round_state"] = self._transition_active(player_id, request_id, round_id, fingerprint, transition)

    # Freeze one provider-stable terminal timestamp before shared history publication.
    def finalize(self, *, player_id, request_id, round_id, fingerprint, lifecycle_context, **_context) -> dict:
        # Define an idempotent terminal lifecycle transition.
        def transition(active: dict) -> None:
            # Mark the public lifecycle complete after every required movement.
            active["phase"] = "settled"
            # Preserve the first provider-owned completion timestamp across concurrent retries.
            active.setdefault("completed_at", self._clock())

        # Commit terminal fields before constructing one identical public round in every process.
        lifecycle_context["round_state"] = self._transition_active(player_id, request_id, round_id, fingerprint, transition)
        # Return the mutated bounded context for the helper's public-round builder.
        return lifecycle_context

    # Build the public state, rules, and read-only wallet snapshot shared by routes.
    def payload(self, player_id: str) -> dict:
        # Load the exact current selected-provider document for this authenticated player.
        current = self._load_raw_state(player_id)
        # Return game-owned public state plus immutable rule metadata and current-player data.
        return {"game": GAME_ID, "state": engine.public_state(current), "bets": engine.public_bets(), "player": self._get_player(player_id)}

    # Execute or replay one ledger-backed Sic Bo shake through the shared helper.
    def play(self, player_id: str, request: dict) -> dict:
        # Require a JSON object before the shared resolver reads request fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before any protected operation.
            raise ValidationError("Sic Bo round body must be an object")
        # Execute preparation, movements, deterministic settlement, and archival through one coordinator.
        result = self._game.play(player_id, request)
        # Convert the helper's settled wrappers into the frozen direct Sic Bo state shape.
        raw_state = self._to_raw_state(result["state"], None)
        # Preserve the established response envelope and payout ledger key.
        return {"round": result["round"], "replayed": result["replayed"], "ledger": {"wager": result["ledger"]["wager"], "payout": result["ledger"]["settlement"]}, "game": GAME_ID, "state": engine.public_state(raw_state), "bets": engine.public_bets(), "player": result["player"]}
