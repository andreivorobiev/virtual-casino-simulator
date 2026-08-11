# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-discovered long-suite driver for Lucky Grid on the shared settlement core. (#153)"""


# Exercise one complete public reveal and its idempotent retry.
def play(client, index):
    # Build one stable request identity for this long-suite iteration.
    request_id = f"long-lucky-grid-{index}"
    # Pick the first three cells so a random prize placement can produce any match count.
    payload = {"request_id": request_id, "picks": [0, 1, 2], "stake": 1}
    # Execute one real-backend ledger-backed reveal through the additive v1 action.
    result = client.call("/api/v1/games/lucky-grid/reveals", "POST", payload)
    # Require three distinct prize cells and a bounded match count in the settled detail.
    detail = result["round"]["detail"]
    # Require three distinct prizes and a match count within zero to three.
    assert len(set(detail["prizes"])) == 3 and 0 <= detail["match_count"] <= 3, "Lucky Grid returned an invalid reveal"
    # Require the outcome to be one of the two settled states.
    assert result["round"]["outcome"] in ("win", "lose"), "Lucky Grid returned an unknown outcome"
    # Retry the identical public action to prove exactly-once replay behavior.
    replay = client.call("/api/v1/games/lucky-grid/reveals", "POST", payload)
    # Require the backend to identify the recovered response explicitly.
    assert replay["replayed"] is True, "Lucky Grid retry was not reported as replayed"
    # Require the same player-scoped round and committed prizes to survive the retry.
    assert replay["round"]["round_id"] == result["round"]["round_id"] and replay["round"]["detail"] == result["round"]["detail"], "Lucky Grid retry changed the committed result"
