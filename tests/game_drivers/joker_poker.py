"""Catalog-proposal long-suite driver for issue #130."""


# Exercise one complete Joker Poker round through only public game actions.
def play(client, index):
    # Build an idempotency key unique to this long-suite iteration.
    deal_action_id = f"long-joker-poker-deal-{index}"
    # Deal one low-cost hand through the public session-bound endpoint.
    started = client.call("/api/v1/games/joker-poker/rounds", "POST", {"action_id": deal_action_id, "wager": 1})
    # Store the returned round id for hold and draw actions.
    round_id = started["round"]["round_id"]
    # Persist an empty hold selection so all cards draw independently.
    client.call(f"/api/v1/games/joker-poker/rounds/{round_id}/holds", "POST", {"holds": []})
    # Complete and settle the hand with one stable draw identity.
    completed = client.call(f"/api/v1/games/joker-poker/rounds/{round_id}/draw", "POST", {"action_id": f"long-joker-poker-draw-{index}", "holds": []})
    # Verify proposal discovery exercised one complete final hand.
    assert len(completed["round"]["result"]["cards"]) == 5, "Joker Poker returned an incomplete hand"
    # Verify the final result uses a documented paytable outcome.
    assert completed["round"]["result"]["outcome"] in completed["rules"]["paytable"], "Joker Poker returned an unknown outcome"
