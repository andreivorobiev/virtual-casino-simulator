"""Game-local catalog driver proposal for Crown and Anchor issue #133."""

# Store one stable wager used by future #77 long-suite integration.
WAGER = {"crown": 1.0}


# Play one complete Crown and Anchor scenario through a registered test client.
def play(client, index):
    # Build one deterministic client request id for the long-suite slot.
    action_id = f"caa-long-{index:03d}"
    # Post one complete symbol coverage action through the additive game route.
    response = client.post("/api/v1/games/crown-and-anchor/rounds", json={"client_request_id": action_id, "wagers": WAGER})
    # Assert the standard success envelope is present.
    assert response.json()["ok"] is True
    # Read the settled round from the standard envelope.
    round_item = response.json()["data"]["round"]
    # Assert the future long-suite action settles exactly three dice.
    assert len(round_item["faces"]) == 3
    # Return the public round for optional caller diagnostics.
    return round_item

