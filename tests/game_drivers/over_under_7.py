"""Catalog-discovered Long Suite driver for Over/Under 7."""

# Cover every proposition so each valid two-dice total produces one returned-token settlement.
WAGERS = {"under": 1.0, "seven": 1.0, "over": 1.0}


# Play one complete public action and verify exact retry recovery.
def play(client, index):
    # Build one deterministic retry identity for this suite scenario.
    action_id = f"ou7-long-{index:03d}"
    # Execute the real ledger-backed two-dice action through the additive v1 endpoint.
    result = client.call("/api/v1/games/over-under-7/plays", "POST", {"action_id": action_id, "wagers": WAGERS})
    # Replay the exact request identity through the same authenticated client.
    replay = client.call("/api/v1/games/over-under-7/plays", "POST", {"action_id": action_id, "wagers": WAGERS})
    # Read the stable authoritative result for concise assertions.
    round_item = result["round"]
    # Require two bounded dice and a legal total classification.
    assert len(round_item["dice"]) == 2 and all(1 <= face <= 6 for face in round_item["dice"]) and round_item["outcome"] in WAGERS, "Over/Under 7 returned an invalid dice result"
    # Require all-outcome coverage to return the winning stake plus its documented net payout.
    assert round_item["total_return"] > 0, "Over/Under 7 all-outcome coverage did not return a settlement credit"
    # Require the retry to preserve round identity and server-authoritative dice.
    assert replay["replayed"] is True and replay["round"]["round_id"] == round_item["round_id"] and replay["round"]["dice"] == round_item["dice"], "Over/Under 7 retry changed the committed result"
    # Return the settled round for optional runner diagnostics.
    return round_item
