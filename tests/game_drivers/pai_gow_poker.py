# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-discovered long-suite driver for integrated Pai Gow Poker."""


# Complete one low-cost Pai Gow Poker round through public session-bound actions.
def play(client, index):
    # Build an idempotency key unique to this future long-suite iteration.
    deal_action_id = f"long-pai-gow-poker-deal-{index}"
    # Deal one low-cost ante round through the public session-bound endpoint.
    started = client.call("/api/v1/games/pai-gow-poker/rounds", "POST", {"action_id": deal_action_id, "ante": 1})
    # Replay the opening action to prove the long suite exercises durable idempotency.
    started_replay = client.call("/api/v1/games/pai-gow-poker/rounds", "POST", {"action_id": deal_action_id, "ante": 1})
    # Require the exact replay marker and stable private round identity.
    assert started_replay["replayed"] is True and started_replay["round"] == started["round"], "Pai Gow Poker deal replay changed the round"
    # Verify the deal exposes exactly seven player cards for setting.
    assert len(started["round"].get("player_cards", [])) == 7, "Pai Gow Poker did not deal seven player cards"
    # Store the returned round id for the decision route.
    round_id = started["round"]["round_id"]
    # Build a separate idempotent decision identity.
    decision_action_id = f"long-pai-gow-poker-decision-{index}"
    # Set every future long-suite round by the house way so both hands settle deterministically.
    completed = client.call(f"/api/v1/games/pai-gow-poker/rounds/{round_id}/decisions", "POST", {"action_id": decision_action_id, "set": "house_way"})
    # Replay the terminal decision to prove settlement cannot duplicate token movement.
    completed_replay = client.call(f"/api/v1/games/pai-gow-poker/rounds/{round_id}/decisions", "POST", {"action_id": decision_action_id, "set": "house_way"})
    # Require the exact settled response under the stable action identity.
    assert completed_replay["replayed"] is True and completed_replay["round"] == completed["round"], "Pai Gow Poker decision replay changed settlement"
    # Verify the action reaches one terminal result.
    assert completed["round"]["phase"] == "settled", "Pai Gow Poker round did not settle"
    # Verify a settled showdown reveals the dealer high and low hands.
    assert len(completed["round"].get("dealer_high", [])) == 5 and len(completed["round"].get("dealer_low", [])) == 2, "Pai Gow Poker did not reveal the dealer arrangement"
