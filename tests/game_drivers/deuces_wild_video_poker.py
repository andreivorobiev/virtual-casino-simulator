"""Catalog-discoverable long-suite driver for issue #92."""


# Exercise one complete Deuces Wild round through only public game endpoints.
def play(client, index):
    # Build three distinct bounded action ids for this long-suite iteration.
    deal_action_id = f"long-dwvp-{index}-deal"
    # Keep hold persistence independently retry-safe from the committed wager.
    holds_action_id = f"long-dwvp-{index}-holds"
    # Keep draw settlement independently retry-safe from both earlier actions.
    draw_action_id = f"long-dwvp-{index}-draw"
    # Deal one low-cost hand through the additive session-bound endpoint.
    started = client.call("/api/v1/games/deuces-wild-video-poker/rounds", "POST", {"action_id": deal_action_id, "wager": 1})
    # Store the server-owned round id for subsequent public actions.
    round_id = started["round"]["round_id"]
    # Persist an empty hold selection so all five cards draw from the deterministic plan.
    client.call(f"/api/v1/games/deuces-wild-video-poker/rounds/{round_id}/holds", "POST", {"action_id": holds_action_id, "holds": []})
    # Complete and ledger-settle the round through the public draw endpoint.
    completed = client.call(f"/api/v1/games/deuces-wild-video-poker/rounds/{round_id}/draw", "POST", {"action_id": draw_action_id})
    # Read the durable settled round returned by the public response envelope.
    settled_round = completed["round"]
    # Verify the public workflow reached its terminal reload-safe phase.
    assert settled_round["phase"] == "settled", "Deuces Wild round did not settle"
    # Verify the contracted outcome key is one of the server's immutable paytable rows.
    assert settled_round["result"] in completed["paytable"], "Deuces Wild result is outside the paytable"
    # Verify the completed round contains exactly one five-card final hand.
    assert len(settled_round["final_hand"]) == 5, "Deuces Wild returned an incomplete hand"
