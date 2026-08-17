# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""SimpleWagerGame-backed, reload-safe Dragon Tiger orchestration."""

# Import deep-copy support for detached shoe, proof, and provider projections.
import copy
# Import conservative action-id validation for persisted retry identities.
import re

# Import the read-only players facade without a game-owned money boundary.
from casino.core import players
# Import the shared clock for persisted round lifecycle timestamps.
from casino.core.clock import utc_now
# Import the shared one-shot wager and settlement coordinator.
from casino.core.simple_game import SimpleWagerGame
# Import player-scoped reads and provider-atomic state mutation.
from casino.core.state_store import load_player_game_state, update_player_game_state
# Import public conflict and validation errors for frozen route envelopes.
from casino.errors import ConflictError, ValidationError
# Import only this game's pure shoe and settlement engine.
from casino.games.dragon_tiger import engine

# Require eight to 128 safe action-ID characters exactly as frozen v1 documents.
ACTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
# Name the private shoe fields restored after a definitively uncommitted wager.
_SHOE_STATE_KEYS = ("shoe", "shoe_number", "burned_cards")


# Validate one required public retry identity.
def require_action_id(value) -> str:
    # Accept only an exact contract string without trimming caller data.
    action_id = value if isinstance(value, str) else ""
    # Reject missing, short, oversized, or unsafe values.
    if not ACTION_ID_PATTERN.fullmatch(action_id):
        # Explain the contract without echoing caller data.
        raise ValidationError("Dragon Tiger action_id must be 8-128 letters, numbers, dots, colons, underscores, or hyphens")
    # Return the validated identity unchanged.
    return action_id


# Persist player-scoped game documents through the shared provider abstraction.
class StateRepository:
    # Load one authenticated player's document.
    def load(self, player_id: str) -> dict:
        # Delegate JSON/MySQL selection and schema metadata to shared state storage.
        return load_player_game_state(engine.GAME_ID, player_id, engine.default_state)

    # Apply one transition while the provider owns its cross-process boundary.
    def update(self, player_id: str, mutator) -> dict:
        # Delegate current-state loading, rollback, and publication atomically.
        return update_player_game_state(engine.GAME_ID, player_id, mutator, engine.default_state)


# Coordinate prepared shoe state with shared exactly-once settlement.
class DragonTigerService:
    # Capture injectable dependencies so focused tests avoid files and ambient shuffles.
    def __init__(self, *, repository=None, ledger_gateway=None, player_reader=None, shoe_factory=None, clock=None):
        # Use shared persistent state unless a test supplies memory storage.
        self.repository = repository or StateRepository()
        # Use the shared player reader unless a focused test supplies a wallet fixture.
        self.player_reader = player_reader or players.get_player
        # Use secure production shuffle unless a test supplies a complete deterministic shoe.
        self.shoe_factory = shoe_factory or engine.standard_shoe
        # Use the shared UTC clock unless a focused test pins lifecycle time.
        self.clock = clock or utc_now
        # Build one shared coordinator with adapters for frozen request, proof, state, and response shapes.
        self._game = SimpleWagerGame(game_id=engine.GAME_ID, wager_transaction_type="DRAGON_TIGER_WAGER_DEBIT", settlement_transaction_type="DRAGON_TIGER_SETTLEMENT_CREDIT", entropy=self._unused_entropy, resolve=self._resolve, validate_bet=self._validate_bet, public_bet_catalog=lambda: engine.rules_payload()["bets"], ledger_gateway=ledger_gateway, state_loader=self._load_core_state, state_updater=self._update_core_state, entropy_source=lambda _span: 0, clock=self.clock, get_player=self.player_reader, request_id_resolver=self._request_id, round_id_factory=self._round_id, action_key_builder=self._action_key, wager_details_builder=self._wager_details, wager_proof_reader=self._wager_proof, settlement_details_builder=self._settlement_details, public_round_builder=self._public_round, recent_round_limit=engine.RECENT_ROUND_LIMIT, legacy_action_detail_key="idempotency_key", lifecycle=self)

    # Keep the helper's ordinary entropy seam unreachable because preparation owns the shoe.
    @staticmethod
    def _unused_entropy(_randbelow):
        # Fail loudly if lifecycle preparation is ever bypassed.
        raise TypeError("Dragon Tiger entropy must come from prepared shoe state")

    # Read and validate the frozen action_id request field.
    @staticmethod
    def _request_id(request: dict) -> str:
        # Delegate exact identity validation to the established public helper.
        return require_action_id(request.get("action_id"))

    # Normalize one frozen Dragon Tiger request for the shared coordinator.
    @staticmethod
    def _validate_bet(request: dict) -> tuple:
        # Normalize the fixed main-bet vocabulary.
        bet = engine.normalize_bet(request.get("bet"))
        # Normalize one positive two-decimal wager.
        wager = engine.normalize_wager(request.get("wager"))
        # Bind helper proof comparison to both semantic request fields.
        normalized = {"bet": bet, "wager": wager}
        # Derive the established semantic conflict fingerprint.
        fingerprint = engine.request_fingerprint(bet, wager)
        # Return canonical request meaning, aggregate debit, and stable fingerprint.
        return normalized, wager, fingerprint

    # Preserve the established authenticated-player-plus-action round identity.
    @staticmethod
    def _round_id(_game_id: str, player_id: str, request_id: str) -> str:
        # Delegate to the published game-owned hash and dt_ prefix contract.
        return engine.round_id_for(player_id, request_id)

    # Preserve historical wager and settlement action suffixes explicitly.
    @staticmethod
    def _action_key(round_id: str, action: str) -> str:
        # Join bounded server identities without exposing caller-controlled text.
        return f"{round_id}:{action}"

    # Rebuild and validate one complete private result projection.
    @staticmethod
    def _require_prepared(prepared, *, player_id, request_id, round_id, fingerprint, fallback_created_at) -> dict:
        # Require a detached provider- or ledger-authored object.
        if not isinstance(prepared, dict):
            # Refuse missing cards before deterministic settlement.
            raise ConflictError("Dragon Tiger committed card proof is invalid")
        # Recalculate every rules-derived field through the historical proof decoder.
        canonical = engine.prepared_from_ledger(player_id=player_id, action_id=request_id, fingerprint=fingerprint, round_id=round_id, details=prepared, fallback_created_at=fallback_created_at)
        # Preserve private lifecycle metadata only after canonical result validation.
        for key in ("status", "wager_ledger", "settlement_ledger", "_include_recent", "_prior_shoe", "_shared_lifecycle"):
            # Copy only explicitly recognized private compatibility fields.
            if key in prepared:
                # Detach nested proof and rollback data from the caller.
                canonical[key] = copy.deepcopy(prepared[key])
        # Return one complete trusted preparation.
        return canonical

    # Resolve one deterministic settlement from committed request and card proof.
    @staticmethod
    def _resolve(wager: dict, prepared: dict) -> dict:
        # Recalculate winner and payout from committed cards and normalized request.
        winner = engine.winner_for(prepared.get("dragon_card"), prepared.get("tiger_card"))
        # Reject a proof whose request meaning diverges from the committed debit.
        if prepared.get("bet") != wager.get("bet") or prepared.get("wager") != wager.get("wager"):
            # Prevent one action from adopting another wager's result.
            raise ConflictError("Dragon Tiger committed wager proof conflicts with the request")
        # Calculate the frozen payout classification from pure rules.
        result = engine.settle(wager["bet"], wager["wager"], winner)
        # Return helper settlement fields plus the authoritative winner.
        return {"winner": winner, **result}

    # Build canonical and historical debit proof fields during compatibility.
    @staticmethod
    def _wager_details(*, request_id, fingerprint, wager, entropy, settled_at, **_context) -> dict:
        # Preserve the old audit fields beside canonical shared-helper dimensions.
        return {"request_id": request_id, "action_id": request_id, "request_fingerprint": fingerprint, "normalized_wager": copy.deepcopy(wager), "wager": wager["wager"], "bet": wager["bet"], "entropy": copy.deepcopy(entropy), "dragon_card": entropy["dragon_card"], "tiger_card": entropy["tiger_card"], "winner": entropy["winner"], "outcome": entropy["outcome"], "total_return": entropy["total_return"], "net": entropy["net"], "created_at": entropy.get("created_at") or settled_at, "settled_at": settled_at, "shoe_number": entropy["shoe_number"], "profile": engine.PROFILE_ID}

    # Decode canonical shared proof or a historical Dragon Tiger debit row.
    @staticmethod
    def _wager_proof(*, details, event, request_id, player_id, round_id, fingerprint, proposed_wager, lifecycle_context, **_context) -> dict:
        # Prefer a complete canonical entropy object when the new helper wrote it.
        source = details.get("entropy") if isinstance(details.get("entropy"), dict) else details
        # Prefer immutable event timing exactly as the pre-migration service did.
        settled_at = event.get("ts") or details.get("settled_at") or details.get("created_at") or (lifecycle_context or {}).get("settled_at")
        # Rebuild every result field through fixed game rules.
        prepared = DragonTigerService._require_prepared(source, player_id=player_id, request_id=request_id, round_id=round_id, fingerprint=fingerprint, fallback_created_at=settled_at)
        # Recover the canonical two-field wager when absent from historical proof.
        committed_wager = details.get("normalized_wager") or {"bet": prepared["bet"], "wager": prepared["wager"]}
        # Require proof meaning to equal the helper's proposed normalized request.
        if committed_wager != proposed_wager:
            # Reject changed historical meaning before any returned credit.
            raise ConflictError("Dragon Tiger committed wager proof is incomplete")
        # Return only deterministic inputs consumed by the shared coordinator.
        return {"wager": copy.deepcopy(committed_wager), "entropy": prepared, "settled_at": settled_at}

    # Build canonical and historical optional-credit evidence.
    @staticmethod
    def _settlement_details(*, request_id, fingerprint, wager, entropy, total_return, settlement, **_context) -> dict:
        # Preserve established audit fields beside canonical request proof.
        return {"request_id": request_id, "action_id": request_id, "request_fingerprint": fingerprint, "bet": wager["bet"], "wager": wager["wager"], "winner": settlement["winner"], "outcome": settlement["outcome"], "total_return": total_return, "entropy": copy.deepcopy(entropy)}

    # Preserve the frozen terminal round shape over shared settlement.
    @staticmethod
    def _public_round(*, lifecycle_context, **_context) -> dict:
        # Require one provider-owned terminal recovery record before response publication.
        round_state = (lifecycle_context or {}).get("round_state")
        # Reject an incomplete lifecycle rather than fabricating a settled response.
        if not isinstance(round_state, dict) or round_state.get("status") != "settled":
            # Surface a programmer-facing integration error outside the public contract.
            raise TypeError("Dragon Tiger lifecycle did not produce a terminal round")
        # Delegate exact public keys and private-field exclusion to the established engine.
        return engine.settled_round(round_state, round_state["settled_at"])

    # Load one detached provider document and normalize malformed legacy state safely.
    def _load_raw_state(self, player_id: str) -> dict:
        # Read one authenticated player's selected-provider document.
        state = self.repository.load(player_id)
        # Preserve a structured document or replace malformed bytes with a safe default.
        return copy.deepcopy(state) if isinstance(state, dict) else engine.default_state()

    # Execute one provider-current raw-state mutation through the configured repository.
    def _update_raw_state(self, player_id: str, mutator) -> dict:
        # Delegate provider serialization to the established production or focused repository.
        return self.repository.update(player_id, mutator)

    # Locate one action in private recovery state or durable terminal index.
    @staticmethod
    def _record_for_action(state: dict, request_id: str):
        # Prefer an exact private action that still owns recovery.
        active = state.get("prepared_actions", {}).get(request_id)
        # Return private state when present.
        if isinstance(active, dict):
            # Preserve provider identity for callback-scoped transitions.
            return active
        # Read the unbounded durable terminal index before bounded visible history.
        record = engine.find_action_record(state, request_id)
        # Return only the immutable public round from a terminal record.
        return record.get("round") if isinstance(record, dict) else None

    # Convert established state into helper-private newest-first wrappers.
    @staticmethod
    def _to_core_state(raw_state: dict) -> dict:
        # Preserve unrelated provider siblings while excluding private active collections.
        core_state = copy.deepcopy(raw_state)
        # Keep private preparation outside settled replay discovery.
        core_state.pop("prepared_actions", None)
        # Keep recovery order outside the shared public-history structure.
        core_state.pop("prepared_order", None)
        # Build one wrapper for every durable action so replay never depends on visible history.
        wrappers = []
        # Traverse durable actions newest-first under JSON insertion order.
        for action_id, record in reversed(list(raw_state.get("settled_actions", {}).items())):
            # Ignore malformed compatibility entries instead of fabricating public rows.
            if not isinstance(record, dict) or not isinstance(record.get("round"), dict):
                # Continue to the next durable action record.
                continue
            # Detach the exact frozen public round once.
            public = copy.deepcopy(record["round"])
            # Recalculate semantic identity from immutable public request fields.
            fingerprint = engine.request_fingerprint(public.get("bet"), public.get("wager"))
            # Publish helper-private metadata around the exact public round.
            wrappers.append({"request_id": action_id, "request_fingerprint": fingerprint, "round_id": public.get("round_id"), "total_return": public.get("total_return", 0), "public": public})
        # Expose durable wrappers to helper replay and publication logic.
        core_state["recent_rounds"] = wrappers
        # Preserve or restore the game marker expected by shared state.
        core_state.setdefault("game", engine.GAME_ID)
        # Return detached compatibility state.
        return core_state

    # Load provider state in the representation expected by helper replay logic.
    def _load_core_state(self, player_id: str) -> dict:
        # Adapt one detached player document without persisting a rewrite.
        return self._to_core_state(self._load_raw_state(player_id))

    # Publish one helper terminal round against exact provider-current game state.
    def _update_core_state(self, player_id: str, mutator) -> dict:
        # Adapt current state, invoke shared merge, and archive only its active action.
        def publish(raw_state: dict) -> dict:
            # Convert provider authority into helper wrappers.
            current_core = self._to_core_state(raw_state)
            # Merge or replay the exact committed terminal wrapper.
            updated_core = mutator(current_core)
            # Locate one newly publishable wrapper whose action is still private.
            owned = next((row for row in updated_core.get("recent_rounds", []) if isinstance(row, dict) and row.get("request_id") in raw_state.get("prepared_actions", {})), None)
            # Preserve provider bytes when replay publication made no new terminal action.
            if owned is None:
                # Reject a terminal-list change that did not own a private action.
                if updated_core.get("recent_rounds") != current_core.get("recent_rounds"):
                    # Prevent another action from being archived without lifecycle proof.
                    raise ConflictError("Dragon Tiger committed round has no owned recovery state")
                # Return exact provider authority unchanged.
                return raw_state
            # Read the exact private action selected by shared publication.
            active = raw_state["prepared_actions"][owned["request_id"]]
            # Reject divergent state and ledger-derived identities before archival.
            if active.get("round_id") != owned.get("round_id") or active.get("request_fingerprint") != owned.get("request_fingerprint"):
                # Preserve active recovery rather than conceal corruption.
                raise ConflictError("Dragon Tiger committed round conflicts with active recovery state")
            # Require terminal lifecycle proof before releasing private state.
            if active.get("status") != "settled" or active.get("settled_at") != owned.get("public", {}).get("settled_at"):
                # Keep incomplete action state visible to exact retry recovery.
                raise ConflictError("Dragon Tiger active round is not ready for archival")
            # Rebuild durable API evidence from provider-owned lifecycle proof.
            ledger = {"wager": copy.deepcopy(active.get("wager_ledger")), "settlement": copy.deepcopy(active.get("settlement_ledger"))}
            # Preserve old visible-history behavior for current versus ledger-only recovery.
            engine.record_round(raw_state, copy.deepcopy(owned["public"]), ledger, include_recent=bool(active.get("_include_recent", True)))
            # Return the provider-ready direct state shape.
            return raw_state

        # Commit through the provider's cross-process atomic callback boundary.
        authoritative = self._update_raw_state(player_id, publish)
        # Return committed authority in helper-private representation.
        return self._to_core_state(authoritative)

    # Locate and update one exact private action without replacing siblings.
    def _transition_action(self, player_id: str, request_id: str, round_id: str, fingerprint: str, transition) -> dict:
        # Apply one action-owned lifecycle transition against provider-current state.
        def publish(current: dict) -> dict:
            # Locate exact private or terminal state for this action.
            existing = self._record_for_action(current, request_id)
            # Reject missing recovery state instead of reconstructing private fields.
            if existing is None:
                # Fail closed because committed money must stay tied to durable state.
                raise ConflictError("Dragon Tiger active recovery state is missing")
            # Reject semantic or round identity divergence before mutation.
            if existing.get("round_id") != round_id or engine.request_fingerprint(existing.get("bet"), existing.get("wager")) != fingerprint:
                # Prevent one action identity from adopting another action's proof.
                raise ConflictError("Dragon Tiger active recovery state conflicts with committed proof")
            # Preserve an already archived terminal winner without rewriting it.
            if current.get("prepared_actions", {}).get(request_id) is not existing:
                # Return complete provider authority unchanged.
                return current
            # Apply the bounded transition to the exact private action only.
            transition(existing)
            # Return complete state with sibling fields intact.
            return current

        # Commit the transition and retain provider-returned authority.
        authoritative = self._update_raw_state(player_id, publish)
        # Re-read exact active or terminal state from provider authority.
        round_state = self._record_for_action(authoritative, request_id)
        # Reject an updater that returned no matching lifecycle record.
        if round_state is None:
            # Fail closed before later settlement or publication stages.
            raise ConflictError("Dragon Tiger lifecycle transition is missing")
        # Return detached authoritative state for later adapters.
        return copy.deepcopy(round_state)

    # Read one helper-owned immutable event without creating a game-local gateway.
    def _find_event(self, *, player_id, round_id, fingerprint, action) -> dict | None:
        # Delegate read-only proof lookup to the helper's public settlement-owned seam.
        return self._game.find_committed_action(player_id=player_id, round_id=round_id, request_fingerprint=fingerprint, action=action)

    # Persist or recover private dealt cards before aggregate wager movement.
    def prepare(self, *, player_id, request_id, round_id, fingerprint, wager, **_context) -> dict:
        # Read historical debit proof before dealing so state-loss recovery consumes no new card.
        committed_wager = self._find_event(player_id=player_id, round_id=round_id, fingerprint=fingerprint, action="wager")
        # Track whether provider or ledger authority already owned this exact action.
        replayed = committed_wager is not None

        # Publish one new preparation or reuse exact provider-current recovery state.
        def publish(current: dict) -> dict:
            # Share replay classification with returned lifecycle context.
            nonlocal replayed
            # Locate private or terminal state for the requested action.
            existing = self._record_for_action(current, request_id)
            # Reuse only exact semantic and round identity.
            if existing is not None:
                # Reject changed input or divergent round before money access.
                if existing.get("round_id") != round_id or engine.request_fingerprint(existing.get("bet"), existing.get("wager")) != fingerprint:
                    # Preserve provider authority and fail this caller closed.
                    raise ConflictError("Dragon Tiger action_id was already used with different round settings")
                # Mark exact provider state as replayed rather than newly dealt.
                replayed = True
                # Preserve provider bytes for active or terminal replay.
                return current
            # Prevent a new action from bypassing any interrupted prior settlement.
            if current.get("prepared_actions"):
                # Require recovery of persisted actions in creation order first.
                raise ConflictError("Resume the active Dragon Tiger round before starting another")
            # Reconstruct a historical debit without consuming current shoe state.
            if committed_wager is not None:
                # Decode exact cards and payout under fixed rules.
                prepared = engine.prepared_from_ledger(player_id=player_id, action_id=request_id, fingerprint=fingerprint, round_id=round_id, details=committed_wager.get("details") or {}, fallback_created_at=committed_wager.get("ts") or self.clock())
                # Keep historical ledger-only replay out of current visible chronology.
                prepared["_include_recent"] = False
                # Mark this recovered action as owned by shared apply-once lifecycle semantics.
                prepared["_shared_lifecycle"] = True
                # Persist the recovered action before optional credit movement.
                current.setdefault("prepared_actions", {})[request_id] = prepared
                # Preserve deterministic recovery order.
                current.setdefault("prepared_order", []).append(request_id)
                # Return provider authority with no shoe mutation.
                return current
            # Snapshot only private shoe fields before a definitively uncommitted proposal.
            prior_shoe = {key: copy.deepcopy(current.get(key, engine.default_state()[key])) for key in _SHOE_STATE_KEYS}
            # Deal and calculate one result only inside provider-current authority.
            prepared = engine.prepare_action(current, player_id=player_id, action_id=request_id, bet=wager["bet"], wager=wager["wager"], fingerprint=fingerprint, round_id=round_id, created_at=self.clock(), shoe_factory=self.shoe_factory)
            # Retain rollback material privately until the wager becomes immutable.
            prepared["_prior_shoe"] = prior_shoe
            # Mark ordinary newly dealt rounds for visible-history publication.
            prepared["_include_recent"] = True
            # Distinguish shared lifecycle intent from legacy ambiguous pre-call markers.
            prepared["_shared_lifecycle"] = True
            # Preserve unrelated provider siblings in the same document.
            return current

        # Commit or recover one provider-current preparation.
        authoritative = self._update_raw_state(player_id, publish)
        # Read exact active or terminal action returned by authority.
        round_state = self._record_for_action(authoritative, request_id)
        # Reject an updater that lost preparation before money movement.
        if round_state is None:
            # Fail closed instead of dealing replacement cards.
            raise ConflictError("Dragon Tiger prepared state is missing")
        # Fail closed on legacy ambiguous movement stages without exact proof.
        if round_state.get("status") == "wager_attempting" and committed_wager is None:
            # Preserve prior state for explicit ledger reconciliation.
            raise ConflictError("Dragon Tiger wager outcome is uncertain and requires ledger reconciliation")
        # Require historical settlement proof before resuming an ambiguous credit stage.
        if round_state.get("status") == "settlement_attempting" and not round_state.get("_shared_lifecycle") and round_state.get("total_return", 0) > 0 and self._find_event(player_id=player_id, round_id=round_id, fingerprint=fingerprint, action="settlement") is None:
            # Preserve prior state for explicit ledger reconciliation.
            raise ConflictError("Dragon Tiger settlement outcome is uncertain and requires ledger reconciliation")
        # Canonically validate cards and request meaning before returning entropy.
        prepared = self._require_prepared(round_state, player_id=player_id, request_id=request_id, round_id=round_id, fingerprint=fingerprint, fallback_created_at=round_state.get("created_at") or self.clock())
        # Return private entropy and stable timing only to shared settlement.
        return {"entropy": prepared, "settled_at": prepared["created_at"], "replayed": replayed, "round_state": copy.deepcopy(round_state)}

    # Restore only a definitively uncommitted deal after wager failure.
    def wager_failed(self, *, player_id, request_id, fingerprint, lifecycle_context, committed_event, **_context) -> None:
        # Retain preparation when immutable proof may require response recovery.
        if committed_event is not None:
            # Leave exact cards available for explicit retry.
            return

        # Remove this action and restore its prior shoe against provider authority.
        def publish(current: dict) -> dict:
            # Read the exact private action proposed by this request.
            active = current.get("prepared_actions", {}).get(request_id)
            # Preserve another action or an already advanced lifecycle phase.
            if not isinstance(active, dict) or active.get("request_fingerprint") != fingerprint or active.get("status") != "prepared":
                # Return provider authority unchanged.
                return current
            # Read the private rollback snapshot owned by this uncommitted proposal.
            prior_shoe = active.get("_prior_shoe")
            # Require complete rollback proof before editing dealt-card state.
            if not isinstance(prior_shoe, dict) or any(key not in prior_shoe for key in _SHOE_STATE_KEYS):
                # Keep corrupt preparation fail-closed for operator recovery.
                raise ConflictError("Dragon Tiger uncommitted shoe rollback proof is missing")
            # Restore only the shoe fields changed during preparation.
            for key in _SHOE_STATE_KEYS:
                # Detach nested card arrays from private proof.
                current[key] = copy.deepcopy(prior_shoe[key])
            # Remove only this exact safe-to-clear action.
            current.setdefault("prepared_actions", {}).pop(request_id, None)
            # Remove its deterministic recovery-order entry.
            current["prepared_order"] = [item for item in current.setdefault("prepared_order", []) if item != request_id]
            # Preserve all unrelated provider fields and terminal actions.
            return current

        # Persist action-owned cleanup before surfacing the original error.
        self._update_raw_state(player_id, publish)

    # Publish committed wager proof before optional returned-credit intent.
    def wager_committed(self, *, player_id, request_id, round_id, fingerprint, entropy, settled_at, wager_event, lifecycle_context, **_context) -> None:
        # Define the exact post-debit lifecycle transition.
        def transition(active: dict) -> None:
            # Validate and replace tentative fields with immutable ledger proof.
            canonical = self._require_prepared(entropy, player_id=player_id, request_id=request_id, round_id=round_id, fingerprint=fingerprint, fallback_created_at=settled_at)
            # Preserve action-owned private lifecycle flags across canonical replacement.
            include_recent = bool(active.get("_include_recent", True))
            # Replace all result fields with committed canonical evidence.
            active.clear()
            # Publish detached canonical action data.
            active.update(canonical)
            # Mark ordinary versus ledger-only visible-history behavior.
            active["_include_recent"] = include_recent
            # Retain shared apply-once intent semantics across canonical replacement.
            active["_shared_lifecycle"] = True
            # Record immutable wager evidence for durable replay responses.
            active["wager_ledger"] = copy.deepcopy(wager_event)
            # Mark the debit complete only after append-only proof exists.
            active["status"] = "wager_committed"
            # Preserve immutable wager timing for the frozen round response.
            active["settled_at"] = settled_at

        # Commit provider-current transition and update shared context.
        lifecycle_context["round_state"] = self._transition_action(player_id, request_id, round_id, fingerprint, transition)

    # Publish deterministic result intent before any positive returned credit.
    def settlement_resolved(self, *, player_id, request_id, round_id, fingerprint, settlement, lifecycle_context, **_context) -> None:
        # Define the exact known-result transition.
        def transition(active: dict) -> None:
            # Require provider cards to produce the same deterministic classification.
            if active.get("winner") != settlement.get("winner") or active.get("outcome") != settlement.get("outcome") or active.get("total_return") != settlement.get("total_return") or active.get("net") != settlement.get("net"):
                # Refuse divergent engine or state proof before credit movement.
                raise ConflictError("Dragon Tiger committed result conflicts with prepared state")
            # Retain the historical pre-credit marker only for positive returns.
            active["status"] = "settlement_attempting" if settlement["total_return"] > 0 else "wager_committed"

        # Commit result intent and carry provider authority into later stages.
        lifecycle_context["round_state"] = self._transition_action(player_id, request_id, round_id, fingerprint, transition)

    # Publish immutable returned-credit proof after a positive movement.
    def settlement_committed(self, *, player_id, request_id, round_id, fingerprint, settlement_event, lifecycle_context, **_context) -> None:
        # Define the exact committed-settlement transition.
        def transition(active: dict) -> None:
            # Store complete immutable credit evidence for durable replay.
            active["settlement_ledger"] = copy.deepcopy(settlement_event)

        # Commit credit proof and carry authority into terminal publication.
        lifecycle_context["round_state"] = self._transition_action(player_id, request_id, round_id, fingerprint, transition)

    # Freeze one provider-stable terminal marker before history publication.
    def finalize(self, *, player_id, request_id, round_id, fingerprint, settled_at, lifecycle_context, **_context) -> dict:
        # Define an idempotent terminal lifecycle transition.
        def transition(active: dict) -> None:
            # Mark the public lifecycle complete after every required movement.
            active["status"] = "settled"
            # Preserve immutable wager timing across every retry.
            active["settled_at"] = settled_at

        # Commit terminal fields before constructing one identical public round.
        lifecycle_context["round_state"] = self._transition_action(player_id, request_id, round_id, fingerprint, transition)
        # Return the mutated bounded context for public-round construction.
        return lifecycle_context

    # Recover every private action in deterministic creation order.
    def _recover_all(self, player_id: str) -> None:
        # Loop until no prepared action remains or one fail-closed boundary surfaces.
        while True:
            # Read a fresh detached provider document for recovery ordering.
            state = self._load_raw_state(player_id)
            # Resolve the next exact private action id from persisted order.
            action_id = next((item for item in state.get("prepared_order", []) if item in state.get("prepared_actions", {})), None)
            # Stop after all persisted actions are terminal or stale order entries remain only.
            if action_id is None:
                # Return without drawing entropy or touching money.
                return
            # Read the complete private request meaning for helper recovery.
            active = state["prepared_actions"][action_id]
            # Resume through the same public action coordinator.
            self._game.play(player_id, {"action_id": action_id, "bet": active.get("bet"), "wager": active.get("wager")})

    # Build exact frozen GET/POST base payload from provider authority.
    def _payload(self, player_id: str) -> dict:
        # Load one exact current document after any recovery publication.
        state = self._load_raw_state(player_id)
        # Return exact public shoe summary, history, wallet, and fixed rules.
        return {"game": engine.GAME_ID, "state": engine.public_state(state), "player": self.player_reader(player_id), "rules": engine.rules_payload()}

    # Return reload-safe state after recovering interrupted actions.
    def state(self, player_id: str) -> dict:
        # Finish actions already requested before exposing current shoe state.
        self._recover_all(player_id)
        # Return the frozen public state contract.
        return self._payload(player_id)

    # Execute or replay one single-bet Dragon Tiger round.
    def play(self, player_id: str, request: dict) -> dict:
        # Require an object before reading request fields.
        if not isinstance(request, dict):
            # Reject malformed bodies before state, shoe, or money access.
            raise ValidationError("Dragon Tiger round body must be an object")
        # Accept only documented fields plus ignored authenticated-player compatibility input.
        if any(key not in {"action_id", "bet", "wager", "player_id"} for key in request):
            # Keep undocumented inputs out of semantic retry processing.
            raise ValidationError("Dragon Tiger round body contains unsupported fields")
        # Validate the complete new request before recovering prior actions.
        self._validate_bet(request)
        # Validate the retry identity before any provider access.
        require_action_id(request.get("action_id"))
        # Finish earlier persisted actions before accepting a distinct new round.
        self._recover_all(player_id)
        # Execute preparation, movements, settlement, and archival centrally.
        result = self._game.play(player_id, request)
        # Read durable game-owned evidence retained beyond provider ledger scan horizons.
        action_record = engine.find_action_record(self._load_raw_state(player_id), request["action_id"])
        # Detach stored wager and settlement proof when the helper lookup was pruned.
        stored_ledger = copy.deepcopy((action_record or {}).get("ledger") or {})
        # Rebuild exact frozen state from provider authority rather than helper wrappers.
        payload = self._payload(player_id)
        # Preserve established response keys and direct ledger evidence exactly.
        return {**payload, "round": result["round"], "ledger": {"wager": result["ledger"]["wager"] or stored_ledger.get("wager"), "settlement": result["ledger"]["settlement"] or stored_ledger.get("settlement")}, "replayed": result["replayed"]}
