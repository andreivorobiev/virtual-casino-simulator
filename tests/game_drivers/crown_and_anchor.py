# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-discovered Long Suite driver for Crown and Anchor."""

# Store one stable wager used by the catalog-wide long-suite scenarios.
WAGER = {"crown": 1.0}


# Play one complete Crown and Anchor scenario through the authenticated test client.
def play(client, index):
    # Build one deterministic client request id for the long-suite slot.
    action_id = f"caa-long-{index:03d}"
    # Post one complete symbol coverage action through the additive game route.
    response = client.call("/api/v1/games/crown-and-anchor/rounds", "POST", {"client_request_id": action_id, "wagers": WAGER})
    # Repeat the same action identity through the public client to prove exact replay.
    replay = client.call("/api/v1/games/crown-and-anchor/rounds", "POST", {"client_request_id": action_id, "wagers": WAGER})
    # Read the settled round from the standard data envelope returned by the shared client.
    round_item = response["round"]
    # Assert the public action settles exactly three server-authoritative dice.
    assert len(round_item["faces"]) == 3 and all(1 <= face <= 6 for face in round_item["faces"]), "Crown and Anchor returned invalid dice"
    # Require the retry to preserve the same session-owned round and authoritative faces.
    assert replay["replayed"] is True and replay["round"]["round_id"] == round_item["round_id"] and replay["round"]["faces"] == round_item["faces"], "Crown and Anchor retry changed the committed result"
    # Return the public round for optional caller diagnostics.
    return round_item
