# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""SimpleWagerGame-backed, reload-safe Chuck-a-Luck orchestration."""

# Import deep-copy support for detached provider and lifecycle projections.
import copy
# Import bounded request validation for client retry identifiers.
import re
# Import cryptographic bounded random selection for production dice.
import secrets

# Import the shared player service without a game-owned ledger mutation boundary.
from casino.core import players
# Import the shared UTC clock for stable lifecycle timestamps.
from casino.core.clock import utc_now
# Import the shared one-shot wager and settlement coordinator.
from casino.core.simple_game import SimpleWagerGame
# Import player-scoped reads and provider-atomic state mutation.
from casino.core.state_store import load_player_game_state, update_player_game_state
# Import public conflict and validation errors for safe API boundaries.
from casino.errors import ConflictError, ValidationError
# Import only this game's pure engine and immutable rule metadata.
from casino.games.chuck_a_luck import engine, rules

# Bound request identifiers to conservative URL-safe characters and length.
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
# Name the single aggregate wager debit consistently across recovery paths.
WAGER_TRANSACTION_TYPE = "CHUCK_A_LUCK_WAGER_DEBIT"
# Name the optional stake-plus-winnings aggregate credit consistently.
SETTLEMENT_TRANSACTION_TYPE = "CHUCK_A_LUCK_SETTLEMENT_CREDIT"


# Validate the required caller-stable identity used for network retries.
def require_request_id(value) -> str:
    # Require a bounded string whose characters remain safe in logs and JSON state.
    if not isinstance(value, str) or not REQUEST_ID_PATTERN.fullmatch(value):
        # Explain the accepted retry-key boundary without echoing caller input.
        raise ValidationError("request_id must be 1-128 URL-safe characters")
    # Return the exact validated identity for stable hashing and comparisons.
    return value


# Coordinate Chuck-a-Luck prepared-state compatibility with shared settlement.
class ChuckALuckService:
    # Capture injectable dependencies so focused tests avoid filesystem and ambient entropy.
    def __init__(self, *, ledger_gateway=None, repository=None, state_loader=None, state_updater=None, randbelow=None, clock=None, get_player=None):
        # Preserve the historical repository seam while preferring explicit provider callbacks.
        if repository is not None:
            # Reject ambiguous state dependency ownership at construction.
            if state_loader is not None or state_updater is not None:
                # Keep tests and production from mixing incompatible provider seams.
                raise TypeError("repository cannot be combined with state_loader or state_updater")
            # Adapt the established repository load method to the shared callback boundary.
            state_loader = repository.load
            # Adapt the established repository update method to the shared callback boundary.
            state_updater = repository.update
        # Use player-scoped storage compatible with the authenticated-player resolver.
        self._state_loader = state_loader or (lambda player_id: load_player_game_state(rules.GAME_ID, player_id, engine.default_state))
        # Retain an optional focused-test updater without hiding the production provider call.
        self._state_updater = state_updater
        # Use the read-only player facade for current wallet snapshots.
        self._get_player = get_player or players.get_player
        # Use cryptographic uniform selection unless a focused test pins dice.
        self._randbelow = randbelow or secrets.randbelow
        # Use the shared UTC clock unless a focused test pins lifecycle time.
        self._clock = clock or utc_now
        # Build exactly one shared coordinator with frozen Chuck-a-Luck compatibility adapters.
        self._game = SimpleWagerGame(game_id=rules.GAME_ID, wager_transaction_type=WAGER_TRANSACTION_TYPE, settlement_transaction_type=SETTLEMENT_TRANSACTION_TYPE, entropy=self._entropy, resolve=self._resolve, validate_bet=self._validate_bet, public_bet_catalog=rules.bet_catalog, ledger_gateway=ledger_gateway, state_loader=self._load_core_state, state_updater=self._update_core_state, entropy_source=self._randbelow, clock=self._clock, get_player=self._get_player, request_id_resolver=self._request_id, round_id_factory=self._round_id, wager_details_builder=self._wager_details, wager_proof_reader=self._wager_proof, settlement_details_builder=self._settlement_details, public_round_builder=self._public_round, recent_round_limit=engine.RECENT_ROUND_LIMIT, legacy_action_detail_key="idempotency_key", lifecycle=self)

    # Read and validate the established request identity from the frozen v1 field.
    @staticmethod
    def _request_id(request: dict) -> str:
        # Delegate exact pattern validation to the game-owned compatibility rule.
        return require_request_id(request.get("request_id"))

    # Normalize one frozen Chuck-a-Luck request for the shared coordinator.
    @staticmethod
    def _validate_bet(request: dict) -> tuple:
        # Normalize all covered faces into canonical one-through-six order.
        wagers = engine.normalize_wagers(request.get("wagers"))
        # Calculate the aggregate debit at shared ledger precision.
        wager_total = engine.total_wager(wagers)
        # Bind conflicting retries to the exact normalized wager map.
        fingerprint = engine.wager_fingerprint(wagers)
        # Return the canonical wager, movement, and semantic identity expected by the helper.
        return wagers, wager_total, fingerprint

    # Preserve the established authenticated-player-plus-request round identity.
    @staticmethod
    def _round_id(_game_id: str, player_id: str, request_id: str) -> str:
        # Delegate to the published game-owned hash and prefix contract.
        return engine.round_id_for(player_id, request_id)

    # Roll exactly three validated server-authoritative dice.
    @staticmethod
    def _entropy(randbelow) -> list[int]:
        # Delegate bounded entropy validation and one-based face conversion to the pure engine.
        return engine.roll_dice(randbelow)

    # Resolve one settlement from committed wagers and committed dice.
    @staticmethod
    def _resolve(wagers: dict, dice: list[int]) -> dict:
        # Reuse the pure engine so the established payout profile remains unchanged.
        return engine.settle(wagers, dice)

    # Build canonical and historical debit proof fields during the compatibility window.
    @staticmethod
    def _wager_details(*, request_id, fingerprint, wager, wager_total, entropy, settled_at, **_context) -> dict:
        # Preserve old readers beside canonical shared-helper recovery dimensions.
        return {"request_id": request_id, "request_fingerprint": fingerprint, "wager": wager, "wagers": wager, "entropy": list(entropy), "dice": list(entropy), "total_wager": wager_total, "settled_at": settled_at}

    # Decode either canonical proof or a pre-migration Chuck-a-Luck debit event.
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

    # Build canonical and historical returned-credit evidence without changing meaning.
    @staticmethod
    def _settlement_details(*, request_id, fingerprint, wager, entropy, total_return, settlement, **_context) -> dict:
        # Preserve old audit fields beside the shared proof dimensions.
        return {"request_id": request_id, "request_fingerprint": fingerprint, "wagers": wager, "entropy": list(entropy), "dice": list(entropy), "total_return": total_return, "settlements": settlement["settlements"]}

    # Preserve the frozen terminal round shape over the shared settlement result.
    @staticmethod
    def _public_round(*, request_id, player_id, round_id, fingerprint, wager, settlement, settled_at, lifecycle_context, **_context) -> dict:
        # Require one provider-owned terminal recovery record before response publication.
        round_state = (lifecycle_context or {}).get("round_state")
        # Reject an incomplete lifecycle rather than fabricating a settled response.
        if not isinstance(round_state, dict) or round_state.get("phase") != "settled":
            # Surface a programmer-facing integration error outside the public contract.
            raise TypeError("Chuck-a-Luck lifecycle did not produce a terminal round")
        # Return the established direct round row without private lifecycle fields.
        return {"round_id": round_id, "request_id": request_id, "request_fingerprint": fingerprint, "player_id": player_id, "status": "settled", "wagers": copy.deepcopy(wager), **copy.deepcopy(settlement), "settled_at": settled_at}

    # Load one detached provider document and normalize malformed legacy state safely.
    def _load_raw_state(self, player_id: str) -> dict:
        # Read one authenticated player's selected-provider document.
        state = self._state_loader(player_id)
        # Preserve a structured document or replace malformed bytes with a safe default.
        return copy.deepcopy(state) if isinstance(state, dict) else engine.default_state()

    # Execute one provider-current raw-state mutation through production or a focused seam.
    def _update_raw_state(self, player_id: str, mutator) -> dict:
        # Keep the production atomic function syntactically visible to governance discovery.
        return update_player_game_state(rules.GAME_ID, player_id, mutator, engine.default_state) if self._state_updater is None else self._state_updater(player_id, mutator)

    # Locate one request in active recovery or direct terminal history.
    @staticmethod
    def _round_for_request(state: dict, request_id: str):
        # Prefer the active recovery slot because it may require ledger completion.
        active = state.get("active_round")
        # Return the active object itself so provider callbacks can update it safely.
        if isinstance(active, dict) and active.get("request_id") == request_id:
            # Preserve object identity for exact lifecycle transitions.
            return active
        # Scan terminal history newest-first for ordinary request replay.
        return engine.find_round(state, request_id)

    # Convert established direct-row state into the helper's private newest-first wrappers.
    @staticmethod
    def _to_core_state(raw_state: dict) -> dict:
        # Preserve unrelated provider-owned fields while excluding the private active slot.
        core_state = copy.deepcopy(raw_state)
        # Keep active preparation outside terminal replay discovery.
        core_state.pop("active_round", None)
        # Wrap terminal history newest-first because the shared helper prepends publications.
        core_state["recent_rounds"] = [{"request_id": row.get("request_id"), "request_fingerprint": row.get("request_fingerprint"), "round_id": row.get("round_id"), "total_return": row.get("total_return", 0), "public": engine.public_round(row)} for row in reversed(raw_state.get("recent_rounds", []))]
        # Preserve or restore the game marker expected by the helper.
        core_state.setdefault("game", rules.GAME_ID)
        # Return detached compatibility state so mutations remain callback-scoped.
        return core_state

    # Convert helper wrappers back to direct oldest-first Chuck-a-Luck history.
    @staticmethod
    def _to_raw_state(core_state: dict, active_round) -> dict:
        # Preserve every unrelated provider-owned sibling from the helper projection.
        raw_state = copy.deepcopy(core_state)
        # Restore direct terminal rows in the established oldest-first order.
        raw_state["recent_rounds"] = [copy.deepcopy(row["public"]) for row in reversed(core_state.get("recent_rounds", []))]
        # Retain private recovery only while an action owns the slot.
        if active_round is not None:
            # Store a detached action record for provider persistence.
            raw_state["active_round"] = copy.deepcopy(active_round)
        else:
            # Preserve the historical terminal state shape without a null private field.
            raw_state.pop("active_round", None)
        # Return one provider-ready document without helper wrapper metadata.
        return raw_state

    # Load provider state in the representation expected by shared replay logic.
    def _load_core_state(self, player_id: str) -> dict:
        # Adapt one detached authenticated-player document without persisting a rewrite.
        return self._to_core_state(self._load_raw_state(player_id))

    # Publish one helper terminal round against exact provider-current state.
    def _update_core_state(self, player_id: str, mutator) -> dict:
        # Adapt current provider state, invoke the shared merge, and archive only the owned action.
        def publish(raw_state: dict) -> dict:
            # Convert exact terminal history into helper wrappers.
            current_core = self._to_core_state(raw_state)
            # Merge the committed terminal round while retaining concurrent distinct history.
            updated_core = mutator(current_core)
            # Read the current private recovery owner before clearing any state.
            active = raw_state.get("active_round")
            # Locate the terminal wrapper for the exact active request.
            owned_terminal = next((row for row in updated_core.get("recent_rounds", []) if isinstance(row, dict) and isinstance(active, dict) and row.get("request_id") == active.get("request_id")), None)
            # Clear only the active action whose exact terminal row is being archived.
            if active is not None and isinstance(owned_terminal, dict):
                # Reject divergent state and ledger-derived identities before archival.
                if active.get("round_id") != owned_terminal.get("round_id") or active.get("request_fingerprint") != owned_terminal.get("request_fingerprint"):
                    # Preserve active recovery rather than concealing corruption.
                    raise ConflictError("Chuck-a-Luck committed round conflicts with active recovery state")
                # Require terminal lifecycle proof before releasing the recovery slot.
                if active.get("phase") != "settled":
                    # Keep an incomplete action visible for exact retry recovery.
                    raise ConflictError("Chuck-a-Luck active round is not ready for archival")
                # Release only this exact completed action.
                active = None
            # Reject a publication that would bypass another action's active recovery slot.
            elif active is not None and updated_core.get("recent_rounds") != current_core.get("recent_rounds"):
                # Keep the distinct active action authoritative until it is recovered.
                raise ConflictError("Resume the active Chuck-a-Luck round before archiving another")
            # Restore direct rows and the verified active slot for provider persistence.
            return self._to_raw_state(updated_core, active)

        # Commit through the provider's cross-process atomic callback boundary.
        authoritative = self._update_raw_state(player_id, publish)
        # Return exact committed authority in the helper's private representation.
        return self._to_core_state(authoritative)

    # Locate and update one exact active action without replacing sibling fields.
    def _transition_active(self, player_id: str, request_id: str, round_id: str, fingerprint: str, transition) -> dict:
        # Apply one action-owned lifecycle transition against provider-current state.
        def publish(current: dict) -> dict:
            # Locate this action in the active slot or terminal history.
            existing = self._round_for_request(current, request_id)
            # Reject missing recovery state rather than reconstructing private fields.
            if existing is None:
                # Fail closed because committed movement must remain tied to durable action state.
                raise ConflictError("Chuck-a-Luck active recovery state is missing")
            # Reject semantic or round identity divergence before mutation.
            if existing.get("request_fingerprint") != fingerprint or existing.get("round_id") != round_id:
                # Prevent one action identity from adopting another action's proof.
                raise ConflictError("Chuck-a-Luck active recovery state conflicts with committed proof")
            # Preserve an already archived terminal winner without rewriting it.
            if current.get("active_round") is not existing:
                # Return complete provider authority unchanged.
                return current
            # Apply the bounded transition only to the exact active object.
            transition(existing)
            # Return the complete provider document with siblings intact.
            return current

        # Commit the transition and retain provider-returned authority.
        authoritative = self._update_raw_state(player_id, publish)
        # Re-read the exact action from active or terminal authority.
        round_state = self._round_for_request(authoritative, request_id)
        # Reject an updater that returned no matching lifecycle record.
        if round_state is None:
            # Fail closed before later settlement or publication stages.
            raise ConflictError("Chuck-a-Luck lifecycle transition is missing")
        # Return a detached authoritative record for later adapters.
        return copy.deepcopy(round_state)

    # Persist or recover private dice before any aggregate wager movement.
    def prepare(self, *, player_id, request_id, round_id, fingerprint, wager, **_context) -> dict:
        # Track whether provider state already owned this exact action.
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
                    # Preserve provider authority and fail this caller closed.
                    raise ConflictError("Chuck-a-Luck request_id was already used with different wagers")
                # Mark preparation as recovered rather than newly generated.
                replayed = True
                # Preserve exact provider bytes for active or terminal replay.
                return current
            # Prevent a new action from bypassing another interrupted settlement.
            if current.get("active_round") is not None:
                # Require recovery of the committed active action first.
                raise ConflictError("Resume the active Chuck-a-Luck round before starting another")
            # Draw one tentative triple only after provider authority proves this action is new.
            dice = engine.roll_dice(self._randbelow)
            # Capture one stable lifecycle start time beside newly prepared private dice.
            created_at = self._clock()
            # Persist the complete private preparation before ledger movement.
            current["active_round"] = {"round_id": round_id, "request_id": request_id, "player_id": player_id, "request_fingerprint": fingerprint, "wagers": copy.deepcopy(wager), "dice": dice, "phase": "prepared", "wager_status": "pending", "settlement_status": "not_ready", "created_at": created_at}
            # Preserve unrelated provider-owned fields in the same document.
            return current

        # Commit or recover one provider-current preparation.
        authoritative = self._update_raw_state(player_id, publish)
        # Read the exact active or terminal action returned by provider authority.
        round_state = self._round_for_request(authoritative, request_id)
        # Reject an updater that lost the prepared action before token movement.
        if round_state is None:
            # Fail closed instead of drawing replacement dice.
            raise ConflictError("Chuck-a-Luck prepared state is missing")
        # Return private entropy and timing only to the shared coordinator.
        return {"entropy": engine.require_dice(round_state.get("dice")), "settled_at": round_state.get("created_at") or round_state.get("settled_at"), "replayed": replayed, "round_state": copy.deepcopy(round_state)}

    # Clear only a genuinely uncommitted preparation after wager failure.
    def wager_failed(self, *, player_id, request_id, fingerprint, lifecycle_context, committed_event, error, **_context) -> None:
        # Detect a newly prepared conflict with an older durable ledger action.
        new_action_conflict = not bool((lifecycle_context or {}).get("replayed")) and isinstance(error, ConflictError)
        # Retain prepared state when immutable proof may require response recovery.
        if committed_event is not None and not new_action_conflict:
            # Leave the exact action available for retry.
            return

        # Clear only this action's unchanged pre-wager preparation.
        def publish(current: dict) -> dict:
            # Read the current provider-owned recovery slot.
            active = current.get("active_round")
            # Preserve another action or a phase already advanced by a winner.
            if not isinstance(active, dict) or active.get("request_id") != request_id or active.get("request_fingerprint") != fingerprint or active.get("phase") != "prepared" or active.get("wager_status") != "pending":
                # Return provider authority unchanged.
                return current
            # Release only the safe-to-edit uncommitted proposal.
            current.pop("active_round", None)
            # Preserve every unrelated sibling and terminal history row.
            return current

        # Persist action-owned cleanup before surfacing the original wager failure.
        self._update_raw_state(player_id, publish)

    # Publish committed wager proof before deterministic settlement intent.
    def wager_committed(self, *, player_id, request_id, round_id, fingerprint, entropy, wager_event, lifecycle_context, **_context) -> None:
        # Define the exact committed-wager marker transition.
        def transition(active: dict) -> None:
            # Replace any tentative dice with immutable ledger proof.
            active["dice"] = engine.require_dice(entropy)
            # Mark the aggregate wager complete only after ledger proof exists.
            active["wager_status"] = "complete"
            # Store the immutable debit event id for recovery evidence.
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
            # Store the immutable credit event id for recovery evidence.
            active["settlement_ledger_id"] = settlement_event.get("ledger_id")

        # Commit credit proof and carry provider authority into terminal publication.
        lifecycle_context["round_state"] = self._transition_active(player_id, request_id, round_id, fingerprint, transition)

    # Freeze one provider-stable terminal marker before shared history publication.
    def finalize(self, *, player_id, request_id, round_id, fingerprint, lifecycle_context, **_context) -> dict:
        # Define an idempotent terminal lifecycle transition.
        def transition(active: dict) -> None:
            # Mark the public lifecycle complete after every required movement.
            active["phase"] = "settled"
            # Preserve the original prepared time as the frozen public settled time.
            active.setdefault("settled_at", active.get("created_at"))

        # Commit terminal fields before constructing one identical public round.
        lifecycle_context["round_state"] = self._transition_active(player_id, request_id, round_id, fingerprint, transition)
        # Return the mutated bounded context for the helper's public-round builder.
        return lifecycle_context

    # Build the shared state, rules, and read-only wallet payload.
    def payload(self, player_id: str) -> dict:
        # Load the exact current selected-provider document for this player.
        current = self._load_raw_state(player_id)
        # Return the frozen game state, wallet snapshot, and immutable bet metadata.
        return {"game": rules.GAME_ID, "state": engine.public_state(current), "player": self._get_player(player_id), "bet_catalog": rules.bet_catalog()}

    # Return the current authenticated player's reload-safe game payload.
    def state(self, player_id: str) -> dict:
        # Reuse the common payload builder without touching ledger or entropy.
        return self.payload(player_id)

    # Execute or replay one complete ledger-backed roll through the shared helper.
    def roll(self, player_id: str, request: dict) -> dict:
        # Require an object payload before the shared resolver reads action fields.
        if not isinstance(request, dict):
            # Reject malformed calls before state, entropy, or ledger access.
            raise ValidationError("Chuck-a-Luck roll body must be an object")
        # Execute preparation, movements, deterministic settlement, and archival centrally.
        result = self._game.play(player_id, request)
        # Convert helper wrappers into the frozen direct oldest-first state shape.
        raw_state = self._to_raw_state(result["state"], None)
        # Preserve the established response envelope and ledger keys exactly.
        return {"round": result["round"], "replayed": result["replayed"], "ledger": result["ledger"], "game": rules.GAME_ID, "state": engine.public_state(raw_state), "player": result["player"], "bet_catalog": rules.bet_catalog()}
