"""Immutable two-dice Over/Under 7 rules for GitHub issue #135."""

# Import an immutable mapping wrapper so paytable constants cannot be changed at runtime.
from types import MappingProxyType

# Store the catalog id used by state, API, ledger, and the parked descriptor proposal.
GAME_ID = "over_under_7"
# Keep wager targets in the player-facing order used by controls and paytable rows.
OUTCOME_ORDER = ("under", "seven", "over")
# Freeze net payout odds for the explicit simulator profile.
NET_ODDS = MappingProxyType({"under": 1, "seven": 4, "over": 1})
# Freeze transparent winning totals for each proposition.
WINNING_TOTALS = MappingProxyType({"under": (2, 3, 4, 5, 6), "seven": (7,), "over": (8, 9, 10, 11, 12)})


# Return a fresh API-safe paytable for this rules profile.
def paytable() -> list[dict]:
    # Build one row per wager target with total-return and probability disclosure.
    return [
        # Describe the wager target without exposing mutable constants.
        {"id": outcome, "winning_totals": list(WINNING_TOTALS[outcome]), "net_odds": NET_ODDS[outcome], "total_return_multiplier": NET_ODDS[outcome] + 1}
        # Preserve the stable control order in every response.
        for outcome in OUTCOME_ORDER
    ]
