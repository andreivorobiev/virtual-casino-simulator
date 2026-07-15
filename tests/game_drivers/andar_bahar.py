"""Catalog-discovered Long Suite driver for Andar Bahar."""


# Play one complete public round and verify exact retry recovery.
def play(client, index):
    # Build one deterministic retry identity for this suite scenario.
    action_id = f"andar-bahar-long-{index:03d}"
    # Execute the real ledger-backed round through the additive v1 endpoint.
    result = client.call("/api/v1/games/andar-bahar/rounds", "POST", {"action_id": action_id, "wager": 1.0, "side": "andar"})
    # Replay the exact request identity through the same authenticated client.
    replay = client.call("/api/v1/games/andar-bahar/rounds", "POST", {"action_id": action_id, "wager": 1.0, "side": "andar"})
    # Read the stable authoritative result for concise assertions.
    round_row = result["round"]
    # Require alternating cards and a terminal match on the published winning side.
    assert round_row["dealt_cards"] and all(item["side"] == ("andar" if position % 2 == 0 else "bahar") for position, item in enumerate(round_row["dealt_cards"])), "Andar Bahar returned a non-alternating deal"
    # Require the terminal reveal to publish the first matching side.
    assert round_row["dealt_cards"][-1]["matched"] is True and round_row["winning_side"] == round_row["dealt_cards"][-1]["side"], "Andar Bahar did not settle on the terminal rank match"
    # Require transparent even-money returned-token settlement.
    expected_payout = 2.0 if round_row["winning_side"] == "andar" else 0.0
    # Compare the published payout and net against the documented rule.
    assert round_row["payout"] == expected_payout and round_row["net"] == expected_payout - 1.0, "Andar Bahar settlement does not match the published rule"
    # Require the retry to preserve identity and every authoritative deal fact.
    assert replay["replayed"] is True and replay["round"]["round_id"] == round_row["round_id"] and replay["round"]["dealt_cards"] == round_row["dealt_cards"], "Andar Bahar retry changed the committed result"
    # Return the settled round for optional runner diagnostics.
    return round_row
