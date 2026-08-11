# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-discovered long-suite driver for Boule on the shared settlement core. (#148)"""


# Exercise one complete public spin and its idempotent retry.
def play(client, index):
    # Build one stable request identity for this long-suite iteration.
    request_id = f"long-boule-{index}"
    # Bet the even group so a common draw can produce either outcome deterministically at the backend.
    payload = {"request_id": request_id, "bet": "even", "stake": 1}
    # Execute one real-backend ledger-backed spin through the additive v1 action.
    result = client.call("/api/v1/games/boule/spins", "POST", payload)
    # Require a bounded server-authoritative drawn number.
    assert 1 <= result["round"]["detail"]["number"] <= 9, "Boule returned an out-of-range number"
    # Require the outcome to be one of the two settled states.
    assert result["round"]["outcome"] in ("win", "lose"), "Boule returned an unknown outcome"
    # Retry the identical public action to prove exactly-once replay behavior.
    replay = client.call("/api/v1/games/boule/spins", "POST", payload)
    # Require the backend to identify the recovered response explicitly.
    assert replay["replayed"] is True, "Boule retry was not reported as replayed"
    # Require the same player-scoped round and drawn number to survive the retry.
    assert replay["round"]["round_id"] == result["round"]["round_id"] and replay["round"]["detail"] == result["round"]["detail"], "Boule retry changed the committed result"
