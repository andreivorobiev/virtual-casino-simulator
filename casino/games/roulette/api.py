# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
# Roulette API actions, bet persistence, spin execution, and settlement orchestration.
# Import deep-copy support for immutable prepared bet and spin recovery markers.
import copy

from casino.core.state_store import load_player_game_state, update_player_game_state
from casino.core.validation import require_amount, require_player_id
from casino.core import players, logger
# Import the one canonical game-money boundary.
from casino.core.settlement import GameSettlementGateway
from casino.core.history import append_history
from casino.games.roulette import engine, rules
from casino.games.roulette.rules import expand_call_bet
from casino.errors import ConflictError, ValidationError
# Import the descriptor allowlist so route behavior cannot drift from central coercion metadata.
from casino.core.game_rules import declared_fields

# Set GAME_ID to the value needed for the next operation.
GAME_ID = "roulette"
# Bind every Roulette movement to one storage-atomic settlement adapter.
SETTLEMENT = GameSettlementGateway(GAME_ID, "bet_id")
# Reserve one private state key for a bet mutation prepared before its ledger effect completes.
PENDING_BET_ACTION_KEY = "_roulette_pending_bet_action"
# Reserve one private state key for committed wheel entropy awaiting settlement finalization.
PENDING_SPIN_KEY = "_roulette_pending_spin"


# Define the request_player_id function used by this module.
def request_player_id(body, query) -> str:
    # Return the explicit player id while keeping legacy v1 calls on the human player.
    return require_player_id({"player_id": body.get("player_id") or query.get("player_id") or "human"})


# Define the scoreboards function used by this module.
def scoreboards(player_id: str):
    return [{"player_id": p["player_id"], "display_name": p["display_name"], "balance": p["balance"], "type": p["type"]} for p in players.list_players() if p["player_id"] == player_id or p.get("type") == "bot"]


# Define the state_payload function used by this module.
def state_payload(player_id: str, state=None, query=None):
    # Set state to the value needed for the next operation.
    state = state or load_player_game_state(GAME_ID, player_id, engine.default_state)
    # Hide private recovery markers so the frozen v1 state response remains unchanged. (ROU-073)
    public_state = {key: value for key, value in state.items() if key not in {PENDING_BET_ACTION_KEY, PENDING_SPIN_KEY}}
    # Build the player-specific response shared by legacy and compact callers. (TEST-166)
    payload = {"game": GAME_ID, "state": public_state, "player": players.get_player(player_id), "players": scoreboards(player_id), "stats": engine.stats(public_state)}
    # Preserve the frozen complete response unless the current client explicitly requests the play projection.
    if not isinstance(query, dict) or query.get("projection") != "play":
        # Retain the complete mode-specific bet catalog for every legacy caller.
        payload["catalog"] = rules.catalog(state.get("mode", "double"))
    # Return the compact or complete response without changing state, money, or settlement semantics.
    return payload


# Replace one caller snapshot with the complete authoritative provider result. (ROU-073)
def _refresh_state(state: dict, authoritative: dict) -> None:
    # Remove stale top-level fields before copying the provider-owned document.
    state.clear()
    # Preserve caller object identity for existing response and recovery code.
    state.update(authoritative)


# Locate one exact open bet without mutating the provider-owned list. (ROU-073)
def _find_bet(state: dict, bet_id: str) -> tuple[int, dict] | None:
    # Inspect the current open-round order for the requested durable identity.
    for index, bet in enumerate(engine.ensure_open_round(state).setdefault("bets", [])):
        # Return the position and bet only for the exact stable identity.
        if bet.get("bet_id") == bet_id:
            # Preserve the list position for bounded rollback and finalization.
            return index, bet
    # Report absence without inventing a bet or response.
    return None


# Build one immutable debit or refund movement from established Roulette identities. (ROU-073)
def _bet_movement(kind: str, bet: dict, *, transaction_type: str | None = None, request_fingerprint: str | None = None, details: dict | None = None) -> dict:
    # Preserve the existing purchase vocabulary supplied by each public placement route.
    if kind == "purchase":
        # Require the caller to bind exact historical transaction and fingerprint semantics.
        if not transaction_type or not request_fingerprint:
            # Reject an incomplete internal action before any state or money effect can proceed.
            raise ValueError("Roulette purchase movement is incomplete")
        # Return the unchanged wager debit identity and audit details.
        return {"signed_amount": -bet["amount"], "transaction_type": transaction_type, "round_id": bet["round_id"], "action_key": f"{bet['bet_id']}:wager", "request_fingerprint": request_fingerprint, "details": copy.deepcopy(details or {})}
    # Preserve the one established refund vocabulary for clear-one and clear-all.
    if kind == "refund":
        # Return the unchanged per-bet refund identity and dimensions.
        return {"signed_amount": bet["amount"], "transaction_type": "ROULETTE_BET_REFUND", "round_id": bet["round_id"], "action_key": f"{bet['bet_id']}:refund", "request_fingerprint": f"{bet['bet_id']}:refund:{bet['amount']}", "details": {"bet_id": bet["bet_id"]}}
    # Reject an unknown private action marker without releasing it.
    raise ValueError("Roulette prepared bet action is invalid")


# Prepare one or more wager debits against the provider-owned latest document. (ROU-073)
def prepare_bet_purchase(player_id: str, state: dict, specifications: list[dict], *, expected_mode: str | None = None, expected_template: list[dict] | None = None) -> tuple[list[dict], dict]:
    # Retain detached bets and their marker only after the provider callback selects them.
    selected = {}

    # Publish every component bet and its immutable movement in one atomic transition.
    def prepare(current: dict) -> dict:
        # Clear callback evidence defensively if a provider ever retries the mutator.
        selected.clear()
        # Refuse overlap with another wallet-affecting Roulette state transition.
        if current.get(PENDING_BET_ACTION_KEY) is not None:
            # Preserve the earlier recoverable action for explicit reconciliation.
            raise ConflictError("Roulette bet state requires settlement recovery")
        # Refuse a new wager while a committed spin owns the current round transition.
        if current.get(PENDING_SPIN_KEY) is not None:
            # Prevent a fresh bet from being attached to an unsettled wheel result.
            raise ConflictError("Roulette committed spin requires settlement recovery")
        # Reject a stale call-bet expansion rather than applying old-mode components.
        if expected_mode is not None and current.get("mode", "double") != expected_mode:
            # Require the caller to retry expansion against the provider-current wheel.
            raise ConflictError("Roulette wheel mode changed before bet placement")
        # Reject a stale rebet template rather than replaying superseded wagers.
        if expected_template is not None and current.get("last_bet_template", []) != expected_template:
            # Require the caller to reload the exact latest template.
            raise ConflictError("Roulette rebet template changed before placement")
        # Retain each newly inserted bet, original position, and exact movement.
        entries = []
        # Apply every validated route component against one latest open round.
        for specification in specifications:
            # Add the bet through the established engine validation and identity boundary.
            bet = engine.add_bet_to_state(current, player_id, specification["bet_type"], specification["amount"], specification.get("covered_numbers"), specification.get("label"), source=specification["source"])
            # Build the exact route-specific debit after the server owns bet and round identities.
            movement = _bet_movement("purchase", bet, transaction_type=specification["transaction_type"], request_fingerprint=specification["fingerprint"](bet), details=specification["details"](bet))
            # Preserve the action-owned list position for exact rollback.
            entries.append({"bet": copy.deepcopy(bet), "bet_index": len(current["open_round"]["bets"]) - 1, "movement": movement})
        # Publish one bounded private marker before the first debit can occur.
        marker = {"kind": "purchase", "entries": copy.deepcopy(entries)}
        # Store recovery evidence beside the exact prepared state effect.
        current[PENDING_BET_ACTION_KEY] = marker
        # Return detached caller evidence only after the complete marker is assembled.
        selected.update({"bets": [copy.deepcopy(entry["bet"]) for entry in entries], "marker": copy.deepcopy(marker)})
        # Return the complete latest document for provider publication.
        return current

    # Commit all prepared bets and their immutable movement descriptions atomically.
    prepared = update_player_game_state(GAME_ID, player_id, prepare, engine.default_state)
    # Adopt every sibling field preserved by the provider transition.
    _refresh_state(state, prepared)
    # Return response bets and the exact persisted recovery marker.
    return selected["bets"], selected["marker"]


# Prepare one or more wager refunds against the provider-owned latest document. (ROU-073)
def prepare_bet_refund(player_id: str, state: dict, bet_ids: list[str] | None = None) -> tuple[list[dict], dict]:
    # Retain detached removed bets and their exact pre-action positions.
    selected = {}

    # Remove only the selected bets and publish every refund intent atomically.
    def prepare(current: dict) -> dict:
        # Clear callback evidence defensively if a provider ever retries the mutator.
        selected.clear()
        # Refuse overlap with another wallet-affecting Roulette state transition.
        if current.get(PENDING_BET_ACTION_KEY) is not None:
            # Preserve the earlier recoverable action for explicit reconciliation.
            raise ConflictError("Roulette bet state requires settlement recovery")
        # Refuse refunds after one spin has committed the round's exact result.
        if current.get(PENDING_SPIN_KEY) is not None:
            # Prevent a settled wager from being credited as an open-bet refund.
            raise ConflictError("Roulette committed spin requires settlement recovery")
        # Read the latest open-round bet order once before any removal.
        current_bets = engine.ensure_open_round(current).setdefault("bets", [])
        # Snapshot original positions before progressive removals can shorten the list.
        original_positions = {bet.get("bet_id"): index for index, bet in enumerate(current_bets)}
        # Select one explicit bet or every player-owned open bet without touching siblings.
        targets = list(bet_ids) if bet_ids is not None else [bet.get("bet_id") for bet in current_bets if bet.get("player_id") == player_id]
        # Retain every removed bet, its original position, and exact refund movement.
        entries = []
        # Remove explicit identities in caller order while recording provider-current positions.
        for bet_id in targets:
            # Locate the exact bet before delegating established ownership validation.
            located = _find_bet(current, bet_id)
            # Remove the bet through the existing engine validation boundary.
            bet = engine.remove_bet_from_state(current, bet_id, player_id)
            # Preserve the original position even as earlier removals shorten the list.
            original_index = original_positions.get(bet_id, located[0] if located is not None else 0)
            # Store the exact state effect and immutable refund dimensions.
            entries.append({"bet": copy.deepcopy(bet), "bet_index": original_index, "movement": _bet_movement("refund", bet)})
        # Publish even an empty clear marker so the state transition has one terminal shape.
        marker = {"kind": "refund", "entries": copy.deepcopy(entries)}
        # Store recovery evidence before the first refund can occur.
        current[PENDING_BET_ACTION_KEY] = marker
        # Retain detached response and settlement evidence outside the callback.
        selected.update({"bets": [copy.deepcopy(entry["bet"]) for entry in entries], "marker": copy.deepcopy(marker)})
        # Return the complete latest document for atomic publication.
        return current

    # Commit exact removals and their refund intents under the shared provider boundary.
    prepared = update_player_game_state(GAME_ID, player_id, prepare, engine.default_state)
    # Adopt every sibling field from the authoritative transition.
    _refresh_state(state, prepared)
    # Return removed bets and the persisted marker in unchanged route order.
    return selected["bets"], selected["marker"]


# Reconcile one prepared bet action from immutable ledger proof. (ROU-073)
def _reconcile_bet_action(player_id: str, state: dict, marker: dict, committed: list[bool]) -> None:
    # Apply exact per-entry terminal or rollback state in one latest-document transition.
    def reconcile(current: dict) -> dict:
        # Require the exact action marker so another transition is never erased.
        if current.get(PENDING_BET_ACTION_KEY) != marker:
            # Preserve divergent state and immutable ledger evidence for operator recovery.
            raise ConflictError("Roulette bet state requires operator recovery")
        # Reconcile purchases before releasing their shared private marker.
        if marker["kind"] == "purchase":
            # Inspect every prepared purchase against its exact ledger outcome.
            for entry, movement_committed in zip(marker["entries"], committed):
                # Resolve the current action-owned bet without trusting stale positions.
                located = _find_bet(current, entry["bet"]["bet_id"])
                # Require committed debits to retain their exact visible bet.
                if movement_committed:
                    # Refuse terminal publication if the purchased bet changed or disappeared.
                    if located is None or located[1] != entry["bet"]:
                        # Keep recovery evidence for explicit repair.
                        raise ConflictError("Roulette bet state requires operator recovery")
                # Roll back only an exact uncommitted prepared bet.
                else:
                    # Reject replacement or mutation of the action-owned bet.
                    if located is None or located[1] != entry["bet"]:
                        # Preserve the provider-current document instead of guessing.
                        raise ConflictError("Roulette bet state requires operator recovery")
                    # Remove only this uncommitted purchase and leave every sibling untouched.
                    current["open_round"]["bets"].pop(located[0])
        # Reconcile removed refunds without resurrecting credited bets.
        elif marker["kind"] == "refund":
            # Restore uncommitted refunds in original order while preserving current siblings.
            for entry, movement_committed in sorted(zip(marker["entries"], committed), key=lambda pair: pair[0]["bet_index"]):
                # Resolve whether the exact removed identity already reappeared.
                located = _find_bet(current, entry["bet"]["bet_id"])
                # Require committed refunds to remain absent.
                if movement_committed:
                    # Fail closed if credited wager state was concurrently resurrected.
                    if located is not None:
                        # Preserve the conflict and its marker for operator review.
                        raise ConflictError("Roulette bet state requires operator recovery")
                # Restore only an uncommitted refund whose identity remains absent.
                else:
                    # Refuse to duplicate or overwrite a racing bet.
                    if located is not None:
                        # Preserve both sources rather than choosing one.
                        raise ConflictError("Roulette bet state requires operator recovery")
                    # Bound the original position to the latest sibling-list length.
                    target_index = min(max(int(entry["bet_index"]), 0), len(current["open_round"]["bets"]))
                    # Reinsert the exact uncredited bet without replacing siblings.
                    current["open_round"]["bets"].insert(target_index, copy.deepcopy(entry["bet"]))
        # Reject malformed private action kinds without releasing their evidence.
        else:
            # Keep unknown state intact for explicit recovery.
            raise ConflictError("Roulette bet state requires operator recovery")
        # Release only this exact action after every component is reconciled.
        current.pop(PENDING_BET_ACTION_KEY, None)
        # Return the complete reconciled latest document.
        return current

    # Publish bounded rollback or completion and refresh the caller snapshot.
    _refresh_state(state, update_player_game_state(GAME_ID, player_id, reconcile, engine.default_state))


# Apply or replay every movement in one prepared bet action. (ROU-073)
def settle_prepared_bet_action(player_id: str, state: dict, marker: dict) -> list[tuple[dict, bool]]:
    # Collect immutable ledger rows in established component order.
    events = []
    # Begin exact settlement so pre-commit failures can restore only owned state.
    try:
        # Apply every component under its existing durable action identity.
        for entry in marker["entries"]:
            # Commit or replay the debit/refund outside the retryable state callback.
            events.append(SETTLEMENT.apply_once(player_id=player_id, **copy.deepcopy(entry["movement"])))
    # Classify every component by immutable proof before changing prepared state.
    except Exception:
        # Record exact committed status for partial groups without issuing retries.
        committed = []
        # Resolve each prepared movement through the indexed proof boundary.
        for entry in marker["entries"]:
            # Copy immutable movement dimensions before proof validation.
            movement = copy.deepcopy(entry["movement"])
            # Read one exact action without proposing a second wallet mutation.
            event = SETTLEMENT.find(player_id, movement["action_key"], round_id=movement["round_id"], transaction_type=movement["transaction_type"], request_fingerprint=movement["request_fingerprint"])
            # Validate present proof against every immutable movement dimension.
            if event is not None:
                # Reject coincidental or divergent ledger rows before retaining their state effect.
                SETTLEMENT.validate_existing(event, transaction_type=movement["transaction_type"], round_id=movement["round_id"], signed_amount=movement["signed_amount"], request_fingerprint=movement["request_fingerprint"])
            # Retain whether this exact component committed.
            committed.append(event is not None)
        # Keep committed effects and roll back only definitively absent components.
        _reconcile_bet_action(player_id, state, marker, committed)
        # Re-raise the original domain or provider failure after state is safe.
        raise
    # Publish terminal state only after all wallet movements are durable.
    _reconcile_bet_action(player_id, state, marker, [True] * len(marker["entries"]))
    # Return event/replay pairs for unchanged response envelopes and tests.
    return events


# Resume one prepared debit/refund before accepting a new Roulette action. (ROU-073)
def resume_prepared_bet_action(player_id: str, state: dict) -> list[tuple[dict, bool]] | None:
    # Read the private marker from the loaded player document.
    marker = state.get(PENDING_BET_ACTION_KEY)
    # Keep ordinary requests cheap when no bet action requires recovery.
    if marker is None:
        # Report that no settlement evidence was produced.
        return None
    # Reconcile exact persisted movements without allocating new bet identities.
    return settle_prepared_bet_action(player_id, state, copy.deepcopy(marker))


# Commit one wheel result and exact per-bet outcomes before any settlement side effect. (ROU-073)
def commit_pending_spin(player_id: str, state: dict) -> dict:
    # Capture the exact pending spin selected inside the provider callback.
    selected = {}

    # Commit or reuse entropy against the latest provider-owned document.
    def commit(current: dict) -> dict:
        # Clear callback evidence defensively if a provider ever retries the mutator.
        selected.clear()
        # Refuse to spin while a wager debit or refund needs reconciliation.
        if current.get(PENDING_BET_ACTION_KEY) is not None:
            # Keep wallet-affecting action state isolated from spin ownership.
            raise ConflictError("Roulette bet state requires settlement recovery")
        # Reuse entropy already committed by a racing or interrupted request.
        pending = current.get(PENDING_SPIN_KEY)
        # Sample and price only when no exact spin commitment exists.
        if pending is None:
            # Preserve the established rebet template before closing the round.
            engine.save_template_from_round(current, player_id)
            # Capture the zero rule that prices this exact committed result.
            zero_rule = current.get("zero_rule", "normal")
            # Commit the wheel pocket and create the next open round through the engine.
            settled = engine.spin_state(current)
            # Remove the engine's terminal summary until settlement state is finalized.
            result_record = current.setdefault("last_results", []).pop()
            # Build exact settlement and carry evidence from the committed round.
            entries = []
            # Price every durable bet once against the committed pocket.
            for bet in settled.get("bets", []):
                # Calculate the established pure settlement outcome.
                result = engine.settle_bet(bet, settled["result"], zero_rule)
                # Start without a carried successor for ordinary wins and losses.
                carried = None
                # Allocate an en-prison successor under the same atomic state boundary.
                if result.get("carry"):
                    # Create the exact successor through the established engine helper.
                    carried = engine.carry_en_prison_bet(current, bet)
                    # Remove the successor until terminal publication makes the carry visible.
                    current["open_round"]["bets"].remove(carried)
                # Retain exact response and final-state evidence in durable order.
                entries.append({"bet": copy.deepcopy(bet), "settlement": copy.deepcopy(result), "carried_bet": copy.deepcopy(carried), "history_status": "pending"})
            # Publish the complete immutable spin commitment before credits or history writes.
            pending = {"round": copy.deepcopy(settled), "result_record": copy.deepcopy(result_record), "settlements": entries}
            # Store private recovery evidence without exposing an unsettled result publicly.
            current[PENDING_SPIN_KEY] = pending
        # Retain a detached commitment for settlement outside the retryable callback.
        selected["pending"] = copy.deepcopy(pending)
        # Return the complete latest document for atomic publication.
        return current

    # Publish or replay the exact spin commitment through the shared provider boundary.
    committed = update_player_game_state(GAME_ID, player_id, commit, engine.default_state)
    # Adopt every sibling field in the authoritative result.
    _refresh_state(state, committed)
    # Return the exact durable commitment selected under provider ownership.
    return selected["pending"]


# Finalize one exact committed Roulette spin and release its private marker. (ROU-073)
def finalize_pending_spin(player_id: str, state: dict, pending: dict) -> None:
    # Apply the result summary and en-prison successors exactly once.
    def finalize(current: dict) -> dict:
        # Read the commitment currently owned by the latest document.
        current_pending = current.get(PENDING_SPIN_KEY)
        # Finalize only the exact expected commitment.
        if current_pending is not None:
            # Reject divergent entropy or settlement content without clearing evidence.
            if current_pending != pending:
                # Preserve both sources for operator-led recovery.
                raise ConflictError("Roulette committed spin requires operator recovery")
            # Append the exact terminal result once.
            current.setdefault("last_results", []).append(copy.deepcopy(pending["result_record"]))
            # Reapply the engine's established bounded history ceiling.
            current["last_results"] = current["last_results"][-1000:]
            # Publish every committed en-prison successor once in the current open round.
            for entry in pending["settlements"]:
                # Skip ordinary win/loss settlements without a carry.
                if entry.get("carried_bet") is None:
                    # Continue to the next exact settlement entry.
                    continue
                # Reject a duplicate identity before appending the successor.
                if _find_bet(current, entry["carried_bet"]["bet_id"]) is not None:
                    # Preserve private evidence rather than duplicating an escrowed stake.
                    raise ConflictError("Roulette committed spin requires operator recovery")
                # Append the exact carry without generating a new identity or debit.
                current["open_round"]["bets"].append(copy.deepcopy(entry["carried_bet"]))
            # Release only this exact commitment after terminal state is complete.
            current.pop(PENDING_SPIN_KEY, None)
        # Accept a replay only when the same round already exists in terminal history.
        elif not any(item.get("round_id") == pending["round"].get("round_id") and item == pending["result_record"] for item in current.get("last_results", []) if isinstance(item, dict)):
            # Reject missing or unrelated terminal state instead of inventing completion.
            raise ConflictError("Roulette committed spin requires operator recovery")
        # Return the complete provider-current document.
        return current

    # Publish terminal state and refresh the caller snapshot.
    _refresh_state(state, update_player_game_state(GAME_ID, player_id, finalize, engine.default_state))


# Claim one zero-credit history row before an overlapping settlement can append it. (ROU-073)
def claim_noncredit_history(player_id: str, state: dict, pending: dict, bet_id: str) -> bool:
    # Retain whether this request won the exact private history claim.
    selected = {"append": False}

    # Mark one zero-credit settlement entry complete before its external append.
    def claim(current: dict) -> dict:
        # Clear callback evidence defensively if a provider ever retries the mutator.
        selected["append"] = False
        # Require the same committed round before inspecting its settlement entries.
        current_pending = current.get(PENDING_SPIN_KEY)
        # Accept an overlapping claimant after the exact result is already terminal.
        if current_pending is None:
            # Require the same immutable terminal result before declining the duplicate append.
            if any(item == pending.get("result_record") for item in current.get("last_results", []) if isinstance(item, dict)):
                # Return the already finalized latest document unchanged.
                return current
            # Preserve missing state for operator-led recovery.
            raise ConflictError("Roulette committed spin requires operator recovery")
        # Refuse a divergent commitment instead of claiming unrelated history.
        if current_pending.get("round", {}).get("round_id") != pending.get("round", {}).get("round_id"):
            # Preserve exact pending state for operator-led recovery.
            raise ConflictError("Roulette committed spin requires operator recovery")
        # Resolve the exact bet entry inside this committed round.
        entry = next((item for item in current_pending.get("settlements", []) if item.get("bet", {}).get("bet_id") == bet_id), None)
        # Reject missing or changed action identity.
        if entry is None:
            # Prevent another bet from satisfying this history action.
            raise ConflictError("Roulette committed spin requires operator recovery")
        # Win the append claim only while the private status is still pending.
        if entry.get("history_status") == "pending":
            # Mark the zero-credit row complete before any external writer can race it.
            entry["history_status"] = "complete"
            # Tell this caller alone to append the history row.
            selected["append"] = True
        # Accept an overlapping claimant only after the exact entry is already owned.
        elif entry.get("history_status") != "complete":
            # Fail closed on malformed or divergent internal state.
            raise ConflictError("Roulette committed spin requires operator recovery")
        # Return the complete latest document for provider publication.
        return current

    # Publish the claim atomically and adopt every provider-current sibling field.
    _refresh_state(state, update_player_game_state(GAME_ID, player_id, claim, engine.default_state))
    # Return whether this request owns the one zero-credit history append.
    return selected["append"]


# Settle one committed spin, finalize its exact state, and append history once. (ROU-073)
def settle_pending_spin(player_id: str, state: dict, pending: dict) -> list[dict]:
    # Collect unchanged per-bet response evidence in committed round order.
    settlements = []
    # Apply every positive payout outside retryable state callbacks.
    for entry in pending["settlements"]:
        # Read detached immutable bet and result details.
        bet = entry["bet"]
        # Preserve the pure committed settlement result.
        result = entry["settlement"]
        # Start zero-credit and carry results without a ledger row.
        credit_event = None
        # Track provider replay so racing or resumed credits cannot duplicate history.
        replayed = False
        # Credit only positive returns because the shared ledger rejects zero movements.
        if result["credit"] > 0:
            # Commit or replay the existing durable per-bet settlement identity.
            credit_event, replayed = SETTLEMENT.apply_once(player_id=bet["player_id"], signed_amount=result["credit"], transaction_type="ROULETTE_SETTLEMENT_CREDIT", round_id=pending["round"]["round_id"], action_key=f"{bet['bet_id']}:settlement", request_fingerprint=f"{bet['bet_id']}:{pending['round']['round_id']}:{result['credit']}", details={"bet_id": bet["bet_id"]})
        # Resolve the authoritative balance after any positive credit.
        balance = players.get_player(bet["player_id"])["balance"]
        # Use ledger replay for positive credits and a provider-atomic claim for zero-credit rows.
        append_result = not replayed if result["credit"] > 0 else claim_noncredit_history(player_id, state, pending, bet["bet_id"])
        # Append history only for the one request that owns this exact result row.
        if append_result:
            # Preserve the existing history shape and add only an internal action identity.
            append_history(GAME_ID, pending["round"]["round_id"], bet["player_id"], bet["type"], bet["label"], bet["amount"], result["outcome"], result["credit"], balance, {"result": pending["round"]["result"], "color": pending["round"]["result_color"], "covered_numbers": bet["covered_numbers"], "carried_bet": entry.get("carried_bet"), "history_action_key": f"{bet['bet_id']}:history"})
        # Retain the frozen response entry keys in their established order-independent shape.
        settlements.append({"bet": copy.deepcopy(bet), "settlement": copy.deepcopy(result), "ledger": credit_event, "carried_bet": copy.deepcopy(entry.get("carried_bet")), "replayed": replayed})
    # Resolve the latest commitment because zero-credit history claims update private status.
    terminal_pending = copy.deepcopy(state.get(PENDING_SPIN_KEY) or pending)
    # Publish the result and carry state only after every ledger movement is durable.
    finalize_pending_spin(player_id, state, terminal_pending)
    # Return exact settlement response evidence.
    return settlements


# Resume one committed spin before accepting any new Roulette mutation. (ROU-073)
def resume_pending_spin(player_id: str, state: dict) -> list[dict] | None:
    # Read the private commitment from the already-loaded player state.
    pending = state.get(PENDING_SPIN_KEY)
    # Keep ordinary requests cheap when no committed result needs recovery.
    if pending is None:
        # Report that no settlement response was produced.
        return None
    # Settle and finalize the exact persisted commitment without resampling entropy.
    return settle_pending_spin(player_id, state, copy.deepcopy(pending))


# Load authoritative state and reconcile every prior wallet/result commitment. (ROU-073)
def load_actionable_state(player_id: str) -> dict:
    # Load one current player document through the established provider-aware helper.
    state = load_player_game_state(GAME_ID, player_id, engine.default_state)
    # Complete an interrupted wager debit/refund before any newer action.
    resume_prepared_bet_action(player_id, state)
    # Complete an interrupted spin before mutating its replacement round.
    resume_pending_spin(player_id, state)
    # Return the now-actionable authoritative snapshot.
    return state


# Apply descriptor-owned Roulette settings against the provider-owned latest state. (ROU-073)
def update_settings(player_id: str, state: dict, body: dict) -> None:
    # Resolve the canonical settings allowlist once from the module descriptor. (SEC-014)
    fields = declared_fields(GAME_ID)

    # Apply both settings under the shared atomic document boundary.
    def apply_settings(current: dict) -> dict:
        # Validate and publish the current wheel mode when supplied.
        if "mode" in fields and "mode" in body:
            # Delegate established mode validation and open-bet conflict behavior.
            engine.set_mode(current, body["mode"])
        # Publish the descriptor-validated zero rule when supplied.
        if "zero_rule" in fields and "zero_rule" in body:
            # Retain the frozen v1 setting field exactly.
            current["zero_rule"] = body["zero_rule"]
        # Return the complete latest document for atomic publication.
        return current

    # Replace the caller snapshot with the authoritative settings transition.
    _refresh_state(state, update_player_game_state(GAME_ID, player_id, apply_settings, engine.default_state))


# Define the register function used by this module.
def register(router):
    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/games/roulette/state")
    # Define the state function used by this module.
    def state(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        return state_payload(player_id, query=query)

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/roulette/settings")
    # Define the settings function used by this module.
    def settings(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Complete any interrupted wallet or spin action before changing round rules.
        state = load_actionable_state(player_id)
        # Publish the descriptor-owned settings against provider-current state.
        update_settings(player_id, state, body)
        # Return the unchanged settings response envelope.
        return state_payload(player_id, state, query=query)

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/games/roulette/bet-catalog")
    # Define the catalog function used by this module.
    def catalog(body, query):
        # Set mode to the value needed for the next operation.
        mode = query.get("mode", "double")
        return {"catalog": rules.catalog(mode)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/roulette/bets")
    # Define the place_bet function used by this module.
    def place_bet(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set amount to the value needed for the next operation.
        amount = require_amount(body.get("amount"))
        # Complete any interrupted action before preparing a new wager.
        state = load_actionable_state(player_id)
        # Normalize covered numbers once for exact engine and fingerprint semantics.
        covered_numbers = [str(value) for value in body.get("covered_numbers", [])]
        # Define the one manual-bet component without invoking money inside state callbacks.
        specification = {"bet_type": body.get("bet_type"), "amount": amount, "covered_numbers": covered_numbers, "label": body.get("label"), "source": "manual", "transaction_type": "ROULETTE_BET_PLACED", "fingerprint": lambda bet: f"{bet['bet_id']}:{bet['type']}:{bet['covered_numbers']}:{amount}", "details": lambda bet: {"bet_id": bet["bet_id"], "covered_numbers": bet["covered_numbers"], "bet_type": bet["type"]}}
        # Publish the wager and immutable debit intent against provider-current state.
        placed, marker = prepare_bet_purchase(player_id, state, [specification])
        # Resolve the exact response bet selected inside the atomic transition.
        item = placed[0]
        # Apply or recover the immutable debit, then release its private marker.
        led, _replayed = settle_prepared_bet_action(player_id, state, marker)[0]
        # Set logger.info("roulette_bet_placed", player_id to the value needed for the next operation.
        logger.info("roulette_bet_placed", player_id=player_id, bet_id=item["bet_id"], amount=amount, bet_type=item["type"])
        return {"bet": item, "ledger": led, **state_payload(player_id, state, query=query)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/roulette/call-bet")
    # Define the call_bet function used by this module.
    def call_bet(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Set amount to the value needed for the next operation.
        amount = require_amount(body.get("amount"))
        # Set call_type to the value needed for the next operation.
        call_type = body.get("call_type")
        # Set number to the value needed for the next operation.
        number = body.get("number")
        # Complete any interrupted action before expanding a new call bet.
        state = load_actionable_state(player_id)
        # Capture the provider-loaded mode used by this exact expansion.
        expected_mode = state.get("mode", "double")
        # Set comps to the value needed for the next operation.
        comps = expand_call_bet(expected_mode, call_type, amount, number)
        if not comps:
            # Raise an error so invalid input or state is reported explicitly.
            raise ValidationError("Call bet produced no legal component bets", {"call_type": call_type})
        # Build component specifications without money side effects.
        specifications = []
        # Preserve established component ordering in state and response.
        for component in comps:
            # Bind loop values into one immutable specification for the provider callback.
            component_amount = float(component["amount"])
            # Normalize covered numbers before fingerprint construction.
            component_numbers = [str(value) for value in component["covered_numbers"]]
            # Retain exact call-bet transaction and audit vocabulary.
            specifications.append({"bet_type": component["type"], "amount": component_amount, "covered_numbers": component_numbers, "label": component.get("label"), "source": "call_bet", "transaction_type": "ROULETTE_CALL_BET_PLACED", "fingerprint": lambda bet, call_type=call_type, component_amount=component_amount: f"{bet['bet_id']}:{call_type}:{bet['covered_numbers']}:{component_amount}", "details": lambda bet, call_type=call_type: {"call_type": call_type, "bet_id": bet["bet_id"], "covered_numbers": bet["covered_numbers"]}})
        # Publish every call-bet component and debit intent in one state transition.
        placed, marker = prepare_bet_purchase(player_id, state, specifications, expected_mode=expected_mode)
        # Settle or replay every component outside the retryable callback.
        settlement_rows = settle_prepared_bet_action(player_id, state, marker)
        # Preserve the historical event-only list response shape.
        ledgers = [event for event, _replayed in settlement_rows]
        return {"placed": placed, "ledger": ledgers, **state_payload(player_id, state, query=query)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/roulette/rebet")
    # Define the rebet function used by this module.
    def rebet(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Complete any interrupted action before reading the latest template.
        state = load_actionable_state(player_id)
        # Set template to the value needed for the next operation.
        template = copy.deepcopy(state.get("last_bet_template") or [])
        if not template:
            # Raise an error so invalid input or state is reported explicitly.
            raise ValidationError("No roulette bet template is available for rebet")
        # Build exact template component specifications without mutating state yet.
        specifications = []
        # Preserve the saved template order in the new open round.
        for template_bet in template:
            # Normalize the amount once for state, ledger, and fingerprint equality.
            template_amount = float(template_bet["amount"])
            # Retain exact historical rebet movement semantics.
            specifications.append({"bet_type": template_bet["type"], "amount": template_amount, "covered_numbers": list(template_bet["covered_numbers"]), "label": template_bet.get("label"), "source": "rebet", "transaction_type": "ROULETTE_REBET_PLACED", "fingerprint": lambda bet, template_amount=template_amount: f"{bet['bet_id']}:rebet:{template_amount}", "details": lambda bet: {"bet_id": bet["bet_id"]}})
        # Publish every rebet component only if the provider-current template is unchanged.
        placed, marker = prepare_bet_purchase(player_id, state, specifications, expected_template=template)
        # Settle or replay each immutable debit outside the state callback.
        settlement_rows = settle_prepared_bet_action(player_id, state, marker)
        # Preserve the historical event-only ledger list response.
        ledgers = [event for event, _replayed in settlement_rows]
        return {"placed": placed, "ledger": ledgers, **state_payload(player_id, state, query=query)}

    # Attach this decorator so the following function is registered with the framework.
    @router.delete(r"/api/v1/games/roulette/bets/(?P<bet_id>[^/]+)")
    # Define the clear_bet function used by this module.
    def clear_bet(body, query, bet_id):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Complete any interrupted action before preparing this refund.
        state = load_actionable_state(player_id)
        # Remove the exact bet and publish its immutable refund intent atomically.
        removed, marker = prepare_bet_refund(player_id, state, [bet_id])
        # Resolve the exact removed response bet.
        bet = removed[0]
        # Apply or recover the refund, then release its private marker.
        cred, _replayed = settle_prepared_bet_action(player_id, state, marker)[0]
        return {"cleared": bet, "ledger": cred, **state_payload(player_id, state, query=query)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/roulette/clear")
    # Define the clear_all function used by this module.
    def clear_all(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Complete any interrupted action before selecting the latest open bets.
        state = load_actionable_state(player_id)
        # Remove every player-owned bet and publish refund intents in one transition.
        bets, marker = prepare_bet_refund(player_id, state)
        # Apply or recover all refunds before returning terminal state.
        settle_prepared_bet_action(player_id, state, marker)
        return {"cleared": bets, **state_payload(player_id, state, query=query)}

    # Attach this decorator so the following function is registered with the framework.
    @router.post(r"/api/v1/games/roulette/spin")
    # Define the spin function used by this module.
    def spin(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        # Complete any prepared debit/refund before committing the wager set.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Reconcile exact wallet state before a spin can own the open round.
        resume_prepared_bet_action(player_id, state)
        # Resume previously committed entropy instead of sampling a second pocket.
        pending = state.get(PENDING_SPIN_KEY)
        # Commit fresh entropy only when no recoverable spin exists.
        if pending is None:
            # Publish exact wheel and settlement outcomes before any credit/history effect.
            pending = commit_pending_spin(player_id, state)
        # Settle every exact committed outcome and finalize terminal state.
        settlements = settle_pending_spin(player_id, state, copy.deepcopy(pending))
        # Preserve the established round response shape.
        settled = pending["round"]
        # Set logger.info("roulette_spin_result", round_id to the value needed for the next operation.
        logger.info("roulette_spin_result", round_id=settled["round_id"], result=settled["result"], color=settled["result_color"], bet_count=len(settled.get("bets",[])))
        return {"round": settled, "settlements": settlements, "bot_bets": [], **state_payload(player_id, state, query=query)}

    # Attach this decorator so the following function is registered with the framework.
    @router.get(r"/api/v1/games/roulette/stats")
    # Define the stats function used by this module.
    def stats(body, query):
        # Set player_id to the value needed for the next operation.
        player_id = request_player_id(body, query)
        return engine.stats(load_player_game_state(GAME_ID, player_id, engine.default_state))
