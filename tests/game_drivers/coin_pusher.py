# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-discovered long-suite driver for Coin Pusher on the shared settlement core. (#156)"""


# Exercise one complete public drop and its idempotent retry.
def play(client, index):
    # Build one stable request identity for this long-suite iteration.
    request_id = f"long-coin-pusher-{index}"
    # Stake the smallest whole-drop wager the table accepts.
    payload = {"request_id": request_id, "stake": 1}
    # Execute one real-backend ledger-backed drop through the additive v1 action.
    result = client.call("/api/v1/games/coin-pusher/drops", "POST", payload)
    # Require a bounded server-authoritative cascade count.
    detail = result["round"]["detail"]
    # Require the cascade count to be within the zero-to-four range.
    assert 0 <= detail["coins"] <= 4, "Coin Pusher returned an invalid cascade count"
    # Require the outcome to be one of the two settled states.
    assert result["round"]["outcome"] in ("win", "lose"), "Coin Pusher returned an unknown outcome"
    # Retry the identical public action to prove exactly-once replay behavior.
    replay = client.call("/api/v1/games/coin-pusher/drops", "POST", payload)
    # Require the backend to identify the recovered response explicitly.
    assert replay["replayed"] is True, "Coin Pusher retry was not reported as replayed"
    # Require the same player-scoped round and committed shelf to survive the retry.
    assert replay["round"]["round_id"] == result["round"]["round_id"] and replay["round"]["detail"] == result["round"]["detail"], "Coin Pusher retry changed the committed result"
