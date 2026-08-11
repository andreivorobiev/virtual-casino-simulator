# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Immutable 50-position Sic Bo rules and payout metadata for issue #88."""

# Import pair generation for the fifteen distinct two-die combinations.
from itertools import combinations
# Import an immutable mapping wrapper so callers cannot alter the paytable.
from types import MappingProxyType

# Identify every state document, route payload, and ledger event owned by the game.
GAME_ID = "sic_bo"
# Preserve the regulator-listed net odds for totals from four through seventeen.
TOTAL_NET_ODDS = MappingProxyType({4: 50, 5: 18, 6: 14, 7: 12, 8: 8, 9: 6, 10: 6, 11: 6, 12: 6, 13: 8, 14: 12, 15: 14, 16: 18, 17: 50})
# Preserve the fixed net odds for non-total wager families.
FIXED_NET_ODDS = MappingProxyType({"small": 1, "big": 1, "double": 8, "triple": 150, "any_triple": 24, "combo": 5})
# Keep groups in the same stable order used by API responses and the browser board.
GROUP_ORDER = ("ranges", "totals", "singles", "doubles", "triples", "combinations")


# Build one fresh metadata row without exposing mutable rule constants.
def _bet(bet_id: str, group: str, kind: str, *, selection=None, values=None, net_odds=None, variable_odds=None) -> dict:
    # Start with stable identifiers shared by engine, API, and frontend localization.
    row = {"id": bet_id, "group": group, "kind": kind}
    # Include a single numeric selection only for total and repeated-face wagers.
    if selection is not None:
        # Store the selected total or die face as an integer.
        row["selection"] = selection
    # Include both distinct die values only for combination wagers.
    if values is not None:
        # Copy the pair into a JSON-compatible list.
        row["values"] = list(values)
    # Include fixed odds when one winning multiplier applies to the position.
    if net_odds is not None:
        # Store net odds using the regulator's "to 1" convention.
        row["net_odds"] = net_odds
    # Include occurrence-based odds for a single-number wager.
    if variable_odds is not None:
        # Copy the occurrence map so callers cannot change shared rule data.
        row["variable_odds"] = dict(variable_odds)
    # Return the complete immutable-by-convention metadata row.
    return row


# Return all fifty legal betting positions in stable table order.
def bet_catalog() -> list[dict]:
    # Start with the two even-money range positions that lose on every triple.
    rows = [
        _bet("small", "ranges", "small", net_odds=FIXED_NET_ODDS["small"]),  # Cover non-triple totals four through ten.
        _bet("big", "ranges", "big", net_odds=FIXED_NET_ODDS["big"]),  # Cover non-triple totals eleven through seventeen.
    ]
    # Add all fourteen exact-total positions from four through seventeen.
    rows.extend(_bet(f"total:{total}", "totals", "total", selection=total, net_odds=TOTAL_NET_ODDS[total]) for total in range(4, 18))
    # Add all six occurrence-counted single-number positions.
    rows.extend(_bet(f"single:{face}", "singles", "single", selection=face, variable_odds={1: 1, 2: 2, 3: 3}) for face in range(1, 7))
    # Add all six specific-double positions.
    rows.extend(_bet(f"double:{face}", "doubles", "double", selection=face, net_odds=FIXED_NET_ODDS["double"]) for face in range(1, 7))
    # Add all six specific-triple positions before the any-triple position.
    rows.extend(_bet(f"triple:{face}", "triples", "triple", selection=face, net_odds=FIXED_NET_ODDS["triple"]) for face in range(1, 7))
    # Add the position that covers any of the six possible triples.
    rows.append(_bet("any_triple", "triples", "any_triple", net_odds=FIXED_NET_ODDS["any_triple"]))
    # Add all fifteen unordered combinations of two distinct faces.
    rows.extend(_bet(f"combo:{left}:{right}", "combinations", "combo", values=(left, right), net_odds=FIXED_NET_ODDS["combo"]) for left, right in combinations(range(1, 7), 2))
    # Return fresh rows so response consumers cannot alter later calls.
    return rows


# Freeze the legal bet identifiers in their canonical response order.
BET_IDS = tuple(row["id"] for row in bet_catalog())
# Freeze fast membership checks without creating another rules source.
BET_ID_SET = frozenset(BET_IDS)
