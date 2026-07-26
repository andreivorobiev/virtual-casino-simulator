"""Catalog-discovered long-suite driver for Color Wheel on the shared settlement core. (#152)"""


# Exercise one complete public spin and its idempotent retry.
def play(client, index):
    # Build one stable request identity for this long-suite iteration.
    request_id = f"long-color-wheel-{index}"
    # Bet red so a common segment can produce either outcome deterministically at the backend.
    payload = {"request_id": request_id, "color": "red", "stake": 1}
    # Execute one real-backend ledger-backed spin through the additive v1 action.
    result = client.call("/api/v1/games/color-wheel/spins", "POST", payload)
    # Require a bounded server-authoritative landed segment.
    assert 0 <= result["round"]["detail"]["segment"] <= 19, "Color Wheel returned an out-of-range segment"
    # Require the outcome to be one of the two settled states.
    assert result["round"]["outcome"] in ("win", "lose"), "Color Wheel returned an unknown outcome"
    # Retry the identical public action to prove exactly-once replay behavior.
    replay = client.call("/api/v1/games/color-wheel/spins", "POST", payload)
    # Require the backend to identify the recovered response explicitly.
    assert replay["replayed"] is True, "Color Wheel retry was not reported as replayed"
    # Require the same player-scoped round and landed segment to survive the retry.
    assert replay["round"]["round_id"] == result["round"]["round_id"] and replay["round"]["detail"] == result["round"]["detail"], "Color Wheel retry changed the committed result"
