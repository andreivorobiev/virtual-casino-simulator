"""Catalog-discoverable long-suite driver for GitHub issue #85."""


# Complete one low-cost Hi-Lo round through public session-bound actions.
def play(client, index):
    # Build a unique idempotent deal identity for this long-suite iteration.
    deal_action_id = f"long-hi-lo-deal-{index}"
    # Deal one opening card and commit one play-token wager.
    started = client.call("/api/v1/games/hi-lo/rounds", "POST", {"action_id": deal_action_id, "wager": 1})
    # Read the stable server round id for the decision route.
    round_id = started["round"]["round_id"]
    # Choose a legal direction without inspecting the private next card.
    guess = "lower" if started["round"]["current_card"].startswith("A") else "higher"
    # Build a separate idempotent settlement identity.
    guess_action_id = f"long-hi-lo-guess-{index}"
    # Reveal and settle the round through the public guess action.
    completed = client.call(f"/api/v1/games/hi-lo/rounds/{round_id}/guesses", "POST", {"action_id": guess_action_id, "guess": guess})
    # Verify the action reaches one terminal result.
    assert completed["round"]["phase"] == "settled", "Hi-Lo round did not settle"
    # Verify the next card is visible only after the decision.
    assert completed["round"].get("next_card"), "Hi-Lo did not reveal the next card"
