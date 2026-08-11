# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Pure Scratch Cards rules, deterministic ticket generation, and public-state masking."""

# Import decimal arithmetic so play-token prizes avoid binary floating-point drift.
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
# Import hashing so player-scoped card and request identities remain deterministic.
import hashlib
# Import JSON normalization so equivalent requests share one conflict fingerprint.
import json

# Import project-standard domain errors for invalid or conflicting actions.
from casino.errors import ConflictError, ValidationError

# Store the catalog identity shared by state, ledger, API, and frontend metadata.
GAME_ID = "scratch_cards"
# Store the two-decimal precision used by the shared play-token ledger.
TOKEN_QUANTUM = Decimal("0.01")
# Publish the deliberately small wager menu used by both API metadata and the UI.
WAGER_OPTIONS = (1.0, 2.0, 5.0, 10.0)
# Store exact decimal counterparts so public values cannot round into an allowed wager.
WAGER_DECIMALS = tuple(Decimal(str(value)) for value in WAGER_OPTIONS)
# Fix one card at a responsive three-by-three prize grid.
CELL_COUNT = 9
# Require exactly three equal prize cells for a winning card.
MATCH_COUNT = 3
# Bound settled history so reload payloads remain responsive.
HISTORY_LIMIT = 20
# Define the prize multipliers used to construct unique match-three boards.
PRIZE_MULTIPLIERS = (1, 2, 5, 10, 25)
# Define cumulative outcome thresholds for an explicit 82-percent toy return profile.
OUTCOME_THRESHOLDS = ((70, 0), (88, 1), (95, 2), (98, 5), (99, 10), (100, 25))


# Normalize one public wager into an approved play-token option.
def normalize_wager(value) -> float:
    # Reject booleans and non-numeric JSON shapes before decimal conversion.
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        # Keep the runtime aligned with the OpenAPI numeric wager contract.
        raise ValidationError("Scratch Card wager must be an available play-token option")
    # Convert through text so JSON numbers and Decimal fixtures normalize identically.
    try:
        # Parse the exact submitted decimal before applying any ledger formatting.
        raw_amount = Decimal(str(value))
    # Convert malformed or unsupported numeric inputs into the project error envelope.
    except (InvalidOperation, TypeError, ValueError):
        # Surface one stable wager diagnostic before state or ledger access.
        raise ValidationError("Scratch Card wager must be an available play-token option")
    # Reject non-finite or unlisted wager values before they can round into an approved option.
    if not raw_amount.is_finite() or raw_amount not in WAGER_DECIMALS:
        # Report accepted values without real-money framing.
        raise ValidationError("Scratch Card wager must be one of 1, 2, 5, or 10 play tokens")
    # Quantize the already-approved exact amount to the shared ledger precision.
    amount = raw_amount.quantize(TOKEN_QUANTUM, rounding=ROUND_HALF_UP)
    # Return the ledger-compatible normalized amount.
    return float(amount)


# Build a canonical purchase fingerprint that detects conflicting request reuse.
def purchase_fingerprint(wager: float) -> str:
    # Serialize normalized content predictably before hashing the request meaning.
    canonical = json.dumps({"wager": wager}, sort_keys=True, separators=(",", ":"))
    # Return a full SHA-256 digest suitable for private ledger details.
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# Derive one stable card id from the authenticated player and purchase action.
def card_id_for(player_id: str, client_request_id: str) -> str:
    # Hash both identities so raw private text never appears in the public card id.
    digest = hashlib.sha256(f"{player_id}\0{client_request_id}".encode("utf-8")).hexdigest()[:24]
    # Prefix the digest for readable Scratch Card state and ledger rows.
    return f"scr_{digest}"


# Validate one bounded action identifier used for safe network retries.
def normalize_action_id(value, field_name: str) -> str:
    # Normalize only string identifiers while preserving caller-visible casing.
    action_id = value.strip() if isinstance(value, str) else ""
    # Reject empty, oversized, whitespace, or control-character identities.
    if not action_id or action_id != value or len(action_id) > 128 or any(character.isspace() or ord(character) < 33 for character in action_id):
        # Name the public field so clients can repair the request safely.
        raise ValidationError(f"{field_name} must be a non-empty string of at most 128 visible characters")
    # Return the bounded identity without transforming its meaning.
    return action_id


# Validate and canonicalize one non-empty set of grid positions.
def normalize_positions(value) -> list[int]:
    # Require one JSON array so ambiguous scalar scratching is impossible.
    if not isinstance(value, list) or not value:
        # Reject empty actions before loading private card state.
        raise ValidationError("positions must be a non-empty array of Scratch Card cell indexes")
    # Collect validated positions in caller order for predictable presentation.
    positions = []
    # Validate every supplied grid position independently.
    for position in value:
        # Reject booleans, non-integers, and indexes outside the nine-cell card.
        if isinstance(position, bool) or not isinstance(position, int) or not 0 <= position < CELL_COUNT:
            # Surface the exact accepted zero-based range.
            raise ValidationError("Scratch Card positions must be integers from 0 through 8")
        # Reject duplicates instead of silently changing the action fingerprint.
        if position in positions:
            # Require callers to express each scratched cell once.
            raise ValidationError("Scratch Card positions must be unique")
        # Preserve the validated position for canonical sorting.
        positions.append(position)
    # Return stable ascending positions for idempotency comparisons.
    return sorted(positions)


# Build a canonical scratch fingerprint for one card and position set.
def scratch_fingerprint(card_id: str, positions: list[int]) -> str:
    # Serialize card identity and normalized positions without insertion-order ambiguity.
    canonical = json.dumps({"card_id": card_id, "positions": positions}, sort_keys=True, separators=(",", ":"))
    # Return a full SHA-256 digest for state replay records and settlement details.
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# Draw one validated bounded integer through the injected production or test source.
def draw_index(randbelow, upper_bound: int) -> int:
    # Require an injectable callable so focused tests never depend on ambient randomness.
    if not callable(randbelow):
        # Surface a programmer-facing integration error for a broken entropy seam.
        raise TypeError("randbelow must be callable")
    # Invoke the source exactly once for this bounded selection.
    index = randbelow(upper_bound)
    # Reject booleans and out-of-range values instead of wrapping or biasing results.
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < upper_bound:
        # Surface the violated entropy adapter contract.
        raise ValueError("randbelow returned an invalid Scratch Card index")
    # Return the validated zero-based selection.
    return index


# Resolve the winning multiplier for one explicit zero-through-ninety-nine roll.
def multiplier_for_roll(roll: int) -> int:
    # Reject invalid persisted or injected outcomes before prize construction.
    if isinstance(roll, bool) or not isinstance(roll, int) or not 0 <= roll < 100:
        # Surface corrupt outcome data explicitly.
        raise ValueError("Scratch Card outcome roll must be an integer from 0 through 99")
    # Inspect cumulative thresholds in documented order.
    for threshold, multiplier in OUTCOME_THRESHOLDS:
        # Return the first outcome whose cumulative range contains the roll.
        if roll < threshold:
            # Publish zero for a non-winning card or the matching prize multiplier.
            return multiplier
    # Guard against malformed profile constants even though the final threshold is one hundred.
    raise RuntimeError("Scratch Card outcome profile does not cover every roll")


# Shuffle one prize template through deterministic Fisher-Yates selections.
def shuffled(values: list[int], randbelow) -> list[int]:
    # Copy the template so callers and module constants are never mutated.
    result = list(values)
    # Walk backward so every permutation is reachable through uniform selections.
    for upper_index in range(len(result) - 1, 0, -1):
        # Draw one swap position from the remaining inclusive prefix.
        swap_index = draw_index(randbelow, upper_index + 1)
        # Swap the current cell with the injected deterministic selection.
        result[upper_index], result[swap_index] = result[swap_index], result[upper_index]
    # Return the independently shuffled prize multipliers.
    return result


# Generate one complete private ticket through an injected bounded entropy source.
def generate_ticket(wager: float, randbelow) -> dict:
    # Normalize wager again so direct engine callers receive the same protection as the service.
    normalized_wager = normalize_wager(wager)
    # Select the documented outcome bucket before constructing any visible prize cells.
    outcome_roll = draw_index(randbelow, 100)
    # Resolve zero for a losing board or the exact three-match multiplier.
    winning_multiplier = multiplier_for_roll(outcome_roll)
    # Branch when the board must contain no three matching prizes.
    if winning_multiplier == 0:
        # Use pairs plus three singles so no prize appears three times.
        template = [1, 1, 2, 2, 5, 5, 10, 10, 25]
    # Build a winning board with exactly one three-of-a-kind prize.
    else:
        # Select three distinct filler multipliers that exclude the winning prize.
        fillers = [multiplier for multiplier in PRIZE_MULTIPLIERS if multiplier != winning_multiplier][:3]
        # Combine the winning triple with three harmless filler pairs.
        template = [winning_multiplier] * MATCH_COUNT + [multiplier for multiplier in fillers for _ in range(2)]
    # Shuffle the private template so outcome position never identifies the result tier.
    prize_multipliers = shuffled(template, randbelow)
    # Convert every multiplier into a two-decimal play-token prize amount.
    prizes = [float((Decimal(str(normalized_wager)) * Decimal(multiplier)).quantize(TOKEN_QUANTUM)) for multiplier in prize_multipliers]
    # Calculate zero for a loss or the single matched prize for a win.
    payout = float((Decimal(str(normalized_wager)) * Decimal(winning_multiplier)).quantize(TOKEN_QUANTUM)) if winning_multiplier else 0.0
    # Return private ticket data that the service must persist and sanitize before exposure.
    return {"outcome_roll": outcome_roll, "winning_multiplier": winning_multiplier, "prize_multipliers": prize_multipliers, "prizes": prizes, "payout": payout}


# Build a fresh player-owned Scratch Cards state document.
def default_state() -> dict:
    # Keep one current card plus bounded settled history for reload and recent-result views.
    return {"game": GAME_ID, "current_card": None, "recent_cards": []}


# Find one player-owned card across current and bounded recent state.
def find_card(state: dict, card_id: str) -> dict | None:
    # Read the current card first because normal actions target it.
    current_card = state.get("current_card")
    # Return the current card when its stable identity matches.
    if current_card and current_card.get("card_id") == card_id:
        # Preserve object identity so the service can update its private state copy.
        return current_card
    # Search recent settled cards newest-first for retry-safe response recovery.
    return next((card for card in reversed(state.get("recent_cards", [])) if card.get("card_id") == card_id), None)


# Find a card created by one purchase retry identity.
def find_purchase(state: dict, client_request_id: str) -> dict | None:
    # Read the current card before scanning older settled history.
    current_card = state.get("current_card")
    # Return the current card when its private purchase identity matches.
    if current_card and current_card.get("client_request_id") == client_request_id:
        # Preserve object identity for conflict checks and public response recovery.
        return current_card
    # Search retained cards newest-first for late network retries.
    return next((card for card in reversed(state.get("recent_cards", [])) if card.get("client_request_id") == client_request_id), None)


# Move a settled current card into bounded history before the next purchase.
def archive_current(state: dict) -> None:
    # Read the current card once before deciding whether it can be archived.
    current_card = state.get("current_card")
    # Stop when there is no prior card to retain.
    if not current_card:
        # Leave the existing bounded history unchanged.
        return
    # Reject replacing an unfinished card because its wager and hidden prizes remain actionable.
    if current_card.get("status") != "settled":
        # Require the player to finish the current card before buying another.
        raise ConflictError("Finish the current Scratch Card before buying another")
    # Append the complete private record so late action retries remain detectable.
    state.setdefault("recent_cards", []).append(current_card)
    # Retain only the newest bounded set for responsive state payloads.
    state["recent_cards"] = state["recent_cards"][-HISTORY_LIMIT:]
    # Clear the current slot for the new purchase.
    state["current_card"] = None


# Convert one private card into a masked public response.
def public_card(card: dict | None) -> dict | None:
    # Preserve the explicit empty current-card state.
    if not card:
        # Return null through the JSON envelope rather than an invented placeholder.
        return None
    # Normalize persisted revealed positions into a fast membership set.
    revealed_positions = {int(position) for position in card.get("revealed_positions", [])}
    # Read private prize values without copying them into covered cell payloads.
    prizes = list(card.get("prizes", []))
    # Collect sanitized cells in stable board order.
    cells = []
    # Build exactly nine public cell records.
    for position in range(CELL_COUNT):
        # Identify whether this cell may expose its server-owned prize.
        is_revealed = position in revealed_positions
        # Start with only position and reveal state so covered values cannot leak.
        cell = {"position": position, "revealed": is_revealed}
        # Add the prize only after this exact position was scratched.
        if is_revealed:
            # Copy the normalized play-token prize into the visible cell.
            cell["prize"] = prizes[position]
        # Add the sanitized cell to the public grid.
        cells.append(cell)
    # Build fields safe for ready, partial, settling, and settled responses.
    result = {"card_id": card["card_id"], "status": card.get("status", "ready"), "wager": card["wager"], "cells": cells, "revealed_count": len(revealed_positions), "cell_count": CELL_COUNT, "purchased_at": card["purchased_at"]}
    # Publish the bounded retry identity only while recovering a crash-interrupted purchase.
    if card.get("status") == "purchasing":
        # Let a reload replay the exact debit action without exposing any covered value.
        result["pending_client_request_id"] = card.get("client_request_id")
    # Publish replay information needed to resume a crash-interrupted final scratch.
    if card.get("status") == "settling":
        # Expose only the bounded action identity, never hidden prize or fingerprint data.
        result["pending_action_id"] = card.get("completion_action_id")
        # Expose the already-authorized positions so the frontend can replay the identical action.
        result["pending_positions"] = list(card.get("completion_positions", []))
    # Publish settlement values only after every prize cell has been revealed.
    if card.get("status") == "settled":
        # Report the credited prize or zero for a non-winning card.
        result["payout"] = card.get("payout", 0.0)
        # Report net play-token change for user-facing history.
        result["net"] = round(float(card.get("payout", 0.0)) - float(card.get("wager", 0.0)), 2)
        # Translate only this stable machine outcome key in the frontend.
        result["outcome"] = "win" if float(card.get("payout", 0.0)) > 0 else "no_win"
        # Preserve the stable settlement time for reload and recent history.
        result["settled_at"] = card.get("settled_at")
    # Return the sanitized card without entropy, fingerprints, action history, or unrevealed prizes.
    return result


# Convert one complete private state document into the public API shape.
def public_state(state: dict) -> dict:
    # Sanitize every retained card independently so private fields never cross the API boundary.
    recent_cards = [public_card(card) for card in state.get("recent_cards", [])]
    # Return immutable rules metadata beside the masked player-owned state.
    return {"game": GAME_ID, "current_card": public_card(state.get("current_card")), "recent_cards": recent_cards, "wager_options": list(WAGER_OPTIONS), "rules": {"cell_count": CELL_COUNT, "match_count": MATCH_COUNT}}
