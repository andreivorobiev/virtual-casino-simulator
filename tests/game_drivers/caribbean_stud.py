# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-discovered Long Suite driver for Caribbean Stud."""


# Exercise one complete ante-first round and exact retry through public actions.
def play(client, index):
    # Build a valid caller-stable deal identity unique to this driver iteration.
    deal_action_id = f"caribbean-stud-long-deal-{index:03d}"
    # Use a small play-token ante to keep long-suite balances stable.
    deal_request = {"action_id": deal_action_id, "ante": 1}
    # Execute one real-backend ante-backed deal through the additive v1 endpoint.
    deal_result = client.call("/api/v1/games/caribbean-stud/rounds", "POST", deal_request)
    # Retain the active decision round for a terminal action route.
    round_item = deal_result["round"]
    # Verify the public action reached the decision phase without dealer hole cards.
    assert round_item["phase"] == "decision" and "dealer_hand" not in round_item, "Caribbean Stud deal exposed invalid decision state"
    # Retry the identical deal to exercise ante exactly-once behavior.
    deal_replay = client.call("/api/v1/games/caribbean-stud/rounds", "POST", deal_request)
    # Verify replay preserved the active round and ante proof.
    assert deal_replay["replayed"] is True and deal_replay["round"] == round_item, "Caribbean Stud deal retry changed the round"
    # Build a call action identity for the active round.
    call_request = {"action_id": f"caribbean-stud-long-call-{index:03d}"}
    # Commit the fixed call wager and settle the showdown.
    called = client.call(f"/api/v1/games/caribbean-stud/rounds/{round_item['round_id']}/call", "POST", call_request)
    # Replay the exact call through the same authenticated client.
    call_replay = client.call(f"/api/v1/games/caribbean-stud/rounds/{round_item['round_id']}/call", "POST", call_request)
    # Read the terminal round once for transparent acceptance assertions.
    settled = called["round"]
    # Require one documented outcome with the full dealer hand revealed after call.
    assert settled["phase"] == "settled" and settled["outcome"] in {"dealer_not_qualified", "player_win", "push", "dealer_win"} and len(settled["dealer_hand"]) == 5, "Caribbean Stud call returned an invalid terminal round"
    # Require exact retry recovery without a second call settlement.
    assert call_replay["replayed"] is True and call_replay["round"] == settled, "Caribbean Stud call retry changed the round"
    # Return the settled round for optional runner diagnostics.
    return settled
