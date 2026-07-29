"""Deterministic two-card Hi-Lo rules for GitHub issue #85.

Requirements used: CARD-001, LEDGER-005, LEDGER-006, and LEDGER-023.
"""

# Import hashing so one authenticated action always derives the same round id.
import hashlib
# Import finite-number checks for ledger-compatible wager validation.
import math

# Import shared card normalization and deterministic shuffle primitives from #96.
from casino.core.cards import RANKS, coerce_card, shuffled_deck
# Import public conflict and validation errors for game-rule boundaries.
from casino.errors import ConflictError, ValidationError

# Identify every state document, API payload, and ledger event owned by this game.
GAME_ID = "hi_lo"
# Offer the two player decisions represented by the Hi-Lo name.
GUESSES = ("higher", "lower")
# Compare cards by rank only with ace high and suits ignored.
RANK_VALUES = {rank: value for value, rank in enumerate(RANKS, start=2)}
# Bound reload-safe history so one player document cannot grow without limit.
RECENT_ROUND_LIMIT = 20
# Target total-return house edge held uniformly across every visible current-card rank. (issue #406)
HOUSE_EDGE = 0.035
# Three cards of the current rank remain unseen, so a stake-refunding tie occurs with probability 3/51.
TIE_PROBABILITY = 3 / 51


# Probability the optimal higher/lower guess wins for a visible card of this ordering value.
def _optimal_win_probability(rank_value: int) -> float:
    # Four cards sit at every other rank; the optimal guess follows the more populated direction.
    higher = 4 * (max(RANK_VALUES.values()) - rank_value)
    # Count the lower-card branch independently so middle ranks remain symmetric.
    lower = 4 * (rank_value - min(RANK_VALUES.values()))
    # Best play always calls the larger side of the 51 unseen cards.
    return max(higher, lower) / 51


# Derive one ledger-precision total-return price from an ordered visible-card rank.
def _rank_return_multiplier(rank_value: int) -> float:
    # Subtract the refunded-tie probability before pricing the correct-call branch.
    return round((1 - HOUSE_EDGE - TIE_PROBABILITY) / _optimal_win_probability(rank_value), 2)


# Own the complete immutable rank price table at the server engine boundary.
CORRECT_PAYTABLE = {rank: _rank_return_multiplier(value) for rank, value in RANK_VALUES.items()}


# Price a correct guess from the server-owned table for the visible current card.
def correct_return_multiplier(current_card) -> float:
    """Return the authoritative total-return multiplier for ``current_card``."""
    # Normalize the card through the shared primitive before selecting its public rank key.
    rank = coerce_card(current_card).rank
    # Return the same value published to API clients in the additive paytable.
    return CORRECT_PAYTABLE[rank]


# Publish a detached rank-to-multiplier table so clients never recompute a price.
def correct_paytable() -> dict:
    # Copy the immutable engine table so callers cannot mutate settlement authority.
    return dict(CORRECT_PAYTABLE)


# Frozen-v1 compatibility scalar retained for legacy even-money clients; superseded by correct_paytable(). (issue #406)
CORRECT_RETURN_MULTIPLIER = 2
# Refund the wager on an equal-rank tie; unchanged by the rank pricing.
TIE_RETURN_MULTIPLIER = 1


# Build one fresh player-scoped state document.
def default_state() -> dict:
    # Return one actionable slot, bounded history, and compact durable action receipts.
    return {"active_round": None, "recent_rounds": [], "action_receipts": {}}


# Normalize one positive play-token wager before cards or state are created.
def normalize_wager(value) -> float:
    # Reject booleans because Python otherwise treats them as numeric values.
    if isinstance(value, bool):
        # Keep malformed wagers outside the shared ledger.
        raise ValidationError("Hi-Lo wager must be a positive play-token amount")
    # Convert supported numeric input into ledger precision.
    try:
        # Round to the shared ledger's two-decimal representation.
        wager = round(float(value), 2)
    # Translate missing or malformed values into the public validation shape.
    except (TypeError, ValueError):
        # Avoid echoing untrusted input in the error message.
        raise ValidationError("Hi-Lo wager must be a positive play-token amount") from None
    # Reject zero, negative, non-finite, and overlarge ledger amounts.
    if wager < 0.01 or wager > 100_000 or not math.isfinite(wager):
        # Report the accepted range without changing shared ledger rules.
        raise ValidationError("Hi-Lo wager must be between 0.01 and 100000 play tokens")
    # Return the normalized amount used by state and ledger fingerprints.
    return wager


# Normalize one higher-or-lower decision.
def normalize_guess(value) -> str:
    # Accept only strings so mappings and numeric aliases cannot become decisions.
    guess = value.strip().lower() if isinstance(value, str) else ""
    # Reject any decision outside the two documented actions.
    if guess not in GUESSES:
        # Keep the stable diagnostic suitable for the additive API contract.
        raise ValidationError("guess must be higher or lower")
    # Return the canonical lower-case decision.
    return guess


# Derive one stable server round id from the authenticated player and deal action.
def round_id_for(player_id: str, action_id: str) -> str:
    # Hash the namespaced identity so hostile characters never enter a route path.
    digest = hashlib.sha256(f"{GAME_ID}:{player_id}:{action_id}".encode("utf-8")).hexdigest()
    # Retain enough digest material for collision-resistant local simulator ids.
    return f"hilo_{digest[:24]}"


# Deal the visible opening card and one private next card without replacement.
def deal_pair(*, seed=None) -> tuple[str, str]:
    # Use the shared secure shuffle in production and deterministic seed in tests.
    cards = shuffled_deck(seed=seed)
    # Return encoding-safe compact codes while preserving shuffled deal order.
    return cards[0].code, cards[1].code


# Build one prepared round that can survive reload before its wager debit commits.
def create_round(player_id: str, wager, start_action_id: str, *, current_card: str, next_card: str, round_id: str, created_at: str, request_fingerprint: str) -> dict:
    # Normalize the wager again at the pure engine boundary.
    amount = normalize_wager(wager)
    # Validate both persisted card codes through the shared primitive.
    visible_card = coerce_card(current_card).code
    # Validate the private next card independently.
    hidden_card = coerce_card(next_card).code
    # Prevent an impossible duplicate physical card from entering state.
    if visible_card == hidden_card:
        # Fail closed rather than representing a replacement draw.
        raise ValidationError("Hi-Lo cards must be dealt without replacement")
    # Return JSON-compatible prepared state with the next card kept private.
    return {
        "round_id": round_id,  # Correlate state, routes, and ledger movements.
        "player_id": player_id,  # Bind the round to the authenticated player.
        "start_action_id": start_action_id,  # Preserve deal retry identity.
        "request_fingerprint": request_fingerprint,  # Detect conflicting retries.
        "wager": amount,  # Store the single round wager.
        "phase": "choose",  # Await one higher-or-lower decision.
        "current_card": visible_card,  # Expose the card the player evaluates.
        "_next_card": hidden_card,  # Persist but never publish the reveal card.
        "guess": None,  # Reserve stable state for the later decision.
        "guess_action_id": None,  # Reserve settlement retry identity.
        "outcome": None,  # Reserve the final correct, tie, or incorrect result.
        "payout": 0.0,  # Reserve the total returned play tokens.
        "net": None,  # Reserve the final net result.
        "wager_status": "pending",  # Require the service to ensure one debit.
        "settlement_status": "not_ready",  # Prevent credits before a guess.
        "created_at": created_at,  # Record the injected audit timestamp.
    }


# Compare the next rank with the visible current rank while ignoring suits.
def compare_cards(current_card, next_card) -> int:
    # Resolve the normalized current rank value.
    current_value = RANK_VALUES[coerce_card(current_card).rank]
    # Resolve the normalized next rank value.
    next_value = RANK_VALUES[coerce_card(next_card).rank]
    # Return negative, zero, or positive ordering without suit tie breakers.
    return (next_value > current_value) - (next_value < current_value)


# Reveal and settle one prepared round without touching a player balance.
def settle_round(round_state: dict, guess, guess_action_id: str, *, completed_at: str, request_fingerprint: str) -> dict:
    # Normalize the requested decision before mutating round state.
    normalized_guess = normalize_guess(guess)
    # Treat an exact repeated engine call as an idempotent read.
    if round_state.get("phase") == "settled":
        # Reject a changed decision or action identity after settlement.
        if round_state.get("guess") != normalized_guess or round_state.get("guess_action_id") != guess_action_id:
            # Preserve the original terminal result.
            raise ConflictError("Hi-Lo round was already settled by another action")
        # Return the existing result without revealing or calculating again.
        return round_state
    # Require the only actionable choice phase.
    if round_state.get("phase") != "choose":
        # Reject corrupt or stale transitions explicitly.
        raise ConflictError("Hi-Lo round cannot accept a guess in its current phase")
    # Read the private reveal card persisted with the prepared wager.
    next_card = round_state.get("_next_card")
    # Reject missing private state instead of generating a replacement result.
    if not next_card:
        # Keep deterministic reload behavior fail-closed.
        raise ConflictError("Hi-Lo reveal card is unavailable")
    # Compare rank-only ordering under the documented ace-high rules.
    comparison = compare_cards(round_state["current_card"], next_card)
    # Determine whether the selected direction matches the revealed ordering.
    correct = (normalized_guess == "higher" and comparison > 0) or (normalized_guess == "lower" and comparison < 0)
    # Classify equal ranks as a refund regardless of suits.
    outcome = "tie" if comparison == 0 else "correct" if correct else "incorrect"
    # Return stake plus the rank-priced winnings for a correct prediction; a tie refunds the wager.
    payout = round(round_state["wager"] * correct_return_multiplier(round_state["current_card"]), 2) if outcome == "correct" else round_state["wager"] if outcome == "tie" else 0.0
    # Store the canonical player decision.
    round_state["guess"] = normalized_guess
    # Store the settlement action identity for safe retries.
    round_state["guess_action_id"] = guess_action_id
    # Store the semantic fingerprint that detects conflicting retries.
    round_state["guess_fingerprint"] = request_fingerprint
    # Publish the formerly private next card only after the decision.
    round_state["next_card"] = coerce_card(next_card).code
    # Remove private state so settled documents contain one card representation.
    round_state.pop("_next_card", None)
    # Store the player-facing result classification.
    round_state["outcome"] = outcome
    # Store the total returned play-token amount.
    round_state["payout"] = payout
    # Store net movement after the original wager.
    round_state["net"] = round(payout - round_state["wager"], 2)
    # Mark deterministic card evaluation complete before ledger settlement.
    round_state["phase"] = "settled"
    # Require one credit only for correct predictions and refunds.
    round_state["settlement_status"] = "pending" if payout else "complete"
    # Record the injected completion time for stable tests and history.
    round_state["completed_at"] = completed_at
    # Return the same mutable round for service persistence.
    return round_state


# Find one round by its deal action identity across active and recent state.
def round_for_start_action(state: dict, action_id: str):
    # Search the active slot before bounded settled history.
    candidates = [state.get("active_round"), *state.get("recent_rounds", [])]
    # Return the first exact identity match while ignoring empty slots.
    return next((item for item in candidates if item and item.get("start_action_id") == action_id), None)


# Find one round by its server identifier across active and recent state.
def round_by_id(state: dict, round_id: str):
    # Search the active slot before bounded settled history.
    candidates = [state.get("active_round"), *state.get("recent_rounds", [])]
    # Return the first matching round while ignoring empty slots.
    return next((item for item in candidates if item and item.get("round_id") == round_id), None)


# Find whether an action identity already belongs to any retained command.
def action_owner(state: dict, action_id: str):
    # Search every active and retained round for either action stage.
    candidates = [state.get("active_round"), *state.get("recent_rounds", [])]
    # Return the matching round and stage for conflict detection.
    for item in candidates:
        # Skip empty active slots.
        if not item:
            # Continue to the next retained round.
            continue
        # Match the deal action before the optional guess action.
        if item.get("start_action_id") == action_id:
            # Report the deal stage and owning round.
            return item, "deal"
        # Match a committed or prepared guess action.
        if item.get("guess_action_id") == action_id:
            # Report the guess stage and owning round.
            return item, "guess"
    # Return no owner when the action id remains unused in retained state.
    return None


# Move a settled round into bounded reload-safe history.
def archive_round(state: dict, round_state: dict) -> None:
    # Normalize the optional active slot before reading its identifier.
    active_round = state.get("active_round") or {}
    # Clear the actionable slot only when it contains this exact round.
    if active_round.get("round_id") == round_state.get("round_id"):
        # Prevent further decisions against the settled round.
        state["active_round"] = None
    # Remove any older copy before appending an idempotent settlement.
    recent = [item for item in state.get("recent_rounds", []) if item.get("round_id") != round_state.get("round_id")]
    # Append the newest settled result in stable chronological order.
    recent.append(round_state)
    # Retain only the bounded newest rounds.
    state["recent_rounds"] = recent[-RECENT_ROUND_LIMIT:]


# Remove private recovery fields from one public round payload.
def public_round(round_state):
    # Preserve a null active-round slot without creating a placeholder.
    if round_state is None:
        # Return JSON null through the router.
        return None
    # Exclude the hidden card and internal fingerprints from public responses.
    private_fields = {"_next_card", "request_fingerprint", "guess_fingerprint"}
    # Return a detached shallow payload containing only public state.
    return {key: value for key, value in round_state.items() if key not in private_fields}


# Build one sanitized player-scoped state snapshot.
def public_state(state: dict) -> dict:
    # Return active and recent state while preserving storage schema metadata.
    return {
        "active_round": public_round(state.get("active_round")),  # Hide the private reveal card.
        "recent_rounds": [public_round(item) for item in state.get("recent_rounds", [])],  # Sanitize history.
        **({"schema_version": state["schema_version"]} if "schema_version" in state else {}),  # Preserve storage metadata.
    }
