"""Catalog-discovered long-suite driver for Big Six Wheel after #110/#77 integration."""

# Exercise one complete round through only public session-bound actions.
def play(client, index):
    # Build a unique retry identity for this long-suite iteration.
    request_id = f"long-big-six-{index}"
    # Cover every outcome so the round always exercises a settlement credit.
    wagers = {"one": 1, "two": 1, "five": 1, "ten": 1, "twenty": 1, "joker": 1, "crest": 1}
    # Execute one real-backend ledger-backed spin through the additive v1 action.
    result = client.call("/api/v1/games/big-six-wheel/spins", "POST", {"client_request_id": request_id, "wagers": wagers})
    # Verify the backend returned one legal settled wheel index.
    assert 0 <= result["round"]["result_index"] < 54, "Big Six result index left the wheel"
    # Verify every covered spin returns a positive stake-plus-winnings credit.
    assert result["round"]["total_return"] > 0, "Big Six all-outcome wager did not settle a winner"
    # Retry the same action identity to exercise exactly-once behavior through the real backend.
    replay = client.call("/api/v1/games/big-six-wheel/spins", "POST", {"client_request_id": request_id, "wagers": wagers})
    # Verify the public response explicitly identifies the safe replay.
    assert replay["replayed"] is True, "Big Six retry was not reported as replayed"
    # Verify the same round identity survives the retry.
    assert replay["round"]["round_id"] == result["round"]["round_id"], "Big Six retry changed round identity"
