"""Catalog-discovered long-suite driver for Daily Draw Lab on the shared settlement core. (#144)"""


# Exercise one complete public draw and its idempotent retry.
def play(client, index):
    # Build one stable request identity for this long-suite iteration.
    request_id = f"long-daily-draw-lab-{index}"
    # Mark three numbers so a random draw can produce a range of hit counts.
    payload = {"request_id": request_id, "picks": [1, 2, 3], "stake": 1}
    # Execute one real-backend ledger-backed draw through the additive v1 action.
    result = client.call("/api/v1/games/daily-draw-lab/draws", "POST", payload)
    # Require five distinct drawn numbers and a bounded hit count in the settled detail.
    detail = result["round"]["detail"]
    # Require five distinct draws in range and a hit count within zero to three.
    assert len(set(detail["drawn"])) == 5 and all(1 <= number <= 30 for number in detail["drawn"]) and 0 <= detail["hit_count"] <= 3, "Daily Draw Lab returned an invalid draw"
    # Require the outcome to be one of the two settled states.
    assert result["round"]["outcome"] in ("win", "lose"), "Daily Draw Lab returned an unknown outcome"
    # Retry the identical public action to prove exactly-once replay behavior.
    replay = client.call("/api/v1/games/daily-draw-lab/draws", "POST", payload)
    # Require the backend to identify the recovered response explicitly.
    assert replay["replayed"] is True, "Daily Draw Lab retry was not reported as replayed"
    # Require the same player-scoped round and committed draw to survive the retry.
    assert replay["round"]["round_id"] == result["round"]["round_id"] and replay["round"]["detail"] == result["round"]["detail"], "Daily Draw Lab retry changed the committed result"
