"""Catalog-discoverable long-suite driver for issue #94."""


# Exercise one complete three-hand round through only public game actions.
def play(client, index):
    # Build an idempotency key unique to this long-suite iteration.
    request_id = f"long-mhvp-{index}"
    # Deal one low-cost three-hand round through the public session-bound endpoint.
    started = client.call("/api/v1/games/multi-hand-video-poker/rounds", "POST", {"request_id": request_id, "hand_count": 3, "wager_per_hand": 1})
    # Store the returned round id for common hold and draw actions.
    round_id = started["round"]["round_id"]
    # Persist an empty hold selection so all cards draw independently.
    client.call(f"/api/v1/games/multi-hand-video-poker/rounds/{round_id}/holds", "POST", {"holds": []})
    # Complete and settle all three result lanes.
    completed = client.call(f"/api/v1/games/multi-hand-video-poker/rounds/{round_id}/draw", "POST", {})
    # Verify catalog discovery exercised the required three-hand mode.
    assert len(completed["round"]["results"]) == 3, "Multi-Hand Video Poker did not return three hands"
    # Verify every result contains exactly five final cards.
    assert all(len(result["cards"]) == 5 for result in completed["round"]["results"]), "Multi-Hand Video Poker returned an incomplete hand"
