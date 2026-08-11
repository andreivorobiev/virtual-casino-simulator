# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-discovered long-suite driver for integrated Casino Hold'em."""


# Complete one low-cost Casino Hold'em round through public session-bound actions.
def play(client, index):
    # Build an idempotency key unique to this future long-suite iteration.
    deal_action_id = f"long-casino-holdem-deal-{index}"
    # Deal one low-cost ante round through the public session-bound endpoint.
    started = client.call("/api/v1/games/casino-holdem/rounds", "POST", {"action_id": deal_action_id, "wager": 1})
    # Replay the opening action to prove the long suite exercises durable idempotency.
    started_replay = client.call("/api/v1/games/casino-holdem/rounds", "POST", {"action_id": deal_action_id, "wager": 1})
    # Require the exact replay marker and stable private round identity.
    assert started_replay["replayed"] is True and started_replay["round"] == started["round"], "Casino Hold'em deal replay changed the round"
    # Store the returned round id for the decision route.
    round_id = started["round"]["round_id"]
    # Build a separate idempotent decision identity.
    decision_action_id = f"long-casino-holdem-decision-{index}"
    # Call every future long-suite round so the board and dealer qualification paths execute.
    completed = client.call(f"/api/v1/games/casino-holdem/rounds/{round_id}/decision", "POST", {"action_id": decision_action_id, "decision": "call"})
    # Replay the terminal decision to prove settlement cannot duplicate token movement.
    completed_replay = client.call(f"/api/v1/games/casino-holdem/rounds/{round_id}/decision", "POST", {"action_id": decision_action_id, "decision": "call"})
    # Require the exact settled response under the stable action identity.
    assert completed_replay["replayed"] is True and completed_replay["round"] == completed["round"], "Casino Hold'em decision replay changed settlement"
    # Verify the action reaches one terminal result.
    assert completed["round"]["phase"] == "settled", "Casino Hold'em round did not settle"
    # Verify a called showdown reveals the full community board.
    assert len(completed["round"].get("community_cards", [])) == 5, "Casino Hold'em did not reveal the full board"
