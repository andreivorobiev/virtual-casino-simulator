"""Catalog-discovered Long Suite driver for Acey-Deucey."""


# Play one complete public round and verify exact retry recovery.
def play(client, index):
    # Build deterministic identities for the free deal and wagered reveal.
    deal_action_id = f"acey-deucey-long-deal-{index:03d}"
    # Deal the private third-card round without moving play tokens.
    dealt = client.call("/api/v1/games/acey-deucey/rounds", "POST", {"action_id": deal_action_id})
    # Build one stable identity for the wagered terminal action.
    play_action_id = f"acey-deucey-long-play-{index:03d}"
    # Settle the prepared round through the ledger-backed public endpoint.
    result = client.call(f"/api/v1/games/acey-deucey/rounds/{dealt['round']['round_id']}/play", "POST", {"action_id": play_action_id, "wager": 1.0})
    # Replay the exact play action through the same authenticated client.
    replay = client.call(f"/api/v1/games/acey-deucey/rounds/{dealt['round']['round_id']}/play", "POST", {"action_id": play_action_id, "wager": 1.0})
    # Read the stable terminal round for concise assertions.
    round_row = result["round"]
    # Require the free deal to hide its prepared third card until play.
    assert dealt["round"]["phase"] == "wager" and not dealt["round"].get("third_card"), "Acey-Deucey exposed the result before the wager decision"
    # Require a documented outcome and transparent even-money settlement.
    expected_payout = 2.0 if round_row["outcome"] == "inside" else 0.0
    # Compare the published payout and net against the fixed in-between profile.
    assert round_row["phase"] == "settled" and round_row["outcome"] in ("inside", "outside", "boundary_tie") and round_row["payout"] == expected_payout and round_row["net"] == expected_payout - 1.0, "Acey-Deucey settlement does not match the published profile"
    # Require exact retry recovery for round identity and hidden-card reveal.
    assert replay["replayed"] is True and replay["round"]["round_id"] == round_row["round_id"] and replay["round"]["third_card"] == round_row["third_card"], "Acey-Deucey retry changed the committed result"
    # Return the settled round for optional runner diagnostics.
    return round_row
