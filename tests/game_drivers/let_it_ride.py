# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-discovered Long Suite driver for Let It Ride."""


# Exercise one complete three-wager round and exact retries through public actions.
def play(client, index):
    # Build a valid caller-stable deal identity unique to this driver iteration.
    deal_action_id = f"let-it-ride-long-deal-{index:03d}"
    # Use a small base wager so the three-unit opening remains long-suite friendly.
    deal_request = {"action_id": deal_action_id, "wager": 1}
    # Execute one real-backend opening through the additive v1 endpoint.
    deal_result = client.call("/api/v1/games/let-it-ride/rounds", "POST", deal_request)
    # Retain the first-decision round for both staged public actions.
    round_item = deal_result["round"]
    # Verify only the three player cards are visible before the first decision.
    assert round_item["phase"] == "first_decision" and round_item["revealed_community"] == 0, "Let It Ride deal exposed invalid opening state"
    # Retry the identical opening to exercise the three-unit debit exactly once.
    deal_replay = client.call("/api/v1/games/let-it-ride/rounds", "POST", deal_request)
    # Verify replay preserved the active round and wager proof.
    assert deal_replay["replayed"] is True and deal_replay["round"] == round_item, "Let It Ride deal retry changed the round"
    # Build and submit the first ride decision without creating a refund movement.
    first_request = {"action_id": f"let-it-ride-long-first-{index:03d}", "decision": "ride"}
    # Reveal the first community card through the documented route.
    first = client.call(f"/api/v1/games/let-it-ride/rounds/{round_item['round_id']}/first-decision", "POST", first_request)
    # Replay the exact first decision through the same authenticated client.
    first_replay = client.call(f"/api/v1/games/let-it-ride/rounds/{round_item['round_id']}/first-decision", "POST", first_request)
    # Require one revealed community card and exact retry recovery.
    assert first["round"]["phase"] == "second_decision" and first["round"]["revealed_community"] == 1 and first_replay["replayed"] is True and first_replay["round"] == first["round"], "Let It Ride first decision was not replay safe"
    # Build and submit the terminal ride decision.
    second_request = {"action_id": f"let-it-ride-long-second-{index:03d}", "decision": "ride"}
    # Settle the five-card result through the final public action.
    settled = client.call(f"/api/v1/games/let-it-ride/rounds/{round_item['round_id']}/second-decision", "POST", second_request)
    # Replay the terminal command to prove no second payout can be issued.
    settled_replay = client.call(f"/api/v1/games/let-it-ride/rounds/{round_item['round_id']}/second-decision", "POST", second_request)
    # Require a complete terminal settlement with both community cards visible.
    assert settled["round"]["phase"] == "settled" and settled["round"]["revealed_community"] == 2 and settled["round"]["settlement"]["complete"] is True, "Let It Ride returned an incomplete settlement"
    # Require exact terminal retry recovery.
    assert settled_replay["replayed"] is True and settled_replay["round"] == settled["round"], "Let It Ride settlement retry changed the round"
    # Return the settled round for optional runner diagnostics.
    return settled["round"]
