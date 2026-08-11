# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-discovered long-suite driver for Teen Patti Practice against the real backend. (#150)"""


# Exercise one complete deal, its replay, one decision, and its replay.
def play(client, index):
    # Build one stable deal action identity for this long-suite iteration.
    deal_action = f"long-teen-patti-deal-{index}"
    # Deal a one-token ante round.
    started = client.call("/api/v1/games/teen-patti/rounds", "POST", {"action_id": deal_action, "ante": 1})
    # Replay the deal to prove the ante debit is not duplicated.
    deal_replay = client.call("/api/v1/games/teen-patti/rounds", "POST", {"action_id": deal_action, "ante": 1})
    # Require the deal replay to report the recovered round.
    assert deal_replay["replayed"] is True and deal_replay["round"]["round_id"] == started["round"]["round_id"], "Teen Patti deal replay changed the round"
    # Require the dealer cards to stay private before the showdown.
    assert "dealer_cards" not in started["round"] and len(started["round"]["player_cards"]) == 3, "Teen Patti exposed dealer cards before the showdown"
    # Read the deterministic round id for the decision route.
    round_id = started["round"]["round_id"]
    # Play the round.
    settled = client.call(f"/api/v1/games/teen-patti/rounds/{round_id}/decisions", "POST", {"action_id": f"long-teen-patti-play-{index}", "decision": "play"})
    # Require the settled round to reveal the dealer and reach a terminal outcome.
    assert settled["round"]["outcome"] in ("player_win", "dealer_win", "push", "dealer_not_qualified") and "dealer_hand" in settled["round"], "Teen Patti did not settle the played round"
    # Replay the decision to prove exactly-once settlement.
    replay = client.call(f"/api/v1/games/teen-patti/rounds/{round_id}/decisions", "POST", {"action_id": f"long-teen-patti-play-{index}", "decision": "play"})
    # Require the decision replay to return the identical settled result.
    assert replay["replayed"] is True and replay["round"]["net"] == settled["round"]["net"], "Teen Patti decision replay changed the result"
