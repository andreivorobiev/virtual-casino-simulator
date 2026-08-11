# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Long-suite driver for Blackjack."""


# Exercise Blackjack with a deal and a safe settlement action when needed.
def play(client, index):
    result = client.call("/api/v1/games/blackjack/rounds", "POST", {"player_id": "human", "bet_amount": 5 + index % 4})  # Deal one round.
    round_data = result["round"]  # Keep the dealt round.
    if round_data.get("status") == "player_turn":  # Stand only when the player must act.
        result = client.call(f"/api/v1/games/blackjack/rounds/{round_data['round_id']}/stand", "POST", {"hand_index": 0})  # Stand to settle active hands.
        round_data = result["round"]  # Refresh the settled round.
    assert round_data["dealer"]["cards"], "Blackjack dealer cards missing"  # Verify dealer state.
