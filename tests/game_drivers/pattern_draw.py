"""Catalog-discovered long-suite driver for Pattern Draw on the shared settlement core. (#155)"""


# Exercise one complete public draw and its idempotent retry.
def play(client, index):
    # Build one stable request identity for this long-suite iteration.
    request_id = f"long-pattern-draw-{index}"
    # Bet the common line pattern so a random grid can produce either outcome.
    payload = {"request_id": request_id, "bet": "line", "stake": 1}
    # Execute one real-backend ledger-backed draw through the additive v1 action.
    result = client.call("/api/v1/games/pattern-draw/draws", "POST", payload)
    # Require a nine-cell grid of on-or-off bits in the settled detail.
    grid = result["round"]["detail"]["grid"]
    # Require the grid to be nine binary cells.
    assert len(grid) == 9 and all(cell in (0, 1) for cell in grid), "Pattern Draw returned an invalid grid"
    # Require the outcome to be one of the two settled states.
    assert result["round"]["outcome"] in ("win", "lose"), "Pattern Draw returned an unknown outcome"
    # Retry the identical public action to prove exactly-once replay behavior.
    replay = client.call("/api/v1/games/pattern-draw/draws", "POST", payload)
    # Require the backend to identify the recovered response explicitly.
    assert replay["replayed"] is True, "Pattern Draw retry was not reported as replayed"
    # Require the same player-scoped round and committed grid to survive the retry.
    assert replay["round"]["round_id"] == result["round"]["round_id"] and replay["round"]["detail"] == result["round"]["detail"], "Pattern Draw retry changed the committed result"
