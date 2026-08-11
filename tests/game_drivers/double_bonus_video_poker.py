# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-discovered long-suite driver for Double Bonus Video Poker against the real backend. (#131)"""


# Exercise one complete deal, its replay, one hold-and-draw, and its replay.
def play(client, index):
    # Build one stable deal action identity for this long-suite iteration.
    deal_action = f"long-double-bonus-video-poker-deal-{index}"
    # Deal a one-token round.
    started = client.call("/api/v1/games/double-bonus-video-poker/rounds", "POST", {"action_id": deal_action, "bet": 1})
    # Replay the deal to prove the wager debit is not duplicated.
    deal_replay = client.call("/api/v1/games/double-bonus-video-poker/rounds", "POST", {"action_id": deal_action, "bet": 1})
    # Require the deal replay to report the recovered round.
    assert deal_replay["replayed"] is True and deal_replay["round"]["round_id"] == started["round"]["round_id"], "Double Bonus deal replay changed the round"
    # Require exactly five dealt hand cards.
    assert len(started["round"]["hand"]) == 5, "Double Bonus did not deal five cards"
    # Read the deterministic round id for the decision route.
    round_id = started["round"]["round_id"]
    # Hold the first two cards and draw the rest.
    settled = client.call(f"/api/v1/games/double-bonus-video-poker/rounds/{round_id}/decisions", "POST", {"action_id": f"long-double-bonus-video-poker-draw-{index}", "hold": [0, 1]})
    # Require the settled round to reveal a final hand and a terminal outcome.
    assert settled["round"]["outcome"] in ("win", "push", "lose") and len(settled["round"]["final_hand"]) == 5, "Double Bonus did not settle the drawn hand"
    # Replay the draw to prove exactly-once settlement.
    replay = client.call(f"/api/v1/games/double-bonus-video-poker/rounds/{round_id}/decisions", "POST", {"action_id": f"long-double-bonus-video-poker-draw-{index}", "hold": [0, 1]})
    # Require the decision replay to return the identical settled result.
    assert replay["replayed"] is True and replay["round"]["net"] == settled["round"]["net"], "Double Bonus draw replay changed the result"
