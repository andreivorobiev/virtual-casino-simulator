"""Catalog-ready public-action driver proposal for Texas Hold'em issue #95."""


# Exercise one complete fixed-limit hand through only documented public routes.
def play(client, index):
    # Build a unique retry-safe start id for this long-suite iteration.
    start_action_id = f"long-thpt-start-{index}"
    # Start one low-cost hand through the session-bound public endpoint.
    started = client.call("/api/v1/games/texas-holdem-practice-table/hands", "POST", {"action_id": start_action_id, "base_wager": 1})
    # Repeat the exact start payload through the real registered route.
    replayed_start = client.call("/api/v1/games/texas-holdem-practice-table/hands", "POST", {"action_id": start_action_id, "base_wager": 1})
    # Verify the retry reused both the logical hand and wallet result.
    assert (replayed_start["replayed"], replayed_start["hand"]["hand_id"], replayed_start["player"]["balance"]) == (True, started["hand"]["hand_id"], started["player"]["balance"]), "Texas Hold'em start retry changed the hand or balance"
    # Retain the server hand identifier for every later action route.
    hand = replayed_start["hand"]
    # Call through every fixed-limit street until the server settles the hand.
    for street_index in range(4):
        # Stop early if a deterministic future opponent policy ends the hand.
        if hand.get("phase") == "settled":
            # Leave the loop after terminal settlement.
            break
        # Build one unique human action id for this hand and street.
        action_id = f"long-thpt-call-{index}-{street_index}"
        # Bind the observed phase into one immutable retry payload.
        action_body = {"action_id": action_id, "action": "call", "expected_phase": hand["phase"]}
        # Apply one public human call plus all immediate server responses.
        completed = client.call(f"/api/v1/games/texas-holdem-practice-table/hands/{hand['hand_id']}/actions", "POST", action_body)
        # Repeat the exact decision against the same public action route.
        replayed_action = client.call(f"/api/v1/games/texas-holdem-practice-table/hands/{hand['hand_id']}/actions", "POST", action_body)
        # Verify retrying cannot advance the phase, pot, or wallet a second time.
        assert (replayed_action["replayed"], replayed_action["hand"]["phase"], replayed_action["hand"]["pot"], replayed_action["player"]["balance"]) == (True, completed["hand"]["phase"], completed["hand"]["pot"], completed["player"]["balance"]), "Texas Hold'em decision retry changed table or wallet state"
        # Retain the latest server-authoritative hand for the next iteration.
        hand = replayed_action["hand"]
    # Verify the public-action sequence reached fully reconciled settlement.
    assert hand["phase"] == "settled", "Texas Hold'em practice hand did not settle"
    # Verify one human and three server-managed opponents remained in the response.
    assert len(hand["seats"]) == 4, "Texas Hold'em practice table returned an incomplete seat set"
    # Verify all five community cards were revealed at showdown.
    assert len(hand["community_cards"]) == 5, "Texas Hold'em showdown returned an incomplete board"
    # Verify terminal wallet settlement is explicitly complete.
    assert hand["settlement"]["complete"], "Texas Hold'em ledger settlement remained pending"
