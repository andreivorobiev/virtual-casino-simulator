# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-discoverable public-action driver for isolated issue #91."""


# Exercise one complete low-cost Jacks-or-Better hand through public game actions.
def play(client, index):
    # Build a deal idempotency key unique to this long-suite iteration.
    deal_action_id = f"long-jobvp-deal-{index}"
    # Build an independent draw idempotency key for exactly-once settlement.
    draw_action_id = f"long-jobvp-draw-{index}"
    # Deal one low-cost single-hand round through the authenticated public endpoint.
    started = client.call("/api/v1/games/jacks-or-better-video-poker/rounds", "POST", {"action_id": deal_action_id, "coins": 1, "coin_value": 1})
    # Store the server round id used by the hold and draw actions.
    round_id = started["round"]["round_id"]
    # Persist one held card so the public hold path participates in every scenario.
    held = client.call(f"/api/v1/games/jacks-or-better-video-poker/rounds/{round_id}/holds", "POST", {"holds": [0]})
    # Verify reload-safe state reflects the public hold action before settlement.
    assert held["round"]["holds"] == [0], "Jacks-or-Better hold selection was not persisted"
    # Draw every unheld card and settle the returned-credit result exactly once.
    completed = client.call(f"/api/v1/games/jacks-or-better-video-poker/rounds/{round_id}/draw", "POST", {"action_id": draw_action_id})
    # Verify the single final hand contains exactly five public card codes.
    assert len(completed["round"]["final_hand"]) == 5, "Jacks-or-Better returned an incomplete final hand"
    # Verify the public action completed the round rather than leaving it actionable.
    assert completed["round"]["phase"] == "settled", "Jacks-or-Better round did not settle"
    # Verify returned credits are present independently of fake-token coin value.
    assert isinstance(completed["round"]["payout_credits"], int), "Jacks-or-Better omitted returned credits"
