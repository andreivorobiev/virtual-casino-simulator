# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Long-suite driver for Slots."""


# Exercise Slots with varied payline counts.
def play(client, index):
    lines = [1, 3, 5, 9, 20][index % 5]  # Vary the active line count.
    result = client.call("/api/v1/games/slots/spin", "POST", {"player_id": "human", "active_lines": lines, "line_bet": 1})  # Spin once.
    assert result["spin"]["cost"] in (0, lines), "Slots cost did not match paid or free-spin rules"  # Verify debit/free-spin shape.
    assert len(result["spin"]["grid"]) == 3, "Slots grid row count changed"  # Verify grid shape.
