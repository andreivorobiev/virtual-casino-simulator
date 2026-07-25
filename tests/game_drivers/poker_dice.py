"""Catalog-discovered long-suite driver for Poker Dice on the shared settlement core. (#151)"""


# Exercise one complete public roll and its idempotent retry.
def play(client, index):
    # Build one stable request identity for this long-suite iteration.
    request_id = f"long-poker-dice-{index}"
    # Stake the smallest whole-roll wager the table accepts.
    payload = {"request_id": request_id, "stake": 1}
    # Execute one real-backend ledger-backed roll through the additive v1 action.
    result = client.call("/api/v1/games/poker-dice/rolls", "POST", payload)
    # Require exactly five committed dice within the six-face range.
    dice = result["round"]["detail"]["dice"]
    # Require the roll to be five bounded face indices.
    assert len(dice) == 5 and all(0 <= die <= 5 for die in dice), "Poker Dice returned an invalid roll"
    # Require the outcome to be one of the two settled states.
    assert result["round"]["outcome"] in ("win", "lose"), "Poker Dice returned an unknown outcome"
    # Retry the identical public action to prove exactly-once replay behavior.
    replay = client.call("/api/v1/games/poker-dice/rolls", "POST", payload)
    # Require the backend to identify the recovered response explicitly.
    assert replay["replayed"] is True, "Poker Dice retry was not reported as replayed"
    # Require the same player-scoped round and committed dice to survive the retry.
    assert replay["round"]["round_id"] == result["round"]["round_id"] and replay["round"]["detail"] == result["round"]["detail"], "Poker Dice retry changed the committed result"
