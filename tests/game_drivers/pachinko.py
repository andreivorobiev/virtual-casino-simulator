# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-discovered long-suite driver for Pachinko on the shared settlement core. (#142)"""


# Exercise one complete public drop and its idempotent retry.
def play(client, index):
    # Build one stable request identity for this long-suite iteration.
    request_id = f"long-pachinko-{index}"
    # Stake the smallest whole-drop wager the table accepts.
    payload = {"request_id": request_id, "stake": 1}
    # Execute one real-backend ledger-backed drop through the additive v1 action.
    result = client.call("/api/v1/games/pachinko/drops", "POST", payload)
    # Require a bounded server-authoritative landing pocket and a full-length path.
    detail = result["round"]["detail"]
    # Require the landing pocket to be one of the thirteen pockets and the path to be twelve bounces.
    assert 0 <= detail["pocket"] <= 12 and len(detail["path"]) == 12, "Pachinko returned an invalid drop"
    # Require the outcome to be one of the settled states.
    assert result["round"]["outcome"] in ("win", "lose", "push"), "Pachinko returned an unknown outcome"
    # Retry the identical public action to prove exactly-once replay behavior.
    replay = client.call("/api/v1/games/pachinko/drops", "POST", payload)
    # Require the backend to identify the recovered response explicitly.
    assert replay["replayed"] is True, "Pachinko retry was not reported as replayed"
    # Require the same player-scoped round and committed path to survive the retry.
    assert replay["round"]["round_id"] == result["round"]["round_id"] and replay["round"]["detail"] == result["round"]["detail"], "Pachinko retry changed the committed result"
