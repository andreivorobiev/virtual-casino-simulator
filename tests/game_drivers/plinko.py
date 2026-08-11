# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-discovered Long Suite driver for Plinko."""


# Play one complete public drop and verify exact retry recovery.
def play(client, index):
    # Build one deterministic retry identity for this suite scenario.
    action_id = f"plinko-long-{index:03d}"
    # Execute the real ledger-backed drop through the additive v1 endpoint.
    result = client.call("/api/v1/games/plinko/drops", "POST", {"action_id": action_id, "wager": 1.0})
    # Replay the exact request identity through the same authenticated client.
    replay = client.call("/api/v1/games/plinko/drops", "POST", {"action_id": action_id, "wager": 1.0})
    # Read the stable authoritative result for concise assertions.
    drop = result["drop"]
    # Require the fixed committed path and a matching terminal bucket.
    assert len(drop["path"]) == 8 and all(step in ("L", "R") for step in drop["path"]) and drop["bucket"] == sum(step == "R" for step in drop["path"]), "Plinko returned an invalid committed path"
    # Require the published multiplier and returned-token calculation to agree.
    assert round(drop["wager"] * drop["multiplier"], 2) == drop["payout"], "Plinko payout does not match the transparent multiplier"
    # Require the retry to preserve drop identity and every authoritative result fact.
    assert replay["replayed"] is True and replay["drop"]["drop_id"] == drop["drop_id"] and replay["drop"]["path"] == drop["path"], "Plinko retry changed the committed result"
    # Return the settled drop for optional runner diagnostics.
    return drop
