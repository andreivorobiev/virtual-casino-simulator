# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-discovered long-suite driver for Dragon Tiger after #77 integration."""


# Exercise one complete round and exact retry through public session-bound actions.
def play(client, index):
    # Build a valid caller-stable action identity unique to this long-suite iteration.
    action_id = f"long-dragon-tiger-{index}"
    # Use an even fake-money wager so every possible half-return remains exact.
    request = {"action_id": action_id, "bet": "dragon", "wager": 2}
    # Execute one real-backend ledger-backed round through the additive v1 endpoint.
    result = client.call("/api/v1/games/dragon-tiger/rounds", "POST", request)
    # Retain the immutable settled round for replay comparison.
    settled_round = result["round"]
    # Verify the public action completed instead of leaking an intermediate settlement phase.
    assert settled_round["status"] == "settled", "Dragon Tiger round did not settle"
    # Verify the backend resolved exactly one legal comparison result.
    assert settled_round["winner"] in {"dragon", "tiger", "tie"}, "Dragon Tiger returned an invalid winner"
    # Verify settlement identifies one of the contract's complete outcome classes.
    assert settled_round["outcome"] in {"win", "half_loss", "loss"}, "Dragon Tiger returned an invalid outcome"
    # Retry the identical public action to exercise exactly-once behavior.
    replay = client.call("/api/v1/games/dragon-tiger/rounds", "POST", request)
    # Verify the response explicitly identifies a safe replay.
    assert replay["replayed"] is True, "Dragon Tiger retry was not reported as replayed"
    # Verify replay preserved the entire settled result, including cards and shoe metadata.
    assert replay["round"] == settled_round, "Dragon Tiger retry changed the settled round"
    # Verify replay returned the original committed ledger evidence rather than new events.
    assert replay["ledger"] == result["ledger"], "Dragon Tiger retry changed ledger evidence"
