# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Big Six Wheel rules for the explicit 54-segment simulator profile."""

# Import an immutable mapping wrapper so callers cannot change the paytable at runtime.
from types import MappingProxyType

# Store the catalog id used by API, ledger, state, and frontend integration.
GAME_ID = "big_six_wheel"
# Preserve the regulator-defined clockwise 54-segment order as immutable game data.
WHEEL_SEGMENTS = (
    "joker", "one", "two", "one", "five", "two", "one", "ten", "one", "five", "one", "two", "one", "twenty",  # Preserve regulated clockwise positions 0 through 13.
    "one", "two", "one", "five", "two", "one", "ten", "one", "two", "five", "one", "two", "one", "crest",  # Preserve regulated clockwise positions 14 through 27.
    "two", "five", "two", "one", "two", "one", "ten", "one", "five", "one", "two", "one", "twenty", "one",  # Preserve regulated clockwise positions 28 through 41.
    "two", "one", "five", "two", "one", "ten", "one", "two", "five", "one", "two", "one",  # Preserve regulated clockwise positions 42 through 53.
)
# Keep betting controls in a stable low-to-high order followed by the two unique symbols.
OUTCOME_ORDER = ("one", "two", "five", "ten", "twenty", "joker", "crest")
# Freeze net payout odds for the selected Pennsylvania/Maryland-style profile.
NET_ODDS = MappingProxyType({"one": 1, "two": 2, "five": 5, "ten": 10, "twenty": 20, "joker": 45, "crest": 45})
# Freeze expected segment counts so tests detect accidental wheel drift.
SEGMENT_COUNTS = MappingProxyType({"one": 23, "two": 15, "five": 8, "ten": 4, "twenty": 2, "joker": 1, "crest": 1})


# Return additive API metadata without exposing mutable rule constants.
def outcome_catalog() -> list[dict]:
    # Build one fresh row per legal wager target for safe response serialization.
    return [
        # Describe one outcome through stable machine keys and numeric rule data.
        {"id": outcome, "segment_count": SEGMENT_COUNTS[outcome], "net_odds": NET_ODDS[outcome]}
        # Preserve the documented control ordering in every API response.
        for outcome in OUTCOME_ORDER
    ]
