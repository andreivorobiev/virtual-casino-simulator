# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-discovered Long Suite driver for Fan-Tan."""


# Play one complete public round and verify exact retry recovery.
def play(client, index):
    # Build one deterministic retry identity for this suite scenario.
    action_id = f"fan-tan-long-{index:03d}"
    # Execute the real ledger-backed round through the additive v1 endpoint.
    result = client.call("/api/v1/games/fan-tan/rounds", "POST", {"action_id": action_id, "wagers": {"1": 1.0}})
    # Replay the exact request identity through the same authenticated client.
    replay = client.call("/api/v1/games/fan-tan/rounds", "POST", {"action_id": action_id, "wagers": {"1": 1.0}})
    # Read the stable authoritative result for concise assertions.
    round_row = result["round"]
    # Require a valid counted pile and canonical modulo-four residue mapping.
    assert 49 <= round_row["pile_count"] <= 80 and round_row["residue"] == str(round_row["pile_count"] % 4 or 4), "Fan-Tan returned an invalid counted-pile residue"
    # Require transparent settlement arithmetic for the one covered residue.
    expected_return = 4.0 if round_row["residue"] == "1" else 0.0
    # Compare the published returned-token total against the documented three-to-one net rule.
    assert round_row["total_wager"] == 1.0 and round_row["total_return"] == expected_return, "Fan-Tan settlement does not match the published paytable"
    # Require the retry to preserve round identity and every authoritative result fact.
    assert replay["replayed"] is True and replay["round"]["round_id"] == round_row["round_id"] and replay["round"]["pile_count"] == round_row["pile_count"], "Fan-Tan retry changed the committed result"
    # Return the settled round for optional runner diagnostics.
    return round_row
