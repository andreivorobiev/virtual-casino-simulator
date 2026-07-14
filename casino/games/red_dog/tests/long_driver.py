"""Game-local catalog driver proposal for Red Dog issue #84."""


# Exercise one complete low-wager round through public session-bound actions only.
def play(client, index):
    # Build a unique deal id so every long-suite iteration has an independent command.
    deal_action_id = f"long-red-dog-deal-{index}"
    # Deal one opening through the additive public route without a caller player id.
    started = client.call("/api/v1/games/red-dog/rounds", "POST", {"action_id": deal_action_id, "wager": 1})
    # Read the affected round returned by the controller.
    round_item = started["round"]
    # Complete a normal spread through the lower-risk call action when a decision is required.
    if round_item["phase"] == "raise_decision":
        # Build a second command id scoped to this exact round decision.
        call_action_id = f"long-red-dog-call-{index}"
        # Draw the third card without adding a matching raise wager.
        completed = client.call(f"/api/v1/games/red-dog/rounds/{round_item['round_id']}/call", "POST", {"action_id": call_action_id})
        # Replace the opening view with the terminal public round.
        round_item = completed["round"]
    # Require every automatic or chosen path to finish ledger reconciliation.
    assert round_item["phase"] == "settled", "Red Dog did not reach settled state"
    # Require the two opening cards on every legal result.
    assert round_item["first_card"] and round_item["second_card"], "Red Dog opening cards are missing"
    # Require a third card except for the regulated consecutive-card push.
    if round_item["outcome"] != "consecutive_push":
        # Verify pair and spread paths expose their terminal third card.
        assert round_item["third_card"], "Red Dog terminal third card is missing"
