"""Immutable Crown and Anchor symbol dice rules for issue #133."""

# Identify this module consistently across state, ledger, and contract proposal files.
GAME_ID = "crown_and_anchor"
# Preserve the canonical six-symbol die order used by the traditional table layout.
SYMBOL_ORDER = ("crown", "anchor", "heart", "diamond", "club", "spade")
# Map one-based dice faces to symbols so frontend dice primitives can share the same order.
FACE_TO_SYMBOL = {index + 1: symbol for index, symbol in enumerate(SYMBOL_ORDER)}
# Pay net odds by number of matching dice for one covered symbol.
NET_ODDS_BY_HITS = {1: 1, 2: 2, 3: 3}
# Publish the fixed number of dice rolled for every round.
DICE_COUNT = 3


# Return catalog-ready immutable symbol metadata for state and proposal descriptors.
def symbol_catalog() -> list[dict]:
    # Build one row per legal wager target in canonical table order.
    return [{"id": symbol, "face": index + 1, "paytable": dict(NET_ODDS_BY_HITS)} for index, symbol in enumerate(SYMBOL_ORDER)]

