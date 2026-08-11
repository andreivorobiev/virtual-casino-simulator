# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Long-suite driver for Baccarat."""


# Exercise Baccarat with all wager types across repeated scenarios.
def play(client, index):
    bet_type = ["banker", "player", "tie"][index % 3]  # Rotate Baccarat bet types.
    client.call("/api/v1/games/baccarat/bets", "POST", {"player_id": "human", "amount": 5, "bet_type": bet_type})  # Place a wager.
    result = client.call("/api/v1/games/baccarat/deal", "POST", {})  # Deal one coup.
    assert result["coup"]["winner"] in ("player", "banker", "tie"), "Baccarat winner invalid"  # Verify winner enum.
    assert result["coup"]["player_cards"] and result["coup"]["banker_cards"], "Baccarat cards missing"  # Verify cards.
