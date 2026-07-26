"""Immutable Color Wheel rules: segment layout, bet catalog, and payout multipliers. (#152)

The wheel has twenty fixed segments arranged so red and black alternate around three green house
segments and a single gold jackpot segment. Every payout multiplier is a total return that already
includes the returned stake, and each is chosen so the expected return stays below one: red and black
pay even money at 8 of 20 segments (0.80 expected), green pays five to one at 3 of 20 (0.90), and gold
pays fifteen to one at 1 of 20 (0.80). All amounts are play tokens with no cash value.
"""

# Bind every ledger and state dimension to this fixed game identity.
GAME_ID = "color_wheel"
# Fix the twenty-segment colour layout so the wheel render and the resolver agree exactly.
SEGMENTS = (
    "red", "black", "red", "black", "green", "red", "black", "red", "black", "gold",
    "red", "black", "red", "black", "green", "red", "black", "red", "black", "green",
)
# Map each colour bet to its total-return multiplier (stake included).
PAYOUTS = {"red": 2, "black": 2, "green": 6, "gold": 16}
# Bound one wager so a single spin can never stake an absurd amount.
MAX_STAKE = 100_000


# Publish the player-facing bet catalog: each colour, its count, and its multiplier.
def bet_catalog() -> dict:
    # Report the segment count and multiplier for each colour so the client can render odds honestly.
    return {"segments": len(SEGMENTS), "bets": [{"color": color, "segments": SEGMENTS.count(color), "multiplier": PAYOUTS[color]} for color in ("red", "black", "green", "gold")]}
