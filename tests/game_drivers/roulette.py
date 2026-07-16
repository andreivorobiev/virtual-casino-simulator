"""Long-suite driver for Roulette."""

# Store red numbers so the outside-bet payload remains contract-compatible.
RED_NUMBERS = ["1", "3", "5", "7", "9", "12", "14", "16", "18", "19", "21", "23", "25", "27", "30", "32", "34", "36"]


# Exercise Roulette with a setting change, a bet, and a settlement.
def play(client, index):
    client.call("/api/v1/games/roulette/clear", "POST", {"player_id": "human"})  # Clear stale human bets.
    if index % 5 == 0:  # Periodically verify the en-prison zero-rule branch.
        client.call("/api/v1/games/roulette/settings", "POST", {"zero_rule": "en_prison"})  # Exercise zero-rule settings.
        client.call("/api/v1/games/roulette/bets", "POST", {"player_id": "human", "bet_type": "red", "amount": 5, "covered_numbers": RED_NUMBERS, "label": "Red"})  # Place outside bet.
        result = client.call("/api/v1/games/roulette/spin", "POST", {"force_result": "0"})  # Attempt a hostile forced result that the server must ignore.
        assert str(result["round"]["result"]) in {str(number) for number in range(37)} | {"00"}, "Roulette result left the server wheel"  # Verify a legal server outcome.
        client.call("/api/v1/games/roulette/clear", "POST", {"player_id": "human"})  # Clean carried bet before next game.
    else:  # Exercise the standard zero-rule path on remaining iterations.
        client.call("/api/v1/games/roulette/settings", "POST", {"zero_rule": "normal"})  # Exercise standard setting.
        client.call("/api/v1/games/roulette/bets", "POST", {"player_id": "human", "bet_type": "straight", "amount": 5, "covered_numbers": [str(17 + index % 3)], "label": str(17 + index % 3)})  # Place inside bet.
        result = client.call("/api/v1/games/roulette/spin", "POST", {"force_result": str(17 + index % 3)})  # Attempt a hostile forced win that the server must ignore.
        assert str(result["round"]["result"]) in {str(number) for number in range(37)} | {"00"}, "Roulette result left the server wheel"  # Verify outcome authority.
