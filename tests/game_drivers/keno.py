"""Long-suite driver for Keno."""


# Exercise Keno with both refund and draw paths.
def play(client, index):
    spots = [1 + index % 10, 20 + index % 10, 40 + index % 10]  # Vary valid spots.
    result = client.call("/api/v1/games/keno/tickets", "POST", {"player_id": "human", "amount": 4, "spots": spots})  # Buy a ticket.
    ticket_id = result["ticket"]["ticket_id"]  # Keep the ticket ID.
    if index % 2 == 0:  # Alternate Keno draw and refund behavior.
        draw = client.call("/api/v1/games/keno/draw", "POST", {})["draw"]  # Draw twenty numbers.
        assert len(draw["drawn"]) == 20, "Keno draw count changed"  # Verify draw size.
    else:  # Exercise the compatible ticket-refund path.
        client.call(f"/api/v1/games/keno/tickets/{ticket_id}", "DELETE", {"player_id": "human"})  # Exercise refund path.
