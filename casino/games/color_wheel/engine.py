# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Pure Color Wheel rules for the shared settlement core: entropy, bet validation, and resolution. (#152)

These are the only game-specific pieces the shared exactly-once core needs. Every function is pure and
deterministic given its inputs, so the core can settle a round, replay a retry, and recover from
committed ledger proof without ever re-drawing entropy.
"""

# Import the immutable segment layout, payout table, and bounds.
from casino.games.color_wheel import rules
# Import the standard bounded validation error.
from casino.errors import ValidationError


# Draw the authoritative landed segment from the injected random function.
def entropy(randbelow) -> dict:
    # Choose one of the twenty fixed segments uniformly at random.
    index = randbelow(len(rules.SEGMENTS))
    # Return the landed index and its colour so the resolver never recomputes randomness.
    return {"segment": index, "color": rules.SEGMENTS[index]}


# Validate and normalize a caller bet into an authoritative wager, its total stake, and a fingerprint.
def validate_bet(request: dict) -> tuple:
    # Read the chosen colour.
    color = str((request or {}).get("color", "")).strip().lower()
    # Reject a colour that is not a payable bet.
    if color not in rules.PAYOUTS:
        # Fail closed on an unknown colour.
        raise ValidationError("color must be red, black, green, or gold")
    # Read the stake as a bounded positive integer.
    stake = (request or {}).get("stake")
    # Reject a non-integer, non-positive, or out-of-range stake before any wallet movement.
    if not isinstance(stake, int) or isinstance(stake, bool) or stake <= 0 or stake > rules.MAX_STAKE:
        # Fail closed on a malformed stake.
        raise ValidationError("stake must be a positive integer within the table limit")
    # Return the authoritative wager, its total, and a stable content fingerprint for retry safety.
    return {"color": color, "stake": stake}, float(stake), f"{color}:{stake}"


# Resolve the deterministic settlement from the committed wager and committed entropy.
def resolve(wager: dict, entropy_value: dict) -> dict:
    # A winning bet matches the landed segment colour.
    if entropy_value["color"] == wager["color"]:
        # Return the winning total, which is the stake times the colour multiplier.
        return {"outcome": "win", "total_return": wager["stake"] * rules.PAYOUTS[wager["color"]], "detail": {"segment": entropy_value["segment"], "color": entropy_value["color"]}}
    # A losing bet returns nothing.
    return {"outcome": "lose", "total_return": 0, "detail": {"segment": entropy_value["segment"], "color": entropy_value["color"]}}
