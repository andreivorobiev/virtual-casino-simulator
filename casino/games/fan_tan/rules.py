"""Immutable Fan-Tan rules profile for the isolated issue #137 slice."""

# Store the stable game id used in state, ledger, and contract payloads.
GAME_ID = "fan_tan"
# Store the public residue outcomes in table order.
RESIDUES = ("1", "2", "3", "4")
# Store the minimum counted pile size for the local simulator profile.
MIN_PILE_COUNT = 49
# Store the maximum counted pile size for the local simulator profile.
MAX_PILE_COUNT = 80
# Store the gross net odds a correct residue pick pays before the house commission is applied.
NET_ODDS = 3
# Store the configurable house commission retained on Fan-Tan winnings only; the original stake always returns in full. (issue #256)
WIN_COMMISSION = 0.05


# Compute the commission-adjusted disclosure values once so settlement, state responses, and paytables stay consistent. (issue #256)
def commission_profile() -> dict:
    # Derive the effective net win odds after the house commission on winnings.
    net_win_odds = round(NET_ODDS * (1 - WIN_COMMISSION), 2)
    # Derive the effective total return multiplier: the returned stake plus the commission-adjusted winnings.
    return_multiplier = round(1 + net_win_odds, 2)
    # Render the commission rate as a clean whole percent when possible for player-facing disclosure.
    raw_pct = round(WIN_COMMISSION * 100, 2)
    # Prefer an integer percent so the paytable reads "5%" rather than "5.0%".
    win_commission_pct = int(raw_pct) if float(raw_pct).is_integer() else raw_pct
    # Return every value the UI and settlement paths need to disclose the commission consistently.
    return {"net_odds": NET_ODDS, "win_commission": WIN_COMMISSION, "win_commission_pct": win_commission_pct, "net_win_odds": net_win_odds, "return_multiplier": return_multiplier}


# Return transparent outcome metadata for state responses and UI paytables.
def outcome_catalog() -> list[dict]:
    # Resolve the shared commission-adjusted disclosure values for every residue row.
    profile = commission_profile()
    # Build one row per possible leftover count after repeated groups of four, carrying the commission disclosure.
    return [{"id": residue, "residue": int(residue), **profile} for residue in RESIDUES]


# Return player-facing rules metadata without requiring client-side rule inference.
def rules_summary() -> dict:
    # Publish the frozen profile that makes Fan-Tan countable as its own module, including the house commission.
    return {"profile": "counted-pile-modulo-four", "pile_min": MIN_PILE_COUNT, "pile_max": MAX_PILE_COUNT, "group_size": 4, "residues": list(RESIDUES), **commission_profile()}
