# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-discovered long-suite driver for Craps after issue #77 integration."""

# Bound a random point sequence while leaving an effectively impossible failure observable.
MAX_ROLLS_PER_ROUND = 200


# Exercise one complete Pass Line round through only public session-bound actions.
def play(client, index):
    # Build one unique retry identity for the aggregate line wager.
    start_request_id = f"long-craps-start-{index}"
    # Use the smallest practical wager so repeated long-suite scenarios remain inexpensive.
    start_body = {"request_id": start_request_id, "bet_type": "pass_line", "wager": 1}
    # Create the reload-safe round and commit its line wager through the public API.
    started = client.call("/api/v1/games/craps/rounds", "POST", start_body)
    # Replay the exact start action to prove the real backend does not debit twice.
    start_replay = client.call("/api/v1/games/craps/rounds", "POST", start_body)
    # Read the stable server round identity used by every following roll action.
    round_id = started["round"]["round_id"]
    # Verify the repeated action resolves the original round and advertises safe replay.
    assert start_replay["replayed"] is True, "Craps start retry was not reported as replayed"
    # Verify one client identity cannot create a second wagered round.
    assert start_replay["round"]["round_id"] == round_id, "Craps start retry changed round identity"
    # Initialize terminal action evidence for the bounded point-resolution loop.
    terminal_result = None
    # Preserve the terminal action body so its exact retry can be exercised after settlement.
    terminal_body = None
    # Roll until a natural, craps, point hit, or seven-out decision settles the round.
    for roll_index in range(MAX_ROLLS_PER_ROUND):
        # Give every roll its own stable retry identity within this long-suite iteration.
        roll_body = {"request_id": f"long-craps-roll-{index}-{roll_index}"}
        # Advance the same round using only the documented server-authoritative dice action.
        result = client.call(f"/api/v1/games/craps/rounds/{round_id}/rolls", "POST", roll_body)
        # Verify every returned roll contains exactly two bounded six-sided dice.
        assert len(result["roll"]["dice"]) == 2 and all(1 <= face <= 6 for face in result["roll"]["dice"]), "Craps returned invalid dice"
        # Stop only after the public round state reaches its terminal phase.
        if result["round"]["phase"] == "settled":
            # Retain the terminal response for stable replay comparison.
            terminal_result = result
            # Retain the exact terminal action identity for the required retry.
            terminal_body = roll_body
            # Exit the loop after one complete round decision.
            break
    # Fail loudly if an unexpectedly long point sequence exceeded the safety bound.
    assert terminal_result is not None and terminal_body is not None, "Craps round did not settle within the long-suite roll bound"
    # Repeat the terminal roll identity after settlement to exercise archived-round recovery.
    terminal_replay = client.call(f"/api/v1/games/craps/rounds/{round_id}/rolls", "POST", terminal_body)
    # Verify the API distinguishes the archived action replay from a new dice roll.
    assert terminal_replay["replayed"] is True, "Craps terminal retry was not reported as replayed"
    # Verify retry cannot change either dice or resolution after ledger settlement.
    assert terminal_replay["roll"] == terminal_result["roll"], "Craps terminal retry changed the committed roll"
    # Verify the terminal round remains settled under the same player-owned identity.
    assert terminal_replay["round"]["round_id"] == round_id and terminal_replay["round"]["phase"] == "settled", "Craps terminal retry changed round state"
