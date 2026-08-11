# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Pure standard-8d Dragon Tiger rules and persistent state transitions.

Proposed requirements: DT-001 through DT-005.
"""

# Import counting support so replacement shoes are proven to contain eight standard decks.
from collections import Counter
# Import decimal arithmetic so token settlement uses stable two-decimal rounding.
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
# Import hashing for deterministic round IDs and request fingerprints.
import hashlib
# Import canonical JSON encoding for semantic request fingerprints.
import json
# Import finite-number checks for public wager validation.
import math

# Reuse the shared #96 card and shuffle primitives.
from casino.core.cards import coerce_card, create_deck, shuffled_deck
# Import public errors for invalid requests and corrupt persisted state.
from casino.errors import ConflictError, ValidationError

# Identify state and ledger records owned by this game.
GAME_ID = "dragon_tiger"
# Name the fixed rules profile exposed by the API.
PROFILE_ID = "standard-8d"
# Define the standard eight-deck shoe without jokers.
DECK_COUNT = 8
# Burn three cards whenever a new shoe is installed.
BURN_CARDS = 3
# Stop dealing before the final fifty-two reserved cards.
CUT_RESERVE_CARDS = 52
# Require two cards beyond the reserve for another round.
ROUND_CARDS = 2
# Bound reload-safe round history.
RECENT_ROUND_LIMIT = 50
# Quantize wagers to ledger precision.
TOKEN_QUANTUM = Decimal("0.01")
# Bound one public wager conservatively.
MAX_WAGER = Decimal("1000000.00")
# Accept only the three standard main bets.
BET_ORDER = ("dragon", "tiger", "tie")
# Rank cards ace-low through king-high while ignoring suits.
RANK_VALUES = {"A": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10, "J": 11, "Q": 12, "K": 13}


# Build the player-scoped document used by the shared state store.
def default_state() -> dict:
    # Return only JSON-compatible persistent values.
    return {
        "profile": PROFILE_ID,  # Mark the immutable rules profile.
        "shoe": [],  # Persist private undealt compact card codes.
        "shoe_number": 0,  # Count installed shoes.
        "burned_cards": [],  # Retain the latest private burn.
        "prepared_actions": {},  # Persist results before ledger movement.
        "prepared_order": [],  # Recover actions in creation order.
        "settled_actions": {},  # Retain durable retry proof beyond visible history.
        "recent_rounds": [],  # Retain bounded settled rounds.
    }


# Expose immutable profile rules without private shoe order.
def rules_payload() -> dict:
    # Return a detached API-compatible rules object.
    return {
        "profile": PROFILE_ID,  # Name the rules profile.
        "deck_count": DECK_COUNT,  # Report the eight-deck shoe.
        "burn_count": BURN_CARDS,  # Report the new-shoe burn count.
        "cut_cards": CUT_RESERVE_CARDS,  # Report the undealt reserve.
        "bets": {  # Group the three fixed main-bet settlement rules.
            "dragon": {"net_odds": 1, "tie_return": 0.5},  # Pay 1:1 and return half on ties.
            "tiger": {"net_odds": 1, "tie_return": 0.5},  # Pay 1:1 and return half on ties.
            "tie": {"net_odds": 11, "tie_return": 0},  # Pay 11:1 only on matching ties.
        },
    }


# Validate a public main-bet identifier.
def normalize_bet(value) -> str:
    # Accept only the contract's exact lowercase enum without silent coercion.
    bet = value if isinstance(value, str) else ""
    # Reject missing or unsupported bets before state mutation.
    if bet not in BET_ORDER:
        # Report the fixed allowed vocabulary.
        raise ValidationError("Dragon Tiger bet must be dragon, tiger, or tie")
    # Return the canonical identifier.
    return bet


# Validate one positive wager at ledger precision.
def normalize_wager(value) -> float:
    # Reject booleans and strings because the contract requires a JSON number.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        # Surface a stable public validation error.
        raise ValidationError("Dragon Tiger wager must be a positive play-token amount")
    # Convert a JSON number through text for deterministic decimal behavior.
    try:
        # Preserve the exact supplied decimal before ledger-precision validation.
        raw_amount = Decimal(str(value))
        # Quantize half-up to two decimal places.
        amount = raw_amount.quantize(TOKEN_QUANTUM, rounding=ROUND_HALF_UP)
    # Translate malformed values to the public error boundary.
    except (InvalidOperation, TypeError, ValueError):
        # Avoid leaking decimal implementation errors.
        raise ValidationError("Dragon Tiger wager must be a positive play-token amount") from None
    # Reject non-finite, non-positive, and oversized wagers.
    if not math.isfinite(float(amount)) or raw_amount != amount or amount <= 0 or amount > MAX_WAGER:
        # Keep invalid amounts out of state and ledger calls.
        raise ValidationError("Dragon Tiger wager must be between 0.01 and 1000000 play tokens")
    # Return a JSON-compatible normalized number.
    return float(amount)


# Build a semantic digest for conflicting action-ID detection.
def request_fingerprint(bet: str, wager: float) -> str:
    # Encode normalized fields with a fixed decimal representation.
    canonical = json.dumps({"bet": bet, "wager": f"{wager:.2f}"}, sort_keys=True, separators=(",", ":"))
    # Return a full SHA-256 proof.
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# Derive a bounded stable round ID from player and action identities.
def round_id_for(player_id: str, action_id: str) -> str:
    # Separate identities unambiguously before hashing.
    digest = hashlib.sha256(f"{player_id}\0{action_id}".encode("utf-8")).hexdigest()[:24]
    # Prefix the digest for readable diagnostics.
    return f"dt_{digest}"


# Create one production standard-8d shuffled shoe.
def standard_shoe() -> list[str]:
    # Return compact card codes from the shared shuffle primitive.
    return [card.code for card in shuffled_deck(decks=DECK_COUNT)]


# Validate and install an injected or production shoe.
def replace_shoe(state: dict, shoe_factory=standard_shoe) -> None:
    # Require a callable deterministic seam.
    if not callable(shoe_factory):
        # Reject invalid wiring before state mutation.
        raise TypeError("shoe_factory must be callable")
    # Build the candidate independently from state.
    raw_cards = shoe_factory()
    # Require a concrete sequence rather than an accidental string.
    if not isinstance(raw_cards, (list, tuple)):
        # Treat invalid internal shoe data as a conflict.
        raise ConflictError("Dragon Tiger shoe factory did not return a card sequence")
    # Normalize every card through #96.
    try:
        # Detach compact codes from the caller fixture.
        shoe = [coerce_card(card).code for card in raw_cards]
    # Translate malformed cards into a stable conflict.
    except ValueError:
        # Avoid leaking arbitrary card input.
        raise ConflictError("Dragon Tiger shoe contains an invalid card") from None
    # Build the expected eight-deck multiset.
    expected = Counter(card.code for card in create_deck(DECK_COUNT))
    # Reject incomplete, joker-bearing, or duplicate-heavy shoes.
    if len(shoe) != DECK_COUNT * 52 or Counter(shoe) != expected:
        # Keep the named profile truthful under test seams.
        raise ConflictError("Dragon Tiger standard-8d shoe must contain eight complete decks")
    # Burn from the same stack end used for dealing.
    burned = [shoe.pop() for _ in range(BURN_CARDS)]
    # Install the validated private shoe.
    state["shoe"] = shoe
    # Increment the public shoe counter.
    state["shoe_number"] = int(state.get("shoe_number", 0)) + 1
    # Persist private burn identities for reload consistency.
    state["burned_cards"] = burned


# Report whether the next round must use a replacement shoe.
def shuffle_pending(state: dict) -> bool:
    # Require the reserve plus both next cards before dealing.
    return len(state.get("shoe", [])) < CUT_RESERVE_CARDS + ROUND_CARDS


# Compare Dragon and Tiger by rank only with ace low.
def winner_for(dragon_card, tiger_card) -> str:
    # Normalize the Dragon card through the shared primitive.
    dragon = coerce_card(dragon_card)
    # Normalize the Tiger card symmetrically.
    tiger = coerce_card(tiger_card)
    # Read the game-owned ace-low rank values.
    dragon_value = RANK_VALUES[dragon.rank]
    # Read Tiger rank without suit information.
    tiger_value = RANK_VALUES[tiger.rank]
    # Return Dragon when its rank is higher.
    if dragon_value > tiger_value:
        # Preserve the public winner vocabulary.
        return "dragon"
    # Return Tiger when its rank is higher.
    if tiger_value > dragon_value:
        # Preserve the public winner vocabulary.
        return "tiger"
    # Equal ranks tie regardless of suit.
    return "tie"


# Calculate returned stake plus winnings for one main bet.
def settle(bet: str, wager: float, winner: str) -> dict:
    # Normalize the selected main bet.
    normalized_bet = normalize_bet(bet)
    # Normalize wager precision before applying odds.
    normalized_wager = normalize_wager(wager)
    # Restore an exact two-decimal value before any settlement arithmetic.
    wager_amount = Decimal(f"{normalized_wager:.2f}")
    # Reject impossible persisted winners.
    if winner not in BET_ORDER:
        # Fail closed on corrupt internal result data.
        raise ConflictError("Dragon Tiger winner is invalid")
    # Pay stake plus 1:1 winnings on matching Dragon/Tiger.
    if normalized_bet == winner and winner in {"dragon", "tiger"}:
        # Calculate the complete credit.
        total_return = wager_amount * Decimal("2")
        # Mark the player-facing result.
        outcome = "win"
    # Pay stake plus 11:1 winnings on matching Tie.
    elif normalized_bet == "tie" and winner == "tie":
        # Calculate the twelve-times total credit.
        total_return = wager_amount * Decimal("12")
        # Mark the player-facing result.
        outcome = "win"
    # Return half a Dragon/Tiger wager on tied ranks.
    elif normalized_bet in {"dragon", "tiger"} and winner == "tie":
        # Credit half the committed wager.
        total_return = (wager_amount * Decimal("0.5")).quantize(TOKEN_QUANTUM, rounding=ROUND_HALF_UP)
        # Distinguish the standard half-loss.
        outcome = "half_loss"
    # Lose the full wager for all other results.
    else:
        # Avoid a zero-value ledger credit.
        total_return = Decimal("0.00")
        # Mark the player-facing loss.
        outcome = "loss"
    # Calculate net relative to the prior debit.
    net = (total_return - wager_amount).quantize(TOKEN_QUANTUM, rounding=ROUND_HALF_UP)
    # Return the complete settlement calculation.
    return {"outcome": outcome, "total_return": float(total_return), "net": float(net)}


# Prepare one deterministic round before ledger movement.
def prepare_action(state: dict, *, player_id: str, action_id: str, bet: str, wager: float, fingerprint: str, round_id: str, created_at: str, shoe_factory=standard_shoe) -> dict:
    # Replace the shoe at the reserve boundary.
    if shuffle_pending(state):
        # Validate, install, and burn a new standard shoe.
        replace_shoe(state, shoe_factory)
    # Deal Dragon first from the private stack.
    dragon_card = state["shoe"].pop()
    # Deal Tiger second from the same shoe.
    tiger_card = state["shoe"].pop()
    # Compare ranks under the named profile.
    winner = winner_for(dragon_card, tiger_card)
    # Calculate the single-bet settlement.
    result = settle(bet, wager, winner)
    # Build private state persisted before ledger calls.
    prepared = {
        "round_id": round_id,  # Correlate state and ledger.
        "action_id": action_id,  # Preserve retry identity.
        "request_fingerprint": fingerprint,  # Detect conflicting reuse.
        "player_id": player_id,  # Bind the authenticated owner.
        "status": "prepared",  # Await ledger reconciliation.
        "bet": bet,  # Preserve normalized bet.
        "wager": wager,  # Preserve normalized debit.
        "dragon_card": dragon_card,  # Store first compact card.
        "tiger_card": tiger_card,  # Store second compact card.
        "winner": winner,  # Store rank-only result.
        "outcome": result["outcome"],  # Store settlement class.
        "total_return": result["total_return"],  # Store credit amount.
        "net": result["net"],  # Store net result.
        "created_at": created_at,  # Store injected timing.
        "shoe_number": int(state["shoe_number"]),  # Link the shoe.
    }
    # Store by action identity for reload-safe lookup.
    state.setdefault("prepared_actions", {})[action_id] = prepared
    # Avoid duplicating recovery order entries.
    if action_id not in state.setdefault("prepared_order", []):
        # Append only a newly prepared action.
        state["prepared_order"].append(action_id)
    # Return the state-owned prepared record.
    return prepared


# Rebuild prepared state from immutable wager ledger details.
def prepared_from_ledger(*, player_id: str, action_id: str, fingerprint: str, round_id: str, details: dict, fallback_created_at: str) -> dict:
    # Require a game-authored details object.
    if not isinstance(details, dict):
        # Reject malformed recovery proof.
        raise ConflictError("Dragon Tiger wager ledger details are unavailable")
    # Verify stable request identities before trusting result data.
    if details.get("action_id") != action_id or details.get("request_fingerprint") != fingerprint:
        # Fail closed on conflicting historic proof.
        raise ConflictError("Dragon Tiger action_id was already used with different round settings")
    # Normalize committed request fields.
    bet = normalize_bet(details.get("bet"))
    # Normalize the committed wager.
    wager = normalize_wager(details.get("wager"))
    # Normalize committed card codes.
    try:
        # Restore the first dealt card.
        dragon_card = coerce_card(details.get("dragon_card")).code
        # Restore the second dealt card.
        tiger_card = coerce_card(details.get("tiger_card")).code
    # Translate malformed historic cards to a conflict.
    except ValueError:
        # Avoid producing a second result.
        raise ConflictError("Dragon Tiger wager ledger cards are invalid") from None
    # Recalculate winner and settlement under fixed rules.
    winner = winner_for(dragon_card, tiger_card)
    # Recalculate payout values rather than trusting duplicates.
    result = settle(bet, wager, winner)
    # Return a complete private action for reconciliation.
    return {
        "round_id": round_id,  # Retain stable round identity.
        "action_id": action_id,  # Retain client identity.
        "request_fingerprint": fingerprint,  # Retain conflict proof.
        "player_id": player_id,  # Bind recovery owner.
        "status": "prepared",  # Continue reconciliation.
        "bet": bet,  # Restore selected bet.
        "wager": wager,  # Restore debit amount.
        "dragon_card": dragon_card,  # Restore Dragon card.
        "tiger_card": tiger_card,  # Restore Tiger card.
        "winner": winner,  # Restore calculated winner.
        "outcome": result["outcome"],  # Restore outcome.
        "total_return": result["total_return"],  # Restore credit.
        "net": result["net"],  # Restore net.
        "created_at": details.get("created_at") or fallback_created_at,  # Restore timing.
        "shoe_number": int(details.get("shoe_number", 0)),  # Restore shoe number.
    }


# Convert private prepared state into the exact public round contract.
def settled_round(prepared: dict, settled_at: str) -> dict:
    # Return no fingerprint, shoe order, or ledger internals.
    return {
        "round_id": prepared["round_id"],  # Expose server identity.
        "action_id": prepared["action_id"],  # Expose retry identity.
        "player_id": prepared["player_id"],  # Expose authenticated owner.
        "status": "settled",  # Report terminal state.
        "bet": prepared["bet"],  # Report selected main bet.
        "wager": prepared["wager"],  # Report committed amount.
        "dragon_card": prepared["dragon_card"],  # Report first compact code.
        "tiger_card": prepared["tiger_card"],  # Report second compact code.
        "winner": prepared["winner"],  # Report rank-only winner.
        "outcome": prepared["outcome"],  # Report win/half_loss/loss.
        "total_return": prepared["total_return"],  # Report credited amount.
        "net": prepared["net"],  # Report net result.
        "settled_at": settled_at,  # Report stable settlement timing.
        "shoe_number": prepared["shoe_number"],  # Report used shoe.
    }


# Find one durable settled action record with bounded-history compatibility.
def find_action_record(state: dict, action_id: str) -> dict | None:
    # Prefer the unbounded action-key index used by every new module state.
    record = state.get("settled_actions", {}).get(action_id)
    # Return a structurally usable durable record.
    if isinstance(record, dict) and isinstance(record.get("round"), dict):
        # Preserve stored round and ledger evidence without mutation.
        return record
    # Search visible history for compatibility with an early pre-index document.
    round_item = next((item for item in reversed(state.get("recent_rounds", [])) if item.get("action_id") == action_id), None)
    # Wrap a legacy visible round in the durable-record shape when found.
    return {"round": round_item, "ledger": {}} if round_item else None


# Find a settled retry without coupling idempotency to visible history retention.
def find_round(state: dict, action_id: str) -> dict | None:
    # Resolve the durable action record first.
    record = find_action_record(state, action_id)
    # Return its immutable public round when present.
    return record.get("round") if record else None


# Record a durable settled action, bounded visible history, and ledger proof.
def record_round(state: dict, round_item: dict, ledger_evidence: dict | None = None, *, include_recent: bool = True) -> dict:
    # Persist every action identity independently from the visible-history limit.
    state.setdefault("settled_actions", {})[round_item["action_id"]] = {"round": dict(round_item), "ledger": dict(ledger_evidence or {})}
    # Remove an older duplicate before appending recovery output.
    recent = [item for item in state.get("recent_rounds", []) if item.get("round_id") != round_item["round_id"]]
    # Append only genuinely current or persisted-preparation recovery output.
    if include_recent:
        # Preserve chronological UI order without promoting a ledger-only historical replay.
        recent.append(round_item)
    # Bound reload-safe history.
    state["recent_rounds"] = recent[-RECENT_ROUND_LIMIT:]
    # Remove the completed private action.
    state.setdefault("prepared_actions", {}).pop(round_item["action_id"], None)
    # Remove the completed recovery-order entry.
    state["prepared_order"] = [item for item in state.setdefault("prepared_order", []) if item != round_item["action_id"]]
    # Return the stable public round.
    return round_item


# Build the exact public state contract.
def public_state(state: dict) -> dict:
    # Return shoe summary and detached bounded history.
    return {
        "shoe": {  # Summarize the private persistent shoe without revealing cards.
            "shoe_number": int(state.get("shoe_number", 0)),  # Report zero before first play.
            "cards_remaining": len(state.get("shoe", [])),  # Hide actual order.
            "shuffle_pending": shuffle_pending(state),  # Explain next-round shuffle.
        },
        "recent_rounds": [dict(item) for item in state.get("recent_rounds", [])],  # Detach history.
    }
