"""Focused Caribbean Stud driver proposal for #77 long-suite integration."""


# Exercise one complete round and exact retry through public session-bound actions.
def play(client, index):
    # Build a valid caller-stable deal identity unique to this driver iteration.
    deal_action_id = f"driver-caribbean-stud-deal-{index}"
    # Use a small fake-token ante to keep long-suite balances stable.
    deal_request = {"action_id": deal_action_id, "ante": 2}
    # Execute one real-backend ante-backed deal through the additive v1 endpoint.
    deal_result = client.call("/api/v1/games/caribbean-stud/rounds", "POST", deal_request)
    # Retain the active decision round for a later action route.
    round_item = deal_result["round"]
    # Verify the public action reached the player decision phase.
    assert round_item["phase"] == "decision", "Caribbean Stud deal did not reach decision phase"
    # Retry the identical deal to exercise ante exactly-once behavior.
    deal_replay = client.call("/api/v1/games/caribbean-stud/rounds", "POST", deal_request)
    # Verify the response explicitly identifies a safe replay.
    assert deal_replay["replayed"] is True, "Caribbean Stud deal retry was not reported as replayed"
    # Verify replay preserved the active round and ante proof.
    assert deal_replay["round"] == round_item, "Caribbean Stud deal retry changed the round"
    # Branch between fold-only and call-settlement paths.
    if index % 2:
        # Build a fold action identity for the active round.
        fold_request = {"action_id": f"driver-caribbean-stud-fold-{index}"}
        # Forfeit the ante without revealing dealer hole cards.
        folded = client.call(f"/api/v1/games/caribbean-stud/rounds/{round_item['round_id']}/fold", "POST", fold_request)
        # Verify the terminal outcome is the documented fold.
        assert folded["round"]["outcome"] == "fold", "Caribbean Stud fold returned an invalid outcome"
        # Verify replay keeps the same terminal fold result.
        assert client.call(f"/api/v1/games/caribbean-stud/rounds/{round_item['round_id']}/fold", "POST", fold_request)["round"] == folded["round"], "Caribbean Stud fold retry changed the round"
    # Exercise the call path on alternating rounds.
    else:
        # Build a call action identity for the active round.
        call_request = {"action_id": f"driver-caribbean-stud-call-{index}"}
        # Commit the fixed call wager and settle the showdown.
        called = client.call(f"/api/v1/games/caribbean-stud/rounds/{round_item['round_id']}/call", "POST", call_request)
        # Verify the call produced one documented terminal outcome.
        assert called["round"]["outcome"] in {"dealer_not_qualified", "player_win", "push", "dealer_win"}, "Caribbean Stud call returned an invalid outcome"
        # Verify replay keeps the same terminal showdown result.
        assert client.call(f"/api/v1/games/caribbean-stud/rounds/{round_item['round_id']}/call", "POST", call_request)["round"] == called["round"], "Caribbean Stud call retry changed the round"
