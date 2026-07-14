"""Catalog-discoverable long-suite driver for GitHub issue #93."""


# Exercise one complete Ante-and-Play round through public session-bound actions.
def play(client, index):
    # Build a wager retry identity unique to this long-suite iteration.
    request_id = f"long-tcp-deal-{index}"
    # Deal one low-cost round with both supported opening wagers.
    started = client.call("/api/v1/games/three-card-poker/rounds", "POST", {"request_id": request_id, "ante": 1, "pair_plus": 1})
    # Replay the exact opening command before deciding so the initial debit cannot duplicate.
    start_replay = client.call("/api/v1/games/three-card-poker/rounds", "POST", {"request_id": request_id, "ante": 1, "pair_plus": 1})
    # Retain the server-owned round identity for the public decision route.
    round_id = started["round"]["round_id"]
    # Require the replay to retain the original prepared round identity.
    assert start_replay["round"]["round_id"] == round_id, "Three Card Poker opening retry changed round identity"
    # Require an explicit replay signal for the initial wager command.
    assert start_replay["replayed"] is True, "Three Card Poker opening retry was not reported as replayed"
    # Require the retry to return the original committed initial-wager evidence.
    assert start_replay["wager"] == started["wager"], "Three Card Poker opening retry changed wager evidence"
    # Require the retry to leave the post-debit wallet balance unchanged.
    assert start_replay["player"]["balance"] == started["player"]["balance"], "Three Card Poker opening retry changed the balance"
    # Require the player cards to be visible at the decision boundary.
    assert len(started["round"]["player_hand"]) == 3, "Three Card Poker did not deal three player cards"
    # Build one stable idempotency key for the Play decision and settlement.
    action_id = f"long-tcp-play-{index}"
    # Match the Ante and settle the round through the public Play action.
    settled = client.call(f"/api/v1/games/three-card-poker/rounds/{round_id}/decisions", "POST", {"action_id": action_id, "decision": "play"})
    # Require the terminal response to expose all three dealer cards.
    assert len(settled["round"]["dealer_hand"]) == 3 and "??" not in settled["round"]["dealer_hand"], "Three Card Poker did not reveal the dealer hand"
    # Replay the identical command to exercise real-backend exactly-once behavior.
    replay = client.call(f"/api/v1/games/three-card-poker/rounds/{round_id}/decisions", "POST", {"action_id": action_id, "decision": "play"})
    # Require an explicit replay signal rather than an ambiguous second settlement.
    assert replay["replayed"] is True, "Three Card Poker retry was not reported as replayed"
    # Require the replay to retain the original settled round identity.
    assert replay["round"]["round_id"] == round_id, "Three Card Poker retry changed round identity"
