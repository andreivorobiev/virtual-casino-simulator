"""Catalog-discovered Long Suite driver for Acey-Deucey."""


# Play one complete public round and verify exact retry recovery.
def play(client, index):
    # Build deterministic identities for the free deal and wagered reveal.
    deal_action_id = f"acey-deucey-long-deal-{index:03d}"
    # Deal the private third-card round without moving play tokens.
    dealt = client.call("/api/v1/games/acey-deucey/rounds", "POST", {"action_id": deal_action_id})
    # Require the free deal to hide its prepared third card until play.
    assert dealt["round"]["phase"] == "wager" and not dealt["round"].get("third_card"), "Acey-Deucey exposed the result before the wager decision"
    # Read the visible spread from the free deal before selecting its server-owned price.
    spread = dealt["round"]["inside_rank_count"]
    # Pass equal or adjacent boundaries because no honest inside price exists.
    if spread == 0:
        # Build one stable identity for the pass-only terminal action.
        pass_action_id = f"acey-deucey-long-pass-{index:03d}"
        # Close the unpriceable deal without wallet movement.
        result = client.call(f"/api/v1/games/acey-deucey/rounds/{dealt['round']['round_id']}/pass", "POST", {"action_id": pass_action_id})
        # Replay the exact pass action through the same authenticated client.
        replay = client.call(f"/api/v1/games/acey-deucey/rounds/{dealt['round']['round_id']}/pass", "POST", {"action_id": pass_action_id})
        # Read the stable pass-only terminal round.
        round_row = result["round"]
        # Require a zero-value pass and exact retry recovery.
        assert round_row["phase"] == "passed" and round_row["outcome"] == "passed" and round_row["payout"] == 0.0 and replay["replayed"] is True, "Acey-Deucey pass-only boundaries did not close safely"
        # Return the passed round for optional runner diagnostics.
        return round_row
    # Build one stable identity for the wagered terminal action.
    play_action_id = f"acey-deucey-long-play-{index:03d}"
    # Settle the priceable round through the ledger-backed public endpoint.
    result = client.call(f"/api/v1/games/acey-deucey/rounds/{dealt['round']['round_id']}/play", "POST", {"action_id": play_action_id, "wager": 1.0})
    # Replay the exact play action through the same authenticated client.
    replay = client.call(f"/api/v1/games/acey-deucey/rounds/{dealt['round']['round_id']}/play", "POST", {"action_id": play_action_id, "wager": 1.0})
    # Read the stable terminal round for concise assertions.
    round_row = result["round"]
    # Resolve the authoritative return multiplier from the response paytable.
    multiplier = dealt["rules"]["inside_paytable"].get(str(spread), dealt["rules"]["inside_paytable"].get(spread))
    # Require a price for every playable Long Suite deal.
    assert multiplier is not None, "Acey-Deucey published no return for the visible spread"
    # Require the deprecated frozen-v1 scalar to describe the same current-round price.
    assert dealt["rules"]["inside_return_multiplier"] == multiplier, "Acey-Deucey compatibility scalar drifted from the current spread price"
    # Derive the terminal return from the server-owned spread price.
    expected_payout = multiplier if round_row["outcome"] == "inside" else 0.0
    # Compare the published payout and net against the priced in-between profile.
    assert round_row["phase"] == "settled" and round_row["outcome"] in ("inside", "outside", "boundary_tie") and round_row["payout"] == expected_payout and round_row["net"] == expected_payout - 1.0, "Acey-Deucey settlement does not match the published profile"
    # Require exact retry recovery for round identity and hidden-card reveal.
    assert replay["replayed"] is True and replay["round"]["round_id"] == round_row["round_id"] and replay["round"]["third_card"] == round_row["third_card"], "Acey-Deucey retry changed the committed result"
    # Return the settled round for optional runner diagnostics.
    return round_row
