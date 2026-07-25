"""Catalog-discovered long-suite driver for Mississippi Stud against the real backend. (#143)"""


# Exercise one complete deal, its replay, three street bets, and a decision replay.
def play(client, index):
    # Build one stable deal action identity for this long-suite iteration.
    deal_action = f"long-mississippi-stud-deal-{index}"
    # Deal a one-token ante round.
    started = client.call("/api/v1/games/mississippi-stud/rounds", "POST", {"action_id": deal_action, "ante": 1})
    # Replay the deal to prove the ante debit is not duplicated.
    deal_replay = client.call("/api/v1/games/mississippi-stud/rounds", "POST", {"action_id": deal_action, "ante": 1})
    # Require the deal replay to report the recovered round.
    assert deal_replay["replayed"] is True and deal_replay["round"]["round_id"] == started["round"]["round_id"], "Mississippi Stud deal replay changed the round"
    # Require the community cards to stay private before any street resolves.
    assert started["round"]["community_revealed"] == [] and len(started["round"]["hole_cards"]) == 2, "Mississippi Stud exposed community cards before the first street"
    # Read the deterministic round id for the decision route.
    round_id = started["round"]["round_id"]
    # Bet all three streets at one time the ante.
    settled = None
    # Place one street bet per betting street.
    for street in range(1, 4):
        # Post the street bet and capture the latest response.
        settled = client.call(f"/api/v1/games/mississippi-stud/rounds/{round_id}/decisions", "POST", {"action_id": f"long-mississippi-stud-s{street}-{index}", "decision": "bet", "multiplier": 1})
    # Require the settled round to reach a terminal outcome with all community cards revealed.
    assert settled["round"]["outcome"] in ("win", "push", "lose") and len(settled["round"]["community_revealed"]) == 3, "Mississippi Stud did not settle the completed hand"
    # Replay the final street bet to prove exactly-once settlement.
    replay = client.call(f"/api/v1/games/mississippi-stud/rounds/{round_id}/decisions", "POST", {"action_id": f"long-mississippi-stud-s3-{index}", "decision": "bet", "multiplier": 1})
    # Require the decision replay to return the identical settled result.
    assert replay["replayed"] is True and replay["round"]["net"] == settled["round"]["net"], "Mississippi Stud decision replay changed the result"
