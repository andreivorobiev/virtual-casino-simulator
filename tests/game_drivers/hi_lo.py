# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-discoverable long-suite driver for GitHub issue #85."""


# Complete one low-cost Hi-Lo round through public session-bound actions.
def play(client, index):
    # Use a fractional wager so the Long Suite proves ledger-precision rank-price rounding.
    wager = 1.37
    # Build a unique idempotent deal identity for this long-suite iteration.
    deal_action_id = f"long-hi-lo-deal-{index}"
    # Deal one opening card and commit one play-token wager.
    started = client.call("/api/v1/games/hi-lo/rounds", "POST", {"action_id": deal_action_id, "wager": wager})
    # Read the stable server round id for the decision route.
    round_id = started["round"]["round_id"]
    # Read the complete authoritative rank table from the server-owned rules response.
    paytable = (started.get("rules") or {}).get("correct_paytable") or {}
    # Require one price for every public rank before using the table as settlement evidence.
    assert set(paytable) == {"2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"}, "Hi-Lo rank paytable is incomplete"
    # Remove the suit suffix from the visible card to select its authoritative price.
    current_rank = started["round"]["current_card"][:-1]
    # Choose a legal direction without inspecting the private next card.
    guess = "lower" if started["round"]["current_card"].startswith("A") else "higher"
    # Build a separate idempotent settlement identity.
    guess_action_id = f"long-hi-lo-guess-{index}"
    # Reveal and settle the round through the public guess action.
    completed = client.call(f"/api/v1/games/hi-lo/rounds/{round_id}/guesses", "POST", {"action_id": guess_action_id, "guess": guess})
    # Verify the action reaches one terminal result.
    assert completed["round"]["phase"] == "settled", "Hi-Lo round did not settle"
    # Verify the next card is visible only after the decision.
    assert completed["round"].get("next_card"), "Hi-Lo did not reveal the next card"
    # Read the canonical terminal class before calculating its documented total return.
    outcome = completed["round"]["outcome"]
    # Apply the server-owned visible-rank price only to a correct prediction.
    expected_payout = round(wager * paytable[current_rank], 2) if outcome == "correct" else wager if outcome == "tie" else 0.0
    # Apply the shared ledger precision to the published net movement.
    expected_net = round(expected_payout - wager, 2)
    # Require Long Suite settlement to match both authoritative price and rounding.
    assert completed["round"]["payout"] == expected_payout and completed["round"]["net"] == expected_net, "Hi-Lo settlement does not match the published rank price"
    # Return the terminal round for optional Long Suite diagnostics.
    return completed["round"]
