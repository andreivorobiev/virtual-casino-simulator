"""Deterministic Andar Bahar rules for GitHub issue #140.

Requirements used before permanent IDs: CARD-001, CARD-002, LEDGER-001,
LEDGER-005, LEDGER-006, SESSION-001, and API-001.
"""

# Import hashing so stable action identities derive stable round ids.
import hashlib
# Import finite-number checks for ledger-compatible wager validation.
import math

# Import shared card primitives allocated by issue #96 without crossing game boundaries.
from casino.core.cards import coerce_card, shuffled_deck
# Import public conflict and validation errors for game-rule boundaries.
from casino.errors import ConflictError, ValidationError

# Identify every state document, API payload, and ledger event owned by this game.
GAME_ID = "andar_bahar"
# Preserve the two culturally standard betting sides in deterministic UI order.
SIDES = ("andar", "bahar")
# Preserve the standard deal order after the joker/match card is exposed.
DEAL_ORDER = ("andar", "bahar")
# Bound reload-safe history so one player document cannot grow indefinitely.
RECENT_ROUND_LIMIT = 20
# Retain the frozen-v1 integer scalar for clients that only understand even-money rules.
RETURN_MULTIPLIER = 2
# Price the first-dealt Andar side below even money while preserving even-money Bahar returns. (issue #409)
RETURN_MULTIPLIERS = {"andar": 1.9, "bahar": 2.0}


# Resolve the authoritative total-return multiplier for one normalized side.
def return_multiplier(side: str) -> float:
    # Reject unknown sides rather than silently applying the deprecated scalar.
    if side not in RETURN_MULTIPLIERS:
        # Keep corrupt stored or caller-controlled values outside settlement.
        raise ValidationError("Andar Bahar side must be andar or bahar")
    # Return the side-specific total return used by settlement and published rules.
    return RETURN_MULTIPLIERS[side]


# Build one fresh player-scoped state document.
def default_state() -> dict:
    # Return one active slot, bounded history, and durable action receipts.
    return {"active_round": None, "recent_rounds": [], "action_receipts": {}}


# Normalize one positive play-token wager before cards or ledger rows exist.
def normalize_wager(value) -> float:
    # Reject booleans because Python otherwise treats them as numeric values.
    if isinstance(value, bool):
        # Keep malformed wagers outside shared ledger calls.
        raise ValidationError("Andar Bahar wager must be a positive play-token amount")
    # Convert supported numeric input to the shared ledger precision.
    try:
        # Round to two decimals so fingerprints and ledger amounts match.
        wager = round(float(value), 2)
    # Translate missing or malformed values into a stable validation error.
    except (TypeError, ValueError):
        # Avoid echoing untrusted input in diagnostics.
        raise ValidationError("Andar Bahar wager must be a positive play-token amount") from None
    # Reject zero, negative, non-finite, and overlarge local-simulator amounts.
    if wager < 0.01 or wager > 100_000 or not math.isfinite(wager):
        # Report the accepted range without changing shared ledger rules.
        raise ValidationError("Andar Bahar wager must be between 0.01 and 100000 play tokens")
    # Return the normalized amount used by state and ledger fingerprints.
    return wager


# Normalize one player side selection.
def normalize_side(value) -> str:
    # Accept only strings so numeric aliases cannot become side choices.
    side = value.strip().lower() if isinstance(value, str) else ""
    # Reject decisions outside the two documented sides.
    if side not in SIDES:
        # Keep the diagnostic culturally precise and API stable.
        raise ValidationError("side must be andar or bahar")
    # Return the canonical lower-case side.
    return side


# Derive one stable server round id from authenticated player and deal action.
def round_id_for(player_id: str, action_id: str) -> str:
    # Hash the namespaced identity so hostile characters never enter route paths.
    digest = hashlib.sha256(f"{GAME_ID}:{player_id}:{action_id}".encode("utf-8")).hexdigest()
    # Retain enough digest material for collision-resistant local simulator ids.
    return f"andar_bahar_{digest[:24]}"


# Deal a full Andar Bahar round from one shuffled deck.
def deal_sequence(*, seed=None) -> tuple[str, list[dict]]:
    # Use the shared secure shuffle in production and deterministic seed in tests.
    deck = shuffled_deck(seed=seed)
    # Expose the first card as the joker or match card in traditional terminology.
    match_card = deck[0]
    # Prepare an alternating reveal sequence that starts with Andar.
    dealt = []
    # Walk the remaining deck until the first rank match determines the outcome.
    for index, card in enumerate(deck[1:]):
        # Alternate Andar, Bahar, Andar, Bahar through the public reveal sequence.
        side = DEAL_ORDER[index % len(DEAL_ORDER)]
        # Store compact card codes and side names in JSON-compatible form.
        dealt.append({"side": side, "card": card.code, "matched": card.rank == match_card.rank})
        # Stop immediately when a side receives the first matching rank.
        if card.rank == match_card.rank:
            # Return the exposed match card and transparent sequence.
            return match_card.code, dealt
    # A standard deck must always find the three remaining rank matches.
    raise ConflictError("Andar Bahar deck ended before a matching rank appeared")


# Build one complete round whose cards are known before the ledger debit commits.
def create_round(player_id: str, wager, side, action_id: str, *, match_card: str, dealt_cards: list[dict], round_id: str, created_at: str, request_fingerprint: str) -> dict:
    # Normalize the wager again at the pure engine boundary.
    amount = normalize_wager(wager)
    # Normalize the selected side again at the pure engine boundary.
    selected_side = normalize_side(side)
    # Validate the exposed match card through the shared primitive.
    normalized_match = coerce_card(match_card).code
    # Require at least one dealt card so an outcome can exist.
    if not dealt_cards:
        # Fail closed rather than representing an impossible round.
        raise ValidationError("Andar Bahar requires a dealt sequence")
    # Normalize every dealt reveal while preserving side order.
    normalized_dealt = [normalize_dealt_card(item) for item in dealt_cards]
    # Read the terminal matching reveal from the deterministic sequence.
    terminal = normalized_dealt[-1]
    # Verify the terminal card actually matches the exposed rank.
    if coerce_card(terminal["card"]).rank != coerce_card(normalized_match).rank:
        # Reject corrupt injected fixtures that do not settle by match rank.
        raise ValidationError("Andar Bahar sequence must end on the first matching rank")
    # Store the side that first received the matching rank.
    winning_side = terminal["side"]
    # Calculate total returned play tokens from the selected side's authoritative price.
    payout = round(amount * return_multiplier(selected_side), 2) if selected_side == winning_side else 0.0
    # Return one complete but settlement-pending state document.
    return {
        "round_id": round_id,  # Correlate state, routes, and ledger movements.
        "player_id": player_id,  # Bind the round to the authenticated player.
        "action_id": action_id,  # Preserve retry identity for the atomic play.
        "request_fingerprint": request_fingerprint,  # Detect conflicting retries.
        "wager": amount,  # Store the single round wager.
        "selected_side": selected_side,  # Store the player's Andar/Bahar prediction.
        "phase": "settled",  # Publish a complete fast-table result after the action.
        "match_card": normalized_match,  # Publish the joker or match card.
        "dealt_cards": normalized_dealt,  # Publish the transparent alternating sequence.
        "winning_side": winning_side,  # Publish the first matching side.
        "outcome": "win" if payout else "loss",  # Publish the player-facing result.
        "payout": payout,  # Store total returned play tokens.
        "net": round(payout - amount, 2),  # Store net movement after the wager.
        "wager_status": "pending",  # Require the service to ensure one debit.
        "settlement_status": "pending" if payout else "complete",  # Require one credit only on wins.
        "created_at": created_at,  # Record the injected audit timestamp.
        "completed_at": created_at,  # Atomic play settles in the same service action.
    }


# Normalize one dealt reveal from fixtures, storage, or deterministic dealing.
def normalize_dealt_card(item: dict) -> dict:
    # Require a mapping so list positions cannot silently become cards.
    if not isinstance(item, dict):
        # Keep malformed fixtures outside persisted state.
        raise ValidationError("Andar Bahar dealt cards must be objects")
    # Normalize the side using the public side validator.
    side = normalize_side(item.get("side"))
    # Normalize the compact card code through the shared card primitive.
    card = coerce_card(item.get("card")).code
    # Preserve the match marker as an explicit boolean.
    matched = bool(item.get("matched"))
    # Return a detached JSON-compatible reveal row.
    return {"side": side, "card": card, "matched": matched}


# Validate that the dealt sequence alternates sides and ends at the first match.
def validate_sequence(match_card: str, dealt_cards: list[dict]) -> None:
    # Resolve the match rank once through the shared primitive.
    match_rank = coerce_card(match_card).rank
    # Track whether a match has already appeared.
    seen_match = False
    # Inspect every reveal in public order.
    for index, item in enumerate(dealt_cards):
        # Require the documented alternating side order.
        if item["side"] != DEAL_ORDER[index % len(DEAL_ORDER)]:
            # Fail closed when fixture or stored state breaks table order.
            raise ValidationError("Andar Bahar cards must alternate Andar then Bahar")
        # Calculate the rank-match fact from the card rather than trusting input.
        rank_matches = coerce_card(item["card"]).rank == match_rank
        # Require persisted match flags to match the actual rank.
        if item["matched"] != rank_matches:
            # Fail closed on inconsistent state.
            raise ValidationError("Andar Bahar match marker does not match card rank")
        # Reject any extra cards after the first rank match.
        if seen_match:
            # Keep the public sequence to exactly the resolving deal.
            raise ValidationError("Andar Bahar sequence must stop at the first match")
        # Remember when the terminal match appears.
        seen_match = rank_matches
    # Require one terminal match in the finite round.
    if not seen_match:
        # Fail closed rather than representing an unresolved atomic play.
        raise ValidationError("Andar Bahar sequence must include a matching rank")


# Build one round from a deterministic seed or injected fixture cards.
def play_round(player_id: str, wager, side, action_id: str, *, round_id: str, created_at: str, request_fingerprint: str, seed=None, fixture=None) -> dict:
    # Use an explicit fixture only in focused deterministic tests.
    if fixture is not None:
        # Read the fixture's exposed match card.
        match_card = fixture["match_card"]
        # Read the fixture's transparent alternating sequence.
        dealt_cards = fixture["dealt_cards"]
    # Otherwise deal through the shared card primitive.
    else:
        # Produce one deterministic or production shuffled sequence.
        match_card, dealt_cards = deal_sequence(seed=seed)
    # Build the complete settled round without touching a player balance.
    round_state = create_round(player_id, wager, side, action_id, match_card=match_card, dealt_cards=dealt_cards, round_id=round_id, created_at=created_at, request_fingerprint=request_fingerprint)
    # Verify order, match markers, and terminal behavior before returning state.
    validate_sequence(round_state["match_card"], round_state["dealt_cards"])
    # Return the deterministic round state to the service layer.
    return round_state


# Find one round by its play action identity across active and recent state.
def round_for_action(state: dict, action_id: str):
    # Search the active slot before bounded settled history.
    candidates = [state.get("active_round"), *state.get("recent_rounds", [])]
    # Return the first exact identity match while ignoring empty slots.
    return next((item for item in candidates if item and item.get("action_id") == action_id), None)


# Move a settled round into bounded reload-safe history.
def archive_round(state: dict, round_state: dict) -> None:
    # Clear the active slot when it contains this exact round.
    if (state.get("active_round") or {}).get("round_id") == round_state.get("round_id"):
        # Prevent stale active state after atomic settlement.
        state["active_round"] = None
    # Remove any older copy before appending an idempotent replay.
    recent = [item for item in state.get("recent_rounds", []) if item.get("round_id") != round_state.get("round_id")]
    # Append the newest settled result in stable chronological order.
    recent.append(round_state)
    # Retain only the bounded newest rounds.
    state["recent_rounds"] = recent[-RECENT_ROUND_LIMIT:]


# Remove internal fingerprints from one public round payload.
def public_round(round_state):
    # Preserve a null slot without creating a placeholder.
    if round_state is None:
        # Return JSON null through the router.
        return None
    # Exclude internal semantic retry fingerprints from public responses.
    private_fields = {"request_fingerprint"}
    # Return a detached shallow payload containing only public state.
    return {key: value for key, value in round_state.items() if key not in private_fields}


# Build one sanitized player-scoped state snapshot.
def public_state(state: dict) -> dict:
    # Return active and recent state while preserving optional storage schema metadata.
    return {
        "active_round": public_round(state.get("active_round")),  # Hide internal retry fields.
        "recent_rounds": [public_round(item) for item in state.get("recent_rounds", [])],  # Sanitize history.
        **({"schema_version": state["schema_version"]} if "schema_version" in state else {}),  # Preserve metadata.
    }
