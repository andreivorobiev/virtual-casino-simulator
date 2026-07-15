"""Pure Pass Line and Don't Pass Craps rules for GitHub issue #90.

Proposed requirements: CRAPS-001, CRAPS-002, and CRAPS-003.
"""

# Import exact decimal arithmetic for JSON-number cent validation.
from decimal import Decimal

# Import public state-conflict and input-validation errors for API boundaries.
from casino.errors import ConflictError, ValidationError

# Identify every state document, ledger event, and catalog record owned by this game.
GAME_ID = "craps"
# Limit the isolated first slice to the two canonical line wagers.
BET_TYPES = ("pass_line", "dont_pass")
# Define every come-out total that establishes a point.
POINT_TOTALS = (4, 5, 6, 8, 9, 10)
# Bound only the public recent-history projection while private proof stays durable.
RECENT_ROUND_LIMIT = 20


# Build an empty player-scoped Craps state document.
def default_state() -> dict:
    # Return one actionable slot plus a private durable action/round journal.
    return {"active_round": None, "_round_journal": []}


# Validate the supported first-slice line wager identifier.
def require_bet_type(value) -> str:
    # Require one of the two stable wire identifiers without accepting labels.
    if value not in BET_TYPES:
        # Keep the diagnostic independent of localized frontend copy.
        raise ValidationError("bet_type must be pass_line or dont_pass")
    # Return the accepted wire identifier unchanged.
    return value


# Normalize a wager to the shared ledger's two-decimal precision.
def require_wager(value) -> float:
    # Accept only JSON numeric types and reject booleans and numeric strings.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        # Match the OpenAPI number type without compatibility coercion.
        raise ValidationError("wager must be a JSON number")
    # Convert the JSON number's stable string representation into exact decimal form.
    wager = Decimal(str(value))
    # Reject NaN and infinity so comparisons and ledger math remain deterministic.
    if not wager.is_finite():
        # Reuse the JSON-number error for non-finite Python test inputs.
        raise ValidationError("wager must be a JSON number")
    # Require the ledger's smallest non-zero precision.
    if wager < Decimal("0.01"):
        # Tell callers the exact minimum without real-money wording.
        raise ValidationError("wager must be at least 0.01")
    # Keep one line wager within the conservative expansion-game ceiling.
    if wager > Decimal("100000"):
        # Tell callers the exact maximum without silently clamping value.
        raise ValidationError("wager must be at most 100000")
    # Quantize once to test the OpenAPI multiple-of-one-cent rule exactly.
    quantized = wager.quantize(Decimal("0.01"))
    # Reject extra fractional precision instead of silently rounding it.
    if wager != quantized:
        # Tell callers the exact wire precision expected by ledger actions.
        raise ValidationError("wager must use at most two decimal places")
    # Return the cent-exact play-token wager in the repository's numeric shape.
    return float(quantized)


# Validate one authoritative ordered pair of six-sided dice.
def require_dice(value) -> list[int]:
    # Require a concrete pair instead of accepting arbitrary iterables.
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        # Describe the server-side roller contract used by deterministic tests.
        raise ValidationError("dice must contain exactly two values")
    # Reject booleans and non-integers before evaluating face bounds.
    if any(isinstance(face, bool) or not isinstance(face, int) for face in value):
        # Keep malformed face diagnostics stable for injected adapters.
        raise ValidationError("dice values must be integers from 1 through 6")
    # Reject impossible faces without wrapping or clamping them.
    if any(face < 1 or face > 6 for face in value):
        # Keep out-of-range diagnostics identical for either die.
        raise ValidationError("dice values must be integers from 1 through 6")
    # Return a JSON-compatible copy that preserves die order.
    return [value[0], value[1]]


# Create one pending line-wager round before any ledger movement occurs.
def create_round(player_id: str, bet_type, wager, request_id: str, *, round_id: str, created_at: str) -> dict:
    # Validate the line wager before constructing persisted state.
    normalized_type = require_bet_type(bet_type)
    # Validate and normalize the play-token wager before persistence.
    normalized_wager = require_wager(wager)
    # Return a JSON-compatible pending round ready for wager recovery.
    return {
        "round_id": round_id,  # Correlate state, actions, and ledger events.
        "start_request_id": request_id,  # Preserve the start idempotency key.
        "player_id": player_id,  # Bind the round to the resolved session player.
        "bet_type": normalized_type,  # Store the stable line wager wire id.
        "wager": normalized_wager,  # Store the single aggregate debit amount.
        "phase": "come_out",  # Begin every line wager before a point exists.
        "point": None,  # Record no point until a point total is rolled.
        "rolls": [],  # Persist every authoritative roll for retry-safe replay.
        "outcome": None,  # Leave outcome unresolved until a terminal roll.
        "wager_status": "pending",  # Let the service recover a missing debit marker.
        "settlement_status": "not_ready",  # Prevent credit before a terminal result.
        "created_at": created_at,  # Store the injected audit timestamp.
    }


# Return every canonical completed round from durable or legacy state.
def completed_rounds(state: dict) -> list[dict]:
    # Prefer the private durable journal before any legacy bounded history copy.
    candidates = [*state.get("_round_journal", []), *state.get("recent_rounds", [])]
    # Track identifiers so malformed duplicate state cannot satisfy two actions.
    seen = set()
    # Collect valid unique completed rounds in chronological order.
    items = []
    # Inspect durable journal entries before legacy compatibility entries.
    for item in candidates:
        # Ignore empty slots and malformed non-dictionary history values.
        if not isinstance(item, dict):
            # Continue to the next candidate without exposing corrupt values.
            continue
        # Read the persisted identifier used to deduplicate state.
        round_id = item.get("round_id")
        # Ignore duplicate identifiers after their first authoritative occurrence.
        if round_id in seen:
            # Continue without returning two mutable references to one round.
            continue
        # Record the identifier before publishing the round in lookup order.
        seen.add(round_id)
        # Append the unique round for action and retry searches.
        items.append(item)
    # Return the canonical unbounded completed-round journal view.
    return items


# Return every active and completed round without duplicating identifiers.
def rounds(state: dict) -> list[dict]:
    # Start with the actionable round before the durable completed journal.
    candidates = [state.get("active_round"), *completed_rounds(state)]
    # Return only concrete dictionaries from the combined canonical view.
    return [item for item in candidates if isinstance(item, dict)]


# Find a round by its stable server identifier.
def round_by_id(state: dict, round_id: str):
    # Return the first active-or-recent round with an exact identifier match.
    return next((item for item in rounds(state) if item.get("round_id") == round_id), None)


# Find one persisted roll inside a round by its action request id.
def roll_for_request(round_state: dict, request_id: str):
    # Return the first exact roll action match from persisted chronological history.
    return next((item for item in round_state.get("rolls", []) if item.get("request_id") == request_id), None)


# Find any start or roll action that already owns a request id.
def action_for_request(state: dict, request_id: str):
    # Search active state before recent history to match normal recovery priority.
    for round_state in rounds(state):
        # Recognize a round-start action before scanning its later rolls.
        if round_state.get("start_request_id") == request_id:
            # Return the action kind, owning round, and no roll record.
            return "start", round_state, None
        # Look for an existing roll action inside this round.
        roll = roll_for_request(round_state, request_id)
        # Return the existing roll when this id already committed dice.
        if roll is not None:
            # Return the action kind, owning round, and stable roll record.
            return "roll", round_state, roll
    # Return no action when the request id remains unused in retained state.
    return None


# Apply one authoritative roll to an active round without touching money.
def apply_roll(round_state: dict, dice, request_id: str, *, created_at: str) -> dict:
    # Replay an already-persisted roll without consuming a new random result.
    existing = roll_for_request(round_state, request_id)
    # Return the exact prior action when the request id is repeated.
    if existing is not None:
        # Preserve engine-level idempotency for direct focused tests.
        return existing
    # Reject new roll actions after a terminal result.
    if round_state.get("phase") == "settled":
        # Keep stale client actions distinct from unknown-round lookups.
        raise ConflictError("This Craps round is already settled")
    # Reject malformed persisted phases instead of guessing game progress.
    if round_state.get("phase") not in ("come_out", "point"):
        # Surface corrupted or stale state as a safe conflict.
        raise ConflictError("This Craps round cannot be rolled in its current phase")
    # Validate the injected server-authoritative dice pair.
    normalized_dice = require_dice(dice)
    # Sum the two ordered faces once for all rule decisions.
    total = sum(normalized_dice)
    # Preserve the prior point in the public roll audit record.
    point_before = round_state.get("point")
    # Start with the point unchanged unless the come-out roll establishes it.
    point_after = point_before
    # Start with no terminal outcome for point-establishing or continuing rolls.
    outcome = None
    # Resolve the come-out table before point-phase comparisons.
    if round_state["phase"] == "come_out":
        # Resolve seven or eleven as a Pass natural and Don't Pass loss.
        if total in (7, 11):
            # Apply the mirrored line-wager outcome without duplicating rules.
            outcome = "win" if round_state["bet_type"] == "pass_line" else "loss"
            # Publish the stable natural resolution key for localization.
            resolution = "natural"
        # Resolve two or three as Pass craps and a Don't Pass win.
        elif total in (2, 3):
            # Apply the mirrored line-wager outcome for two or three.
            outcome = "loss" if round_state["bet_type"] == "pass_line" else "win"
            # Publish the stable craps resolution key for localization.
            resolution = "craps"
        # Resolve twelve as a Pass loss and the Don't Pass bar push.
        elif total == 12:
            # Preserve the standard bar-twelve refund only for Don't Pass.
            outcome = "loss" if round_state["bet_type"] == "pass_line" else "push"
            # Publish the distinct refund-capable resolution key.
            resolution = "bar_twelve"
        # Establish the rolled point for every remaining legal total.
        else:
            # Store the new point used by every later roll in this round.
            point_after = total
            # Move the round into point play without settling the wager.
            round_state["phase"] = "point"
            # Publish the point transition for accessible frontend status copy.
            resolution = "point_established"
    # Resolve an existing point through a hit, seven-out, or continuing roll.
    else:
        # Resolve the round when the shooter repeats the established point.
        if total == point_before:
            # Pay Pass and defeat Don't Pass on a point hit.
            outcome = "win" if round_state["bet_type"] == "pass_line" else "loss"
            # Publish the point-hit resolution key.
            resolution = "point_hit"
        # Resolve the round when seven appears before the point.
        elif total == 7:
            # Defeat Pass and pay Don't Pass on a seven-out.
            outcome = "loss" if round_state["bet_type"] == "pass_line" else "win"
            # Publish the seven-out resolution key.
            resolution = "seven_out"
        # Keep the point active for every other total.
        else:
            # Publish a stable non-terminal resolution key.
            resolution = "no_decision"
    # Build the immutable-by-convention public roll record.
    roll = {
        "request_id": request_id,  # Store the per-roll idempotency key.
        "roll_index": len(round_state["rolls"]) + 1,  # Use one-based display order.
        "dice": normalized_dice,  # Persist authoritative ordered die faces.
        "total": total,  # Persist the visible summed result.
        "point_before": point_before,  # Show the rule context before the roll.
        "point_after": point_after,  # Show the resulting point context.
        "resolution": resolution,  # Expose a localization-safe rule result key.
        "created_at": created_at,  # Store the injected roll timestamp.
    }
    # Append the action before any service-level settlement credit can occur.
    round_state["rolls"].append(roll)
    # Persist the resulting point for reload-safe continuation or history.
    round_state["point"] = point_after
    # Complete terminal state before the service attempts any ledger credit.
    if outcome is not None:
        # Store the player-facing terminal classification.
        round_state["outcome"] = outcome
        # Close the round against any fresh roll action.
        round_state["phase"] = "settled"
        # Require recovery credit for wins and pushes, but not losses.
        round_state["settlement_status"] = "pending" if outcome in ("win", "push") else "complete"
        # Store the terminal audit timestamp alongside the final roll.
        round_state["completed_at"] = created_at
    # Return the persisted roll record for the API response.
    return roll


# Calculate the returned play-token credit for a terminal round.
def settlement_amount(round_state: dict) -> float:
    # Return stake plus equal winnings for a winning even-money line wager.
    if round_state.get("outcome") == "win":
        # Round the two-times return to ledger precision.
        return round(float(round_state["wager"]) * 2, 2)
    # Return only the original wager for a Don't Pass bar-twelve push.
    if round_state.get("outcome") == "push":
        # Preserve the already-normalized wager precision.
        return round(float(round_state["wager"]), 2)
    # Return zero for losses and unresolved rounds.
    return 0.0


# Select the ledger transaction type for a terminal returned credit.
def settlement_transaction_type(round_state: dict):
    # Use a payout row when a line wager wins at even money.
    if round_state.get("outcome") == "win":
        # Return the game-owned payout transaction type.
        return "CRAPS_PAYOUT_CREDIT"
    # Use an explicit refund row for the Don't Pass bar-twelve push.
    if round_state.get("outcome") == "push":
        # Return the game-owned push refund transaction type.
        return "CRAPS_PUSH_REFUND"
    # Return no transaction type for losses or unresolved state.
    return None


# Move one settled round into the private durable action/round journal.
def archive_round(state: dict, round_state: dict) -> None:
    # Reject accidental archival before a terminal result exists.
    if round_state.get("phase") != "settled":
        # Keep active state intact when a caller violates lifecycle order.
        raise ConflictError("Only a settled Craps round can be archived")
    # Read the actionable slot defensively because the normal empty value is null.
    active_round = state.get("active_round")
    # Clear the actionable slot once its exact object reaches terminal state.
    if active_round and active_round.get("round_id") == round_state.get("round_id"):
        # Remove the completed round from the active slot.
        state["active_round"] = None
    # Remove any prior retry copy before appending the canonical terminal object.
    journal = [item for item in completed_rounds(state) if item.get("round_id") != round_state.get("round_id")]
    # Append the terminal round to the private unbounded action journal.
    journal.append(round_state)
    # Persist every completed action owner beyond the public history horizon.
    state["_round_journal"] = journal
    # Remove a legacy bounded copy after migrating it into the durable journal.
    state.pop("recent_rounds", None)


# Copy one round into a JSON-safe public response object.
def public_round(round_state):
    # Preserve the null active-round slot without constructing a placeholder.
    if round_state is None:
        # Return JSON null for no active game.
        return None
    # Copy only public fields so cached ledger proof never leaks through game state.
    public = {key: value for key, value in round_state.items() if not key.startswith("_") and key != "rolls"}
    # Copy nested roll and dice collections so response consumers cannot mutate state.
    public["rolls"] = [{**roll, "dice": list(roll["dice"])} for roll in round_state.get("rolls", [])]
    # Return the sanitized detached round payload.
    return public


# Build the exact public reload-safe state payload.
def public_state(state: dict) -> dict:
    # Slice the durable journal only at the public presentation boundary.
    recent = completed_rounds(state)[-RECENT_ROUND_LIMIT:]
    # Return only active and recent rounds required by the additive contract.
    return {
        "active_round": public_round(state.get("active_round")),  # Sanitize actionable state.
        "recent_rounds": [public_round(item) for item in recent],  # Sanitize bounded public history.
    }
