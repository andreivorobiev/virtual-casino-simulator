"""Catalog-discovered long-suite driver for Four Card Poker against the real backend. (#141)"""


# Exercise one complete deal, its idempotent replay, one decision, and its replay.
def play(client, index):
    # Build one stable deal action identity for this long-suite iteration.
    deal_action = f"long-four-card-poker-deal-{index}"
    # Deal a one-token ante round with no Aces Up side bet.
    started = client.call("/api/v1/games/four-card-poker/rounds", "POST", {"action_id": deal_action, "ante": 1})
    # Replay the deal to prove the opening debit is not duplicated.
    deal_replay = client.call("/api/v1/games/four-card-poker/rounds", "POST", {"action_id": deal_action, "ante": 1})
    # Require the deal replay to report the recovered round.
    assert deal_replay["replayed"] is True and deal_replay["round"]["round_id"] == started["round"]["round_id"], "Four Card Poker deal replay changed the round"
    # Require the dealer cards to stay private before the showdown.
    assert "dealer_cards" not in started["round"] and len(started["round"]["player_cards"]) == 5, "Four Card Poker exposed dealer cards before the showdown"
    # Read the deterministic round id for the decision route.
    round_id = started["round"]["round_id"]
    # Play the round at one time the ante.
    settled = client.call(f"/api/v1/games/four-card-poker/rounds/{round_id}/decisions", "POST", {"action_id": f"long-four-card-poker-play-{index}", "decision": "play", "multiplier": 1})
    # Require the settled round to reveal the dealer and reach a terminal outcome.
    assert settled["round"]["outcome"] in ("player_win", "dealer_win") and "dealer_hand" in settled["round"], "Four Card Poker did not settle the played round"
    # Replay the decision to prove exactly-once settlement.
    replay = client.call(f"/api/v1/games/four-card-poker/rounds/{round_id}/decisions", "POST", {"action_id": f"long-four-card-poker-play-{index}", "decision": "play", "multiplier": 1})
    # Require the decision replay to return the identical settled round.
    assert replay["replayed"] is True and replay["round"]["round_id"] == round_id and replay["round"]["net"] == settled["round"]["net"], "Four Card Poker decision replay changed the result"
