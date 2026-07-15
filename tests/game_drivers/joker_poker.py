"""Catalog-discovered long-suite driver for integrated Joker Poker."""


# Exercise one complete Joker Poker round through only public game actions.
def play(client, index):
    # Build an idempotency key unique to this long-suite iteration.
    deal_action_id = f"long-joker-poker-deal-{index}"
    # Deal one low-cost hand through the public session-bound endpoint.
    started = client.call("/api/v1/games/joker-poker/rounds", "POST", {"action_id": deal_action_id, "wager": 1})
    # Replay the deal to prove the wager debit remains exactly once.
    started_replay = client.call("/api/v1/games/joker-poker/rounds", "POST", {"action_id": deal_action_id, "wager": 1})
    # Require the exact replay marker and stable source hand.
    assert started_replay["replayed"] is True and started_replay["round"] == started["round"], "Joker Poker deal replay changed the hand"
    # Store the returned round id for hold and draw actions.
    round_id = started["round"]["round_id"]
    # Persist an empty hold selection so all cards draw independently.
    client.call(f"/api/v1/games/joker-poker/rounds/{round_id}/holds", "POST", {"holds": []})
    # Complete and settle the hand with one stable draw identity.
    draw_action_id = f"long-joker-poker-draw-{index}"
    # Complete and settle through the stable draw action identity.
    completed = client.call(f"/api/v1/games/joker-poker/rounds/{round_id}/draw", "POST", {"action_id": draw_action_id, "holds": []})
    # Replay the terminal draw to prove payout settlement remains exactly once.
    completed_replay = client.call(f"/api/v1/games/joker-poker/rounds/{round_id}/draw", "POST", {"action_id": draw_action_id, "holds": []})
    # Require the same settled hand under the replayed action.
    assert completed_replay["replayed"] is True and completed_replay["round"] == completed["round"], "Joker Poker draw replay changed settlement"
    # Verify catalog discovery exercised one complete final hand.
    assert len(completed["round"]["result"]["cards"]) == 5, "Joker Poker returned an incomplete hand"
    # Verify the final result uses a documented paytable outcome.
    assert completed["round"]["result"]["outcome"] in completed["rules"]["paytable"], "Joker Poker returned an unknown outcome"
