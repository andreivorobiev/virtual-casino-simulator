# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-discoverable long-suite driver for issue #88."""


# Exercise one complete retry-safe Sic Bo round through public game actions.
def play(client, index):
    # Read authenticated player-owned state before moving any play tokens.
    initial = client.call("/api/v1/games/sic-bo/state")
    # Verify the public rules catalog exposes all fifty classic positions.
    assert len(initial["bets"]) == 50, "Sic Bo did not expose fifty betting positions"
    # Build one stable idempotency key unique to this long-suite iteration.
    action_id = f"long-sic-bo-{index}"
    # Cover both a range and exact-total position in one aggregate ledger wager.
    request = {"action_id": action_id, "wagers": {"small": 1, "total:10": 1}}
    # Settle the authoritative three-die round through the public session-bound endpoint.
    first = client.call("/api/v1/games/sic-bo/rounds", "POST", request)
    # Retry the exact same atomic action to prove replay safety under the long suite.
    replay = client.call("/api/v1/games/sic-bo/rounds", "POST", request)
    # Verify the server returned exactly three ordinary die faces.
    assert len(first["round"]["dice"]) == 3, "Sic Bo returned an incomplete dice result"
    # Verify every authoritative die face stays inside the standard six-face range.
    assert all(1 <= face <= 6 for face in first["round"]["dice"]), "Sic Bo returned an invalid die face"
    # Verify the retry cannot roll new dice or create another logical round.
    assert replay["round"]["round_id"] == first["round"]["round_id"], "Sic Bo retry changed the round identity"
    # Verify the recovered response preserves the exact authoritative dice result.
    assert replay["round"]["dice"] == first["round"]["dice"], "Sic Bo retry changed the dice"
    # Verify the response marks the repeated action as an idempotent replay.
    assert replay["replayed"] is True, "Sic Bo retry was not reported as a replay"
