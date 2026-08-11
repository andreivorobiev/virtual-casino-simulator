# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-discoverable long-suite driver for Casino War issue #82."""


# Exercise one complete round through session-bound public game actions.
def play(client, index):
    # Build a stable idempotency key unique to this long-suite iteration.
    start_action_id = f"long-cw-start-{index}"
    # Read the wallet before the first command so replay checks include token movement.
    balance_before = client.balance()
    # Deal one low-cost round through the public session-bound endpoint.
    started = client.call("/api/v1/games/casino-war/rounds", "POST", {"wager": 1, "action_id": start_action_id})
    # Replay the same action id to prove it resolves the same logical round.
    replayed = client.call("/api/v1/games/casino-war/rounds", "POST", {"wager": 1, "action_id": start_action_id})
    # Preserve the round id for an optional tie decision.
    round_id = started["round"]["round_id"]
    # Require the replay to return the original round without another deal.
    assert replayed["round"]["round_id"] == round_id, "Casino War start replay changed the round"
    # Require the replay to leave the balance at the first command's settled value.
    assert replayed["player"]["balance"] == started["player"]["balance"], "Casino War start replay changed the balance"
    # Continue only when the initial cards require a tie decision.
    if started["round"]["phase"] == "war_decision":
        # Alternate both supported decisions across long-suite iterations.
        decision = "war" if index % 2 == 0 else "surrender"
        # Build a separate idempotency key for the selected decision.
        decision_action_id = f"long-cw-{decision}-{index}"
        # Execute the decision through its public round endpoint.
        completed = client.call(f"/api/v1/games/casino-war/rounds/{round_id}/{decision}", "POST", {"action_id": decision_action_id})
        # Replay the decision so optional war debits and settlement credits cannot duplicate.
        decision_replay = client.call(f"/api/v1/games/casino-war/rounds/{round_id}/{decision}", "POST", {"action_id": decision_action_id})
        # Require the replay to return the original terminal round.
        assert decision_replay["round"]["round_id"] == completed["round"]["round_id"], "Casino War decision replay changed the round"
        # Require the replay to leave the terminal wallet unchanged.
        assert decision_replay["player"]["balance"] == completed["player"]["balance"], "Casino War decision replay changed the balance"
    # Use the initial result when no tie decision was necessary.
    else:
        # Preserve one terminal payload for common settlement assertions.
        completed = started
    # Require every public scenario to finish in the terminal phase.
    assert completed["round"]["phase"] == "settled", "Casino War did not settle"
    # Read the settlement accounting exposed by the game adapter.
    settlement = completed["round"]["settlement"]
    # Require every prepared ledger movement to have a committed ledger row.
    assert settlement["complete"] and settlement["required_actions"] == settlement["committed_actions"], "Casino War settlement is incomplete"
    # Require a positive numeric wallet both before and after this fake-money round.
    assert balance_before >= 0 and completed["player"]["balance"] >= 0, "Casino War returned an invalid play-token balance"
