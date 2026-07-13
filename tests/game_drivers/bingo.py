"""Long-suite driver for Bingo."""


# Exercise Bingo with call, reset, and auto-win variants.
def play(client, index):
    client.call("/api/v1/games/bingo/cards", "POST", {"player_id": "human", "amount": 5, "pattern": "line"})  # Buy one card.
    if index % 7 == 0:  # Periodically drive Bingo to an automatic win.
        result = client.call("/api/v1/games/bingo/auto", "POST", {"max_calls": 75})  # Exercise auto-play path.
        assert result["session"]["status"] == "won", "Bingo auto-play did not win"  # Verify terminal status.
    else:  # Exercise stepwise call and refund behavior.
        client.call("/api/v1/games/bingo/call", "POST", {})  # Call one ball.
        client.call("/api/v1/games/bingo/reset", "POST", {})  # Reset and refund remaining active cards.
