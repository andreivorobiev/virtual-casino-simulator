"""Catalog-discovered long-suite driver for Faro on the shared settlement core. (#146)"""


# Exercise one complete public deal and its idempotent retry.
def play(client, index):
    # Build one stable request identity for this long-suite iteration.
    request_id = f"long-faro-{index}"
    # Bet on the ace so a common deal can produce any of the four settled outcomes.
    payload = {"request_id": request_id, "rank": 1, "stake": 1}
    # Execute one real-backend ledger-backed deal through the additive v1 action.
    result = client.call("/api/v1/games/faro/deals", "POST", payload)
    # Require the outcome to be one of the four settled states.
    assert result["round"]["outcome"] in ("win", "lose", "push", "split"), "Faro returned an unknown outcome"
    # Require both dealt card ranks to be present in the settled detail.
    assert result["round"]["detail"]["banker"] and result["round"]["detail"]["player"], "Faro did not report both dealt cards"
    # Retry the identical public action to prove exactly-once replay behavior.
    replay = client.call("/api/v1/games/faro/deals", "POST", payload)
    # Require the backend to identify the recovered response explicitly.
    assert replay["replayed"] is True, "Faro retry was not reported as replayed"
    # Require the same player-scoped round and dealt cards to survive the retry.
    assert replay["round"]["round_id"] == result["round"]["round_id"] and replay["round"]["detail"] == result["round"]["detail"], "Faro retry changed the committed result"
