# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Bingo API actions, atomic state publication, and settlement recovery."""

# Import detached-copy support for provider-owned recovery markers and public payloads.
import copy

# Import atomic player-state publication beside the established read helper.
from casino.core.state_store import load_player_game_state, update_player_game_state
from casino.core.validation import require_amount, require_player_id
from casino.core import players, logger
# Import the shared id factory so every prepared action has a stable recovery identity.
from casino.core.ids import new_id
# Import the one canonical game-money boundary.
from casino.core.settlement import GameSettlementGateway
from casino.core.history import append_history
from casino.games.bingo import engine
# Import bot capability profiles so every session seats funded competitor cards. (issue #405)
from casino.bots import profiles
from casino.errors import ConflictError, ValidationError

# Bind the registered game namespace used by state, ledger, and history records.
GAME_ID = "bingo"
# Bind every Bingo movement to one storage-atomic settlement adapter.
SETTLEMENT = GameSettlementGateway(GAME_ID, "card_id")
# Seat at most three competitor cards per session so the human card genuinely races to win. (issue #405)
MAX_BOT_CARDS = 3
# Always present exactly this many competitor cards so the house edge cannot be thinned by disabling bots. (issue #452)
COMPETITOR_CARDS = 3
# Own the synthetic house spoiler identity that fills unfunded competitor seats without a wallet or payout. (issue #452)
HOUSE_COMPETITOR_ID = "bingo_house"
# Reserve one private action slot so money and history work never runs under the provider document lock. (BINGO-028)
PENDING_ACTION_KEY = "_bingo_pending_action"
# Retain the private debit-to-session join after the transient purchase marker is released. (BINGO-029)
PURCHASE_ASSOCIATIONS_KEY = "_bingo_purchase_session_associations"
# Bound associations for sessions no longer present in active or archived game state. (BINGO-029)
PURCHASE_ASSOCIATION_HISTORY_LIMIT = 1000


# Replace a stale caller snapshot with the complete provider-authoritative document. (BINGO-028)
def _refresh_state(state: dict, authoritative: dict) -> None:
    # Remove stale top-level fields before copying provider-owned state.
    state.clear()
    # Preserve caller object identity for established response construction.
    state.update(authoritative)


# Return a detached v1 state without exposing private recovery or association metadata. (BINGO-028, BINGO-029)
def _public_state(state: dict) -> dict:
    # Deep-copy because private marker snapshots contain nested cards and sessions.
    public = copy.deepcopy(state)
    # Remove the one private action owner while preserving every established public field.
    public.pop(PENDING_ACTION_KEY, None)
    # Remove the server-only debit-to-session join from every public state payload.
    public.pop(PURCHASE_ASSOCIATIONS_KEY, None)
    # Return the frozen public state shape.
    return public


# Validate the private association index before it can authorize replay or retention. (BINGO-029)
def _validated_purchase_session_associations(state: dict) -> list[dict]:
    # Treat an older document without the private index as an empty compatible state.
    records = state.get(PURCHASE_ASSOCIATIONS_KEY, [])
    # Refuse malformed durable metadata rather than guessing a debit/session relationship.
    if not isinstance(records, list):
        # Keep corruption operator-visible and prevent a false authoritative join.
        raise ConflictError("Bingo purchase association state is invalid")
    # Detect duplicate or conflicting identities while preserving insertion order.
    purchases = {}
    sessions = {}
    # Inspect every bounded record before trusting any one match.
    for record in records:
        # Require the two exact non-empty durable identifiers.
        if not isinstance(record, dict) or not isinstance(record.get("purchase_id"), str) or not record["purchase_id"] or not isinstance(record.get("session_id"), str) or not record["session_id"]:
            # Reject partial or type-confused private metadata.
            raise ConflictError("Bingo purchase association state is invalid")
        # Read the immutable pair once for duplicate checks.
        purchase_id = record["purchase_id"]
        session_id = record["session_id"]
        # Refuse duplicate purchase or session ownership, including duplicate exact rows.
        if purchase_id in purchases or session_id in sessions:
            # Preserve the one-to-one association invariant.
            raise ConflictError("Bingo purchase association state is invalid")
        # Index the validated pair for the remaining rows.
        purchases[purchase_id] = session_id
        sessions[session_id] = purchase_id
    # Return the provider-owned list after complete validation.
    return records


# Retain one immutable purchase/session join inside the session publication transaction. (BINGO-029)
def _retain_purchase_session_association(state: dict, purchase_id: str, session_id: str) -> None:
    # Require exact non-empty identities before any private state mutation.
    if not isinstance(purchase_id, str) or not purchase_id or not isinstance(session_id, str) or not session_id:
        # Reject missing recovery identity instead of publishing an ambiguous join.
        raise ConflictError("Bingo purchase association identity is invalid")
    # Validate all existing records before checking replay or conflict semantics.
    records = _validated_purchase_session_associations(state)
    # Compare the requested pair with each retained immutable association.
    for record in records:
        # Make an exact replay a stable no-op that does not reorder retention.
        if record["purchase_id"] == purchase_id and record["session_id"] == session_id:
            # Preserve byte-stable provider state across a lost-response replay.
            return
        # Prevent either durable identity from being rebound to another action.
        if record["purchase_id"] == purchase_id or record["session_id"] == session_id:
            # Fail closed on a one-to-one association conflict.
            raise ConflictError("Bingo purchase association identity changed")
    # Append the newly accepted relationship in provider transaction order.
    updated = [*records, {"purchase_id": purchase_id, "session_id": session_id}]
    # Pin every association whose session remains in the public active/archive state.
    retained_session_ids = set()
    # Preserve the active session join for its complete visible lifetime.
    active = state.get("active_session")
    # Add only one structured non-empty identity.
    if isinstance(active, dict) and isinstance(active.get("session_id"), str) and active["session_id"]:
        # Keep its debit association regardless of later reset history volume.
        retained_session_ids.add(active["session_id"])
    # Preserve all terminal sessions still retained by the engine archive.
    for session in state.get("last_sessions", []):
        # Ignore unrelated malformed archive entries here; engine validation owns public state.
        if isinstance(session, dict) and isinstance(session.get("session_id"), str) and session["session_id"]:
            # Pin the exact terminal session identity.
            retained_session_ids.add(session["session_id"])
    # Select bounded historical rows whose sessions are no longer retained by game state.
    historical_indexes = [index for index, record in enumerate(updated) if record["session_id"] not in retained_session_ids]
    # Keep only the newest bounded historical associations while never evicting pinned sessions.
    historical_indexes = set(historical_indexes[-PURCHASE_ASSOCIATION_HISTORY_LIMIT:])
    # Preserve original transaction order for every retained pair.
    state[PURCHASE_ASSOCIATIONS_KEY] = [record for index, record in enumerate(updated) if record["session_id"] in retained_session_ids or index in historical_indexes]


# Resolve the private purchase identity for one exact session without exposing the index. (BINGO-029)
def _purchase_id_for_session(state: dict, session_id: str) -> str | None:
    # Reject missing session identity before consulting durable metadata.
    if not isinstance(session_id, str) or not session_id:
        # Report no association for an absent lookup key.
        return None
    # Validate the complete index before returning one authoritative relationship.
    for record in _validated_purchase_session_associations(state):
        # Return only the exact session match.
        if record["session_id"] == session_id:
            # Preserve the raw internal purchase identity for server-only consumers.
            return record["purchase_id"]
    # Report absence without synthesizing an association.
    return None


# Locate an active or archived session by its durable identity. (BINGO-028)
def _find_session(state: dict, session_id: str) -> dict | None:
    # Prefer the active slot when the requested session is still in progress.
    active = state.get("active_session")
    # Return the active session only when its identity matches exactly.
    if isinstance(active, dict) and active.get("session_id") == session_id:
        # Preserve the provider-owned nested object for callback-local mutation.
        return active
    # Search newest archived sessions first because identifiers are immutable and unique.
    for session in reversed(state.get("last_sessions", [])):
        # Return only a structured session with the exact identity.
        if isinstance(session, dict) and session.get("session_id") == session_id:
            # Preserve the provider-owned archived object.
            return session
    # Report absence without inventing a session or outcome.
    return None


# Build one canonical signed movement without changing established Bingo ledger vocabulary. (BINGO-028)
def _movement(*, player_id: str, signed_amount: float, transaction_type: str, round_id: str, action_key: str, request_fingerprint: str, details: dict) -> dict:
    # Return exact immutable dimensions used for apply, recovery, and validation.
    return {"player_id": player_id, "signed_amount": signed_amount, "transaction_type": transaction_type, "round_id": round_id, "action_key": action_key, "request_fingerprint": request_fingerprint, "details": copy.deepcopy(details)}


# Apply once or recover a compatible committed row after a lost provider response. (BINGO-028)
def _apply_movement(movement: dict) -> tuple[dict, bool]:
    # Attempt the one authorized storage-atomic money mutation.
    try:
        # Preserve the gateway's event and replay marker response.
        return SETTLEMENT.apply_once(**movement)
    # Reconcile any transport/provider failure without issuing a mutation retry.
    except Exception:
        # Read only the exact player/game/action proof selected by the prepared marker.
        event = SETTLEMENT.find(movement["player_id"], movement["action_key"], round_id=movement["round_id"], transaction_type=movement["transaction_type"], request_fingerprint=movement["request_fingerprint"])
        # Preserve the original failure when no immutable movement committed.
        if event is None:
            # Re-raise the active exception with its original traceback.
            raise
        # Reject a coincidentally named row whose immutable dimensions diverge.
        SETTLEMENT.validate_existing(event, transaction_type=movement["transaction_type"], round_id=movement["round_id"], signed_amount=movement["signed_amount"], request_fingerprint=movement["request_fingerprint"])
        # Classify the recovered committed movement as a replay for response compatibility.
        return event, True


# Build the established human purchase debit from one prepared marker. (BINGO-028)
def _human_purchase_movement(marker: dict) -> dict:
    # Reuse the pre-session purchase identity and exact historical fingerprint.
    return _movement(player_id=marker["player_id"], signed_amount=-marker["amount"], transaction_type="BINGO_CARD_PURCHASED", round_id=marker["purchase_id"], action_key=f"{marker['purchase_id']}:human:wager", request_fingerprint=f"{marker['purchase_id']}:{marker['player_id']}:{marker['pattern']}:{marker['amount']}", details={"pattern": marker["pattern"]})


# Build one funded bot purchase debit from the stable pre-session identity. (BINGO-028)
def _bot_purchase_movement(marker: dict, bot: dict, stake: float) -> dict:
    # Preserve the existing bot transaction type, action key, and audit dimensions.
    return _movement(player_id=bot["player_id"], signed_amount=-stake, transaction_type="BOT_BINGO_CARD_PURCHASED", round_id=marker["purchase_id"], action_key=f"{marker['purchase_id']}:bot:{bot['player_id']}:wager", request_fingerprint=f"{marker['purchase_id']}:{bot['player_id']}:{marker['pattern']}:{stake}", details={"bot_id": bot.get("bot_id"), "strategy_id": bot.get("strategy_id"), "pattern": marker["pattern"]})


# Build the existing purchase-failure refund for one already-funded wallet. (BINGO-028)
def _purchase_refund_movement(marker: dict, funded: dict) -> dict:
    # Distinguish the human and bot refund vocabulary without changing ledger semantics.
    is_human = funded["player_id"] == marker["player_id"]
    # Select the exact historical transaction meaning.
    transaction_type = "BINGO_CARD_REFUND_AFTER_ERROR" if is_human else "BOT_BINGO_CARD_REFUND_AFTER_ERROR"
    # Preserve the established stable action key for each wallet.
    action_key = f"{marker['purchase_id']}:human:refund" if is_human else f"{marker['purchase_id']}:bot:{funded['player_id']}:refund"
    # Preserve the exact request fingerprint used before atomic publication.
    fingerprint = f"{marker['purchase_id']}:{funded['player_id']}:{marker['pattern']}:{funded['amount']}:refund"
    # Retain bot identity only for bot refunds.
    details = {"pattern": marker["pattern"]}
    # Add the old bot audit field without leaking it onto the human row.
    if not is_human:
        # Preserve the funded bot identity from the selected seat.
        details["bot_id"] = funded.get("bot_id")
    # Return the exact positive refund movement.
    return _movement(player_id=funded["player_id"], signed_amount=funded["amount"], transaction_type=transaction_type, round_id=marker["purchase_id"], action_key=action_key, request_fingerprint=fingerprint, details=details)


# Build the existing per-card reset refund movement. (BINGO-028)
def _card_refund_movement(session: dict, card: dict) -> dict:
    # Preserve the durable card/session identity and historical refund vocabulary.
    return _movement(player_id=card["player_id"], signed_amount=card["amount"], transaction_type="BINGO_CARD_REFUND", round_id=session["session_id"], action_key=f"{card['card_id']}:refund", request_fingerprint=f"{card['card_id']}:{session['session_id']}:{card['amount']}:refund", details={"card_id": card["card_id"]})


# Build the existing winning-card payout movement. (BINGO-028)
def _card_payout_movement(session: dict, card: dict) -> dict:
    # Preserve the exact session/card settlement identity and pattern audit field.
    return _movement(player_id=card["player_id"], signed_amount=card["payout"], transaction_type="BINGO_PAYOUT_CREDIT", round_id=session["session_id"], action_key=f"{card['card_id']}:settlement", request_fingerprint=f"{card['card_id']}:{session['session_id']}:{card['payout']}", details={"pattern": session["pattern"], "card_id": card["card_id"]})


# Preserve the established direct settlement helper for engine/economics callers. (BINGO-028)
def settle_if_done(session: dict | None) -> list[dict]:
    # Preserve the historical empty credit response for missing or non-winning sessions.
    credits = []
    # Settle each real winning card under its stable card/session identity.
    if session and session.get("status") == "won":
        # Inspect every card because one terminal call can complete multiple cards.
        for card in session.get("cards", []):
            # Skip non-winners, synthetic house cards, and already-published credits.
            if card.get("status") != "won" or card.get("source") == "house" or card.get("credited"):
                # Preserve the established no-credit behavior for this card.
                continue
            # Commit or recover the exact payout when the card has a positive award.
            event, replayed = _apply_movement(_card_payout_movement(session, card)) if card.get("payout") else (None, False)
            # Append history and expose only a newly committed credit.
            if not replayed:
                # Read the wallet balance after the payout commits.
                balance = players.get_player(card["player_id"])["balance"]
                # Preserve the established winning-card history projection.
                append_history(GAME_ID, session["session_id"], card["player_id"], "card", session["pattern"], card["amount"], "win", card["payout"], balance, {"called": session["called"], "card": card["card"], "winning_coords": card.get("winning_coords", [])})
                # Return the new immutable payout event to the direct caller.
                credits.append(event)
            # Mark the detached session card after committed or replayed evidence exists.
            card["credited"] = True
    # Preserve the bounded no-win history path for direct engine callers.
    elif session and session.get("status") == "no_win" and not session.get("loss_recorded"):
        # Append the established session-level zero-payout history row.
        append_history(GAME_ID, session["session_id"], session["player_id"], "session", session["pattern"], session["amount"], "no_win", 0, players.get_player(session["player_id"])["balance"], {"called": session.get("called", []), "max_calls": session.get("max_calls")})
        # Prevent a repeated direct invocation from appending a second row.
        session["loss_recorded"] = True
    # Return only newly committed payouts.
    return credits


# Fund real bot seats while reconciling lost responses under stable action identities. (BINGO-028)
def fund_bot_players(player_id, amount, pattern, purchase_id):
    # Reconstruct the immutable purchase marker used by movement builders.
    marker = {"player_id": player_id, "amount": amount, "pattern": pattern, "purchase_id": purchase_id}
    # Collect only bots whose card purchase actually debited a bot wallet. (issue #405)
    funded = []
    # Iterate through the eligible Bingo bots, bounded to the per-session seat limit.
    for bot in profiles.eligible_bots(GAME_ID)[:MAX_BOT_CARDS]:
        # Never seat the requesting player's own wallet as its competitor.
        if bot.get("player_id") == player_id:
            # Skip the colliding identity.
            continue
        # Price the bot card from configured stake, falling back to the human card price.
        stake = round(float(bot.get("stake") or amount), 2)
        # Start protected funding so an unfundable bot shrinks the real-bot field.
        try:
            # Commit or recover the exact funded bot movement without a second mutation.
            event, _replayed = _apply_movement(_bot_purchase_movement(marker, bot, stake))
        # Keep the existing behavior that an unfundable bot receives no card.
        except Exception as exc:
            # Emit the established value-bounded skip warning.
            logger.warning("bingo_bot_card_skipped", bot_id=bot.get("bot_id"), message=str(exc))
            # Continue seating remaining fundable bots.
            continue
        # Record the funded competitor shape consumed by engine.start_session.
        funded.append({"player_id": bot["player_id"], "amount": stake, "bot_id": bot.get("bot_id"), "ledger_id": event.get("ledger_id")})
    # Return the funded competitor list to the card purchase flow.
    return funded


# Seat a fixed competitor field so the paytable edge is independent of the bot roster. (issue #452)
def seat_competitors(player_id, amount, pattern, purchase_id):
    # Fund real bot competitor cards first so genuine bot wallets carry real stakes. (issue #405)
    seats = fund_bot_players(player_id, amount, pattern, purchase_id)
    # Fill every remaining seat with an unfunded, never-paid synthetic house spoiler. (issue #452)
    for _index in range(max(0, COMPETITOR_CARDS - len(seats))):
        # Preserve display parity with the human stake without touching a wallet.
        seats.append({"player_id": HOUSE_COMPETITOR_ID, "amount": amount, "source": "house"})
    # Return the always-full competitor field.
    return seats


# Resolve the authenticated player while preserving the legacy human default.
def request_player_id(body, query) -> str:
    # Validate the explicit or legacy identity through the shared boundary.
    return require_player_id({"player_id": body.get("player_id") or query.get("player_id") or "human"})


# Build the frozen Bingo state response without private recovery markers. (BINGO-028)
def payload(player_id: str, state=None):
    # Read provider-authoritative state only when the caller did not supply it.
    state = state or load_player_game_state(GAME_ID, player_id, engine.default_state)
    # Limit the visible player set to the requester and bots as before.
    visible_players = [player for player in players.list_players() if player["player_id"] == player_id or player.get("type") == "bot"]
    # Preserve every established response field and nested public shape.
    return {"game": GAME_ID, "state": _public_state(state), "player": players.get_player(player_id), "players": visible_players}


# Reserve one purchase before any wallet movement can race another state action. (BINGO-028)
def prepare_purchase(player_id: str, state: dict, amount: float, pattern: str) -> dict:
    # Reject unknown patterns before reserving state or debiting any wallet.
    if pattern not in {"line", "four_corners", "postage_stamp", "blackout"}:
        # Preserve the existing public validation diagnostic.
        raise ValidationError("Unknown Bingo pattern")
    # Allocate the stable pre-session identity once for debit and recovery.
    purchase_id = new_id("bingo-purchase")
    # Capture the exact marker selected by the provider callback.
    selected = {}

    # Reserve one action against the latest complete player document.
    def prepare(current: dict) -> dict:
        # Reject overlap with purchase, call settlement, or reset recovery.
        if current.get(PENDING_ACTION_KEY) is not None:
            # Preserve the recoverable earlier action for explicit completion.
            raise ConflictError("Bingo state requires action recovery")
        # Reject a second active card before touching the wallet.
        if isinstance(current.get("active_session"), dict) and current["active_session"].get("status") == "active":
            # Preserve the existing active-session conflict behavior.
            raise ConflictError("A Bingo session is already active")
        # Build the immutable private purchase marker.
        marker = {"kind": "purchase", "status": "prepared", "purchase_id": purchase_id, "player_id": player_id, "amount": amount, "pattern": pattern}
        # Publish only the marker; session entropy remains unallocated until funding succeeds.
        current[PENDING_ACTION_KEY] = marker
        # Return detached evidence to the caller after provider commit.
        selected.update(copy.deepcopy(marker))
        # Publish the complete current document atomically.
        return current

    # Commit the reservation under JSON/MySQL provider serialization.
    authoritative = update_player_game_state(GAME_ID, player_id, prepare, engine.default_state)
    # Replace the caller's stale snapshot for established response code.
    _refresh_state(state, authoritative)
    # Return the exact committed private marker.
    return selected


# Publish the funded session and durable private debit association atomically. (BINGO-028, BINGO-029)
def commit_purchase(player_id: str, state: dict, marker: dict, bot_players: list[dict]) -> dict:
    # Capture the exact provider-owned session selected or replayed by the callback.
    selected = {}

    # Commit cards and session against the provider-current document.
    def commit(current: dict) -> dict:
        # Read the one private action owner.
        pending = current.get(PENDING_ACTION_KEY)
        # Refuse another action or a changed purchase identity.
        if not isinstance(pending, dict) or pending.get("kind") != "purchase" or pending.get("purchase_id") != marker.get("purchase_id"):
            # Fail closed instead of adopting another purchase.
            raise ConflictError("Bingo purchase recovery identity changed")
        # Reuse an already-committed session when the provider response was lost.
        if pending.get("status") == "committed":
            # Locate the session owned by the exact purchase marker.
            session = _find_session(current, pending.get("session_id"))
            # Reject corrupt committed state without inventing cards.
            if session is None:
                # Require operator-visible recovery rather than a second debit/session.
                raise ConflictError("Bingo committed purchase session is unavailable")
        else:
            # Allocate and publish the complete session only after every retained seat is funded.
            session = engine.start_session(current, player_id, marker["amount"], marker["pattern"], bot_players=copy.deepcopy(bot_players))
            # Bind the terminal recovery marker to the exact created session.
            pending["status"] = "committed"
            # Preserve the session identity for response-loss reconciliation.
            pending["session_id"] = session["session_id"]
        # Persist the debit purchase identity beside the accepted session in this same transaction.
        _retain_purchase_session_association(current, pending["purchase_id"], session["session_id"])
        # Return detached session evidence after provider publication.
        selected.update(copy.deepcopy(session))
        # Publish the complete state atomically.
        return current

    # Serialize the complete funded-session transition.
    authoritative = update_player_game_state(GAME_ID, player_id, commit, engine.default_state)
    # Replace stale caller state with the provider result.
    _refresh_state(state, authoritative)
    # Return the exact committed session.
    return selected


# Clear only the exact committed purchase marker after its durable association exists. (BINGO-028, BINGO-029)
def finalize_purchase(player_id: str, state: dict, marker: dict) -> dict:
    # Capture the provider-current session returned after marker release.
    selected = {}

    # Remove private recovery ownership without touching sibling fields.
    def finalize(current: dict) -> dict:
        # Read the marker that may already have been cleared by a sibling recovery.
        pending = current.get(PENDING_ACTION_KEY)
        # Remove only the exact committed purchase marker.
        if isinstance(pending, dict) and pending.get("kind") == "purchase" and pending.get("purchase_id") == marker.get("purchase_id"):
            # Reject premature finalization before the session commit exists.
            if pending.get("status") != "committed":
                # Keep the prepared action recoverable.
                raise ConflictError("Bingo purchase is not committed")
            # Locate exact session before clearing its recovery identity.
            session = _find_session(current, pending.get("session_id"))
            # Refuse a corrupt committed marker.
            if session is None:
                # Leave the marker intact for operator recovery.
                raise ConflictError("Bingo committed purchase session is unavailable")
            # Upgrade a valid legacy BINGO-028 marker from its exact authoritative session identity.
            _retain_purchase_session_association(current, pending["purchase_id"], session["session_id"])
            # Require the private durable join before discarding the transient purchase identity.
            if _purchase_id_for_session(current, session["session_id"]) != pending["purchase_id"]:
                # Leave the marker available for explicit repair or operator recovery.
                raise ConflictError("Bingo committed purchase association is unavailable")
            # Retain detached response evidence.
            selected.update(copy.deepcopy(session))
            # Release only this action slot.
            current.pop(PENDING_ACTION_KEY, None)
        else:
            # Recover an already-finalized exact session by the identity retained by the caller.
            session = _find_session(current, marker.get("session_id")) if marker.get("session_id") else None
            # Retain it only when a sibling already completed this action.
            if session is not None:
                # Require the same private association before accepting an already-finalized replay.
                if _purchase_id_for_session(current, session["session_id"]) != marker.get("purchase_id"):
                    # Refuse a coincidental session identifier without the exact debit join.
                    raise ConflictError("Bingo committed purchase association is unavailable")
                # Return the same authoritative session without further mutation.
                selected.update(copy.deepcopy(session))
        # Publish or replay the complete document.
        return current

    # Serialize marker release with every sibling state mutation.
    authoritative = update_player_game_state(GAME_ID, player_id, finalize, engine.default_state)
    # Refresh the caller snapshot.
    _refresh_state(state, authoritative)
    # Return the exact committed session.
    return selected


# Roll back only a definitively uncommitted purchase reservation. (BINGO-028)
def rollback_purchase(player_id: str, state: dict, marker: dict) -> None:
    # Remove the exact prepared marker without reverting sibling state.
    def rollback(current: dict) -> dict:
        # Read provider-current private ownership.
        pending = current.get(PENDING_ACTION_KEY)
        # Clear only the matching marker that never published a session.
        if isinstance(pending, dict) and pending.get("kind") == "purchase" and pending.get("purchase_id") == marker.get("purchase_id") and pending.get("status") == "prepared":
            # Release the state action for a safe explicit retry.
            current.pop(PENDING_ACTION_KEY, None)
        # Preserve every sibling field and committed marker.
        return current

    # Publish the bounded rollback through the provider boundary.
    authoritative = update_player_game_state(GAME_ID, player_id, rollback, engine.default_state)
    # Refresh the caller snapshot after rollback.
    _refresh_state(state, authoritative)


# Debit, fund, commit, and finalize one prepared purchase with exact recovery. (BINGO-028)
def settle_purchase(player_id: str, state: dict, marker: dict) -> dict:
    # Track only wallets whose exact debit has committed and may require compensation.
    funded = []
    # Start the one no-retry money/state workflow.
    try:
        # Commit or recover the human stake under the prepared purchase identity.
        _human_event, _human_replayed = _apply_movement(_human_purchase_movement(marker))
        # Record the human wallet for bounded failure compensation.
        funded.append({"player_id": player_id, "amount": marker["amount"]})
        # Fund each eligible real bot through its own immutable action identity.
        bot_players = seat_competitors(player_id, marker["amount"], marker["pattern"], marker["purchase_id"])
        # Retain only actually funded bot seats for failure compensation.
        funded.extend({"player_id": seat["player_id"], "amount": seat["amount"], "bot_id": seat.get("bot_id")} for seat in bot_players if seat.get("source") != "house")
        # Publish all cards/session state in one provider-atomic transition.
        session = commit_purchase(player_id, state, marker, bot_players)
        # Carry the committed session identity into finalization and response-loss recovery.
        marker = {**marker, "status": "committed", "session_id": session["session_id"]}
        # Release the private marker only after the session is authoritative.
        return finalize_purchase(player_id, state, marker)
    # Compensate only when no committed session can be recovered.
    except Exception:
        # Read current state without issuing another money mutation.
        current = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Inspect the exact action marker for a lost provider response.
        pending = current.get(PENDING_ACTION_KEY)
        # Recover a committed session instead of refunding valid stakes.
        if isinstance(pending, dict) and pending.get("kind") == "purchase" and pending.get("purchase_id") == marker.get("purchase_id") and pending.get("status") == "committed":
            # Rebind the caller to provider-current committed identity.
            _refresh_state(state, current)
            # Finalize without issuing another debit or session mutation.
            return finalize_purchase(player_id, state, pending)
        # Refund only debits known to have committed in this invocation.
        for funded_wallet in funded:
            # Commit or recover each exact compensation once.
            _apply_movement(_purchase_refund_movement(marker, funded_wallet))
        # Release only this uncommitted reservation after compensation.
        rollback_purchase(player_id, state, marker)
        # Preserve the original failure contract.
        raise


# Commit one or more balls and a private response marker in provider order. (BINGO-028)
def commit_calls(player_id: str, state: dict, max_calls: int) -> dict:
    # Allocate one identity before entering the provider callback.
    action_id = new_id("bingo-call")
    # Capture the exact committed marker for settlement and response construction.
    selected = {}

    # Mutate the latest session while the provider serializes sibling callers.
    def commit(current: dict) -> dict:
        # Refuse overlap with a purchase, earlier call settlement, or reset.
        if current.get(PENDING_ACTION_KEY) is not None:
            # Require the earlier action to settle before another ball can start.
            raise ConflictError("Bingo state requires action recovery")
        # Execute one call or the compatibility bounded batch against provider-current state.
        if max_calls == 1:
            # Preserve the historical single-call engine path and label.
            session, number = engine.call_next(current)
            # Normalize response construction to one exact call list.
            calls = [number]
        else:
            # Preserve the existing compatibility batch behavior.
            session, calls = engine.auto_play(current, max_calls)
        # Publish one private response/settlement marker before leaving the atomic boundary.
        marker = {"kind": "call", "status": "committed", "action_id": action_id, "session_id": session["session_id"], "calls": list(calls), "terminal": session.get("status") != "active", "history_claims": []}
        # Retain the exact provider-ordered result for lost-response recovery.
        current[PENDING_ACTION_KEY] = marker
        # Return detached marker evidence.
        selected.update(copy.deepcopy(marker))
        # Publish the complete state and marker together.
        return current

    # Start the one provider mutation and reconcile a response lost after publication.
    try:
        # Serialize ball selection, terminal transition, and marker publication.
        authoritative = update_player_game_state(GAME_ID, player_id, commit, engine.default_state)
    # Recover only this exact action when the provider committed before response loss.
    except Exception:
        # Read the authoritative document without retrying ball selection.
        authoritative = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Read its private committed marker.
        pending = authoritative.get(PENDING_ACTION_KEY)
        # Preserve the original failure if another or no action owns the state.
        if not isinstance(pending, dict) or pending.get("kind") != "call" or pending.get("action_id") != action_id:
            # Re-raise the active provider error.
            raise
        # Rebind selected evidence to the exact committed result.
        selected.update(copy.deepcopy(pending))
    # Replace stale caller state with provider-authoritative state.
    _refresh_state(state, authoritative)
    # Return the exact committed action marker.
    return selected


# Atomically claim ownership of one immutable history row. (BINGO-028)
def claim_history(player_id: str, state: dict, marker: dict, claim_id: str) -> bool:
    # Retain whether this contender won the provider-serialized claim.
    claimed = {"value": False}

    # Add one claim only while the exact committed action marker still exists.
    def claim(current: dict) -> dict:
        # Read provider-current recovery ownership.
        pending = current.get(PENDING_ACTION_KEY)
        # Ignore an already-finalized or unrelated action.
        if not isinstance(pending, dict) or pending.get("kind") != marker.get("kind") or pending.get("action_id") != marker.get("action_id"):
            # Preserve current state without granting ownership.
            return current
        # Normalize the private claim list defensively.
        claims = pending.setdefault("history_claims", [])
        # Grant exactly one contender for this semantic history row.
        if claim_id not in claims:
            # Persist ownership before the append side effect runs.
            claims.append(claim_id)
            # Report the winning claim to this caller.
            claimed["value"] = True
        # Publish the complete marker update atomically.
        return current

    # Serialize the claim with terminal finalization and sibling settlement attempts.
    authoritative = update_player_game_state(GAME_ID, player_id, claim, engine.default_state)
    # Refresh caller state to the provider result.
    _refresh_state(state, authoritative)
    # Return whether this contender owns the append.
    return claimed["value"]


# Mark terminal settlement fields and release one committed call marker. (BINGO-028)
def finalize_call(player_id: str, state: dict, marker: dict, credited_card_ids: set[str], loss_recorded: bool) -> dict:
    # Capture the exact active or archived session after finalization.
    selected = {}

    # Publish settlement markers against the latest archived session.
    def finalize(current: dict) -> dict:
        # Locate the exact session even when a sibling already cleared the marker.
        session = _find_session(current, marker["session_id"])
        # Reject missing committed state instead of inventing a terminal response.
        if session is None:
            # Fail closed on a corrupt private marker.
            raise ConflictError("Bingo committed call session is unavailable")
        # Mark only cards whose exact payout proof committed.
        for card in session.get("cards", []):
            # Preserve every other card field and status.
            if card.get("card_id") in credited_card_ids:
                # Record terminal payout publication exactly once.
                card["credited"] = True
        # Publish the no-win audit marker only after one history owner appended it.
        if loss_recorded:
            # Preserve existing history behavior on the archived session.
            session["loss_recorded"] = True
        # Remove only the exact call marker when still present.
        pending = current.get(PENDING_ACTION_KEY)
        # Permit a sibling to have finalized first without changing state again.
        if isinstance(pending, dict) and pending.get("kind") == "call" and pending.get("action_id") == marker.get("action_id"):
            # Release the action slot after all terminal side effects converge.
            current.pop(PENDING_ACTION_KEY, None)
        # Return detached response evidence.
        selected.update(copy.deepcopy(session))
        # Publish the complete terminal document atomically.
        return current

    # Serialize terminal markers with sibling requests.
    authoritative = update_player_game_state(GAME_ID, player_id, finalize, engine.default_state)
    # Refresh caller state after final publication.
    _refresh_state(state, authoritative)
    # Return the authoritative session.
    return selected


# Settle or replay one committed call marker and publish one terminal state. (BINGO-028)
def settle_committed_call(player_id: str, state: dict, marker: dict) -> tuple[dict, list[int], list[dict]]:
    # Refresh before any payout decision so a stale contender sees finalized card evidence.
    _refresh_state(state, load_player_game_state(GAME_ID, player_id, engine.default_state))
    # Locate the exact active or archived provider-current session.
    session = _find_session(state, marker["session_id"])
    # Refuse a corrupt committed marker.
    if session is None:
        # Fail closed without a payout or fabricated response.
        raise ConflictError("Bingo committed call session is unavailable")
    # Preserve the historical credits response as newly committed events only.
    credits = []
    # Retain every card whose exact payout proof committed.
    credited_card_ids = set()
    # Settle only terminal winning sessions.
    if marker.get("terminal") and session.get("status") == "won":
        # Inspect every real winning card because one ball can complete multiple cards.
        for card in session.get("cards", []):
            # Skip lost/active cards, synthetic house spoilers, zero payouts, and already-final cards.
            if card.get("status") != "won" or card.get("source") == "house" or not card.get("payout") or card.get("credited"):
                # Preserve the existing no-credit behavior for those cards.
                continue
            # Commit or recover the exact payout without retrying a failed mutation.
            event, replayed = _apply_movement(_card_payout_movement(session, card))
            # Preserve the prior response contract: only a newly committed credit is returned.
            if not replayed:
                # Expose the immutable new event.
                credits.append(event)
            # Claim the one winning-card history row across sibling settlers.
            if claim_history(player_id, state, marker, f"win:{card['card_id']}"):
                # Read the post-commit wallet balance for the accepted row.
                balance = players.get_player(card["player_id"])["balance"]
                # Append the established complete winning-card history shape.
                append_history(GAME_ID, session["session_id"], card["player_id"], "card", session["pattern"], card["amount"], "win", card["payout"], balance, {"called": session["called"], "card": card["card"], "winning_coords": card.get("winning_coords", [])})
            # Publish the credited marker after immutable payout proof exists.
            credited_card_ids.add(card["card_id"])
    # Record a bounded no-win terminal exactly once across sibling settlers.
    loss_recorded = bool(session.get("loss_recorded"))
    # Claim only when this action created the terminal loss and no prior row exists.
    if marker.get("terminal") and session.get("status") == "no_win" and not loss_recorded:
        # Serialize ownership of the zero-money history append.
        if claim_history(player_id, state, marker, "no-win"):
            # Append the established session-level no-win history row.
            append_history(GAME_ID, session["session_id"], session["player_id"], "session", session["pattern"], session["amount"], "no_win", 0, players.get_player(session["player_id"])["balance"], {"called": session.get("called", []), "max_calls": session.get("max_calls")})
        # Mark the provider session terminal after the claim converges.
        loss_recorded = True
    # Release the call marker and publish terminal card/history flags.
    finalized = finalize_call(player_id, state, marker, credited_card_ids, loss_recorded)
    # Return the frozen route response dimensions.
    return finalized, list(marker.get("calls", [])), credits


# Prepare one reset against the exact provider-current active session. (BINGO-028)
def prepare_reset(player_id: str, state: dict) -> dict | None:
    # Allocate a private action identity for history-claim ownership.
    action_id = new_id("bingo-reset")
    # Retain the selected marker or explicit no-session result.
    selected = {}

    # Reserve reset ownership without clearing visible state before refunds settle.
    def prepare(current: dict) -> dict:
        # Refuse overlap with any earlier recoverable action.
        if current.get(PENDING_ACTION_KEY) is not None:
            # Preserve the earlier action for explicit completion.
            raise ConflictError("Bingo state requires action recovery")
        # Read the exact active session selected by this reset.
        session = current.get("active_session")
        # Preserve the historical no-op reset when no active session exists.
        if not isinstance(session, dict) or session.get("status") != "active":
            # Return without publishing a private marker.
            return current
        # Snapshot immutable refund/history inputs under the provider lock.
        marker = {"kind": "reset", "status": "prepared", "action_id": action_id, "session_id": session["session_id"], "session": copy.deepcopy(session), "history_claims": []}
        # Publish reset ownership while keeping the active session visible until settlement completes.
        current[PENDING_ACTION_KEY] = marker
        # Retain detached marker evidence for money work outside the lock.
        selected.update(copy.deepcopy(marker))
        # Publish the complete current document.
        return current

    # Serialize reset selection with every call and purchase.
    authoritative = update_player_game_state(GAME_ID, player_id, prepare, engine.default_state)
    # Refresh caller state to provider authority.
    _refresh_state(state, authoritative)
    # Return no marker for the historical empty reset.
    return selected or None


# Release an exact reset marker after a definitively failed refund. (BINGO-028)
def rollback_reset(player_id: str, state: dict, marker: dict) -> None:
    # Clear only the matching prepared reset ownership.
    def rollback(current: dict) -> dict:
        # Read provider-current action ownership.
        pending = current.get(PENDING_ACTION_KEY)
        # Release only the exact reset marker; never restore a stale whole document.
        if isinstance(pending, dict) and pending.get("kind") == "reset" and pending.get("action_id") == marker.get("action_id"):
            # Remove the private action slot while leaving the active session untouched.
            current.pop(PENDING_ACTION_KEY, None)
        # Preserve every sibling field.
        return current

    # Publish the bounded rollback atomically.
    authoritative = update_player_game_state(GAME_ID, player_id, rollback, engine.default_state)
    # Refresh caller state.
    _refresh_state(state, authoritative)


# Settle one prepared reset and atomically clear only its exact session. (BINGO-028)
def settle_prepared_reset(player_id: str, state: dict, marker: dict) -> list[dict]:
    # Use the immutable selected session for refund and history dimensions.
    session = copy.deepcopy(marker["session"])
    # Preserve the historical refund event list response.
    refunds = []
    # Start the no-retry reset settlement workflow.
    try:
        # Refund every funded card only when no ball was called.
        if not session.get("called"):
            # Inspect the exact selected card order.
            for card in session.get("cards", []):
                # Never refund an unfunded synthetic house spoiler. (issue #452)
                if card.get("source") == "house":
                    # Skip the non-wallet seat.
                    continue
                # Commit or recover the exact per-card refund once.
                event, _replayed = _apply_movement(_card_refund_movement(session, card))
                # Preserve the established response list shape for replay and first commit.
                refunds.append(event)
            # Claim the one reset history row across sibling recovery attempts.
            if claim_history(player_id, state, marker, "refunded"):
                # Append the unchanged refunded-session audit row.
                append_history(GAME_ID, session["session_id"], session["player_id"], "session", session["pattern"], session["amount"], "refunded", sum(abs(row["amount"]) for row in refunds), players.get_player(session["player_id"])["balance"], {"reason": "reset_before_calls"})
        else:
            # Claim the one abandoned-session history row across sibling recovery attempts.
            if claim_history(player_id, state, marker, "abandoned"):
                # Append the unchanged abandonment history shape.
                append_history(GAME_ID, session["session_id"], session["player_id"], "session", session["pattern"], session["amount"], "abandoned", 0, players.get_player(session["player_id"])["balance"], {"called": session.get("called", [])})
                # Preserve the existing operations warning for abandoned sessions.
                logger.warning("bingo_session_abandoned", session_id=session["session_id"], calls=len(session.get("called", [])))

        # Clear the exact active session only after refund/history work converges.
        def finalize(current: dict) -> dict:
            # Read provider-current reset ownership.
            pending = current.get(PENDING_ACTION_KEY)
            # Permit a sibling to have finalized first.
            if not isinstance(pending, dict) or pending.get("kind") != "reset" or pending.get("action_id") != marker.get("action_id"):
                # Preserve the already-final state.
                return current
            # Reject an unexpected replacement session rather than clearing it.
            active = current.get("active_session")
            if isinstance(active, dict) and active.get("session_id") != marker.get("session_id"):
                # Leave both the replacement and marker intact for operator recovery.
                raise ConflictError("Bingo reset session changed")
            # Clear only the selected active session.
            current["active_session"] = None
            # Release the exact reset action slot.
            current.pop(PENDING_ACTION_KEY, None)
            # Publish the complete current document.
            return current

        # Serialize terminal reset publication with all sibling state.
        authoritative = update_player_game_state(GAME_ID, player_id, finalize, engine.default_state)
        # Refresh caller state after reset.
        _refresh_state(state, authoritative)
        # Return the established refund list.
        return refunds
    # Preserve an actionable session when a movement definitively failed.
    except Exception:
        # Release only this marker; committed earlier refunds replay safely on explicit retry.
        rollback_reset(player_id, state, marker)
        # Preserve the original error.
        raise


# Complete a prior terminal call/reset or reject an in-flight purchase before a new action. (BINGO-028)
def resume_pending_action(player_id: str, state: dict) -> None:
    # Refresh from provider authority before classifying private recovery state.
    authoritative = load_player_game_state(GAME_ID, player_id, engine.default_state)
    # Replace the caller's possibly stale document.
    _refresh_state(state, authoritative)
    # Read the one private action owner.
    pending = state.get(PENDING_ACTION_KEY)
    # Return immediately when the document is actionable.
    if not isinstance(pending, dict):
        # Leave public state unchanged.
        return
    # Complete a committed call and its exactly-once settlement/history publication.
    if pending.get("kind") == "call" and pending.get("status") == "committed":
        # Converge the prior action without selecting another ball.
        settle_committed_call(player_id, state, copy.deepcopy(pending))
        # Return after exact recovery.
        return
    # Complete a selected reset through stable refund action identities.
    if pending.get("kind") == "reset" and pending.get("status") == "prepared":
        # Converge the prior reset before admitting another action.
        settle_prepared_reset(player_id, state, copy.deepcopy(pending))
        # Return after exact recovery.
        return
    # Finalize a purchase whose session already committed.
    if pending.get("kind") == "purchase" and pending.get("status") == "committed":
        # Release its private marker without another wallet mutation.
        finalize_purchase(player_id, state, copy.deepcopy(pending))
        # Return after exact recovery.
        return
    # Refuse an in-flight prepared purchase because no client-side request may replay its debit.
    raise ConflictError("Bingo purchase is still in progress")


# Register the frozen v1 Bingo routes around the provider-atomic state machine.
def register(router):
    # Expose the player-specific state without mutating pending recovery work.
    @router.get(r"/api/v1/games/bingo/state")
    def state(body, query):
        # Preserve the established payload and legacy player selection.
        return payload(request_player_id(body, query))

    # Buy one card and publish the funded session atomically.
    @router.post(r"/api/v1/games/bingo/cards")
    def card(body, query):
        # Validate identity, amount, and established default pattern.
        player_id = request_player_id(body, query); amount = require_amount(body.get("amount")); pattern = body.get("pattern", "line")
        # Start from an authoritative snapshot used only for response construction.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Finish any prior recoverable terminal action before a new purchase.
        resume_pending_action(player_id, state)
        # Reserve one exact purchase before any wallet mutation.
        marker = prepare_purchase(player_id, state, amount, pattern)
        # Debit/fund/publish/finalize without a stale whole-document save.
        session = settle_purchase(player_id, state, marker)
        # Preserve the established response envelope.
        return {"session": session, **payload(player_id, state)}

    # Call exactly one provider-ordered ball and settle any terminal result.
    @router.post(r"/api/v1/games/bingo/call")
    def call(body, query):
        # Resolve the established player identity.
        player_id = request_player_id(body, query)
        # Load one response snapshot before recovery and mutation.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Complete an earlier terminal action before selecting another ball.
        resume_pending_action(player_id, state)
        # Commit one ball and its private response marker atomically.
        marker = commit_calls(player_id, state, 1)
        # Settle/finalize the exact committed session without selecting again.
        session, calls, credits = settle_committed_call(player_id, state, marker)
        # Preserve the exact one-ball response fields.
        return {"session": session, "called": calls[0], "label": engine.ball_label(calls[0]), "credits": credits, **payload(player_id, state)}

    # Preserve the compatibility bounded auto-call endpoint behind one atomic callback.
    @router.post(r"/api/v1/games/bingo/auto")
    def auto(body, query):
        # Compatibility endpoint remains bounded; browser autoplay still calls /call one tick at a time.
        player_id = request_player_id(body, query)
        # Load the response snapshot and recover an earlier terminal action first.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Prevent a stale batch from overwriting an earlier committed call/reset.
        resume_pending_action(player_id, state)
        # Preserve the historical integer conversion before classifying an empty batch.
        max_calls = int(body.get("max_calls", 1))
        # Preserve the established no-op response for zero or negative compatibility batches.
        if max_calls <= 0:
            # Return no session/calls/credits without publishing a marker or selecting entropy.
            return {"session": None, "calls": [], "labels": [], "credits": [], **payload(player_id, state)}
        # Preserve the established bounded engine batch semantics.
        marker = commit_calls(player_id, state, max_calls)
        # Settle/finalize only the committed provider result.
        session, calls, credits = settle_committed_call(player_id, state, marker)
        # Preserve exact calls, labels, credits, and payload response shape.
        return {"session": session, "calls": calls, "labels": [engine.ball_label(number) for number in calls], "credits": credits, **payload(player_id, state)}

    # Reset one selected active session after exact refund or abandonment evidence.
    @router.post(r"/api/v1/games/bingo/reset")
    def reset(body, query):
        # Resolve the established player identity.
        player_id = request_player_id(body, query)
        # Load one response snapshot before recovery and reset selection.
        state = load_player_game_state(GAME_ID, player_id, engine.default_state)
        # Converge any prior terminal action before selecting the reset target.
        resume_pending_action(player_id, state)
        # Reserve the exact active session under the provider lock.
        marker = prepare_reset(player_id, state)
        # Preserve the historical no-op reset when no active session exists.
        refunds = [] if marker is None else settle_prepared_reset(player_id, state, marker)
        # Preserve the frozen reset response envelope.
        return {"refunds": refunds, **payload(player_id, state)}
