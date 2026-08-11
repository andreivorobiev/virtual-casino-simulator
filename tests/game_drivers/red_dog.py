# Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
# SPDX-License-Identifier: Apache-2.0
"""Catalog-discoverable long-suite driver for Red Dog issue #84."""


# Exercise one complete round through session-bound public game actions.
def play(client, index):
    # Build a stable idempotency key unique to this long-suite iteration.
    deal_action_id = f"long-red-dog-deal-{index}"
    # Read the wallet before the first command so replay checks include token movement.
    balance_before = client.balance()
    # Deal one low-cost opening through the public session-bound endpoint.
    started = client.call("/api/v1/games/red-dog/rounds", "POST", {"action_id": deal_action_id, "wager": 1})
    # Replay the exact opening command to prove no duplicate debit can occur.
    replayed = client.call("/api/v1/games/red-dog/rounds", "POST", {"action_id": deal_action_id, "wager": 1})
    # Preserve the original logical round identity for all following assertions.
    round_id = started["round"]["round_id"]
    # Require the replay to resolve the original round without another deal.
    assert replayed["round"]["round_id"] == round_id, "Red Dog start replay changed the round"
    # Require the replay to preserve the first command's wallet balance.
    assert replayed["player"]["balance"] == started["player"]["balance"], "Red Dog start replay changed the balance"
    # Continue only when the opening spread requires a call-or-raise decision.
    if started["round"]["phase"] == "raise_decision":
        # Alternate both public decision actions across long-suite iterations.
        decision = "raise" if index % 2 == 0 else "call"
        # Build a separate stable action identity for the chosen decision.
        decision_action_id = f"long-red-dog-{decision}-{index}"
        # Complete the third-card action through the public round endpoint.
        completed = client.call(f"/api/v1/games/red-dog/rounds/{round_id}/{decision}", "POST", {"action_id": decision_action_id})
        # Replay the decision so optional raise and payout movements cannot duplicate.
        decision_replay = client.call(f"/api/v1/games/red-dog/rounds/{round_id}/{decision}", "POST", {"action_id": decision_action_id})
        # Require the replay to return the same terminal round identity.
        assert decision_replay["round"]["round_id"] == completed["round"]["round_id"], "Red Dog decision replay changed the round"
        # Require the replay to leave the terminal wallet balance unchanged.
        assert decision_replay["player"]["balance"] == completed["player"]["balance"], "Red Dog decision replay changed the balance"
    # Use the automatically settled pair or consecutive result when no decision was required.
    else:
        # Preserve one terminal payload for common settlement assertions.
        completed = started
    # Require every public game path to reach the terminal phase.
    assert completed["round"]["phase"] == "settled", "Red Dog did not settle"
    # Read the public prepared-versus-committed settlement accounting.
    settlement = completed["round"]["settlement"]
    # Require every prepared wallet movement to have a durable ledger row.
    assert settlement["complete"] and settlement["required_actions"] == settlement["committed_actions"], "Red Dog settlement is incomplete"
    # Require valid nonnegative play-token balances before and after the round.
    assert balance_before >= 0 and completed["player"]["balance"] >= 0, "Red Dog returned an invalid play-token balance"
