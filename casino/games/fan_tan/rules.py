"""Immutable Fan-Tan rules profile for the isolated issue #137 slice."""

# Store the stable game id used in state, ledger, and contract payloads.
GAME_ID = "fan_tan"
# Store the public residue outcomes in table order.
RESIDUES = ("1", "2", "3", "4")
# Store the minimum counted pile size for the local simulator profile.
MIN_PILE_COUNT = 49
# Store the maximum counted pile size for the local simulator profile.
MAX_PILE_COUNT = 80
# Store the net odds for a correct residue pick after stake has been debited.
NET_ODDS = 3


# Return transparent outcome metadata for state responses and UI paytables.
def outcome_catalog() -> list[dict]:
    # Build one row per possible leftover count after repeated groups of four.
    return [{"id": residue, "residue": int(residue), "net_odds": NET_ODDS, "return_multiplier": NET_ODDS + 1} for residue in RESIDUES]


# Return player-facing rules metadata without requiring client-side rule inference.
def rules_summary() -> dict:
    # Publish the frozen profile that makes Fan-Tan countable as its own module.
    return {"profile": "counted-pile-modulo-four", "pile_min": MIN_PILE_COUNT, "pile_max": MAX_PILE_COUNT, "group_size": 4, "residues": list(RESIDUES), "net_odds": NET_ODDS}
