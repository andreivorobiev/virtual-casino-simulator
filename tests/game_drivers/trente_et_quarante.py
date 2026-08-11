# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-discovered long-suite driver for Trente et Quarante on the shared settlement core. (#147)"""


# Exercise one complete public coup and its idempotent retry.
def play(client, index):
    # Build one stable request identity for this long-suite iteration.
    request_id = f"long-teq-{index}"
    # Bet Rouge so a common coup can produce any settled outcome.
    payload = {"request_id": request_id, "bet": "rouge", "stake": 1}
    # Execute one real-backend ledger-backed coup through the additive v1 action.
    result = client.call("/api/v1/games/trente-et-quarante/coups", "POST", payload)
    # Require both row totals to land in the thirty-one to forty range.
    detail = result["round"]["detail"]
    # Require Noir and Rouge totals to be valid Trente et Quarante totals.
    assert 31 <= detail["noir_total"] <= 40 and 31 <= detail["rouge_total"] <= 40, "Trente et Quarante produced an invalid row total"
    # Require the outcome to be one of the settled states.
    assert result["round"]["outcome"] in ("win", "lose", "push", "refait"), "Trente et Quarante returned an unknown outcome"
    # Retry the identical public action to prove exactly-once replay behavior.
    replay = client.call("/api/v1/games/trente-et-quarante/coups", "POST", payload)
    # Require the backend to identify the recovered response explicitly.
    assert replay["replayed"] is True, "Trente et Quarante retry was not reported as replayed"
    # Require the same player-scoped round and dealt rows to survive the retry.
    assert replay["round"]["round_id"] == result["round"]["round_id"] and replay["round"]["detail"] == result["round"]["detail"], "Trente et Quarante retry changed the committed result"
