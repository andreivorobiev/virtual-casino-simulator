"""Catalog-discovered long-suite driver for Chuck-a-Luck after #77 integration."""


# Exercise one complete public round and its idempotent retry.
def play(client, index):
    # Build one stable request identity for this long-suite iteration.
    request_id = f"long-chuck-a-luck-{index}"
    # Cover every number so any valid three-die result creates a settlement credit.
    wagers = {number_id: 1 for number_id in ("one", "two", "three", "four", "five", "six")}
    # Execute one real-backend ledger-backed roll through the additive v1 action.
    result = client.call("/api/v1/games/chuck-a-luck/rolls", "POST", {"request_id": request_id, "wagers": wagers})
    # Require exactly three bounded server-authoritative dice.
    assert len(result["round"]["dice"]) == 3 and all(1 <= face <= 6 for face in result["round"]["dice"]), "Chuck-a-Luck returned invalid dice"
    # Require the all-number wager to return at least one covered stake plus winnings.
    assert result["round"]["total_return"] > 0, "Chuck-a-Luck all-number wager did not settle a return"
    # Retry the identical public action to prove exactly-once replay behavior.
    replay = client.call("/api/v1/games/chuck-a-luck/rolls", "POST", {"request_id": request_id, "wagers": wagers})
    # Require the backend to identify the recovered response explicitly.
    assert replay["replayed"] is True, "Chuck-a-Luck retry was not reported as replayed"
    # Require the same player-scoped round and dice to survive the retry.
    assert replay["round"]["round_id"] == result["round"]["round_id"] and replay["round"]["dice"] == result["round"]["dice"], "Chuck-a-Luck retry changed the committed result"
