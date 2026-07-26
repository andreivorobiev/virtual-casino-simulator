"""Catalog-discovered long-suite driver for Marble Race on the shared settlement core. (#157)"""


# Exercise one complete public race and its idempotent retry.
def play(client, index):
    # Build one stable request identity for this long-suite iteration.
    request_id = f"long-marble-race-{index}"
    # Bet the first marble to win so a common race can produce either outcome.
    payload = {"request_id": request_id, "bet": "win", "marble": 0, "stake": 1}
    # Execute one real-backend ledger-backed race through the additive v1 action.
    result = client.call("/api/v1/games/marble-race/races", "POST", payload)
    # Require a full six-marble finishing order in the settled detail.
    order = result["round"]["detail"]["order"]
    # Require the finishing order to be a permutation of all six marbles.
    assert sorted(order) == list(range(6)), "Marble Race returned an invalid finishing order"
    # Require the outcome to be one of the two settled states.
    assert result["round"]["outcome"] in ("win", "lose"), "Marble Race returned an unknown outcome"
    # Retry the identical public action to prove exactly-once replay behavior.
    replay = client.call("/api/v1/games/marble-race/races", "POST", payload)
    # Require the backend to identify the recovered response explicitly.
    assert replay["replayed"] is True, "Marble Race retry was not reported as replayed"
    # Require the same player-scoped round and finishing order to survive the retry.
    assert replay["round"]["round_id"] == result["round"]["round_id"] and replay["round"]["detail"] == result["round"]["detail"], "Marble Race retry changed the committed result"
